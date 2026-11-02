# FAST-LIVO2 重定位增强版（中文说明）

本项目在 FAST-LIVO2 ROS 2 版本的基础上，增加了先验地图定位及多种点云重定位方案。

本文依据当前工作区代码及本地适配说明运行行为。原仓库 `dev` 分支中未合入的历史方案不包含在以下两种模式的主流程中。

当前共享配置为 **无先验建图＋重力对齐**：`locate_in_prior_map=false`、`uav.gravity_align_en=true`，视觉关闭，开启正常退出时的 PCD 保存。重新采集命令见 [cmd.md](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/cmd.md)。切到有先验时，填写有效 `prior_map_path` 并开启定位模式；两阶段初值交接已通过合成联合检查，实机联合精度与长期运行待测。此前独立实机记录见 [重定位测试](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/重定位测试.md)。

本次是否执行重力对齐由 `uav.gravity_align_en` 控制，不再配置或校验先验 PCD 的生成模式。开启时仍由建图保存实际重力旋转 A，使用 `B=T_map_I0×inverse(A)` 处理先验并交接最终 TF；不会重写原 PCD 的坐标。

## 快速启动：雷达、建图与重定位三个入口

**2026-10-30：用户已实机运行，确认 `locate_in_prior_map=false` 时 LIO 部分运行正常。**

当前自定义入口为 [mapping_relocation.launch.py](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/launch/mapping_relocation.launch.py)，默认加载：

- [mapping_relocation.yaml](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation.yaml)：参考 A 工程的算法与 MID360 参数，最初为 `locate_in_prior_map=false`、`img_en=0` 的 LiDAR＋IMU 建图配置；当前为无先验建图并开启重力对齐。
- [camera_parameter.yaml](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/camera_parameter.yaml)：参考 A 工程的 D405 标定，使用 B 工程支持的参数名。当前不启用视觉融合，不需要启动相机；B 仍会读取该相机模型。

建图配置全部 72 项参数的含义、单位和生效条件见 [mapping_relocation 参数说明](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation参数说明.md)。

旧配置及原建图、重定位和顶层组合示例现归档到工作区根目录的 [old](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/old/README.md)，与 `src` 同级。活动包各保留一个当前入口，`old` 不再列入 FAST-LIVO2 安装规则，归档文件仅供对照。

### 终端 1：启动 Livox 驱动

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source install/setup.bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

雷达型号由驱动的 `msg_MID360.yaml` 选择，默认 `mid360`。驱动配置与 SDK 版本要求见后文和驱动包内的 `版本.md`。

### 终端 2：启动自定义建图入口

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source install/setup.bash
ros2 launch fast_livo mapping_relocation.launch.py
```

该 launch 只将两个配置传给 FAST-LIVO2，并启动可选 RViz；`locate_in_prior_map` 由节点自身读取。launch 不解析模式、不检查先验地图、不启动 `teaser_gicp_node` 或地图对齐 TF 发布器。普通建图模式不要求先验 PCD；后续定位模式需要另行启动外部重定位和地图对齐 TF 节点。RViz 默认开启，始终使用 `fast_livo` 安装目录中的 `rviz_cfg/fast_livo2.rviz`；关闭可追加 `enable_rviz:=false`。

### 终端 3：启动重定位与地图 TF 入口

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source install/setup.bash
ros2 launch relocalization relocalization.launch.py
```

此入口与建图入口默认读取同一份 `fast_livo` 安装目录中的 `config/mapping_relocation.yaml`，提取模式、地图路径及定位模式需要的外参和重力对齐开关，自动选择 TF 初值来源；配准算法参数仍在重定位 launch 内维护。三个入口都不需要额外启动参数。

