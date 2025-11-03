# Multi-Session Mapping in Isaac Sim Guide

This guide explains how to use multi-session mapping with the Nova Carter robot in Isaac Sim.

## What is Multi-Session Mapping?

Multi-session mapping allows you to:
- Build maps across multiple separate robot runs
- Start each session from an **unknown location** (kidnapped robot problem)
- Automatically merge sessions when robot recognizes previous areas
- Create large-scale maps incrementally over time

## Files Created

1. **`isaac_sim_multisession_demo.launch.py`** - Main launch file (replaces isaac_sim_vslam_demo.launch.py)
2. **`isaac_vslam_multisession.launch.py`** - RTAB-Map configuration with multi-session parameters

## Quick Start

### 1. First Mapping Session

```bash
# Fresh start - delete old database
rm ~/.ros/rtabmap.db

# Launch Isaac Simulator
# Open: Isaac Examples -> ROS2 -> Navigation -> Carter Navigation
# Enable stereo cameras (see isaac_sim_vslam_demo.launch.py for details)

# Start multi-session SLAM
ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py

# Drive robot around area A
# Use Nav2 goals in RViz or keyboard teleop:
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# When done mapping area A, Ctrl+C to stop
```

### 2. Second Mapping Session (Different Location)

```bash
# In Isaac Sim: Pick up robot and place in different location (area B)
# Robot now has NO IDEA where it is!

# DON'T delete database! Start same launch:
ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py

# Robot is "lost" - will build local map of area B
# Drive around area B

# When robot revisits area A (or shared corridor):
# 🎉 LOOP CLOSURE! Maps merge together!
```

### 3. Additional Sessions

```bash
# Repeat: move robot to area C, D, etc.
# Each time: DON'T delete database
# Each area adds to the global map
```

## What You'll See

### Phase 1: Lost Robot (Building Local Map)

```
rtabmap_viz shows:
- New green nodes (robot poses) disconnected from previous map
- Two separate "map islands"
- Robot position uncertain relative to global map
```

### Phase 2: Loop Closure Detection

```
When robot recognizes previous area:
- Pink/magenta line appears between old and new map areas
- Maps suddenly snap together
- Robot knows global position
- Single unified map
```

### Phase 3: Continued Mapping

```
- Robot adds new nodes to unified map
- Navigation works globally
- Can receive Nav2 goals anywhere in merged map
```

## Visual Odometry Options

Choose based on your needs:

### Option A: Isaac VO (Recommended for Multi-Session)

```bash
ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py vo:=isaac
```

**Best for:**
- Fast, accurate odometry (60+ Hz)
- Low drift between sessions
- Reliable loop closure detection
- Production deployments

**Note:** Must disable Isaac Sim's wheel odometry TF (see isaac_sim_vslam_demo.launch.py comments)

### Option B: RTAB-Map VO

```bash
ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py vo:=rtabmap
```

**Best for:**
- Understanding traditional visual odometry
- Customizing VO parameters
- Systems without NVIDIA GPU

### Option C: Wheel Odometry Only

```bash
ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py vo:=none
```

**Best for:**
- Testing loop closure with noisy odometry
- Showing importance of good odometry

## Key Differences from Standard Isaac Demo

| Feature | Standard Demo | Multi-Session Demo |
|---------|--------------|-------------------|
| Database | Deleted on start (`-d` flag) | **Preserved** between runs |
| Loop Closure | Proximity-based | **Global** (entire map) |
| Starting Position | Known (near previous) | **Unknown** (anywhere) |
| Use Case | Single session mapping | **Multiple** session mapping |

## Critical Parameters (What Makes It Work)

```python
# In isaac_vslam_multisession.launch.py:

'RGBD/ProximityBySpace': 'false',      # 🔑 Search entire map, not just nearby
'Kp/TfIdfLikelihoodUsed': 'false',     # Don't use location priors
'Bayes/FullPredictionUpdate': 'true',  # Full Bayesian update
'Mem/RehearsalSimilarity': '0.30',     # Visual similarity threshold
'RGBD/OptimizeFromGraphEnd': 'true',   # Optimize from newest data
'Optimizer/Strategy': '2',              # GTSAM for large graphs
```

