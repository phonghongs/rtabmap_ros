# rtabmap_isaacsim

RTAB-Map SLAM package for NVIDIA Nova Carter robot in Isaac Sim, featuring **3D LiDAR** and **Stereo Camera** fusion.

## Features

- **3D LiDAR + Stereo Visual SLAM** - Fuses 3D point clouds with stereo visual features for robust mapping
- **GPU-Accelerated Processing** - Uses Isaac ROS for hardware-accelerated stereo processing (resize, rectify, disparity)
- **Multiple Odometry Options**:
  - `none` - Wheel odometry only (default)
  - `rtabmap` - RTAB-Map visual odometry
  - `isaac` - Isaac ROS Visual SLAM odometry
- **Full 6-DOF 3D Mapping** - Creates detailed 3D occupancy grids and point cloud maps
- **Nav2 Integration** - Ready for autonomous navigation with Nav2 stack
- **Multi-Session Mapping** - Supports incremental mapping across multiple sessions
- **Optional 2D Scan Generation** - Convert 3D LiDAR to 2D laser scan for Nav2

## Requirements

### Isaac Sim
- NVIDIA Isaac Sim (tested with latest version)
- Nova Carter robot asset

### ROS2 Packages
- `rtabmap_ros` (this workspace)
- `isaac_ros_image_proc` - GPU-accelerated image processing
- `isaac_ros_stereo_image_proc` - GPU-accelerated stereo processing
- `nav2_bringup` - Nav2 navigation stack
- `pointcloud_to_laserscan` - Optional, for 2D scan generation
- `isaac_ros_visual_slam` - Optional, for Isaac VO mode

## Isaac Sim Setup

### 1. Launch Isaac Sim

Start Isaac Sim application.

### 2. Load Nova Carter Scene

Open: **Isaac Examples → ROS2 → Navigation → Carter Navigation**

Or use the warehouse environment for more visual features:
**Isaac Examples → ROS2 → Navigation → iw.hub Navigation**

### 3. Enable Front Stereo Cameras

In the **Stage** tab:
1. Navigate to: `World → Nova_Carter_ROS → front_hawk → left_camera_render_product`
2. Under **Property → Isaac Create Render Product Node → Inputs**, check **"Enabled"**
3. Optionally set resolution:
   - `height = 600`
   - `width = 960`
4. Repeat for `right_camera_render_product`

### 4. Enable Front 3D LiDAR

The front 3D LiDAR should be enabled by default. Verify it publishes to `/front_3d_lidar/lidar_points`.

### 5. Verify Topics

Click **Play** button in Isaac Sim, then verify topics are publishing:

```bash
ros2 topic list
```

Expected topics:
```
/front_3d_lidar/lidar_points
/front_stereo_camera/left/image_raw
/front_stereo_camera/left/camera_info
/front_stereo_camera/right/image_raw
/front_stereo_camera/right/camera_info
/front_stereo_imu/imu
/chassis/odom
/chassis/imu
/tf
```

## Build

```bash
cd ~/ros2_ws
colcon build --packages-select rtabmap_isaacsim --symlink-install
source install/setup.bash
```

## Usage

### Basic 3D LiDAR + Stereo SLAM (Wheel Odometry)

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py
```

This launches:
- GPU-accelerated stereo processing
- RTAB-Map SLAM with 3D LiDAR fusion
- rtabmap_viz GUI for 3D visualization
- Nav2 navigation stack
- RViz for navigation interface

### With RTAB-Map Visual Odometry

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py vo:=rtabmap
```

Adds visual odometry from stereo cameras for improved accuracy.

### With Isaac ROS Visual SLAM Odometry

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py vo:=isaac
```

Uses NVIDIA's GPU-accelerated visual SLAM for odometry.

### With 2D Scan Generation (for Nav2)

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py generate_2d_scan:=true
```

Converts 3D LiDAR to 2D laser scan at `/scan` topic for Nav2 local costmap.

### Localization Mode (Using Existing Map)

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py localization:=true
```

Loads existing map from `~/.ros/rtabmap.db` for localization-only mode.

### Without Nav2 (SLAM Only)

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py nav2:=false
```

### Without RViz (Headless)

```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py rviz:=false
```

## Launch Arguments

| Argument | Default | Options | Description |
|----------|---------|---------|-------------|
| `vo` | `none` | `none`, `rtabmap`, `isaac` | Visual odometry method |
| `stereo` | `true` | `true`, `false` | Use stereo or depth images |
| `use_3d_lidar` | `true` | `true`, `false` | Enable 3D LiDAR fusion |
| `generate_2d_scan` | `false` | `true`, `false` | Generate 2D scan from 3D LiDAR |
| `rtabmap_viz` | `true` | `true`, `false` | Launch rtabmap_viz GUI |
| `rviz` | `true` | `true`, `false` | Launch RViz |
| `nav2` | `true` | `true`, `false` | Launch Nav2 navigation |
| `localization` | `false` | `true`, `false` | Localization mode |
| `image_width` | `960` | integer | Stereo image resize width |
| `image_height` | `600` | integer | Stereo image resize height |

## Control the Robot

### Option 1: Nav2 Goal in RViz

1. Click **"Nav2 Goal"** button in RViz toolbar
2. Click and drag on the map to set goal pose
3. Robot will navigate autonomously

### Option 2: Keyboard Teleop

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Use keyboard to drive the robot around for mapping.

### Option 3: Autonomous Exploration

Install m-explore-ros2:
```bash
sudo apt install ros-${ROS_DISTRO}-explore-lite
```

Launch exploration:
```bash
ros2 launch explore_lite explore.launch.py
```

