# 建图与重定位建图命令

第 1～5 节用于 **无先验建图＋开启重力校正＋LiDAR/IMU 输入**，持续运行需两个终端：雷达驱动、建图。第 6～11 节用于 **有先验建图＋重定位＋开启重力校正，不保存 PCD**；第 12 节在此基础上开启本次观测保存。两种有先验测试都需三个终端：雷达驱动、建图、重定位，可另开第四个终端检查输出。以下命令供手动执行，本文不会自动修改配置或启动设备。

## 1. 采集前准备

先在原有终端中用 `Ctrl+C` 结束上一次建图、重定位及其 TF 发布器，等待进程退出。将雷达放稳，初始化完成前保持静止。

在终端 2 编辑建图配置：

```bash
nano /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation.yaml
```

将对应参数设置为下面的值，保留文件中的其余配置。以下是字段摘录，不要用它替换整个配置文件；`nano` 中按 `Ctrl+O`、回车保存，再按 `Ctrl+X` 退出。

```yaml
/**:
  ros__parameters:
    locate_in_prior_map: false
    prior_map_path: ""

    time_check:
      enabled: true

    common:
      img_en: 0
      lidar_en: 1

    imu:
      imu_en: true
      gravity_est_en: true

    uav:
      gravity_align_en: true

    pcd_save:
      pcd_save_en: true
      save_in_localization: false
      output_dir: "/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD"
      colmap_output_en: false
      interval: -1
```

`locate_in_prior_map=false` 才会从实时观测建立、更新新地图。此时 `save_in_localization=false` 不影响保存；`interval=-1` 表示正常退出时保存整段累积点云。

核对系统时间：

```bash
timedatectl status
```

确认日期、时间和时区正确，查看 `System clock synchronized`。建图节点还会自行检查系统时钟状态，只有打印“时间校验通过”才继续；失败时应先完成系统校时，再重新启动。

更新安装配置，构建成功后再执行后面的启动命令：

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
colcon build --packages-select fast_livo
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
```

雷达型号在下面的驱动配置中选择，当前为 `mid360`：

```bash
nano /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/livox_ros_driver2/config/msg_MID360.yaml
```

`lidar_model` 可填写 `mid360` 或 `mid360s`，设备和主机 IP 使用对应 JSON 中的配置。如果修改了驱动 YAML 或 JSON，启动前再更新驱动安装副本：

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
colcon build --packages-select livox_ros_driver2
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
```

## 2. 终端 1：启动雷达驱动

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

保持此终端运行。检查启动日志选择的型号与设备一致。

## 3. 终端 2：启动无先验建图

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
ros2 launch fast_livo mapping_relocation.launch.py
```

两个入口默认读取安装目录的配置，不需要附加参数。建图入口同时启动 RViz；本次以 `camera_init` 为 Fixed Frame 查看 `/cloud_registered`。若不需要 RViz，可给建图命令追加 `enable_rviz:=false`。

启动后保持静止，确认：

- 打印“时间校验通过”，并记录“本次地图文件前缀：map_MMDD_HHMM”。
- 打印 `Gravity Alignment Finished`。
- 随后持续出现 `[ LIO ] Update Voxel Map (mapping mode)`，并在 RViz 中看到正常点云。

满足上述条件后开始缓慢移动采集。无先验建图不等待 `/icp_result`，也不会打印有先验初始化流程的 “the device may now move” 提示。

如果持续打印 `Waiting for initial pose...`，说明仍处于有先验模式，应停止建图，检查 `locate_in_prior_map=false` 是否已更新到安装副本。

## 4. 可选终端 3：运行中核对参数与输出

```bash
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash

