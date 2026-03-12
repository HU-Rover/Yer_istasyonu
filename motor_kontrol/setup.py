from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'motor_kontrol'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omer',
    maintainer_email='kapanomer2006@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
		"pub= motor_kontrol.pub:main",
		"pub2= motor_kontrol.keyboard_publisher:main",
		"bluetooth = motor_kontrol.bluetooth:main",
		"kumanda = motor_kontrol.kumanda:main",
		"uzaktan_kumanda = motor_kontrol.uzaktan_kumanda:main",
		"kinematiksiz_robot_kol2 = motor_kontrol.kinematiksiz_robot_ko2l:main"
        ],
    },
)
