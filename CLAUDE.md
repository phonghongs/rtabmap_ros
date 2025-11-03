# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

rtabmap_ros is the ROS2 package for RTAB-Map (Real-Time Appearance-Based Mapping), a RGB-D Graph-Based SLAM library. This is the `ros2` branch supporting ROS2 Humble and later distributions.

**Repository**: https://github.com/introlab/rtabmap_ros
**Branch**: ros2
**ROS Wiki**: http://wiki.ros.org/rtabmap_ros
**Minimum ROS2 Version**: Humble

## Build System

### Initial Setup from Source

```bash
# Remove any binary installations first
sudo apt remove ros-$ROS_DISTRO-rtabmap*

# Clone repositories
cd ~/ros2_ws
git clone https://github.com/introlab/rtabmap.git src/rtabmap
git clone --branch ros2 https://github.com/introlab/rtabmap_ros.git src/rtabmap_ros

# Install dependencies
rosdep update && rosdep install --from-paths src --ignore-src -r -y

# Build (limit parallel jobs if RAM < 16GB)
export MAKEFLAGS="-j6"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

### Build with Extended Features

For multi-camera support (`rgbd_cameras>1`) and user data subscription:

```bash
colcon build --symlink-install --cmake-args \
  -DRTABMAP_SYNC_MULTI_RGBD=ON \
  -DRTABMAP_SYNC_USER_DATA=ON \
  -DCMAKE_BUILD_TYPE=Release
```

### Standard Build Commands

```bash
# Full workspace build
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Build specific package
colcon build --packages-select rtabmap_slam --symlink-install

# Build with verbose output for debugging
colcon build --event-handlers console_direct+
```

### Testing

Python packages have basic linting tests:

```bash
# Run tests for specific package
colcon test --packages-select rtabmap_python

# View test results
colcon test-result --verbose
```

## Package Architecture

The repository is a metapackage containing 14 sub-packages organized by functionality:

### Core SLAM Packages

- **rtabmap_slam**: Main SLAM node (`rtabmap`)
  - `CoreWrapper.cpp`: Main SLAM implementation wrapper
  - `CoreNode.cpp`: ROS2 node interface
  - Handles loop closure detection, graph optimization, and 3D mapping

- **rtabmap_odom**: Visual/lidar odometry nodes
  - `RGBDOdometryNode.cpp`: RGB-D camera odometry
  - `StereoOdometryNode.cpp`: Stereo camera odometry
  - `ICPOdometryNode.cpp`: LiDAR ICP odometry
  - `OdometryROS.cpp`: Common odometry interface

- **rtabmap_sync**: Sensor synchronization nodes
  - `RGBDSyncNode.cpp`: Single RGB-D camera synchronization
  - `RGBDXSyncNode.cpp`: Multi-camera synchronization (requires `RTABMAP_SYNC_MULTI_RGBD=ON`)
  - `StereoSyncNode.cpp`: Stereo camera synchronization
  - Synchronizes image, depth, and camera_info topics with approximate/exact time sync

### Utility Packages

- **rtabmap_util**: Supporting utility nodes
  - `MapAssemblerNode.cpp`: Assembles 2D/3D maps from graph
  - `PointCloudAggregatorNode.cpp`: Aggregates point clouds
  - `ObstaclesDetectionNode.cpp`: Detects obstacles for navigation
  - `LidarDeskewingNode.cpp`: Motion compensation for rotating LiDAR
  - `ImuToTFNode.cpp`, `OdomMsgToTFNode.cpp`: TF broadcasting utilities

- **rtabmap_viz**: Visualization GUI node
  - Qt-based 3D visualization interface
  - Alternative to rviz2 for RTAB-Map specific visualization

- **rtabmap_rviz_plugins**: RViz2 plugins for map display

- **rtabmap_costmap_plugins**: Nav2 integration (voxel layer plugin)

### Message and Conversion Packages

- **rtabmap_msgs**: Custom ROS2 message/service definitions
- **rtabmap_conversions**: Conversions between rtabmap and ROS types

### Launch and Example Packages

- **rtabmap_launch**: Main launch files
  - `rtabmap.launch.py`: Primary launch file (ROS1 `rtabmap.launch` equivalent)
  - See `rtabmap_launch/README.md` for migration examples from ROS1

- **rtabmap_examples**: Sensor integration examples
  - Stereo cameras, RGB-D cameras (RealSense, Kinect, ZED, etc.)
  - 3D LiDAR examples with point cloud assembly
  - Dataset playback (EuRoC, etc.)

- **rtabmap_demos**: Robot integration demos
  - Turtlebot3/Turtlebot4 with Nav2
  - Clearpath Husky, Champ quadruped
  - Isaac Sim integration
  - Multi-session mapping examples

- **rtabmap_python**: Python utilities and API

## Launch System

The main entry point is `rtabmap.launch.py` which maintains compatibility with ROS1 parameter names:

```bash
# Basic RGB-D SLAM
ros2 launch rtabmap_launch rtabmap.launch.py \
  rtabmap_args:="--delete_db_on_start" \
  rgb_topic:=/camera/rgb/image_raw \
  depth_topic:=/camera/depth/image_raw \
  camera_info_topic:=/camera/rgb/camera_info \
  frame_id:=base_link \
  rviz:=true