有先验且开启重力对齐时，重定位成功先提供初始 IMU 位姿，建图完成 IMU、重力与先验初始化后发布 `/fast_livo2/initial_map_pose`，TF 发布器据此建立最终变换。保持静止直到建图打印 `Published /fast_livo2/initial_map_pose after prior-map initialization; the device may now move.`；`false` 时才跳过匹配并提供单位 TF 与空点云。模式和地图路径在共享 YAML 中修改，再重新安装并重启相关入口，无需在命令中重复填写。重定位入口保留默认 5 秒启动延时，可选 `start_delay:=0.0`。

启动命令默认读取安装目录中的两个 YAML。修改源码配置后，需在 B 工作区执行 `colcon build --packages-select fast_livo` 更新安装文件；也可以直接指定源码配置：

```bash
ros2 launch fast_livo mapping_relocation.launch.py \
  config_file:=/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation.yaml \
  camera_file:=/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/camera_parameter.yaml
```

若显式覆盖建图入口的 `config_file`，重定位入口也需显式传入同一 `config_file`；两个独立的 ros2 launch 不会传递彼此的命令行参数。正常使用默认配置时不需要覆盖。

`time_check.enabled` 默认 `true`。建图节点在初始化输出文件和传感器订阅之前检查系统时钟同步状态：通过时打印完整本地日期、时间、时区和本次地图前缀；未同步、时钟异常或查询失败时立即打印原因并以错误码 1 退出，不进入建图。检查只读、不自动联网校时或修改时钟。设为 `false` 可跳过，并会提示时间未经校验；此开关不控制独立的驱动或重定位节点，也不负责传感器时间戳同步。

`pcd_save.pcd_save_en` 当前为 `true`，无先验模式允许保存；切到有先验模式后，`save_in_localization=false` 会关闭有效 PCD 保存。独立重定位节点始终只读地图。切回普通建图后，`interval=-1` 会在正常结束时将累积观测写到 `/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_MMDD_HHMM.pcd`。前缀在校验通过后按启动时的系统本地时间固定，例如 `map_1102_1509`；跨分钟或跨日继续沿用该前缀。正数间隔分段时文件依次为 `map_1102_1509_0001.pcd`、`map_1102_1509_0002.pcd`，位姿记录为 `map_1102_1509_scans_pos.json`。同名文件允许覆盖，不清理其他文件。`pcd_save.output_dir` 控制绝对目录，开启保存时自动创建；改变位置只需修改该参数并更新安装配置。建图等待初值的修复与剩余边界见 1.2，不能将普通建图或独立重定位的实机确认视为完整有先验建图已验证。

## 1. 两种运行模式分别执行什么操作

两种模式由 FAST-LIVO2 节点启动时读取的 `locate_in_prior_map` 参数控制。切换模式后需要重新启动节点。

| 对比项 | 建图模式 | 先验地图定位模式 |
| --- | --- | --- |
| `locate_in_prior_map` | `false`，也是代码默认值 | `true` |
| 是否需要已有地图 | 不需要 | 需要可读取的 PCD 先验地图 |
| 是否需要外部重定位初始位姿 | 不需要 | 需要通过 `/icp_result` 接收 |
| 体素地图初始化来源 | 本次运行的实时点云 | 加载并变换后的先验地图 |
| 后续状态估计 | 将实时点云与逐步建立的地图匹配 | 将实时点云与先验地图匹配 |
| 是否向体素地图插入实时观测 | 是 | 否 |
| PCD 保存 | 由 `pcd_save.pcd_save_en` 控制 | 总开关和 `pcd_save.save_in_localization` 同时开启才保存本次观测 |
| 典型用途 | 首次扫描环境，建立地图 | 重新启动后，在已有地图中确定位置并持续定位 |

### 1.1 建图模式

**目标：在估计自身运动的同时，使用本次采集的数据建立并更新地图。**

#### 配置方式

原示例配置文件现归档为 [old/config/avia.yaml](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/old/config/avia.yaml)。该文件没有显式填写 `locate_in_prior_map`，因此使用代码默认值 `false`。当前自定义建图使用前述 `mapping_relocation.yaml`。

也可以在 ROS 2 参数文件中显式设置：

