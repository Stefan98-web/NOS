import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Quaternion
import asyncio
import websockets
import json
import threading


class CubeWebServer(Node):

    def __init__(self):
        super().__init__('cube_web_server')

        self.latest_quat = {
            "x": 0,
            "y": 0,
            "z": 0,
            "w": 1
        }

        self.sub = self.create_subscription(
            Quaternion,
            '/imu/orientation',
            self.cb,
            10
        )

        # start websocket server in thread
        thread = threading.Thread(target=self.start_server, daemon=True)
        thread.start()

        self.get_logger().info("Web server running on ws://localhost:8000")

    def cb(self, msg):
        self.latest_quat = {
            "x": msg.x,
            "y": msg.y,
            "z": msg.z,
            "w": msg.w
        }

    async def handler(self, websocket):
        while True:
            await websocket.send(json.dumps(self.latest_quat))
            await asyncio.sleep(0.01)  # 100Hz

    def start_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def runner():
            async with websockets.serve(self.handler, "0.0.0.0", 8000):
                await asyncio.Future()  # keep server alive forever

        loop.run_until_complete(runner())


def main():
    rclpy.init()
    node = CubeWebServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
