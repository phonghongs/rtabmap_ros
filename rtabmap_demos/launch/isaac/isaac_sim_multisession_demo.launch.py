#
# Requirements:
#  * Isaac simulator
#  * isaac_ros_image_proc
#  * isaac_ros_stereo_image_proc
#  * nav2_bringup
#  * isaac_ros_visual_slam (optional, for vo:=isaac)
#
# This is a HYBRID of isaac_sim_vslam_demo.launch.py + multisession_mapping_demo.launch.py
# It enables multi-session mapping in Isaac Sim with the Nova Carter robot.
#
# Usage:
# 1. Launch Isaac Simulator (see isaac_sim_vslam_demo.launch.py for setup)
# 2. First mapping session:
#    $ rm ~/.ros/rtabmap.db  # Fresh start
#    $ ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py
#    Drive robot around, Ctrl+C when done
#
# 3. Move robot to different location in Isaac Sim (pick up and place)
#
# 4. Second mapping session (robot starts in unknown location):
#    $ ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py
#    Robot will be "lost" initially, drive around until it recognizes previous area
#    Maps will merge via loop closure!
#
# 5. Repeat for more sessions...
#

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def launch_setup(context, *args, **kwargs):
    # Directories
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_rtabmap_demos = get_package_share_directory('rtabmap_demos')

    # Paths
    nav2_launch = PathJoinSubstitution([pkg_nav2_bringup, 'launch', 'navigation_launch.py'])
    nav2_vo_params = PathJoinSubstitution([pkg_rtabmap_demos, 'params', 'isaac_vslam_nav2_params.yaml'])
    nav2_params = PathJoinSubstitution([pkg_rtabmap_demos, 'params', 'isaac_nav2_params.yaml'])
    rviz_launch = PathJoinSubstitution([pkg_nav2_bringup, 'launch', 'rviz_launch.py'])
    rtabmap_launch = PathJoinSubstitution([pkg_rtabmap_demos, 'launch', 'isaac', 'isaac_vslam_multisession.launch.py'])

    vo = LaunchConfiguration('vo').perform(context)
    image_width = int(LaunchConfiguration('image_width').perform(context))
    image_height = int(LaunchConfiguration('image_height').perform(context))

    # GPU-accelerated stereo processing (same as original)
    left_resize_node = ComposableNode(
        name='left_resize_node',
        package='isaac_ros_image_proc',
        plugin='nvidia::isaac_ros::image_proc::ResizeNode',
        parameters=[{
            'use_sim_time': True,
            'output_width': image_width,
            'output_height': image_height,
        }],
        namespace="front_stereo_camera",
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
        namespace="front_stereo_camera",
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
        namespace="front_stereo_camera",
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
        namespace="front_stereo_camera",
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
        namespace="front_stereo_camera",
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
        namespace="front_stereo_camera"
    )

    stereo_img_proc_container = ComposableNodeContainer(
        name='stereo_img_proc_container',
        package='rclcpp_components',
        namespace="front_stereo_camera",
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
        arguments=['--ros-args', '--log-level', 'info',
                   '--log-level', 'color_format_convert:=info',
                   '--log-level', 'NitrosImage:=info',
                   '--log-level', 'NitrosNode:=info'
                   ],
    )

    nav2_args = [('use_sim_time', 'true')]
    if vo == 'rtabmap':
        nav2_args.append(('params_file', nav2_vo_params))
    else:
        nav2_args.append(('params_file', nav2_params))
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([nav2_launch]),
        launch_arguments=nav2_args
    )

    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([rviz_launch])
    )

    # Launch RTAB-Map with multi-session parameters
    rtabmap = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([rtabmap_launch]),
        launch_arguments=[
            ('rtabmap_viz', LaunchConfiguration('rtabmap_viz')),
            ('localization', LaunchConfiguration('localization')),
            ('use_sim_time', 'true'),
            ('stereo_camera_namespace', 'front_stereo_camera'),
            ('enable_vo', str(vo == 'rtabmap')),
            ('stereo', LaunchConfiguration('stereo'))
        ]
    )

    # Add actions
    actions = [rtabmap, nav2, rviz, stereo_img_proc_container]

    if vo == 'isaac':
        isaac_visual_slam_node = ComposableNode(
            name='visual_slam_node',
            package='isaac_ros_visual_slam',
            plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode',
            remappings=[('visual_slam/image_0', 'front_stereo_camera/left/image_rect'),
                        ('visual_slam/camera_info_0', 'front_stereo_camera/left/camera_info_rect'),
                        ('visual_slam/image_1', 'front_stereo_camera/right/image_rect'),
                        ('visual_slam/camera_info_1', 'front_stereo_camera/right/camera_info_rect')],
            parameters=[{
                        'use_sim_time': True,
                        'enable_image_denoising': True,
                        'enable_planar_mode': True,
                        'rectified_images': True,
                        'publish_map_to_odom_tf': False,
                        'odom_frame': 'odom',
                        'enable_slam_visualization': True,
                        'enable_observations_view': True,
                        'enable_landmarks_view': True}]
        )

        isaac_vslam_container = ComposableNodeContainer(
            name='isaac_visual_slam_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[isaac_visual_slam_node],
            output='screen',
        )
        actions.append(isaac_vslam_container)

    return actions

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('rtabmap_viz', default_value='true',
                          choices=['true', 'false'], description='Start rtabmap_viz.'),
        DeclareLaunchArgument('localization', default_value='false',
                          choices=['true', 'false'], description='Start rtabmap in localization mode (a map should have been already created).'),
        DeclareLaunchArgument('vo', default_value='isaac',
                          choices=['none', 'rtabmap', 'isaac'], description='Enable visual odometry. Recommended: isaac for multi-session.'),
        DeclareLaunchArgument('stereo', default_value='true',
                          choices=['true', 'false'], description='Use stereo images as input instead of left+depth images.'),
        DeclareLaunchArgument('image_width', default_value='960',
                          description='Resize input images.'),
        DeclareLaunchArgument('image_height', default_value='600',
                          description='Resize input images.'),
        OpaqueFunction(function=launch_setup)
    ])
