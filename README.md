# Mobile Manipulator Full-Stack Physical AI (ROS 2 Jazzy & Gazebo Harmonic)

Proyecto que integra los componentes más novedosos en el estado del arte de la robótica (2024-2026):
1. **Gemelo Digital Modular en Gazebo Harmonic**:
   - Base holonómica mecanum de 4 ruedas (`mecanum_drive_controller`).
   - Brazo articulado de 4-DOF + pinza (`position_controllers/JointGroupPositionController`).
   - Sensores: Cámara RGB-D en `/camera/image_raw`, LiDAR 2D en `/scan`, IMU 100 Hz en `/imu/data`.
2. **NASA-JPL ROSA (`jpl-rosa`)**:
   - Agente autónomo con 47 herramientas de introspección, diagnóstico y control mediante lenguaje natural.
3. **Hugging Face LeRobot (`lerobot 0.6.1`)**:
   - Pipeline de aprendizaje por imitación (Diffusion Policy / ACT) acelerado por hardware en tu GPU **NVIDIA GeForce RTX 4060**.
4. **Entorno Python moderno con `uv`**:
   - Gestor ultrarrápido configurado en `.venv` con acceso a los paquetes nativos de ROS 2.

---

## 🚀 Guía de Ejecución

### 1. Lanzar la Simulación en Gazebo Harmonic (Terminal 1)
```bash
cd /home/lvanegas/Documents/ros2_esp
source install/setup.bash
ros2 launch robot_bringup sim.launch.py
```

### 2. Agente Supervisor NASA-JPL ROSA (Terminal 2)
```bash
cd /home/lvanegas/Documents/ros2_esp
source install/setup.bash
source .venv/bin/activate
ros2 run robot_bringup rosa_agent.py
```
*Puedes preguntarle a ROSA cosas como:*
- *"¿Cuáles son los tópicos y sensores activos en el sistema?"*
- *"Mueve el brazo a la postura de la mesa (reach_table) y abre la pinza"*
- *"Avanza hacia adelante 2 segundos y detente"*
- *"¿Hay algún error en los controladores o nodos?"*

### 3. Bridge con Hugging Face LeRobot (Terminal 3)
```bash
cd /home/lvanegas/Documents/ros2_esp
source install/setup.bash
source .venv/bin/activate
ros2 run robot_bringup lerobot_bridge.py
```
*Convierte las imágenes de cámara (`/camera/image_raw`) en tensores normalizados en GPU y prepara el buffer de articulaciones para entrenamiento o inferencia de políticas (Diffusion / ACT).*

### 4. Teleoperación Manual por Teclado (Terminal 4 - Opcional)
```bash
cd /home/lvanegas/Documents/ros2_esp
source install/setup.bash
ros2 run robot_bringup teleop.py
```
- Base: `w/s/a/d` (omnidireccional), `q/e` (rotación).
- Brazo: `j/l`, `i/k`, `u/o`, `m/,`, `g/h` (pinza).

---

## 🧹 Limpieza Opcional Adicional del Sistema
Si deseas recuperar otros 6 a 8 GB adicionales de versiones viejas de Snap y cachés de APT:
```bash
cd /home/lvanegas/Documents/ros2_esp
sudo ./clean_system.sh
```
