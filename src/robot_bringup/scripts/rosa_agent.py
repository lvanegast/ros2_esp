#!/usr/bin/env python3
"""
NASA-JPL ROSA (Robot Operating System Agent) para el Mobile Manipulator
Permite inspeccionar, diagnosticar y operar el robot mediante lenguaje natural y LLMs.
"""

import os
import sys
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float64MultiArray
from langchain_core.tools import tool

from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Importar el framework ROSA de la NASA
from rosa import ROSA
from rosa.prompts import RobotSystemPrompts

class RobotControllerNode(Node):
    def __init__(self):
        super().__init__('rosa_robot_controller')
        self.cmd_pub = self.create_publisher(TwistStamped, '/mecanum_controller/reference', 10)
        self.arm_pub = self.create_publisher(Float64MultiArray, '/arm_controller/commands', 10)
        self.gripper_pub = self.create_publisher(Float64MultiArray, '/gripper_controller/commands', 10)

        # Poses predefinidas para el brazo
        self.presets = {
            "home": [0.0, 0.0, 0.0, 0.0],
            "ready": [0.0, 0.5, 0.5, 0.0],
            "reach_table": [0.0, 0.8, -0.6, -0.2],
            "pick_pose": [0.0, 0.9, -0.8, -0.1],
            "retract": [0.0, -0.5, 1.2, 0.0]
        }

    def move_base(self, vx: float, vy: float, wz: float, duration: float = 1.0):
        t = TwistStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_footprint'
        t.twist.linear.x = float(vx)
        t.twist.linear.y = float(vy)
        t.twist.angular.z = float(wz)
        
        # Enviar comando durante la duración especificada
        start = time.time()
        while time.time() - start < duration:
            self.cmd_pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)
            time.sleep(0.05)

        # Detener robot
        t.twist.linear.x = 0.0
        t.twist.linear.y = 0.0
        t.twist.angular.z = 0.0
        self.cmd_pub.publish(t)

    def set_arm_angles(self, angles: list):
        msg = Float64MultiArray()
        msg.data = [float(a) for a in angles]
        self.arm_pub.publish(msg)

    def set_gripper(self, pos: float):
        msg = Float64MultiArray()
        msg.data = [float(pos)]
        self.gripper_pub.publish(msg)


# Instancia global del nodo para las herramientas
_robot_node = None

def get_robot_node():
    global _robot_node
    if _robot_node is None:
        rclpy.init()
        _robot_node = RobotControllerNode()
    return _robot_node


# ==================== HERRAMIENTAS PERSONALIZADAS DE ROSA ====================

@tool
def move_robot_base(direction: str, duration_seconds: float = 1.0) -> str:
    """Mueve la base mecanum del robot. Direcciones válidas: forward, backward, left, right, rotate_left, rotate_right, stop."""
    node = get_robot_node()
    speed = 0.4
    turn = 0.8
    direction = direction.lower().strip()
    
    if direction == "forward":
        node.move_base(speed, 0.0, 0.0, duration_seconds)
    elif direction == "backward":
        node.move_base(-speed, 0.0, 0.0, duration_seconds)
    elif direction == "left":
        node.move_base(0.0, speed, 0.0, duration_seconds)
    elif direction == "right":
        node.move_base(0.0, -speed, 0.0, duration_seconds)
    elif direction == "rotate_left":
        node.move_base(0.0, 0.0, turn, duration_seconds)
    elif direction == "rotate_right":
        node.move_base(0.0, 0.0, -turn, duration_seconds)
    elif direction == "stop":
        node.move_base(0.0, 0.0, 0.0, 0.1)
    else:
        return f"Dirección desconocida: {direction}. Usa forward, backward, left, right, rotate_left, rotate_right o stop."
        
    return f"Base movida hacia '{direction}' por {duration_seconds} segundos con éxito."


@tool
def set_arm_pose(pose_name: str) -> str:
    """Posiciona el brazo en una postura predefinida. Opciones: home, ready, reach_table, pick_pose, retract."""
    node = get_robot_node()
    pose_name = pose_name.lower().strip()
    if pose_name not in node.presets:
        return f"Postura '{pose_name}' no existe. Opciones disponibles: {list(node.presets.keys())}"
        
    angles = node.presets[pose_name]
    node.set_arm_angles(angles)
    return f"Brazo posicionado en '{pose_name}' con ángulos {angles}."


