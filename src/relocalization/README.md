# Relocalization

本包用于在 ROS2 环境下，将实时接收到的激光雷达点云与先验地图进行重定位（relocalization）。
实现了多种全局/局部配准算法并可组合使用：基于 TEASER++ 的全局配准（粗定位） + small_gicp（或 GICP）的精细配准，从而在大尺度场景下实现更快速、更精确的重定位。

当前已使用本机 `PCD/map_1102_1549.pcd` 完成独立实机重定位测试。当前共享配置为 `locate_in_prior_map=true`，完整启动步骤、RViz 配置与结果见 [重定位测试](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/重定位测试.md)。本轮不启动 FAST-LIVO2；配准节点不写 PCD。新增 `pcd_save.save_in_localization=false` 控制的是以后 FAST-LIVO2 定位模式下的观测保存，不改变配准程序。

## 主要功能

- 使用 TEASER++（全局鲁棒配准）做初始位姿估计，能在无初值情况下全局检索候选位姿。
- 使用 small_gicp（或 GICP）做局部精配准，基于 TEASER 结果进行跟踪与精化。
- 支持 Livox 原生 CustomMsg、以及标准 `sensor_msgs/PointCloud2`。
- 支持地图与在线点云的降采样以控制速度/精度权衡。
- 可配置的阈值和恢复策略：当 GICP 失败时可回退到 TEASER；也支持手动通过 `initialpose` 触发 GICP。

## 算法来源与致谢

- 基础框架以及 ICP、SAC_IA+ICP 实现来自：
	https://github.com/PolarisXQ/Fast-LIO2-Localization
- 全局配准（TEASER++）参考：
	https://github.com/MIT-SPARK/TEASER-plusplus
- small_gicp (改进版 GICP) 参考：
	https://github.com/koide3/small_gicp

得益于以上工作，本包将全局鲁棒初始化与高效的局部配准结合起来，在重定位精度与速度上相比单一方法有显著提升。

## 依赖（主要）

- ROS 2 Humble（或兼容版本）
- PCL
- Eigen3
- TEASER++（建议开启 FPFH 支持，见下）
- small_gicp
- livox_ros_driver2（可选，若使用 Livox）

注意：TEASER++ 的 FPFH 支持为可选项（CMake 选项 `BUILD_TEASER_FPFH`），若你在使用 TEASER 的 FPFH 功能，请确保在编译 TEASER++ 时启用该选项：

```bash
colcon build --packages-select teaserpp --cmake-args -DBUILD_TEASER_FPFH=ON
```

然后重新编译本包：

```bash
colcon build --packages-select relocalization
source install/setup.bash
```

## 独立重定位入口

`launch/relocalization.launch.py` 提取原组合示例中属于 `relocalization` 包的两个节点；历史示例现位于工作区 `old/launch_top/example_teaser_gicp.launch.py`：

| 启动时机 | 节点 | 作用 |
| --- | --- | --- |
| 立即启动 | `transform_publisher` | 有先验且开启重力对齐时等待建图的 `/fast_livo2/initial_map_pose`；其他模式等待 `/icp_result`，收到对应结果后发布静态 TF |
| 默认延时 5 秒 | `teaser_gicp_node` | 读取 `locate_in_prior_map`；开启时执行 TEASER++ → VGICP，关闭时仅发布单位位姿与空点云 |

提取后保留原示例的配准参数，包括 16 个 GICP 线程、两阶段降采样尺寸和成功判定阈值。该入口只启动这两个节点，不启动 FAST-LIVO2、RViz、相机或 Livox 驱动。当前与建图入口默认读取同一份 `fast_livo` 安装目录中的 `config/mapping_relocation.yaml`，提取模式与地图路径；定位模式还提取 `extrin_calib.extrinsic_R`、`extrin_calib.extrinsic_T` 和 `uav.gravity_align_en`，供初值换算使用。其他建图参数不会传给配准节点，配准参数也不会被建图配置覆盖。

从工作区根目录构建并启动：

