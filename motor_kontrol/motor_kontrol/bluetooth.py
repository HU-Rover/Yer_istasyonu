import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
import sys
import termios
import tty
from rover_msgs.msg import ControllerMsg
import serial

ser = serial.Serial('/dev/ttyUSB0', 115200)

class KeyboardPublisher(Node):
    def __init__(self):
        super().__init__('keyboard_publisher')
        self.publisher = self.create_publisher(ConteollerMsg, '/keyboard_input', 10)
        self.get_logger().info('Keyboard Publisher Node Started. Enter three float values separated by spaces.')
        self.msg = ControllerMsg()
        self.timer = self.create_timer(timer_period, self.run)

    def run(self):
        x = ser.readline().decode('utf-8').strip()
        y = ser.readline().decode('utf-8').strip()
        self.msg.throttle = x
        self.msg.y = y
        self.publisher.publish(self.msg)
        
        self.create_timer


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardPublisher()
    try:
        node.run()
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Keyboard Publisher')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