## Monitoring Multi-Session Mapping

### Check Loop Closure Status

```bash
# Watch for loop closures
ros2 topic echo /rtabmap/info | grep loop

# Output when loop closure detected:
# loop_closure_id: 142
# loop_closure_transform: [x, y, z, ...]
```

### Monitor Map Size

```bash
# Number of nodes in map
ros2 topic echo /rtabmap/info | grep nodes

# Memory usage
ros2 topic echo /rtabmap/info | grep memory
```

### View Statistics

```bash
# Full RTAB-Map info
ros2 topic echo /rtabmap/info
```

## Troubleshooting

### Problem: Maps Don't Merge

**Symptoms:**
- Drove through same area, no loop closure
- Two separate map islands remain

**Solutions:**
1. Ensure areas have **visual features** (not blank walls)
2. Drive **slower** through overlap area
3. Reduce `Mem/RehearsalSimilarity` (e.g., 0.25) for stricter matching
4. Check if areas actually overlap in 3D space

### Problem: False Loop Closures

**Symptoms:**
- Maps merge incorrectly
- Distorted/twisted map after merge

**Solutions:**
1. Increase `Mem/RehearsalSimilarity` (e.g., 0.35) for looser matching
2. Increase `Vis/MinInliers` (e.g., 15) for more reliable matches
3. Add more visual features to environment

### Problem: Database Too Large

**Symptoms:**
- RTAB-Map slows down over many sessions
- High memory usage

**Solutions:**
1. Set memory management parameters:
   ```python
   'Mem/STMSize': '30',              # Short-term memory size
   'Mem/ImageKept': 'false',         # Don't keep all images
   'Mem/IntermediateNodeDataKept': 'false'  # Reduce data storage
   ```

2. Or start fresh:
   ```bash
   rm ~/.ros/rtabmap.db
   ```

## Advanced: Localization Mode

After building complete map, use localization-only mode:

```bash
# Build map across multiple sessions (as above)
# Then switch to localization mode:

ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py \
    localization:=true
```

**Localization mode:**
- No new nodes added to map
- Robot localizes in existing map
- Faster, lower memory
- Good for production navigation

## Performance Tips

1. **Use Isaac VO**: Much faster and more accurate than RTAB-Map VO
2. **GPU acceleration**: Ensure Isaac ROS nodes use GPU (should be automatic)
3. **Limit features**: `Kp/MaxFeatures: 400` balances speed vs accuracy
4. **Reduce image size**: Default 960x600 is good balance

## Comparison to Standard Demo

```bash
# Standard demo (single session):
ros2 launch rtabmap_demos isaac_sim_vslam_demo.launch.py
# - Deletes database each time
# - Fast loop closure (proximity-based)
# - Knows starting position

# Multi-session demo:
ros2 launch rtabmap_demos isaac_sim_multisession_demo.launch.py
# - Keeps database between runs
# - Global loop closure (slower but works from anywhere)
# - Unknown starting position OK
```

## Real-World Applications

### Warehouse Mapping

```bash
# Day 1: Map loading dock area
# Day 2: Map aisle 1-5
# Day 3: Map aisle 6-10
# Day 4: Map office area
# Result: Complete warehouse map
```

### Campus Navigation

```bash
# Session 1: Building A
# Session 2: Building B (start anywhere)
# Session 3: Outdoor paths connecting A and B
# Result: Multi-building navigation
```

### Long-Term Mapping

```bash
# Week 1: Initial map
# Week 2: Add new area
# Month 2: Expand to parking
# Year 1: Complete site coverage
```

## References

- Paper: https://arxiv.org/abs/2407.15305
- Original multi-session demo: `rtabmap_demos/launch/multisession_mapping_demo.launch.py`
- Isaac Sim VSLAM demo: `rtabmap_demos/launch/isaac/isaac_sim_vslam_demo.launch.py`