```bash
cd /home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra
source /opt/ros/jazzy/setup.bash
colcon build --packages-select fast_livo relocalization
source install/setup.bash

# 模式、地图路径及定位模式所需外参从共享 YAML 读取，无需附加参数
ros2 launch relocalization relocalization.launch.py
```

进行真实重定位时，修改共享的 `mapping_relocation.yaml`：

```yaml
/**:
  ros__parameters:
    locate_in_prior_map: true
    prior_map_path: "/absolute/path/to/your_map.pcd"
```

保留原文件其余配置，更新安装副本后，建图和重定位仍分别执行原来的无参数启动命令。当前共享配置为无先验模式并开启重力对齐；切到有先验时需设置 `locate_in_prior_map=true` 并填写地图路径。开启重定位时还需要实际可读且非空的 PCD 地图。模式与地图路径必须存在，类型分别为 YAML 布尔值和字符串；定位模式要求有效 LiDAR→IMU 外参；开启重力对齐时由建图提供最终参考系旋转。节点发现无效外参、空路径、地图加载失败或地图无点时会报错退出，不会改发单位初值。其他旧算法节点的接口没有一起改名。

不再提供独立的 `locate_in_prior_map`、`prior_map_path` launch 参数，避免与共享 YAML 中的值分离。保留可选 `config_file` 指定其他配置文件；若使用，建图入口也应传入同一文件。配置在启动时读取，修改后需重启两个入口，不会在运行中自动刷新。

`start_delay` 默认 `5.0`，两种模式都沿用，可追加 `start_delay:=0.0` 取消延时。这个定时器只控制配准进程何时启动，不表示 TF 已就绪、重定位已成功或自动启动建图。

| 模式 | 初始化与输入 | 输出及进程行为 |
| --- | --- | --- |
| `false` | 不读取地图、不计算 FPFH、不初始化配准，不建立雷达或 `/initialpose` 订阅 | 启动后立即发布一次，并每秒重复发布：`/icp_result` 位置 `(0,0,0)`、四元数 `(0,0,0,1)`、协方差全 0；`/prior_map` 和 `/transformed_cloud` 都是 `map` 坐标系的空点云。节点保持轻量运行，TF 发布器据此发布单位 `map → camera_init` 静态变换 |
| `true` | 加载地图、计算特征并建立配准，默认订阅 `/livox/lidar`（CustomMsg），也接收 `/initialpose` 手动初值 | 地图和调试点云正常发布，成功后发布真实 `/icp_result`，最多等待 2 秒传输 ACK 后退出配准进程；TF 发布器继续运行。配准失败可能持续重试，无整个任务的超时限制 |

关闭模式每秒重复输出，是为兼容后启动的 TF 发布器及其他订阅者；仍有进程、定时器和少量消息开销，但不会执行点云匹配。单位位姿只是关闭模式的占位输出，不表示真实重定位成功或测量精度。

与 FAST-LIVO2 配合时，默认入口共享模式、地图路径及定位模式所需外参。真实重定位结果仍只在成功时发布一次，不为晚加入的订阅者保留，因此需要接收真实初值的节点应在发布前就绪。2026-11-02 已修复建图等待初值时提前退出和地图初始化异常处理的问题；随后增加 `/icp_result` 发送后的有界 ACK 等待，并完成下述初值坐标换算；真实初值仍只发布一次。普通建图可不启动重定位入口；若需要单位地图 TF 和空点云输出，保持共享配置为 `false` 即可。

真实配准成功时，节点先发布最终位姿和调试点云，再对已有默认 Reliable、Volatile 的 `/icp_result` 调用 `wait_for_all_acked()`，最多等待 2 秒。确认完成则打印 INFO；超时、没有匹配订阅者或接口异常则打印 WARN，说明传输未确认，随后仍正常退出，不增加重发或重试。无订阅者时直接提示并退出，避免把没有接收者误报为确认成功；`false` 模式不执行此等待，仍以 1 Hz 持续输出占位数据。2 秒是代码中的固定上限，无需修改配置或 launch。

