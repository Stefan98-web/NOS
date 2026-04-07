import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import json
import threading


class SerialNode(Node):
    def __init__(self):
        super().__init__('serial_node')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 9600)

        port = self.get_parameter('port').get_parameter_value().string_value
        baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value

        self.publisher_ = self.create_publisher(String, 'sensorData', 10)

        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.get_logger().info(f"Connected to {port} @ {baudrate}")
        except Exception as e:
            self.get_logger().error(f"Serial connection failed: {e}")
            raise

        self.thread = threading.Thread(target=self.read_serial_loop, daemon=True)
        self.thread.start()

    def read_serial_loop(self):
        buffer = ""

        while rclpy.ok():
            try:
                chunk = self.ser.read(1024).decode(errors='ignore')
                buffer += chunk

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_line(line.strip())

            except Exception as e:
                self.get_logger().error(f"Read error: {e}")

    def process_line(self, line):
        if not line:
            return

        try:
            data = json.loads(line)

            msg = String()
            msg.data = json.dumps(data)

            self.publisher_.publish(msg)

        except json.JSONDecodeError:
            self.get_logger().warn(f"Invalid JSON: {line}")


def main(args=None):
    rclpy.init(args=args)
    node = SerialNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
