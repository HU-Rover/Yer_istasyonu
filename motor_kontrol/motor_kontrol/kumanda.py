import rclpy
import serial 
from rover_msgs.msg import ControllerMsg
from rclpy.node import Node

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

class JoySubscriber(Node):
    def __init__(self):
        super().__init__('joy_subscriber')
        self.publisher = self.create_publisher(ControllerMsg, 'joystick_cmd', 10)
        self.timer = self.create_timer(0.1, self.run)  # 10 Hz
        self.get_logger().info("JoySubscriber node started")

    def run(self):
        try:
            line = ser.readline().decode().strip()
            self.get_logger().info(f"Serial Data: {line}")
            channel_values = line.split()

            if len(channel_values) >= 2:
                msg = ControllerMsg()
                msg.saghiz = float(channel_values[0])
                msg.solhiz = float(channel_values[1])
                self.publisher.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Error reading/parsing serial: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = JoySubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down JoySubscriber node')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