ACK 由 DDS 自动处理，接收端由 DDS 自动确认；它只涉及当前匹配接收端的传输确认，不检查指定两个节点是否都在线，不代表回调或建图初始化已经完成，也不保证发布者退出后才启动的节点可以补收结果。因此仍应先启动建图、确认进入等待，再启动重定位。后续初值换算保留了这段 ACK 逻辑，坐标约定见下节。

ACK 增强通过 5 项隔离 ROS 域测试：两个接收端（包括实际 TF 发布器）收到最终位姿与 TF；没有订阅者时明确提示；暂停测试接收进程后实际等待约 2 秒并超时退出；注入 ACK 接口错误后警告退出；`false` 模式继续周期输出、不等待 ACK。使用合成地图和手动初值进入 GICP，验证真实成功出口及传输行为，不属于 TEASER 粗配准或实机精度测试。原地图与配置未变。

共享配置接入后已重新编译安装，并在独立 ROS 通信域中验证：完全不附加参数启动时，节点读到安装 YAML 中的实际模式和路径，输出单位位姿、空点云与单位 TF；临时 YAML 切到 `true` 并指定 700 点合成 PCD 后，节点正确加载地图并完成 FPFH／配准初始化，其他 YAML 字段不会覆盖原配准参数。此前节点分支的空路径、无效地图和后加入订阅测试结果仍保留。此前测试未启动硬件驱动；本次已复用实机驱动完成独立 TEASER→VGICP 配准，并接收最终位姿与 TF；该次实机测试未联合运行 FAST-LIVO2，后续合成联合检查见下节。

本次是否执行重力对齐由 `uav.gravity_align_en` 控制，不再配置或校验先验 PCD 的生成模式。开启时仍由建图保存实际重力旋转 A，使用 `B=T_map_I0×inverse(A)` 处理先验并交接最终 TF；不会重写原 PCD 的坐标。

### 初值交接与重力对齐

2026-11-02 已支持 `uav.gravity_align_en=true`，无需额外声明先验地图的重力属性。约定 `T_A_B` 将 B 系点坐标转换到 A 系，`I0` 为初始 IMU 参考系，`C` 为固定的 `camera_init`：

```text
重定位：T_map_I0 = T_map_lidar × inverse(T_imu_lidar)
建图：  A = T_C_I0（本次 IMU 初始化得到的重力旋转；关闭对齐时 A=I）
最终：  B = T_map_C = T_map_I0 × inverse(A)
先验：  p_C = inverse(B) × p_map
```

`/icp_result` 现在统一表示初始 IMU 在 map 中的位姿；`header.frame_id` 仍为 `map`。建图先接收该结果以允许传感器处理，再完成 IMU 初始化和重力对齐，保存实际使用的 A，用 B 的逆变换处理先验点云并构建体素地图。只有构建成功后才发布最终位姿；建图计算 B 不等待 TF，因此不存在相互等待。

| 话题 | 发布者 | 内容、接收者与 QoS |
| --- | --- | --- |
| `/icp_result` | `teaser_gicp_node` | `PoseWithCovarianceStamped`，`T_map_I0`，建图接收以启动初始化；默认 Reliable、Volatile，真实结果一次，保留最长 2 秒 ACK 等待 |
| `/fast_livo2/initial_map_pose` | `laserMapping` | 同类型，`T_map_C`，先验体素地图初始化成功后发布一次；Reliable、Transient Local、depth=1。发布者存活时，晚加入且采用相同持久性策略的订阅者可以接收保留结果 |
| `/tf_static` | `transform_publisher` | `map → camera_init` 的最终 B；有先验且重力对齐开启时只从上一话题取值，不提前使用 `/icp_result` |

重定位 launch 根据共享 YAML 自动设置 TF 发布器的 `initial_pose_topic` 和 `initial_pose_transient_local`。仅在 `locate_in_prior_map=true` 且 `gravity_align_en=true` 时选择建图最终位姿与 Transient Local；其他模式保留直接订阅 `/icp_result` 的原有路径。重力关闭时 A=I，`T_map_I0` 与 `T_map_C` 相同；先验建图仍会在成功后发布最终话题。无先验模式不要求初值，也不发布这个先验初始化结果；重定位关闭时仍每秒输出单位位姿、空点云和单位 TF。