```yaml
/**:
  ros__parameters:
    locate_in_prior_map: false
```

#### 执行流程

1. **接收传感器数据。** 接收激光雷达和 IMU 数据；启用图像输入时，还会接收相机图像。
2. **进行预处理与初始化。** 筛选点云、同步传感器数据，完成 IMU 初始化和点云运动畸变补偿；开启重力对齐时执行重力对齐。
3. **建立初始体素地图。** 将首个用于建图的有效点云转换到本次运行的局部参考系，用它初始化体素地图。
4. **估计当前位姿。** 使用 IMU 传播结果作为预测，将后续实时点云与已有体素地图匹配，更新状态估计。启用视觉时，还会执行视觉观测更新。
5. **更新地图。** 将实时观测插入体素地图，增加或更新地图中的几何信息。开启滑动地图时，还会执行地图滑动和远处体素裁剪。
6. **发布运行结果。** 发布局部里程计、轨迹、变换后的点云及对应 TF；其他可视化和状态输出受各自配置及运行条件控制。
7. **按配置保存点云。** 开启 PCD 保存后，累积并写出点云文件，供后续查看或作为先验地图使用。

```text
激光雷达 / IMU / 可选相机
          ↓
预处理、同步、初始化、运动畸变补偿
          ↓
用实时点云初始化体素地图
          ↓
后续点云与地图匹配，更新位姿
          ↓
向体素地图插入实时观测
          ↓
发布结果，按配置保存点云
          ↺ 持续处理后续数据
```

#### 地图与输出说明

- 主要局部参考系为 `camera_init`，机体位姿通过 `camera_init → aft_mapped` TF 和 `/aft_mapped_to_init` 里程计输出。
- 原 `avia.yaml` 示例中的 `pcd_save.pcd_save_en` 为 `false`；当前自定义 `mapping_relocation.yaml` 已设为 `true`。**运行建图模式不会自动保证生成 PCD 文件**，还需满足输出目录、有效缓存和正常结束等保存条件。
- 开启保存且 `pcd_save.interval: -1` 时，正常结束处理循环后保存整段累积点云；输出为 `/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_MMDD_HHMM.pcd`，前缀取启动时的本地日期与时分，目录由 `pcd_save.output_dir` 控制并自动创建。正数间隔按处理帧分段；退出不补存剩余不足一段的点云，`interval=0` 不用于关闭保存。
- 建图模式本身不生成 `map → camera_init` 的全局对齐关系。只有外部提供该 TF 时，节点才会进一步发布 `/aft_mapped_in_map`。

### 1.2 先验地图定位模式

**目标：加载已建立的地图，在完成初始重定位后，持续估计自身在该地图中的位置。**

#### 配置方式

原示例配置文件现归档为 [old/config/avia_relocation.yaml](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/old/config/avia_relocation.yaml)，关键参数如下：

```yaml
/**:
  ros__parameters:
    locate_in_prior_map: true
    prior_map_path: "/absolute/path/to/your_map.pcd"
```

`prior_map_path` 需要替换为实际存在的 PCD 地图绝对路径。当前示例文件仍使用作者电脑上的路径，不能直接用于其他机器。

当前 `teaser_gicp_node` 与 FAST-LIVO2 从同一份 `mapping_relocation.yaml` 获取 `locate_in_prior_map` 和 `prior_map_path`，定位模式还共用其中的 LiDAR→IMU 外参和重力对齐开关，两个默认入口无需分别传值。旧 ICP／单独 TEASER 等其他节点仍保留各自原有地图参数接口。

#### 执行流程

以下是代码实现的定位流程；启动等待、初始化异常处理与初值坐标修复及验证边界见本节末尾。