Robot will autonomously explore and map the environment.

## Multi-Session Mapping

RTAB-Map supports incremental mapping across multiple sessions:

### Session 1: Create Initial Map

```bash
rm ~/.ros/rtabmap.db  # Fresh start
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py
# Drive robot around, then Ctrl+C when done
```

### Session 2: Extend the Map

```bash
# Move robot to different location in Isaac Sim (or teleport)
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py
# Robot will be "lost" initially
# Drive around until it recognizes previous area
# Maps will merge via loop closure!
```

### Session N: Continue Mapping

Repeat Session 2 to keep extending the map across sessions.

## Data Visualization

### RTAB-Map Viz (3D Visualization)

Launched by default with `rtabmap_viz:=true`. Shows:
- 3D point cloud map
- Loop closures (graph optimization)
- Feature matches
- Camera poses
- LiDAR scans

### RViz (Navigation Visualization)

Launched by default with `rviz:=true`. Shows:
- 2D/3D occupancy map
- RTAB-Map graph
- Navigation plan
- Costmaps
- Robot pose

## Troubleshooting

### No Stereo Images

Verify cameras are enabled in Isaac Sim (see Setup step 3).

### No 3D LiDAR Data

Check that LiDAR is enabled:
```bash
ros2 topic echo /front_3d_lidar/lidar_points --once
```

### Slow Performance

Reduce image resolution:
```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py \
  image_width:=640 image_height:=480
```

### TF Errors with Isaac VO

If using `vo:=isaac`, disable wheel odometry TF in Isaac Sim:

In Stage tab: `World → Nova_Carter_ROS → transform_tree_odometry → ros2_publish_raw_transform_tree`

Change `topicName` from `"tf"` to `"tf_odom_ignored"`

### Robot Stuck During Navigation

Adjust Nav2 parameters in `params/nova_carter_nav2_params.yaml`:
- Increase `max_vel_x` for faster movement
- Adjust obstacle detection thresholds
- Tune DWB local planner parameters

## Advanced Configuration

### RTAB-Map Parameters

Edit `launch/nova_carter_slam.launch.py` to adjust SLAM parameters:

- `Reg/Strategy`: Registration strategy (0=Visual, 1=ICP, 2=Visual+ICP)
- `Grid/3D`: Enable/disable 3D occupancy grid
- `Grid/CellSize`: Grid cell size in meters
- `Grid/MaxObstacleHeight`: Maximum obstacle height
- `Kp/DetectorStrategy`: Feature detector (0=SURF, 6=GFTT, etc.)

See [RTAB-Map parameters documentation](https://github.com/introlab/rtabmap/wiki/parameters) for full list.

### Nav2 Parameters

Edit `params/nova_carter_nav2_params.yaml` to tune navigation:

- Velocity limits
- Acceleration limits
- DWB local planner tuning
- Costmap configuration
- Recovery behaviors

## Database Management

### View Database Statistics

```bash
rtabmap-info ~/.ros/rtabmap.db
```

### Export Map

```bash
# Export point cloud
rtabmap-export ~/.ros/rtabmap.db -o map.ply

# Export occupancy grid
rtabmap-export ~/.ros/rtabmap.db -o map.pgm
```

### Clear Database

```bash
rm ~/.ros/rtabmap.db
```

Or use launch argument (automatic):
```bash
ros2 launch rtabmap_isaacsim nova_carter_slam.launch.py  # -d flag deletes db on start
```

## Package Structure

```
rtabmap_isaacsim/
├── launch/
│   └── nova_carter_slam.launch.py    # Main launch file
├── params/
│   └── nova_carter_nav2_params.yaml  # Nav2 configuration
├── config/
│   └── nova_carter_slam.rviz         # RViz configuration
├── CMakeLists.txt
├── package.xml
└── README.md
```

## Topics Published

| Topic | Type | Description |
|-------|------|-------------|
| `/rtabmap/grid_map` | `nav_msgs/OccupancyGrid` | 2D occupancy grid |
| `/rtabmap/cloud_map` | `sensor_msgs/PointCloud2` | 3D point cloud map |
| `/rtabmap/mapData` | `rtabmap_msgs/MapData` | Full map data with graph |
| `/rtabmap/info` | `rtabmap_msgs/Info` | SLAM statistics |
| `/rtabmap/mapGraph` | `rtabmap_msgs/MapGraph` | Pose graph |
| `/map` | `nav_msgs/OccupancyGrid` | Nav2 map |
| `/scan` | `sensor_msgs/LaserScan` | 2D scan (if enabled) |

## Services

| Service | Type | Description |
|---------|------|-------------|
| `/rtabmap/reset` | `std_srvs/Empty` | Reset SLAM |
| `/rtabmap/pause` | `std_srvs/Empty` | Pause mapping |
| `/rtabmap/resume` | `std_srvs/Empty` | Resume mapping |
| `/rtabmap/trigger_new_map` | `std_srvs/Empty` | Start new map session |
| `/rtabmap/set_mode_localization` | `std_srvs/Empty` | Switch to localization |
| `/rtabmap/set_mode_mapping` | `std_srvs/Empty` | Switch to mapping |

## References

- [RTAB-Map ROS2](https://github.com/introlab/rtabmap_ros/tree/ros2)
- [RTAB-Map Documentation](https://github.com/introlab/rtabmap/wiki)
- [Isaac ROS](https://github.com/NVIDIA-ISAAC-ROS)
- [Nav2 Documentation](https://navigation.ros.org/)
- [Nova Carter Robot](https://docs.omniverse.nvidia.com/isaacsim/latest/robot_examples/nova_carter.html)

## License

BSD

## Author

void