初始化期间须保持静止。只有看到建图日志 `Published /fast_livo2/initial_map_pose after prior-map initialization; the device may now move.` 才表示已完成该阶段；重定位日志 `LOCALIZATION SUCCESS!` 或传输 ACK 不代表建图初始化完成。有效初值只接受一次，后续重复结果被忽略；错误 frame、非有限位置、无效四元数会被拒绝，继续等待有效结果。重力为零／非有限、体素构建失败时建图以错误码 1 退出，不发布最终位姿；该最终路径的 TF 也不发布。

外参要求不变：`extrinsic_R` 为按行排列的 9 个有限数值，满足正交旋转矩阵和行列式 +1（容差 `1e-6`）；`extrinsic_T` 为 3 个有限数值、单位米，表示雷达原点在 IMU 系中的位置。定位模式缺失外参报错；开启重力对齐还要求建图 `imu.imu_en=true`。协方差保留既有占位值，不是重力旋转不确定性的传播结果。

GICP 初值、迭代和调试点云保持原始雷达配准变换，手动 `/initialpose` 仍输入雷达在地图中的位姿。重定位与建图各自读取同一 PCD，先验只在内存中换系；不会自动旋转原 PCD 的地图坐标系。当前定位保存开关关闭；以后允许保存时，仍仅保存本次 C 系观测，不自动合并先验。

独立运行雷达＋重定位＋RViz 时仍可取得 `/icp_result` 和两个 map 系点云。开启重力对齐但不启动建图时，TF 发布器会等待最终位姿，不产生 `map → camera_init`；使用 `Fixed Frame=map` 检查配准即可。独立测试的历史 TF 数值来自重力支持之前，不代表本次流程。运动交接、初始化后重新重定位及长期实机运行不在本次验证范围内。

25 项隔离检查通过：四种 launch 路由、倾斜静止启动、非单位外参、原始初值／最终位姿／TF 的先后顺序、全局里程计和注册点云、晚加入订阅与晚启动 TF、重复或无效初值、无效重力与体素构建失败，以及关闭对齐和无先验模式。合成雷达／IMU、实际编译节点、关闭 PCD 保存；原地图及目录清单不变，没有新的硬件采集或实机精度验证。

## 保留的其他入口

原 `icp.launch.py`、`teaser.launch.py` 与 `sac_ia_gicp.launch.py` 已移到工作区 `old/launch_relocalization`，当前活动 launch 目录仅保留组合入口。重复的 `small_gicp.launch.py` 已删除，`small_gicp` 算法库与 `small_gicp_node` 可执行程序仍保留。以下仅保留旧 SAC-IA 问题的源码说明，未修改其算法和接口。

## sac_ia_gicp.launch.py 存在的问题

以下基于归档的 [sac_ia_gicp.launch.py](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/old/launch_relocalization/sac_ia_gicp.launch.py) 及其对应的 [sac_ia_gicp.cpp](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/relocalization/src/sac_ia_gicp.cpp) 分析，未运行配准压测。

### 包名错误，当前入口无法直接启动

launch 同时调用 `get_package_share_directory('sac_ia_gicp')` 并设置 `Node(package='sac_ia_gicp', ...)`。当前工作区的 ROS 包名实际是 `relocalization`，`sac_ia_gicp` 只是其中一个可执行程序；本机已安装环境也没有该同名包。因此生成 launch 时就会在查询包路径处失败，即使删除那句未使用的路径查询，节点的 `package` 仍然错误。

后续若启用，包查询与 Node 所属包都需对应 `relocalization`，可执行程序名才是 `sac_ia_gicp`。

### 与当前建图链路的输入、输出和 TF 不匹配