ros2 param get /laserMapping locate_in_prior_map
ros2 param get /laserMapping uav.gravity_align_en
ros2 param get /laserMapping pcd_save.pcd_save_en
ros2 param get /laserMapping pcd_save.interval
ros2 param get /laserMapping pcd_save.output_dir
```

预期依次为 `false`、`true`、`true`、`-1` 和本工作区的绝对 PCD 目录。

查看建图里程计是否持续输出：

```bash
ros2 topic hz /aft_mapped_to_init
```

此命令持续运行，按 `Ctrl+C` 仅结束本终端的频率检查。

## 5. 结束采集并保存

1. 先在终端 2 按一次 `Ctrl+C`，让建图正常结束，等待写盘完成。
2. 确认终端出现 `Raw point cloud data saved to: ... with point count: ...`，并等待建图进程退出。
3. 再在终端 1 按 `Ctrl+C` 停止雷达驱动。

当前 LiDAR/IMU 模式的整图保存位置为：

```text
/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_MMDD_HHMM.pcd
```

日期和时分取建图启动时的本地时间，整次运行固定。例如 11 月 2 日 15:09 启动，保存为 `map_1102_1509.pcd`。同一分钟内重复启动会使用相同文件名，并可能覆盖同名文件；如需保留，重新采集前先备份该文件。目录中的其他文件不会自动删除。

不要通过强制杀进程或直接关闭终端结束采集；退出保存依赖正常结束流程。如果没有有效点云缓存，不会生成整图文件。

查看地图文件，按修改时间从新到旧排列，并与终端记录的本次前缀核对：

```bash
ls -lht -- /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/*.pcd
```

如果要采集未重力校正的地图，在无先验建图前将 `uav.gravity_align_en` 改为 `false`。该模式不会出现 `Gravity Alignment Finished`，应以 IMU 初始化完成和持续更新地图确认可以采集。

## 6. 有先验建图：配置与构建

以下以本工作区新生成的地图为例：

```text
/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_1102_2214.pcd
```

先在原终端中用 `Ctrl+C` 结束上次建图、重定位及其 TF 发布器，等待进程退出。把雷达放在该地图覆盖的区域内，保持静止直到本次先验初始化完成。

在准备终端或终端 2 编辑共享配置：

```bash
nano /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation.yaml
```

修改下列对应字段，保留所有其他参数，特别是 LiDAR→IMU 外参。以下仍为字段摘录，不能替换整个文件：

```yaml
/**:
  ros__parameters:
    locate_in_prior_map: true
    prior_map_path: "/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_1102_2214.pcd"

    time_check:
      enabled: true

    common:
      img_en: 0
      lidar_en: 1

    imu:
      imu_en: true

    preprocess:
      filter_size_map: 0.1

    uav:
      gravity_align_en: true

    pcd_save:
      pcd_save_en: true
      save_in_localization: false
      colmap_output_en: false
```

`save_in_localization=false` 使本次有先验建图不累积或保存 PCD；独立重定位节点始终只读地图。当前有先验实现利用先验持续定位，不向先验体素地图插入新观测扩图。若换用其他 PCD，替换上述绝对路径即可；本次是否重力校正由 `uav.gravity_align_en` 控制。

先验降采样保持 `filter_size_map=0.1`。2026-11-02 用户已确认旧图 `1549`、重力关闭时，改用该值后持续定位不再漂移；原 `0.5` 会使该图的先验过稀，离线检查没有可用平面。该次实机确认不等于开启重力校正的测试已经通过。

核对地图文件和系统时间，再构建安装。后面的两个入口默认读取同一份安装配置，无需在启动命令中重复填写地图路径：

```bash
ls -lh -- /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_1102_2214.pcd
timedatectl status

cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
colcon build --packages-select fast_livo relocalization
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
```

确认构建成功后，按终端 1、终端 2、终端 3 的顺序启动。雷达型号仍在 `msg_MID360.yaml` 中选择；如果改过驱动配置，先按第 1 节更新驱动安装副本。

## 7. 有先验建图：终端 1 启动雷达驱动

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

保持雷达静止，保留此终端运行。

## 8. 有先验建图：终端 2 启动建图

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
ros2 launch fast_livo mapping_relocation.launch.py
```

确认时间校验通过、先验地图正常加载，出现：

```text
Waiting for initial pose...
```

这是正常等待。此时再启动终端 3，不要移动雷达。建图入口仍会启动 RViz；重定位成功之前，开启重力校正的流程尚未发布最终 `map → camera_init` TF。

## 9. 有先验建图：终端 3 启动重定位

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
ros2 launch relocalization relocalization.launch.py
```

该入口启动 TF 发布器，并默认延时 5 秒启动 TEASER++／VGICP 配准节点。先加载地图、计算特征，再用实时雷达点云粗定位和精配准。首次验证自动粗定位时，不要使用 RViz 的 `2D Pose Estimate` 工具；手动初值会跳过 TEASER 阶段。

观察两个终端的日志：

1. 终端 3：TEASER 成功后切换 GICP，最终出现 `LOCALIZATION SUCCESS!`，发布 `/icp_result`。
2. 终端 2：出现 `Initial pose received.`，开始本次传感器初始化，随后出现 `Gravity Alignment Finished`。
3. 终端 2：先验体素构建成功，出现 `Initialized voxel map from prior map (locate_in_prior_map).`。
4. 终端 2：最终出现以下提示，才表示可以开始移动：

```text
Published /fast_livo2/initial_map_pose after prior-map initialization; the device may now move.
```

此后缓慢移动，检查实时点云是否与先验环境对齐，以及里程计是否持续输出。RViz 可使用 `Fixed Frame=map`，添加 `/prior_map`（Reliable、Transient Local）和 `/cloud_registered` 观察先验与实时点云。

配准进程成功后会退出，终端 3 中的 TF 发布器仍继续运行；保留终端 3。`LOCALIZATION SUCCESS!` 和传输 ACK 都不代表建图初始化已经完成，应等待上面的最终提示。`/icp_result` 为一次性 Volatile 消息，所以建图接收端必须先就绪；若重定位结束后建图仍等待初值，先停止并重新启动终端 3，本次仍保持静止。

## 10. 可选终端 4：检查参数、最终位姿与 TF

加载环境并确认实际使用的配置：

```bash
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash

ros2 param get /laserMapping locate_in_prior_map
ros2 param get /laserMapping prior_map_path
ros2 param get /laserMapping uav.gravity_align_en
ros2 param get /laserMapping pcd_save.save_in_localization
```

预期依次为 `true`、本次先验绝对路径、`true`、`false`。如果不一致，应先停止相关入口，检查源码配置是否构建安装，然后重新启动。

在建图进程仍运行时，读取最终位姿；使用 Transient Local 可以接收已经发布并保留的结果：

```bash
ros2 topic echo /fast_livo2/initial_map_pose geometry_msgs/msg/PoseWithCovarianceStamped \
  --qos-reliability reliable \
  --qos-durability transient_local \
  --once
```

该命令收到一次结果后退出。若初始化尚未完成，会继续等待。

查看固定的地图对齐 TF：

```bash
ros2 run tf2_ros tf2_echo map camera_init
```

确认输出后按 `Ctrl+C` 停止本终端的检查，再检查地图系里程计是否持续发布：

```bash
ros2 topic hz /aft_mapped_in_map
```

此命令也持续运行，按 `Ctrl+C` 结束。最终 TF 应保持固定，地图系里程计则随设备运动变化。只有成功日志还不足以确认配准正确，还应结合点云对齐效果与实际运动判断。

## 11. 结束有先验建图

1. 在终端 2 按 `Ctrl+C`，等待建图进程退出。
2. 在终端 3 按 `Ctrl+C`，结束 TF 发布器及仍存活的配准进程。
3. 在终端 1 按 `Ctrl+C`，停止雷达驱动。
4. 停止可选终端 4 中的检查命令。

按上述保存配置，本次不会写出整图、分段或分段位姿记录，也不会把先验复制保存。因此退出时不要求出现无先验采集流程中的 `Raw point cloud data saved to` 提示。

## 12. 开启重力校正，并保存重定位后的本次观测

本节使用第 7～9 节的三个入口和启动顺序，配置采用本节内容替代第 6 节的旧示例。先验降采样继续使用已验证的 `0.1`。

如果正在重新采集开启重力校正的地图，先按第 1～5 节完成无先验采集，正常退出建图并确认 PCD 已写盘，再进行本节测试。后续必须使用这次实际保存的新文件；之前的 `2214` 示例若已删除，就不能继续填写该路径。查看可用地图：

```bash
ls -lht -- /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/*.pcd
```

先停止此前的三个入口，再编辑源码配置：

```bash
nano /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation.yaml
```

将对应字段改为以下值，保留其他参数。`prior_map_path` 必须替换为本次实际生成的 PCD 绝对路径，下面的路径只是占位示例；本段不能替换完整 YAML：

```yaml
/**:
  ros__parameters:
    locate_in_prior_map: true
    prior_map_path: "/absolute/path/to/gravity_aligned_map.pcd"

    preprocess:
      filter_size_map: 0.1

    uav:
      gravity_align_en: true

    pcd_save:
      pcd_save_en: true
      save_in_localization: true
      output_dir: "/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD"
      colmap_output_en: false
      interval: -1
```

两个保存开关都为 true 才会在有先验模式下保存。该开关只允许累积、写出本次观测，不启用先验体素地图的实时插点，也不会合并先验 PCD。

构建安装并核对安装副本，避免只修改源码而仍使用上次配置：

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
colcon build --packages-select fast_livo relocalization
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash

python3 - <<'PY'
from pathlib import Path
import yaml

path = Path('/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/fast_livo/share/fast_livo/config/mapping_relocation.yaml')
params = yaml.safe_load(path.read_text())['/**']['ros__parameters']
print('安装配置：', path)
print('locate_in_prior_map:', params['locate_in_prior_map'])
print('prior_map_path:', params['prior_map_path'])
print('filter_size_map:', params['preprocess']['filter_size_map'])
print('gravity_align_en:', params['uav']['gravity_align_en'])
print('pcd_save:', params['pcd_save'])
assert params['locate_in_prior_map'] is True, '需要切换为有先验模式'
assert params['uav']['gravity_align_en'] is True, '本节测试需要开启重力校正'
assert params['preprocess']['filter_size_map'] == 0.1, '先验降采样应保留为 0.1'
assert params['pcd_save']['pcd_save_en'] is True and params['pcd_save']['save_in_localization'] is True, '本节需要同时开启两个保存开关'
assert params['pcd_save']['interval'] == -1, '本节使用正常退出时保存整图'
assert Path(params['prior_map_path']).is_file(), '先验不存在，请填写本次实际生成的 PCD 绝对路径'
PY
```

确认输出与上面的目标配置一致，按第 7、8、9 节依次启动雷达驱动、建图、重定位。保持静止，等待重力校正及最终先验初始化提示；随后还应检查 `effective feature num` 持续非零、`average residual` 为有限值，静止观察点云和位姿稳定后再缓慢移动。

可选终端 4 中加载环境并确认实际节点的开关：

```bash
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/install/setup.bash
ros2 param get /laserMapping prior_map_path
ros2 param get /laserMapping preprocess.filter_size_map
ros2 param get /laserMapping uav.gravity_align_en
ros2 param get /laserMapping pcd_save.pcd_save_en
ros2 param get /laserMapping pcd_save.save_in_localization
ros2 param get /laserMapping pcd_save.interval
```

预期为本次新先验的绝对路径、`0.1`、`true`、`true`、`true`、`-1`。第 10 节的最终位姿、TF 和里程计检查仍适用。

记录终端 2 的“本次地图文件前缀”。测试结束时，先在终端 2 按 `Ctrl+C`，等待出现 `Raw point cloud data saved to: ... with point count: ...` 且进程退出，再依次停止终端 3、终端 1。这与第 11 节关闭保存的情况不同。

```bash
ls -lht -- /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/*.pcd
```

按启动前缀找到本次 `map_MMDD_HHMM.pcd`。新文件保存的是本次实时观测在重力对齐后的 **camera_init 局部坐标系** 下的结果；原先验文件保持原样。即使 RViz 使用 `Fixed Frame=map`，保存模块也不会自动把 PCD 转到旧地图的 map 坐标系。因此，离线叠加原先验与新 PCD 时，还需要对应的 `map → camera_init` 变换，不能仅因两个点云都重力对齐就直接按坐标叠加。

当前纯 LIO 模式不生成 RGB 降采样附图，`pcd_save.filter_size_pcd` 不作用于这份整图。没有有效观测缓存时不会生成整图；同一分钟内重启仍可能覆盖同名前缀文件。
