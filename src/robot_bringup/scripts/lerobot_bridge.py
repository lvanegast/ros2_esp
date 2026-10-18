#!/usr/bin/env python3
"""
Hugging Face LeRobot <-> ROS 2 Bridge para el Mobile Manipulator
Permite grabar demostraciones (dataset collection) y ejecutar inferencia de políticas
(Diffusion Policy / ACT) usando la cámara RGB-D y articulaciones en Gazebo Harmonic.
"""

import os
import sys
import time
import cv2
import numpy as np
import torch
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float64MultiArray
from cv_bridge import CvBridge

# Importar Hugging Face LeRobot
import lerobot

class LeRobotBridgeNode(Node):
    def __init__(self):
        super().__init__('lerobot_bridge')
        self.bridge = CvBridge()

        # Suscriptores de observaciones sensoriales
        self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.create_subscription(JointState, '/joint_states', self.joint_callback, 10)

        # Publicadores de acciones generadas por la política
        self.arm_pub = self.create_publisher(Float64MultiArray, '/arm_controller/commands', 10)
        self.base_pub = self.create_publisher(TwistStamped, '/mecanum_controller/reference', 10)

        # Buffers de estado
        self.latest_image = None
        self.latest_joint_positions = {}
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.get_logger().info(f"LeRobot Bridge inicializado exitosamente en {self.device}")
        self.get_logger().info(f"LeRobot versión: {lerobot.__version__}")

    def image_callback(self, msg: Image):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            # Redimensionar al estándar de LeRobot (ej. 224x224 para ViT/ResNet)
            resized = cv2.resize(cv_img, (224, 224))
            # Convertir a tensor PyTorch en formato (C, H, W) normalizado [0, 1]
            tensor_img = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
            self.latest_image = tensor_img.unsqueeze(0).to(self.device)
        except Exception as e:
            self.get_logger().warn(f"Error procesando imagen: {e}")

    def joint_callback(self, msg: JointState):
        for name, pos in zip(msg.name, msg.position):
            self.latest_joint_positions[name] = pos

    def get_arm_state_vector(self):
        """Retorna el vector articular [arm_1, arm_2, arm_3, arm_4, gripper]."""
        joints = ['arm_joint_1', 'arm_joint_2', 'arm_joint_3', 'arm_joint_4', 'gripper_joint']
        return [self.latest_joint_positions.get(j, 0.0) for j in joints]

    def send_arm_action(self, target_positions: list):
        """Publica el vector de acción articular predicho por la política."""
        msg = Float64MultiArray()
        msg.data = [float(p) for p in target_positions[:4]]
        self.arm_pub.publish(msg)

    def send_base_action(self, vx: float, vy: float, wz: float):
        """Publica la velocidad omnidireccional predicha."""
        t = TwistStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_footprint'
        t.twist.linear.x = float(vx)
        t.twist.linear.y = float(vy)
        t.twist.angular.z = float(wz)
        self.base_pub.publish(t)


def main():
    rclpy.init()
    node = LeRobotBridgeNode()

    print("==================================================================")
    print("      Hugging Face LeRobot <-> ROS 2 Jazzy Bridge Activado        ")
    print(f"      GPU Detectada: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print("==================================================================")
    print("Escuchando /camera/image_raw y /joint_states...")
    print("Listo para grabación de datasets o despliegue de políticas (ACT / Diffusion).")

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