| 项目 | 该入口当前行为 | 对接时需要处理 |
| --- | --- | --- |
| 输入 | `/source_cloud` 重映射到 `/cloud_registered_body`，类型为 `sensor_msgs/msg/PointCloud2` | B 当前建图节点没有发布这个 body 话题；Livox 驱动的 `/livox/lidar` 默认又是 `CustomMsg`，不能只改话题名就连接 |
| 位姿输出 | `/relocalization_result` | FAST-LIVO2 与当前 TF 发布器接收的是 `/icp_result`，当前结果无人自动转接 |
| 调试点云 | `/icp_cloud`、`/template_cloud` | 与组合节点的 `/transformed_cloud`、`/prior_map` 不同，RViz 配置需对应 |
| TF | launch 没有启动 `transform_publisher`，算法自身也不广播地图对齐 TF | 需要另行组织，并核实变换的坐标含义 |

结果表示输入点云坐标系到地图坐标系的配准变换。若输入为当前机体坐标系中的点云，得到的是当前机体在地图中的位姿；不能在建图已经运动后，未经换算就直接当作 `map → camera_init` 的固定变换。也不能为了凑话题名，把已经变换到局部世界系的 `/cloud_registered` 当成 body 点云使用。

### 名称写 GICP，实际精配准使用普通 ICP

程序先计算法向量和 FPFH，执行 `SampleConsensusInitialAlignment`（SAC-IA）粗配准；后续实际实例化 `pcl::IterativeClosestPoint`，没有实例化 GICP。文件名、注释、日志写 GICP 不代表它使用了 GICP，也不等价于新入口的 TEASER++ → VGICP 流程。

### 地图读取和粗配准结果缺少有效性检查

`target_pcd_file` 写死为作者电脑上的路径，launch 没有暴露地图参数。节点调用 `loadPCDFile()` 后没有检查返回码或空地图，仍继续滤波和计算特征；输入点云及降采样结果也缺少必要的空点云／点数检查。SAC-IA 完成后没有根据 `hasConverged()` 决定能否继续，而是直接把结果当作 ICP 初值，日志还固定打印 “has converged”。因此缺失地图或粗配准失败时没有清晰的失败退出路径，不能据日志文字判断成功。

### 部分参数不生效，多次优化逻辑也有问题

- `num_threads` 虽被读取，法向量与 FPFH 计算却固定调用 `setNumberOfThreads(8)`，修改该参数不会控制这些线程数。
- `icp_euclidean_fitness_epsilon` 虽被读取，设置到 ICP 的调用被注释，当前不生效。
- 代码声称以 `max_optimize_times` 控制多次优化，但 `while` 条件包含 `!icp_converged`。当 ICP 已收敛、分数仍高于阈值时，分支虽更新初值并打印继续优化，下次循环却会因 `icp_converged=true` 结束，因此预期的多轮精配准并未实现。
- 默认 `mode=0` 会对后续点云持续尝试配准，成功发布后也不会退出。每次仍要计算 FPFH 和 SAC-IA，ICP 单次最大迭代次数又配置为 10000；可能产生持续负载，具体需实测。`mode=1` 则依赖 `/need_recovery` 触发，当前 launch 不提供触发节点。

本次仅删除重复 launch、整理说明；上述 SAC-IA 问题尚未修复，不影响新增独立入口继续使用 `teaser_gicp_node`。

## 归档组合示例

工作区 `old/launch_top` 中保留历史示例：

- `example_gicp.launch.py`：仅使用 small_gicp 的定位流程（适合已有较好初始位姿场景）。
- `example_teaser_gicp.launch.py`：先 TEASER++ 全局定位，达到阈值后切换到 GICP 精细配准（推荐用于完全丢失位姿或大范围重定位）。

归档文件仅用于对照，不随当前活动包安装，也不保证移动后可直接启动。当前运行方式采用工作区中文 README 中的雷达、建图、重定位三个独立入口。

## 参数说明（常用）

以下为组合节点的常用参数，可在 launch 的 Node 参数中调整：

- `locate_in_prior_map`：是否执行配准，默认 `false`
- `prior_map_path`：地图 PCD 文件路径，默认空，仅开启配准时必填
- `map_frame_id` : 地图 TF Frame，默认 `map`
- `pcl_type` : `livox` 或 `standard`