1. **分别加载地图。** 重定位与建图各自读取同一路径 PCD，并按自己的参数降采样，点云此时仍在原 `map` 系中。
2. **重定位提供初始 IMU 位姿。** TEASER/VGICP 匹配原始雷达点，得到 `T_map_lidar`；结合共享外参，通过 `/icp_result` 发布 `T_map_I0 = T_map_lidar × inverse(T_imu_lidar)`。
3. **建图初始化 IMU。** 收到有效初值后允许传感器处理；完成 IMU 初始化后，若开启重力对齐，由建图计算并保存实际旋转 `A = T_camera_init_I0`，关闭时 A 为单位矩阵。
4. **统一最终变换。** 建图计算 `B = T_map_camera_init = T_map_I0 × inverse(A)`，用 `inverse(B)` 将先验点云转换到本次局部系，再构建体素地图。
5. **成功后发布最终初值。** 仅在体素构建成功后发布 `/fast_livo2/initial_map_pose`（Reliable、Transient Local）。当前重力开启时，TF 发布器只接收该最终结果并广播 `map → camera_init`；重力关闭时保留原先直接接收 `/icp_result` 的路径。
6. **持续定位。** 实时点云按 `T_camera_init_imu(t) × T_imu_lidar` 变换到局部系，与同系先验体素匹配；局部位姿再乘 B，得到 `/aft_mapped_in_map`。定位模式跳过实时地图插入，当前滑动地图关闭。
7. **按开关处理保存。** 当前禁止定位模式保存；即使以后允许，也仅保存本次局部系观测，不自动合并先验或改写原 PCD。

```text
重定位：PCD + 实时雷达 → 初始 IMU 在 map 中的位姿
                               ↓ /icp_result
建图：加载 PCD → 等初值 → IMU 初始化 → 实际重力旋转 A
                               ↓
                  最终 B → 先验换系 → 体素构建成功
                               ↓ /fast_livo2/initial_map_pose
                         map → camera_init TF
                               ↓
                         持续定位与全局输出
```

#### 重定位与持续定位的分工

- **外部重定位节点**负责确定启动时当前雷达点云与先验地图之间的初始对齐关系。
- **FAST-LIVO2**负责接收该初值，并使用先验体素地图执行后续连续定位。
- 当前主分支的 `teaser_gicp_node` 和 `small_gicp_node` 在定位成功、发布结果后会退出。初始化阶段的 GICP 失败回退，不等同于后续 FAST-LIVO2 定位丢失时能够自动重新启动全局重定位。
- 建图入口不会自动启动外部重定位节点；历史组合示例现位于 `old/launch_top`，仅供源码对照。
- 独立的 [relocalization.launch.py](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/relocalization/launch/relocalization.launch.py) 启动 `transform_publisher` 和 `teaser_gicp_node`，从建图 YAML 读取模式、地图路径，以及定位模式所需外参和重力对齐开关。`false` 时输出单位 TF 与空点云；切到 `true` 时需填写有效地图，此前实机仅测试外部配准，后续另有合成联合检查。完整启动方法及旧 SAC-IA 问题说明见 [relocalization/README.md](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/relocalization/README.md)。
- 定位模式需 `pcd_save_en` 和 `save_in_localization` 同时开启才累积和保存本次观测；当前后者为 `false`，禁止保存。开启后也不自动保存或合并先验地图，不表示开启了先验体素地图更新。

#### 建图等待初值的修复与剩余边界

2026-11-02 已修复 `LIVMapper::run()` 等待初值时提前退出的问题：先处理订阅回调，再判断是否等待初值；等待时使用 100 Hz 的墙上时钟限频，不执行数据同步、IMU 初始化或状态估计。已有传感器回调仍在初值前丢弃输入；收到初值后恢复原有处理流程。无先验建图不进入该等待分支，正常同步等待仍保持原 5000 Hz 设置。

隔离 ROS 域验证了持续等待和 SIGINT 正常退出、初值前丢弃传感器输入、延迟初值回调接收后恢复传感器与主循环处理，以及无先验模式不要求初值。

