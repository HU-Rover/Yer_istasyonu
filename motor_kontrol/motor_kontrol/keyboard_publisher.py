import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
import sys
import termios
import tty

class KeyboardPublisher(Node):
    def __init__(self):
        super().__init__('keyboard_publisher')
        self.publisher = self.create_publisher(Vector3, '/keyboard_input', 10)
        self.get_logger().info('Keyboard Publisher Node Started. Enter three float values separated by spaces.')

    def get_input(self):
        """Reads a line of input from the keyboard."""
        return input("Enter three floats: ")

    def run(self):
        while rclpy.ok():
            try:
                data = self.get_input()
                floats = [float(x) for x in data.split()]
                if len(floats) == 3:
                    msg = Vector3()
                    msg.x, msg.y, msg.z = floats
                    self.publisher.publish(msg)
                    self.get_logger().info(f'Published: {msg.x}, {msg.y}, {msg.z}')
                else:
                    self.get_logger().warn('Please enter exactly three float values.')
            except ValueError:
                self.get_logger().error('Invalid input. Please enter valid float values.')


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