TEASER 参数：
- `fpfh_normal_radius`：法线估计半径（m）
- `fpfh_feature_radius`：FPFH 特征半径（m）
- `noise_bound`：TEASER 预期噪声水平（m）
- `teaser_inlier_threshold`：内点数阈值（达到后计为一次成功）
- `teaser_success_count`：连续成功次数后切换到 GICP

GICP / small_gicp 参数：
- `gicp_map_voxel_leaf_size`, `gicp_cloud_voxel_leaf_size`：地图与点云降采样体素大小（m）
- `num_threads`：并行线程数
- `max_correspondence_distance`：对应点搜索半径
- `fitness_score_thre`：GICP 适应度阈值（越小越严格）
- `converged_count_thre`：连续收敛次数阈值（判定定位成功）
- `registration_type`：`VGICP` 或 `GICP`

这些参数可以通过 launch 的 `parameters` 字段传入（参考 `example_teaser_gicp.launch.py`）。

## 开启配准时的节点话题（默认名称）

- 订阅：
	- `/pointcloud2` 或 `/livox/lidar`（取决于 `pcl_type`）——输入实时点云
	- `initialpose` —— 手动给定初始位姿（会触发 GICP 阶段）

- 发布：
	- `icp_result`（geometry_msgs/PoseWithCovarianceStamped）——发布重定位结果位姿
	- `prior_map`（sensor_msgs/PointCloud2）——发布下采样后的地图（用于 RViz）
	- `transformed_cloud`（sensor_msgs/PointCloud2）——发布根据当前估计变换后的点云以便可视化

## 可视化（RViz）

当前独立 `relocalization.launch.py` 不启动 RViz，需要提前手动运行 `rviz2`；不要沿用建图 RViz 的默认 `camera_init`。历史组合入口的 RViz 行为只供归档对照。
确保 RViz 中：

- 订阅正确的 `Fixed Frame` 为 `map`
- 添加 `PointCloud2` 话题 `prior_map` 与 `transformed_cloud`，查看地图与当前变换后的点云

如果在 RViz 中看不到 `transformed_cloud`：

1. 检查节点日志，确认程序有调用 `publish_debug_cloud()` 并没有返回早期错误。
2. 确认 `transformed_cloud` 的 `header.frame_id` 与 RViz 中的 Fixed Frame（通常为 `map`）一致。
3. 如果 TEASER 无足够内点而没有生成变换，节点现在已改为在失败时发布降采样后的原始点云作为调试点云，方便查看。

## 调参建议

- 如果 TEASER 匹配到的内点很少（例如只有个位数），可：
	- 降低 `teaser_inlier_threshold`（或先观察对应数再调整）；
	- 放大 `fpfh` 搜索半径（`fpfh_normal_radius`, `fpfh_feature_radius`）；
	- 增大 `noise_bound` 提高鲁棒性。

- GICP 收敛慢或质量差时：
	- 减小 `gicp_cloud_voxel_leaf_size` 提高分辨率；
	- 增大 `max_correspondence_distance` 以容忍较大初始误差；
	- 调整 `fitness_score_thre` 以便判定准/不准。

## 故障排查

- 若编译时提示找不到 `teaserpp::teaser_features`，请确保 TEASER++ 在编译时启用了 FPFH：

```bash
colcon build --packages-select teaserpp --cmake-args -DBUILD_TEASER_FPFH=ON
```

- 若运行时看不到点云或 TF 错误：检查话题名、frame_id 与 RViz Fixed Frame 是否一致，并查看节点日志获取更多线索。

## 许可证与引用

该项目整合并改进了若干开源实现，请在学术或工程引用中同时引用相关工作：

- Fast-LIO2 Localization: https://github.com/PolarisXQ/Fast-LIO2-Localization
- TEASER++: https://github.com/MIT-SPARK/TEASER-plusplus
- small_gicp: https://github.com/koide3/small_gicp

欢迎基于本代码进一步改进。


