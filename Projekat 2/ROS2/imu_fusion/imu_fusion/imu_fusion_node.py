import rclpy
from rclpy.node import Node

import json
import numpy as np

from std_msgs.msg import String
from geometry_msgs.msg import Quaternion

from ahrs.filters import Madgwick


class IMUFusionNode(Node):

    def __init__(self):
        super().__init__('imu_fusion_node')

        # Subscriber
        self.subscription = self.create_subscription(
            String,
            '/sensorData',
            self.callback,
            10
        )

        # Publisher
        self.publisher = self.create_publisher(
            Quaternion,
            '/imu/orientation',
            10
        )

        # Madgwick filter
        self.filter = Madgwick()
        self.quat = np.array([1.0, 0.0, 0.0, 0.0])  # w, x, y, z

        self.get_logger().info("IMU Fusion Node started")

    def normalize(self, v):
        norm = np.linalg.norm(v)
        if norm == 0:
            return v
        return v / norm

    def callback(self, msg):
        try:
            data = json.loads(msg.data)

            acc = np.array([
                data['acc']['x'],
                data['acc']['y'],
                data['acc']['z']
            ], dtype=float)

            gyro = np.array([
                data['gyro']['x'],
                data['gyro']['y'],
                data['gyro']['z']
            ], dtype=float)

            mag = np.array([
                data['mag']['x'],
                data['mag']['y'],
                data['mag']['z']
            ], dtype=float)

            # 🔧 NORMALIZATION (IMPORTANT)
            acc = acc / 16384.0
            gyro = np.deg2rad(gyro / 131.0)  # assuming typical MPU scaling
            mag = self.normalize(mag)

            # ❗ update filter
            self.quat = self.filter.updateMARG(
                self.quat,
                gyr=gyro,
                acc=acc,
                mag=mag
            )

            # Madgwick returns [w, x, y, z]
            q = Quaternion()
            q.w = float(self.quat[0])
            q.x = float(self.quat[1])
            q.y = float(self.quat[2])
            q.z = float(self.quat[3])

            self.publisher.publish(q)

        except Exception as e:
            self.get_logger().error(f"Parse/Fusion error: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = IMUFusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
