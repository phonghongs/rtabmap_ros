#
# Nova Carter SLAM Launch File for Isaac Sim
#
# Features:
#   - 3D LiDAR SLAM with point cloud processing
#   - GPU-accelerated stereo camera processing (Isaac ROS)
#   - Visual odometry options (rtabmap/isaac/none)
#   - Nav2 integration for autonomous navigation
#   - Multi-session mapping support
#
# Requirements:
#  * Isaac Simulator with Nova Carter robot
#  * isaac_ros_image_proc
#  * isaac_ros_stereo_image_proc
#  * nav2_bringup
#  * pointcloud_to_laserscan (optional for 2D nav)
#
# Usage:
# 1. Launch Isaac Sim with Nova Carter
# 2. Enable front stereo cameras (left/right)
# 3. Enable front 3D LiDAR
# 4. Launch this file:
#    $ ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py
#
# Arguments:
#   vo:=none|rtabmap|isaac  - Visual odometry method (default: none, uses wheel odom)
#   stereo:=true|false      - Use stereo or depth images (default: true)
#   rtabmap_viz:=true|false - Launch rtabmap_viz GUI (default: true)
#   rviz:=true|false        - Launch RViz (default: true)
#   nav2:=true|false        - Launch Nav2 navigation (default: true)
#   localization:=true|false - Localization mode (default: false)
#   use_3d_lidar:=true|false - Enable 3D LiDAR fusion (default: true)
#   generate_2d_scan:=true|false - Generate 2D scan from 3D LiDAR (default: false)
#

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