@tool
def control_gripper(action: str) -> str:
    """Abre o cierra la pinza del brazo robótico. Opciones: 'open' o 'close'."""
    node = get_robot_node()
    action = action.lower().strip()
    if action == "open":
        node.set_gripper(0.03)
        return "Pinza abierta."
    elif action == "close":
        node.set_gripper(0.0)
        return "Pinza cerrada."
    else:
        return f"Acción inválida '{action}'. Usa 'open' o 'close'."


def create_rosa_agent():
    """Crea e inicializa el agente ROSA de la NASA con herramientas estándar y personalizadas."""
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        print(f"[ROSA] Proveedor LLM: Google Gemini ({gemini_model})")
        llm = ChatGoogleGenerativeAI(model=gemini_model, api_key=gemini_key, temperature=0.2)
    elif openai_key:
        from langchain_openai import ChatOpenAI
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        print(f"[ROSA] Proveedor LLM: OpenAI ({openai_model})")
        llm = ChatOpenAI(model=openai_model, api_key=openai_key, temperature=0.2)
    else:
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        print(f"[ROSA] No se detectó GEMINI_API_KEY ni OPENAI_API_KEY. Intentando Ollama local ({ollama_model})...")
        print("[ROSA] Sugerencia: Puedes exportar GEMINI_API_KEY en tu terminal o en un archivo .env")
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=ollama_model, temperature=0.2)

    # Configurar el sistema y personalidad de ROSA
    prompts = RobotSystemPrompts(
        embodiment_and_persona=(
            "Eres ROSA (Robot Operating System Agent), un agente inteligente desarrollado por NASA-JPL. "
            "Supervisas y operas un Manipulador Móvil con base Mecanum de 4 ruedas holonómicas, "
            "brazo robótico de 4 DOF con pinza, LiDAR 2D, IMU 100 Hz y cámara RGB-D en ROS 2 Jazzy. "
            "Responde siempre en español de manera clara, técnica y concisa."
        ),
        mission_and_objectives=(
            "Diagnosticar el estado de los nodos y tópicos (ej. ros2_node_list, ros2_topic_list, ros2_doctor), "
            "y comandar el movimiento de la base, el brazo y la pinza cuando el operador lo solicite."
        ),
        about_your_capabilities=(
            "Dispones de herramientas nativas de ROS 2 para inspeccionar el sistema, y herramientas de control físico: "
            "1. 'move_robot_base': Mueve la base (direcciones: forward, backward, left, right, rotate_left, rotate_right, stop). "
            "2. 'set_arm_pose': Mueve el brazo a posturas predefinidas ('home', 'ready', 'reach_table', 'pick_pose', 'retract'). "
            "3. 'control_gripper': Abre ('open') o cierra ('close') la pinza."
        )
    )

    tools = [move_robot_base, set_arm_pose, control_gripper]

    agent = ROSA(
        ros_version=2,
        llm=llm,
        tools=tools,
        prompts=prompts,
        streaming=False
    )
    return agent


def main():
    print("==================================================================")
    print("      NASA-JPL ROSA Agent para Mobile Manipulator (ROS 2 Jazzy)  ")
    print("==================================================================")
    try:
        agent = create_rosa_agent()
        print("Agente ROSA inicializado. Escribe tus preguntas o comandos en lenguaje natural.")
        print("Ejemplos:")
        print("  - '¿Qué tópicos de sensores están activos?'")
        print("  - 'Mueve el brazo a la mesa (reach_table) y abre la pinza'")
        print("  - 'Revisa si hay algún error en los controladores'")
        print("Escribe 'salir' para terminar.\n")

        while True:
            prompt = input("Tú > ")
            if prompt.strip().lower() in ["salir", "exit", "quit"]:
                break
            if not prompt.strip():
                continue
            response = agent.invoke(prompt)
            print(f"\nROSA > {response}\n")

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if _robot_node is not None:
            _robot_node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
