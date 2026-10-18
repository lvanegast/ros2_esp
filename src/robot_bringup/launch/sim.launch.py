import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_robot_description = get_package_share_directory('robot_description')
    pkg_robot_bringup = get_package_share_directory('robot_bringup')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Argumentos de lanzamiento
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_path = os.path.join(pkg_robot_bringup, 'worlds', 'arena.sdf')
    controllers_file = os.path.join(pkg_robot_bringup, 'config', 'controllers.yaml')
    bridge_config_file = os.path.join(pkg_robot_bringup, 'config', 'bridge.yaml')

    # Generación de la descripción del robot con xacro
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ',
        PathJoinSubstitution([FindPackageShare('robot_description'), 'urdf', 'robot.urdf.xacro']),
        ' controllers_file:=',
        controllers_file,
    ])

    robot_description = {'robot_description': ParameterValue(robot_description_content, value_type=str)}

    # 1. Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[robot_description, {'use_sim_time': True}],
    )

    # 2. Servidor de Simulación Gazebo Harmonic
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r -v 3 {world_path}'}.items(),
    )

    # 3. Spawn del Robot en Gazebo
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'mobile_manipulator',
            '-topic', 'robot_description',
            '-z', '0.05'
        ],
        output='screen',
    )

    # 4. Puente de sensores y reloj (ros_gz_bridge)
    ros_gz_bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config_file, 'use_sim_time': True}],
        output='screen',
    )

    # 5. Spawners de controladores ros2_control
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    mecanum_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['mecanum_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    gripper_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Secuenciación: Activar controladores tras el spawn del robot
    delay_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[
                joint_state_broadcaster_spawner,
                mecanum_controller_spawner,
                arm_controller_spawner,
                gripper_controller_spawner,
            ],
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true', description='Usar reloj de simulación'),
        robot_state_publisher_node,
        gz_sim,
        spawn_robot,
        ros_gz_bridge_node,
        delay_controllers,
    ])