# With IMU initialization
ros2 launch rtabmap_launch rtabmap.launch.py \
  wait_imu_to_init:=true \
  imu_topic:=/imu/data \
  approx_sync:=false
```

For examples with specific sensors or robots, see launch files in `rtabmap_examples/launch/` and `rtabmap_demos/launch/`.

## ROS2-Specific Configuration

### Logging Setup

To ensure RTAB-Map logs appear ordered with RCLCPP logs, add to `.bashrc`:

```bash
export RCUTILS_LOGGING_USE_STDOUT=1
export RCUTILS_LOGGING_BUFFERED_STREAM=1
export RCUTILS_COLORIZED_OUTPUT=1  # Optional: colored output
```

### DDS Recommendation

For better performance (reduced lag in GUI and topics):

```bash
# Use Cyclone DDS instead of default
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Disable multicast if router becomes spammed
export CYCLONEDDS_URI="<Disc><DefaultMulticastAddress>0.0.0.0</></>"
```

## Development Notes

### CMake Definitions

- **Pre-Jazzy compatibility**: Code uses `#ifdef PRE_ROS_JAZZY` for ROS distro differences
- **Multi-camera support**: `RTABMAP_SYNC_MULTI_RGBD=ON` enables `RGBDXSyncNode`
- **User data subscription**: `RTABMAP_SYNC_USER_DATA=ON` enables user data topic support

### CI/CD

GitHub Actions workflows test builds on:
- ROS2 Humble, Jazzy, Kilted, Rolling
- Some packages excluded on Rolling due to missing Nav2 dependencies

### Node Communication Pattern

1. **Sensor Drivers** → **Sync Nodes** (`rtabmap_sync/*`)
2. **Sync Nodes** → **Odometry Nodes** (`rtabmap_odom/*`) and/or **SLAM Node** (`rtabmap_slam`)
3. **SLAM Node** → **Visualization** (`rtabmap_viz`, `rviz2`) and **Map Utilities** (`rtabmap_util/*`)
4. **Map Utilities** → **Navigation Stack** (Nav2 via `rtabmap_costmap_plugins`)

### Service Interface

Odometry and SLAM nodes expose services under their namespace (not global):
- Example: `rgbd_odometry/reset_odom` (not `/reset_odom`)
- Set `odometry_node_name` parameter in rtabmap_viz to match your odometry node namespace

## Docker Support

Pre-built images available at `introlab3it/rtabmap_ros`:
- Tags: `humble`, `humble-latest`, `jazzy`, `jazzy-latest`
- `-latest` tags built from latest source, others match ROS binary versions

Basic headless usage:

```bash
docker run -it --rm \
  --user $UID \
  -e ROS_HOME=/tmp/.ros \
  --network=host \
  --ipc=host \
  -v ~/.ros:/tmp/.ros \
  introlab3it/rtabmap_ros:humble-latest \
  ros2 launch rtabmap_launch rtabmap.launch.py rtabmap_viz:=false database_path:=/tmp/.ros/rtabmap.db
```

## Key File Locations

- **Main SLAM logic**: `rtabmap_slam/src/CoreWrapper.cpp`
- **Primary launch file**: `rtabmap_launch/launch/rtabmap.launch.py`
- **Sensor examples**: `rtabmap_examples/launch/*.py`
- **Robot demos**: `rtabmap_demos/launch/*/` (organized by robot platform)
- **Message definitions**: `rtabmap_msgs/msg/`, `rtabmap_msgs/srv/`
