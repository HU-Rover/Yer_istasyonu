import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray
import serial
import serial.tools.list_ports
from rover_msgs.msg import ControllerMsg
from rover_msgs.msg import EncoderMsg
from std_msgs.msg import Int8  
import math
import numpy as np
from math import sqrt
import serial
import threading

BAUD_RATE = 115200  

class MinimalSubscriber(Node):
    def __init__(self):
        super().__init__('sub_node')
        self.subscription = self.create_subscription(ControllerMsg,'joystick_cmd',self.listener_callback, 10)
        
        self.publisher = self.create_publisher(EncoderMsg,"encoder_data",10)
        self.encoder_msg = EncoderMsg()
        
        
        self.SERIAL_PORT_SAG_ON = '/dev/ttyACM0'
        self.SERIAL_PORT_SOL_ON = '/dev/ttyACM1'
        self.SERIAL_PORT_SOL_ARKA = '/dev/ttyACM2'
        self.SERIAL_PORT_SAG_ARKA = '/dev/ttyACM3'  
        
        for port in serial.tools.list_ports.comports():
            
            match(port.serial_number):
                case '002400293233510F39363634':
                    self.SERIAL_PORT_SOL_ARKA = port.device
                case '002400283233511339363634':
                    self.SERIAL_PORT_SOL_ON = port.device
                case '005500373235511238363730':
                    self.SERIAL_PORT_SAG_ON = port.device
                case '0049002A3235511138363730':
                    self.SERIAL_PORT_SAG_ARKA = port.device

        
        
            
        
        self.stm_sol_on =  serial.Serial(port=self.SERIAL_PORT_SOL_ON,baudrate=BAUD_RATE,timeout=0.1)
       
        self.stm_sag_on =  serial.Serial(port=self.SERIAL_PORT_SAG_ON,baudrate=BAUD_RATE,timeout=0.1)
                
        self.stm_sol_arka =  serial.Serial(port=self.SERIAL_PORT_SOL_ARKA,baudrate=BAUD_RATE,timeout=0.1)
        
        self.stm_sag_arka =  serial.Serial(port=self.SERIAL_PORT_SAG_ARKA,baudrate=BAUD_RATE,timeout=0.1)
        
        self.sag_on_hiz = 0.0
        self.sag_arka_hiz = 0.0
        self.sol_arka_hiz = 0.0
        self.sol_on_hiz = 0.0


    def listener_callback(self, msg):
    
        mode = msg.mode
        
        Kp = msg.kp
        Kd = msg.kd
        Ki = msg.ki
        
        if self.stm_sag_arka.in_waiting > 0:
            raw = self.stm_sag_arka.readline()

            clean = raw.replace(b'\x00', b'')

            text = clean.decode('utf-8', errors='ignore').strip()
            
            self.sag_arka_hiz = float(text)

            
        if self.stm_sag_on.in_waiting > 0:
            raw2 = self.stm_sag_on.readline()

            clean2 = raw2.replace(b'\x00', b'')

            text2 = clean2.decode('utf-8', errors='ignore').strip()
            
            self.sag_on_hiz = float(text2)
            

            
        if self.stm_sol_on.in_waiting > 0:
            raw = self.stm_sol_on.readline()

            clean = raw.replace(b'\x00', b'')

            text = clean.decode('utf-8', errors='ignore').strip()
            
            self.sol_on_hiz = float(text)

          
        if self.stm_sol_arka.in_waiting > 0:
            raw = self.stm_sol_arka.readline()

            clean = raw.replace(b'\x00', b'')

            text = clean.decode('utf-8', errors='ignore').strip()
            
            self.sol_arka_hiz = float(text)
        
        
        self.encoder_msg.sag_on = self.sag_on_hiz
        self.encoder_msg.sag_arka = self.sag_arka_hiz
        self.encoder_msg.sol_on = self.sol_on_hiz
        self.encoder_msg.sol_arka = self.sol_arka_hiz
        
        self.publisher.publish(self.encoder_msg)
        

        
        if (mode == 2):
                    
            saghiz = f"2 {msg.saghiz:.4f}"
            solhiz = f"2 {msg.solhiz:.4f}"
                    
            self.stm_sag_arka.write(saghiz.encode('utf-8'))
            self.stm_sag_on.write(saghiz.encode('utf-8'))
            self.stm_sol_on.write(solhiz.encode('utf-8'))
            self.stm_sol_arka.write(solhiz.encode('utf-8'))
            #self.get_logger().info(f'Published: solhiz={msg.solhiz:.4f}, saghiz={msg.saghiz:.4f}')
                    
                
        elif(mode == 0):
            data = f"0"
                
            self.stm_sag_on.write(data.encode('utf-8'))
            self.stm_sag_arka.write(data.encode('utf-8'))
            self.stm_sol_arka.write(data.encode('utf-8'))
            self.stm_sol_on.write(data.encode('utf-8'))
                    
        
        
def main(args=None):
    rclpy.init(args=args)
    node = MinimalSubscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
