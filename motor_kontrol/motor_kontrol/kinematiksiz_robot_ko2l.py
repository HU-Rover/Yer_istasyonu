import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray
import serial
from rover_msgs.msg import ControllerMsg
from rover_msgs.msg import RobotKolMsg
from std_msgs.msg import Int8  # Add at top  # Make sure this custom message is built correctly
import math
import numpy as np
from math import sqrt



class SerialJoystickPublisher(Node):
    def __init__(self):
        super().__init__('serial_joystick_publisher')

        # Publisher for joystick commands
        self.yurur_sistem_publisher_ = self.create_publisher(ControllerMsg, 'joystick_cmd', 10)
        self.robot_kol_publisher_ = self.create_publisher(RobotKolMsg, 'robot_kol', 10)
        self.mode_publisher = self.create_publisher(Int8, 'vehicle_mode', 10)
        self.joy_msg = ControllerMsg()
        self.mode_msg = Int8()
        self.kol_msg = RobotKolMsg()
        self.previous_message = 0
        self.published = 1
        self.x = 0.5
        self.y = 0.5
        self.z = 0.5
        self.ustkol = 0.357
        self.altkol = 0.3

        # Open serial port
        self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        self.get_logger().info('Opened /dev/ttyUSB0')

        # Timer to read serial input periodically
        self.create_timer(0.1, self.read_serial)
    
    def kinematik_hesaplama(self, x, y, z):
        #Bilek pozisyonunun hesaplanması
        
        if (x == 0 and y == 0): 
    	    return

        hipotenus_xy = sqrt(x * x + y * y + 0.15)

        # Toplam uzunluk hesaplanıyor
        c = sqrt(hipotenus_xy + z * z )
        R = self.ustkol + self.altkol
        r = abs(self.ustkol - self.altkol)

        #Kinematik tanım alanı kontrolü
        if (c > R or c < r):
            self.get_logger().info('degerler alanin disinda')
            return
    

        # Z eksenine bağlı olarak Teta açısının hesaplanması
        Teta = 0 if z == 0 else math.asin(z / c) * (180 / np.pi)

        # Yörünge açısını hesapla
        base_angle = math.atan2(y, x) * (180/np.pi)

        # Dirsek ve Omuz açılarının hesaplanması
        cos_Dirsek = max(-1.0, min(1.0, (pow(self.ustkol, 2) + pow(self.altkol, 2) - pow(c, 2)) / (2 * self.ustkol * self.altkol)))
        cos_Beta = max(-1.0, min(1.0, (pow(self.ustkol, 2) + pow(c, 2) - pow(self.altkol, 2)) / (2 * self.ustkol * c)))


        if (abs(cos_Dirsek) > 1 or abs(cos_Beta) > 1): 
    	    return

        #Dirsek açısını hesapla
        dirsek_angle = math.acos(cos_Dirsek) * (180/np.pi)
       # Omuz açısını hesapla
        Beta = math.acos(cos_Beta) * (180/np.pi)
        shoulder_angle = Teta + Beta
       # Bilek açısını hesapla
        wrist_angle = (shoulder_angle + dirsek_angle)
        
        
        self.kol_msg.base = int(base_angle)
        self.kol_msg.shoulder = int(shoulder_angle)
        self.kol_msg.dirsek = int(dirsek_angle)
        self.kol_msg.gripper = int(wrist_angle)
        
        self.robot_kol_publisher_.publish(self.kol_msg)
     
    def read_serial(self):
        if self.ser.in_waiting > 0:
            line = self.ser.readline().decode('utf-8').strip()
            try:
                numbers = list(map(int, line.split()))
                if len(numbers) < 6:
                    self.get_logger().warn(f'Incomplete data: {line}')
                    return

                # Rearranged indexing
                yonelim = (numbers[0] - 1500)/2500   # 1st value
                throttle = (numbers[1] - 1500)/625
                mode2 = numbers[9]     #robot kol moduna gecmek icin 10. kanal
                mode = numbers[5]      # 6th value
                if(mode2 == 2000 ):
                    self.mode_msg.data = 2
                elif(mode == 2000):
                    self.mode_msg.data = 0
                elif(mode == 1000):
                    self.mode_msg.data = 1    
                
                if(self.previous_message != self.mode_msg.data):
                    self.mode_publisher.publish(self.mode_msg)
                
                self.previous_message = self.mode_msg.data
                    

                # Fill your custom ControllerMsg
                self.joy_msg.solhiz = float(throttle - (yonelim*2) ) 
                self.joy_msg.saghiz = float(throttle + (yonelim*2) ) 

                # Publish the message
                if not (self.mode_msg.data ==2):
                    self.yurur_sistem_publisher_.publish(self.joy_msg)
                    self.get_logger().info(
                    f'Published: solhiz={self.joy_msg.solhiz}, saghiz={self.joy_msg.saghiz}'
                )
                
                elif(self.mode_msg.data == 2):
                    degisimx =  (numbers[0] - 1500) *0.5
                    degisimy =  (numbers[3] - 1500) *0.5
                    degisimz =  (numbers[1] -1500)*0.5                       
                    #self.kinematik_hesaplama(self.x, self.y , self.z)
                    
                    self.get_logger().info(
                    f'Published: degisimx={degisimx} , y={degisimy} , z={degisimz} '
                )
                    self.kol_msg.base = int(degisimx)
                    self.kol_msg.shoulder = int(degisimy)
                    self.kol_msg.dirsek = int(degisimz)
                    self.robot_kol_publisher_.publish(self.kol_msg)
                    
                     
            except ValueError:
                self.get_logger().warn(f'Invalid data format: {line}')

def main(args=None):
    rclpy.init(args=args)
    node = SerialJoystickPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

