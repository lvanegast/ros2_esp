#!/usr/bin/env python3
import sys
import select
import termios
import tty
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float64MultiArray

msg = """
================================================================
Control Holonómico + Brazo Robótico (Mobile Manipulator)
================================================================
Base Mecanum (Desplazamiento Omnidireccional):
    w/s : Avanzar / Retroceder
    a/d : Desplazamiento lateral (Strafe Izq / Der)
    q/e : Rotar sobre el eje (Giro Antihorario / Horario)
    espacio : Detener la base

Brazo Articulado:
    i/k : Hombro arriba / abajo (arm_joint_2)
    j/l : Cintura rotar izq / der (arm_joint_1)
    u/o : Codo flexionar / extender (arm_joint_3)
    m/, : Muñeca arriba / abajo (arm_joint_4)
    g/h : Abrir / Cerrar Pinza

CTRL-C para salir
================================================================
"""

class TeleopNode(Node):
    def __init__(self):
        super().__init__('teleop_mobile_manipulator')
        self.cmd_pub = self.create_publisher(TwistStamped, '/mecanum_controller/reference', 10)
        self.arm_pub = self.create_publisher(Float64MultiArray, '/arm_controller/commands', 10)
        self.gripper_pub = self.create_publisher(Float64MultiArray, '/gripper_controller/commands', 10)

        # Posiciones articulares iniciales
        self.arm_positions = [0.0, 0.0, 0.0, 0.0]
        self.gripper_pos = 0.015

        self.get_logger().info("Teleoperador listo. Usa el teclado para controlar el robot.")

    def publish_twist(self, vx, vy, wz):
        t = TwistStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_footprint'
        t.twist.linear.x = vx
        t.twist.linear.y = vy
        t.twist.angular.z = wz
        self.cmd_pub.publish(t)

    def publish_arm(self):
        msg = Float64MultiArray()
        msg.data = [float(p) for p in self.arm_positions]
        self.arm_pub.publish(msg)

    def publish_gripper(self):
        msg = Float64MultiArray()
        msg.data = [float(self.gripper_pos)]
        self.gripper_pub.publish(msg)

def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def main():
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = TeleopNode()
    print(msg)

    vx, vy, wz = 0.0, 0.0, 0.0
    speed = 0.4
    turn = 1.0

    try:
        while True:
            key = get_key(settings)
            if key == '\x03': # CTRL-C
                break
            elif key == 'w':
                vx = speed; vy = 0.0; wz = 0.0
            elif key == 's':
                vx = -speed; vy = 0.0; wz = 0.0
            elif key == 'a':
                vx = 0.0; vy = speed; wz = 0.0
            elif key == 'd':
                vx = 0.0; vy = -speed; wz = 0.0
            elif key == 'q':
                vx = 0.0; vy = 0.0; wz = turn
            elif key == 'e':
                vx = 0.0; vy = 0.0; wz = -turn
            elif key == ' ':
                vx, vy, wz = 0.0, 0.0, 0.0
            elif key == 'j':
                node.arm_positions[0] = min(3.14, node.arm_positions[0] + 0.1)
                node.publish_arm()
            elif key == 'l':
                node.arm_positions[0] = max(-3.14, node.arm_positions[0] - 0.1)
                node.publish_arm()
            elif key == 'i':
                node.arm_positions[1] = min(1.57, node.arm_positions[1] + 0.1)
                node.publish_arm()
            elif key == 'k':
                node.arm_positions[1] = max(-1.57, node.arm_positions[1] - 0.1)
                node.publish_arm()
            elif key == 'u':
                node.arm_positions[2] = min(2.0, node.arm_positions[2] + 0.1)
                node.publish_arm()
            elif key == 'o':
                node.arm_positions[2] = max(-2.0, node.arm_positions[2] - 0.1)
                node.publish_arm()
            elif key == 'm':
                node.arm_positions[3] = min(1.57, node.arm_positions[3] + 0.1)
                node.publish_arm()
            elif key == ',':
                node.arm_positions[3] = max(-1.57, node.arm_positions[3] - 0.1)
                node.publish_arm()
            elif key == 'g':
                node.gripper_pos = min(0.03, node.gripper_pos + 0.005)
                node.publish_gripper()
            elif key == 'h':
                node.gripper_pos = max(0.0, node.gripper_pos - 0.005)
                node.publish_gripper()

            node.publish_twist(vx, vy, wz)

    except Exception as e:
        print(e)
    finally:
        node.publish_twist(0.0, 0.0, 0.0)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