def launch_setup(context, *args, **kwargs):
    # Directories
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_rtabmap_isaacsim = get_package_share_directory('rtabmap_isaacsim')

    # Paths
    nav2_launch = PathJoinSubstitution([pkg_nav2_bringup, 'launch', 'navigation_launch.py'])
    nav2_params = PathJoinSubstitution([pkg_rtabmap_isaacsim, 'params', 'nova_carter_nav2_params.yaml'])
    rviz_launch = PathJoinSubstitution([pkg_nav2_bringup, 'launch', 'rviz_launch.py'])
    rviz_config = PathJoinSubstitution([pkg_rtabmap_isaacsim, 'config', 'nova_carter_slam.rviz'])

    # Launch configuration values
    vo = LaunchConfiguration('vo').perform(context)
    stereo = LaunchConfiguration('stereo').perform(context) == 'true'
    use_3d_lidar = LaunchConfiguration('use_3d_lidar').perform(context) == 'true'
    generate_2d_scan = LaunchConfiguration('generate_2d_scan').perform(context) == 'true'
    image_width = int(LaunchConfiguration('image_width').perform(context))
    image_height = int(LaunchConfiguration('image_height').perform(context))
    localization = LaunchConfiguration('localization').perform(context) == 'true'

    # Stereo namespace
    stereo_ns = 'front_stereo_camera'

    # ========================================
    # GPU-Accelerated Stereo Image Processing
    # ========================================

    left_resize_node = ComposableNode(
        name='left_resize_node',
        package='isaac_ros_image_proc',
        plugin='nvidia::isaac_ros::image_proc::ResizeNode',
        parameters=[{
            'use_sim_time': True,
            'output_width': image_width,
            'output_height': image_height,
        }],
        namespace=stereo_ns,
        remappings=[
            ('image', 'left/image_raw'),
            ('camera_info', 'left/camera_info'),
            ('resize/image', 'left/image_resize'),
            ('resize/camera_info', 'left/camera_info_resize')
        ]
    )

    right_resize_node = ComposableNode(
        name='right_resize_node',
        package='isaac_ros_image_proc',
        plugin='nvidia::isaac_ros::image_proc::ResizeNode',
        parameters=[{
            'use_sim_time': True,
            'output_width': image_width,
            'output_height': image_height,
        }],
        namespace=stereo_ns,
        remappings=[
            ('image', 'right/image_raw'),
            ('camera_info', 'right/camera_info'),
            ('resize/image', 'right/image_resize'),
            ('resize/camera_info', 'right/camera_info_resize')
        ]
    )

    left_rectify_node = ComposableNode(
        name='left_rectify_node',
        package='isaac_ros_image_proc',
        plugin='nvidia::isaac_ros::image_proc::RectifyNode',
        parameters=[{
            'use_sim_time': True,
            'output_width': image_width,
            'output_height': image_height,
        }],
        namespace=stereo_ns,
        remappings=[
            ('image_raw', 'left/image_resize'),
            ('camera_info', 'left/camera_info_resize'),
            ('image_rect', 'left/image_rect'),
            ('camera_info_rect', 'left/camera_info_rect')
        ]
    )

    right_rectify_node = ComposableNode(
        name='right_rectify_node',
        package='isaac_ros_image_proc',
        plugin='nvidia::isaac_ros::image_proc::RectifyNode',
        parameters=[{
            'use_sim_time': True,
            'output_width': image_width,
            'output_height': image_height,
        }],
        namespace=stereo_ns,
        remappings=[
            ('image_raw', 'right/image_resize'),
            ('camera_info', 'right/camera_info_resize'),
            ('image_rect', 'right/image_rect'),
            ('camera_info_rect', 'right/camera_info_rect')
        ]
    )

    disparity_node = ComposableNode(
        name='disparity_node',
        package='isaac_ros_stereo_image_proc',
        plugin='nvidia::isaac_ros::stereo_image_proc::DisparityNode',
        parameters=[{
            'use_sim_time': True,
            'backends': 'CUDA',
            'max_disparity': 64.0
        }],
        namespace=stereo_ns,
        remappings=[
            ('left/camera_info', 'left/camera_info_rect'),
            ('right/camera_info', 'right/camera_info_rect'),
        ],
    )

    disparity_to_depth_node = ComposableNode(
        name='disparity_to_depth_node',
        package='isaac_ros_stereo_image_proc',
        plugin='nvidia::isaac_ros::stereo_image_proc::DisparityToDepthNode',
        parameters=[{
            'use_sim_time': True,
        }],
        namespace=stereo_ns
    )

    stereo_img_proc_container = ComposableNodeContainer(
        name='stereo_img_proc_container',
        package='rclcpp_components',
        namespace=stereo_ns,
        executable='component_container_mt',
        composable_node_descriptions=[
            left_resize_node,
            right_resize_node,
            left_rectify_node,
            right_rectify_node,
            disparity_node,
            disparity_to_depth_node
        ],
        output='screen',
        arguments=['--ros-args', '--log-level', 'info'],
    )

    # ========================================
    # RTAB-Map Sync Node
    # ========================================

    sync_node = Node(
        package='rtabmap_sync',
        executable='stereo_sync' if stereo else 'rgbd_sync',
        output='screen',
        namespace=stereo_ns,
        parameters=[{
            'approx_sync': False,
            'use_sim_time': True
        }],
        remappings=[
            ('left/image_rect', 'left/image_rect'),
            ('left/camera_info', 'left/camera_info_rect'),
            ('right/image_rect', 'right/image_rect'),
            ('right/camera_info', 'right/camera_info_rect'),
            ('rgb/image', 'left/image_rect'),
            ('rgb/camera_info', 'left/camera_info_rect'),
            ('depth/image', 'depth')
        ]
    )

    # ========================================
    # RTAB-Map Parameters
    # ========================================

    rtabmap_parameters = {
        'frame_id': 'base_link',
        'use_sim_time': True,
        'subscribe_rgbd': True,
        'subscribe_scan_cloud': use_3d_lidar,
        'subscribe_odom': vo == 'rtabmap' or vo == 'isaac',
        'subscribe_odom_info': vo == 'rtabmap',
        'approx_sync': False,
        'use_action_for_goal': True,

        # RTAB-Map SLAM parameters
        'Reg/Strategy': '0',  # 0=Visual, 1=ICP, 2=Visual+ICP
        'Reg/Force3DoF': 'false',  # Enable full 6DOF for 3D mapping
        'RGBD/NeighborLinkRefining': 'true',
        'RGBD/ProximityBySpace': 'true',
        'RGBD/ProximityPathMaxNeighbors': '10',
        'RGBD/OptimizeFromGraphEnd': 'false',

        # Visual feature parameters
        'Vis/MinInliers': '15',
        'Vis/InlierDistance': '0.1',
        'GFTT/MinDistance': '5',
        'GFTT/QualityLevel': '0.00001',

        # 3D Grid mapping parameters
        'Grid/RayTracing': 'true',
        'Grid/3D': 'true',  # Full 3D occupancy grid
        'Grid/MaxObstacleHeight': '2.0',
        'Grid/MaxGroundHeight': '0.1',
        'Grid/RangeMin': '0.2',
        'Grid/RangeMax': '20.0',
        'Grid/CellSize': '0.05',

        # Loop closure parameters
        'Kp/MaxDepth': '10.0',
        'Kp/DetectorStrategy': '6',  # 6=GFTT
        'Mem/NotLinkedNodesKept': 'false',
        'Mem/STMSize': '30',
        'Mem/LaserScanNormalK': '20',

        # Optimizer parameters
        'Optimizer/Strategy': '0',  # 0=TORO, 1=g2o, 2=GTSAM
        'Optimizer/Epsilon': '0.00001',
        'Optimizer/Iterations': '100',
        'Optimizer/GravitySigma': '0.3',
    }

    # Adjust parameters based on odometry source
    if vo == 'rtabmap' or vo == 'isaac':
        rtabmap_parameters['guess_frame_id'] = 'odom'
    else:
        rtabmap_parameters['odom_frame_id'] = 'odom'

    # Localization mode parameters
    if localization:
        rtabmap_parameters['Mem/IncrementalMemory'] = 'false'
        rtabmap_parameters['Mem/InitWMWithAllNodes'] = 'true'

    rtabmap_args = []
    if not localization:
        rtabmap_args.append('-d')  # Delete database on start

    # ========================================
    # Visual Odometry (Optional)
    # ========================================

    vo_node = None
    if vo == 'rtabmap':
        vo_node = Node(
            package='rtabmap_odom',
            executable='stereo_odometry' if stereo else 'rgbd_odometry',
            output='screen',
            namespace='rtabmap',
            parameters=[{
                **rtabmap_parameters,
                'odom_frame_id': 'vo',
                'Vis/FeatureType': '6',  # GFTT
                'Vis/MaxDepth': '10.0',
            }],
            remappings=[
                ('rgbd_image', f'/{stereo_ns}/rgbd_image'),
                ('odom', '/vo')
            ]
        )

    # ========================================
    # RTAB-Map SLAM Node
    # ========================================

    rtabmap_slam = Node(
        package='rtabmap_slam',
        executable='rtabmap',
        output='screen',
        namespace='rtabmap',
        parameters=[rtabmap_parameters],
        remappings=[
            ('rgbd_image', f'/{stereo_ns}/rgbd_image'),
            ('scan_cloud', '/front_3d_lidar/lidar_points'),
            ('map', '/map'),
            ('odom', '/chassis/odom' if vo == 'none' else ('/vo' if vo == 'rtabmap' else '/visual_slam/tracking/odometry'))
        ],
        arguments=rtabmap_args
    )

    # ========================================
    # RTAB-Map Visualization
    # ========================================

    rtabmap_viz_node = Node(
        condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
        package='rtabmap_viz',
        executable='rtabmap_viz',
        output='screen',
        namespace='rtabmap',
        parameters=[{
            **rtabmap_parameters,
            'odometry_node_name': 'stereo_odometry' if (vo == 'rtabmap' and stereo) else 'rgbd_odometry'
        }],
        remappings=[
            ('rgbd_image', f'/{stereo_ns}/rgbd_image'),
            ('scan_cloud', '/front_3d_lidar/lidar_points'),
            ('odom', '/chassis/odom' if vo == 'none' else '/vo')
        ]
    )

    # ========================================
    # 3D LiDAR to 2D Scan Converter (Optional)
    # ========================================

    pointcloud_to_laserscan_node = None
    if generate_2d_scan:
        pointcloud_to_laserscan_node = Node(
            package='pointcloud_to_laserscan',
            executable='pointcloud_to_laserscan_node',
            name='pointcloud_to_laserscan',
            parameters=[{
                'use_sim_time': True,
                'target_frame': 'base_link',
                'transform_tolerance': 0.01,
                'min_height': -0.5,
                'max_height': 0.5,
                'angle_min': -3.14159,
                'angle_max': 3.14159,
                'angle_increment': 0.00872665,  # 0.5 degrees
                'scan_time': 0.1,
                'range_min': 0.2,
                'range_max': 30.0,
                'use_inf': True,
            }],
            remappings=[
                ('cloud_in', '/front_3d_lidar/lidar_points'),
                ('scan', '/scan')
            ]
        )

    # ========================================
    # Nav2 Navigation
    # ========================================

    nav2 = IncludeLaunchDescription(
        condition=IfCondition(LaunchConfiguration('nav2')),
        launch_descriptor=PythonLaunchDescriptionSource([nav2_launch]),
        launch_arguments=[
            ('use_sim_time', 'true'),
            ('params_file', nav2_params)
        ]
    )

    # ========================================
    # RViz Visualization
    # ========================================

    rviz = Node(
        condition=IfCondition(LaunchConfiguration('rviz')),
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}]
    )

    # ========================================
    # Isaac Visual SLAM (Optional)
    # ========================================

    isaac_vslam_container = None
    if vo == 'isaac':
        isaac_visual_slam_node = ComposableNode(
            name='visual_slam_node',
            package='isaac_ros_visual_slam',
            plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode',
            remappings=[
                ('visual_slam/image_0', f'/{stereo_ns}/left/image_rect'),
                ('visual_slam/camera_info_0', f'/{stereo_ns}/left/camera_info_rect'),
                ('visual_slam/image_1', f'/{stereo_ns}/right/image_rect'),
                ('visual_slam/camera_info_1', f'/{stereo_ns}/right/camera_info_rect')
            ],
            parameters=[{
                'use_sim_time': True,
                'enable_image_denoising': True,
                'enable_planar_mode': False,  # Full 3D mode
                'rectified_images': True,
                'publish_map_to_odom_tf': False,
                'odom_frame': 'odom',
                'enable_slam_visualization': True,
                'enable_observations_view': True,
                'enable_landmarks_view': True
            }]
        )

        isaac_vslam_container = ComposableNodeContainer(
            name='isaac_visual_slam_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[isaac_visual_slam_node],
            output='screen',
        )

    # ========================================
    # Build action list
    # ========================================

    actions = [
        stereo_img_proc_container,
        sync_node,
        rtabmap_slam,
        rtabmap_viz_node,
        nav2,
        rviz
    ]

    if vo_node:
        actions.insert(2, vo_node)  # Add VO before SLAM

    if pointcloud_to_laserscan_node:
        actions.append(pointcloud_to_laserscan_node)

    if isaac_vslam_container:
        actions.append(isaac_vslam_container)

    return actions

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'vo', default_value='none',
            choices=['none', 'rtabmap', 'isaac'],
            description='Visual odometry method: none (wheel odom), rtabmap (RTAB-Map VO), isaac (Isaac ROS Visual SLAM)'),

        DeclareLaunchArgument(
            'stereo', default_value='true',
            choices=['true', 'false'],
            description='Use stereo images as input instead of left+depth images'),

        DeclareLaunchArgument(
            'rtabmap_viz', default_value='true',
            choices=['true', 'false'],
            description='Launch rtabmap_viz GUI for 3D visualization'),

        DeclareLaunchArgument(
            'rviz', default_value='true',
            choices=['true', 'false'],
            description='Launch RViz for navigation visualization'),

        DeclareLaunchArgument(
            'nav2', default_value='true',
            choices=['true', 'false'],
            description='Launch Nav2 navigation stack'),

        DeclareLaunchArgument(
            'localization', default_value='false',
            choices=['true', 'false'],
            description='Launch in localization mode (map must already exist)'),

        DeclareLaunchArgument(
            'use_3d_lidar', default_value='true',
            choices=['true', 'false'],
            description='Enable 3D LiDAR point cloud fusion with SLAM'),

        DeclareLaunchArgument(
            'generate_2d_scan', default_value='false',
            choices=['true', 'false'],
            description='Generate 2D laser scan from 3D LiDAR for Nav2'),

        DeclareLaunchArgument(
            'image_width', default_value='960',
            description='Resize stereo image width for processing'),

        DeclareLaunchArgument(
            'image_height', default_value='600',
            description='Resize stereo image height for processing'),

        OpaqueFunction(function=launch_setup)
    ])