随后已修复初始化异常处理：有先验建图遇到空路径、PCD 读取失败、空地图或非有限 XYZ 时明确报错，降采样结果也须非空且坐标有限；体素地图只在输入和必要参数合法、实际构建成功且非空后设置初始化完成标志。初始化失败时关闭 ROS 并以错误码 1 退出，不再带着失败状态继续运行。27 项检查覆盖实际安装程序的地图异常退出、有效地图等待、无先验模式以及实际初始化函数的失败和成功分支。

随后在重定位节点中增加 `/icp_result` 发送后的 ACK 等待：真实配准成功发布一次位姿后，最多等待 2 秒，确认、超时、无订阅者或接口异常均有明确日志，之后退出；关闭重定位时的周期占位输出保持不变。接收端由 DDS 自动处理 ACK，建图与 TF 发布器代码、配置及 launch 无需修改。5 项隔离检查验证了正常接收及 TF、无订阅者、真实超时、接口异常和关闭模式。仍应先启动建图并确认等待，再启动重定位；传输 ACK 不代表建图初始化完成，也不能补收发布者退出后的历史消息。

已进一步支持重力对齐：当前 `/icp_result` 是初始 IMU 位姿，建图结合自己实际测得的重力旋转计算最终 `map → camera_init`，用同一结果处理先验地图并在体素构建成功后发布最终话题。重定位和 TF 发布器无需独立估计重力，也不会提前广播未修正的 TF。固定局部系仍为 `camera_init`，它与初始 IMU 系仅在关闭重力对齐时重合。

当前 YAML 已开启重力对齐，三个无参数启动命令保持不变；需启用 IMU 并静止到初始化完成。25 项隔离检查覆盖倾斜启动、非单位外参、最终位姿／TF／先验点云一致性、延迟 TF 和保留消息、错误与重复初值、失败退出，以及关闭对齐和无先验模式。测试使用合成数据，未进行新的实机采集或精度验证。原地图不改写，RViz 配置不改，运动启动和后续自动重定位未实现。接口含义见 [relocalization/README.md](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/relocalization/README.md)。

## 2. 通过配置选择 MID360 或 MID360S 驱动

统一启动入口是 `livox_ros_driver2` 包中的 `msg_MID360_launch.py`。它读取包内 `config/msg_MID360.yaml`，根据 `lidar_model` 选择设备 JSON，每次启动一个型号。

| `lidar_model` | 设备配置文件 | JSON 设备键 |
| --- | --- | --- |
| `mid360`（默认） | `config/MID360_config.json` | `MID360` |
| `mid360s` | `config/MID360s_config.json` | `Mid360s` |

例如，使用 MID360S 时将 YAML 中这一行改为：

```yaml
lidar_model: mid360s
```

型号选择不区分大小写，填入其他型号时启动会明确报错。YAML 的 `driver_parameters` 集中保存点云格式、发布频率和 frame_id 等驱动参数，设备 IP 与端口仍在各自 JSON 内配置；`user_config_path` 由型号自动选择。

初次修改启动文件或设备 JSON 后，先在工作区根目录编译并加载环境：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select livox_ros_driver2
source install/setup.bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

默认命令读取安装目录中的 YAML。如果想直接编辑源码中的 YAML 并立即应用，可指定该文件，之后仅切换型号或调整 YAML 参数无需重新编译：

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py config_file:=/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/livox_ros_driver2/config/msg_MID360.yaml
```

设备 JSON 仍从包安装目录读取，修改源码中的 JSON 后需要重新构建驱动包。切换型号后应结束原驱动进程，再重新启动；本入口不提供运行中的热切换。

2026-10-29 检查：两份 JSON 均通过本机 SDK2 1.5.2 的解析器与参数检查，使用雷达 `192.168.2.3`、主机 `192.168.2.50`，适用于分别切换设备。检查时本机已启用网卡中未配置 `192.168.2.50`，连接雷达时需确保对应网卡具有该地址。两种型号的启动参数生成及无效型号报错已验证，整个工作区 8 个包构建通过；未进行实机收包验证。
