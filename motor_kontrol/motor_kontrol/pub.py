import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from rover_msgs.msg import ControllerMsg
from std_msgs.msg import String
from geometry_msgs.msg import Vector3
import math

class JoySubscriber(Node):
    def __init__(self):
        super().__init__('joy_subscriber')

        # Subscribe to joystick and keyboard topics
        self.subscription = self.create_subscription(
            Joy,
            '/joy',
            self.listener_callback,
            10
        )
        self.keyboard_subscription = self.create_subscription(
            Vector3,
            '/keyboard_input',
            self.keyboard_callback,
            10
        )


        # Publisher for ControllerMsg topic
        self.publisher = self.create_publisher(ControllerMsg, 'joystick_cmd', 10)
        self.joy_msg = ControllerMsg()

    def keyboard_callback(self, msg: Vector3):
        self.joy_msg.kp = msg.x
        self.joy_msg.ki = msg.y
        self.joy_msg.kd = msg.z


    def listener_callback(self, msg: Joy):
        # Process joystick inputs
        x = msg.axes[0] * 0.38      # X axis
        throttle = (msg.axes[1])
        throttle = max(-0.8, min(throttle, 0.8))
        x = max(-0.25, min(x, 0.25))
        
        light = 1 if msg.axes[3] > 0.2 else 0 if msg.axes[3] < -0.2 else -1

        # Create and populate the ControllerMsg

        self.joy_msg.solhiz = throttle - (x*2)
        self.joy_msg.saghiz = throttle + (x*2)
        self.joy_msg.light = int(light)
        # Use the computed yaw from magnetometer data

        # Publish the message
        self.publisher.publish(self.joy_msg)
        self.get_logger().info(
            f'Published: saghiz={throttle - x}, solhiz={throttle + x}, light={light} '
        )

def main(args=None):
    rclpy.init(args=args)
    node = JoySubscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

