from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Launch the joy_node from the joy package
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen'
        ),
        # Launch the pub2 node from the motor_kontrol package
        Node(
            package='motor_kontrol',
            executable='pub',
            name='pub2_node',
            output='screen'
        )
    ])

