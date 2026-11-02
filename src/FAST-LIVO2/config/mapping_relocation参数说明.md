# mapping_relocation.yaml 参数说明

核对日期：2026-11-02。本文对应当前 [mapping_relocation.yaml](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/config/mapping_relocation.yaml)，逐项说明其中全部 **72 个参数**，依据 B 工程实际读取和使用代码，而非仅依据参数名称。

表中的“当前值”是本文件现有配置，不一定是 C++ 默认值。建图入口将该文件和 `camera_parameter.yaml` 传给 `fastlivo_mapping`，并启动可选 RViz；重定位入口从同一文件提取模式和地图路径，定位模式还提取 LiDAR→IMU 外参和重力对齐开关，传给自己的节点。修改参数后需要重新启动节点；默认启动使用安装目录副本，源码 YAML 修改后需重新构建安装，或让两个入口通过相同的 `config_file` 显式指定源码文件。

## 文件结构与当前模式

```yaml
/**:
  ros__parameters:
    # 以下填写节点参数
```

`/**` 是 ROS 2 参数文件的节点匹配规则，`ros__parameters` 表示其下为 ROS 参数；它们不是算法参数。嵌套配置在代码中对应点号名称，例如 `common.img_en`。

运行模式以实际 YAML 为准，修改后应重新安装并重启入口。用户已确认的实机组合为：**旧图 `1549`、有先验定位、关闭重力对齐、先验降采样 `0.1`**，可持续定位且不再漂移。开启重力校正并保存本次观测的后续测试步骤见工作区 `cmd.md` 第 12 节；该测试需要手动切换配置，尚未实机验收。`camera_parameter.yaml` 仍必须提供，因为 B 当前会初始化相机模型，即使不启用图像融合。

## 1. 运行模式与先验地图

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `locate_in_prior_map` | `false` | `false`：使用实时点云初始化并更新体素地图；`true`：加载先验地图，并利用外部 `/icp_result` 初值进行先验地图定位，后续不插入实时观测更新体素地图。由 FAST-LIVO2 节点判断，不会自动启动外部重定位节点。 |
| `prior_map_path` | `/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_1102_1549.pcd` | 先验 PCD 地图文件路径，只在定位模式加载；普通建图允许为空。定位时应填写实际可读的绝对路径；建图遇到空路径、读取失败、空地图或非有限 XYZ 会报错并返回 1。两个默认入口直接读取本文件中的同一项，无需在重定位命令中重复填写。 |

2026-11-02 已修复有先验建图等待初值时提前退出的问题，当前会持续处理回调并限频等待，收到初值后恢复正常处理。随后修复地图初始化异常处理：地图降采样后须非空且坐标有限，体素地图只有实际构建成功且非空才标记完成，失败时明确报错退出；27 项隔离检查通过。重定位节点另已增加 `/icp_result` 最多 2 秒的传输 ACK 等待，该次 ACK 增强未修改接收端、配置及 launch；该确认不等于建图初始化完成。当前已支持重力对齐：重定位用共享外参提供 `T_map_I0`，建图收到后初始化 IMU 并保存实际重力旋转 A，再用 `B=T_map_I0×inverse(A)` 变换先验。体素地图成功构建后才发布 `/fast_livo2/initial_map_pose`；当前 TF 发布器等待该最终结果。开启后要求 IMU 可用并静止初始化，缺失初值或 IMU 时不会提前构建；无效重力和体素构建失败报错退出、不发布最终结果。25 项隔离检查通过，实机联合运行待测。详见工作区 `diff.md` 2.4。

本次是否执行重力对齐由 `uav.gravity_align_en` 控制，不再配置或校验先验 PCD 的生成模式。开启时仍由建图保存实际重力旋转 A，使用 `B=T_map_I0×inverse(A)` 处理先验并交接最终 TF；不会重写原 PCD 的坐标。

### time_check：启动前系统时间校验

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `time_check.enabled` | `true` | FAST-LIVO2 启动时只读检查 Linux 系统时钟同步状态。未同步、时钟异常或查询失败时立即打印原因并以错误码 1 退出，不创建输出文件、不订阅传感器或进入建图。关闭时打印“时间校验已关闭”，允许使用未经校验的当前系统时间继续运行。代码默认值也为 `true`。 |

读取参数后调用校验，发生在地图、相机、输出文件和传感器订阅初始化之前。使用 `adjtimex()` 的 `modes=0` 查询，不修改时钟、不要求管理员权限，不在每次启动时重新联网校时；系统报告已同步且无时钟错误即可通过，正常闰秒状态也允许通过，不承诺固定毫秒误差。通过时打印完整本地日期、时间和时区。

校验对 FAST-LIVO2 每次启动生效，与 `locate_in_prior_map`、`pcd_save_en` 无关；它检查的是电脑系统时间，与 LiDAR／IMU／相机数据时间戳的同步不同。校验只执行一次，通过后立即根据系统本地时间固定本次 `map_MMDD_HHMM` 文件名前缀，不使用 ROS `/clock`；当前电脑时区为 `Asia/Shanghai`。关闭校验时同样固定前缀，并提示日期未经校验。运行中不重新检查时间，也不会随时钟或时区变化重命名。独立的驱动、重定位节点不受此开关控制。

## 2. common：输入话题与传感器开关

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `common.img_topic` | `/camera/camera/color/image_raw` | 图像输入话题，消息类型为 `sensor_msgs/msg/Image`。节点虽然始终创建订阅，但 `img_en=0` 时图像回调直接返回，建图不等待图像；该参数不负责启动相机或解压压缩图像。 |
| `common.lid_topic` | `/livox/lidar` | 雷达输入话题。当前 `lidar_type=1` 时使用 `livox_ros_driver2/msg/CustomMsg`，需要驱动输出类型匹配。 |
| `common.imu_topic` | `/livox/imu` | IMU 输入话题，消息类型为 `sensor_msgs/msg/Imu`。 |
| `common.img_en` | `0` | 整数开关，0 关闭视觉观测，1 启用视觉；不是 `locate_in_prior_map` 的同义开关。启用视觉时还需有效图像、相机内参、外参和时间对齐。 |
| `common.lidar_en` | `1` | 整数开关，1 启用雷达输入。与图像、IMU 开关共同影响节点模式选择；当前组合进入 LIO 分支。不能据此认为任意关闭传感器的组合都已验证。 |
| `common.ros_driver_bug_fix` | `false` | 针对驱动时间戳整秒错位的兼容处理。启用后，IMU 回调会将时间加上 `round(最近雷达时间 − IMU时间)` 秒；不是通用时间同步、硬件同步或连续偏移标定。当前保持关闭。 |

## 3. extrin_calib：传感器之间的刚体变换

| 参数 | 当前值 | 含义与单位 |
| --- | --- | --- |
| `extrin_calib.extrinsic_T` | `[-0.011, -0.02329, 0.04412]` | LiDAR 到 IMU 的平移，表示雷达原点在 IMU 系中的位置，单位 m，参与点云运动补偿和坐标变换。定位模式也供重定位节点进行初值换算，要求 3 个有限数值。 |
| `extrin_calib.extrinsic_R` | 3×3 单位矩阵 | LiDAR 到 IMU 的旋转矩阵，9 个数按行排列；不能直接填欧拉角。定位模式也供重定位初值换算，并校验有限值、正交性及行列式 +1（容差 `1e-6`）。 |
| `extrin_calib.Rcl` | 3×3 矩阵，完整数值见 YAML | LiDAR 到相机的旋转矩阵，9 个数按行排列，用于投影与视觉几何计算。当前关闭视觉，不参与实时视觉观测更新。 |
| `extrin_calib.Pcl` | `[0.031768816365067, -0.108594539194672, 0.016584619676391]` | LiDAR 到相机的平移，单位 m；与 `Rcl` 配套使用。当前关闭视觉，不参与实时视觉观测更新。 |

变换方向为：

```text
p_imu    = extrinsic_R × p_lidar + extrinsic_T
p_camera = Rcl × p_lidar + Pcl
```

相机内参、分辨率和畸变参数位于 `camera_parameter.yaml`，不在本文件中。外参应与实际安装关系一致；它们不是在线自动标定开关。

## 4. time_offset：输入时间修正

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `time_offset.imu_time_offset` | `0.0` | 预期用于 IMU 时间偏移，单位 s；**B 当前没有从参数文件读取此项**。IMU 回调使用的同名成员默认是 0，修改此 YAML 值不会改变该成员。 |
| `time_offset.img_time_offset` | `0.1` | 图像时间偏移，单位 s；代码使用 `图像消息时间 + img_time_offset`，正值使参与同步的图像时刻后移。当前关闭视觉，不参与实时图像融合。 |
| `time_offset.exposure_time_init` | `0.0` | 在图像同步分支中继续加到图像时刻上的时间修正，单位 s，即捕获时刻按 `消息时间 + img_time_offset + exposure_time_init` 使用。它不设置相机硬件曝光，也不是逆曝光状态的初始数值。当前关闭视觉。 |

## 5. preprocess：点云预处理

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `preprocess.lidar_type` | `1` | 雷达数据处理类型。当前枚举值 1 对应代码中的 `AVIA`／Livox CustomMsg 分支，本工程也用该分支处理当前 MID360 数据；它不是驱动 JSON 中的设备型号选择。 |
| `preprocess.scan_line` | `4` | 允许的扫描线数量；当前 Livox 处理会保留 `point.line < 4` 的点，并据此组织扫描线缓存。不控制雷达输出频率。 |
| `preprocess.scan_rate` | `10` | 预处理中的扫描频率参数，单位 Hz。部分标准旋转雷达分支用它推算点时间；**当前 Livox 分支使用点的 `offset_time`，不使用此值推算时间**。修改它不会改变 Livox 驱动的发布频率。 |
| `preprocess.blind` | `0.6` | 最小点距离，单位 m；当前处理将距离小于 0.6 m 的近点剔除。 |
| `preprocess.point_filter_num` | `3` | 均匀抽样间隔。当前关闭特征提取时，对通过扫描线条件的点计数，每 3 个取 1 个，再检查盲区；不是每三帧取一帧。 |
| `preprocess.filter_size_surf` | `0.1` | 实时点云体素降采样边长，单位 m，供 LIO 匹配／地图更新的点云使用。调大通常减少点数及计算量，同时减少几何细节。 |
| `preprocess.filter_size_map` | `0.1` | 加载先验 PCD 时使用的体素降采样边长，单位 m；先验加载时要求转换为滤波器使用的浮点数后仍为有限正数，否则建图报错退出。当前值已由用户改为 0.1，解决旧图在 0.5 下过稀、无法建立有效平面的问题。普通建图模式不加载先验地图；实时体素地图分辨率由 `lio.voxel_size` 控制。独立重定位使用其 launch 中的两阶段降采样参数，不读取本项。 |
| `preprocess.feature_extract_enabled` | `false` | 是否走预处理中的扫描线几何特征提取分支。当前关闭，使用筛选、抽样后的点云；不代表后面的 LIO 不使用平面几何约束。 |

`point_filter_num` 应为正整数，体素尺寸应为正数。当前雷达驱动的设备型号、网口和发布频率由 `livox_ros_driver2` 的独立配置管理。

## 6. vio：视觉更新与图像块参数

本组参数会被读取并用于初始化，但当前 `common.img_en=0`，不执行实时视觉观测更新。逆曝光噪声仍会传给 IMU 状态传播模块，不能把“关闭视觉”理解为所有这些参数都没有被读取。

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `vio.max_iterations` | `5` | 视觉迭代优化的最大迭代次数，图像金字塔各层按此上限优化，满足停止条件时可提前结束。与 LIO 的迭代次数独立。 |
| `vio.outlier_threshold` | `1000` | 图像块光度误差剔除阈值。代码将块内灰度残差平方和与 `outlier_threshold × patch_size²` 比较；不是像素位移或距离阈值。当前 B 声明为整数。 |
| `vio.img_point_cov` | `1000` | 视觉光度观测的噪声权重参数，用于视觉状态更新；按当前公式，数值增大时视觉相对先验的权重降低。不是特征点数量，当前 B 声明为整数。 |
| `vio.patch_size` | `8` | 图像块边长，单位像素；当前每块为 8×8，共 64 个采样像素。块越大通常计算越多。 |
| `vio.patch_pyrimid_level` | `4` | 图像块金字塔层数，当前使用层号 0～3。`pyrimid` 是现有代码实际读取的拼写，不能自行改成 `pyramid`。 |
| `vio.grid_size` | `5` | 图像网格尺寸控制参数；**只有大于 10 时才直接按像素边长使用**。当前 5 走另一分支，以 `图像高度 / grid_n_height` 重新计算边长，不等于使用 5 像素网格。 |
| `vio.grid_n_height` | `17` | 当前上述分支中的纵向网格数量参考值。以当前相机高度 360 计算，整数网格边长为 `360 / 17 = 21` 像素，代码再计算网格数量；若 `grid_size > 10`，此值则被重新计算。 |
| `vio.normal_en` | `true` | 在视觉图像块变换／参考观测处理中使用平面法向几何信息。它不是 IMU 重力估计开关。 |
| `vio.raycast_en` | `false` | 是否启用视觉地图检索中的射线采样补充流程，用于寻找投影网格对应的地图点。不是控制雷达发射或驱动功能。 |
| `vio.inverse_composition_en` | `false` | 是否采用反向组合的视觉优化分支；当前使用常规前向计算分支。不改变外参矩阵的定义方向。 |
| `vio.exposure_estimate_en` | `true` | 允许估计视觉光度模型中的逆曝光／亮度尺度状态，并启用对应传播噪声。不是相机驱动的自动曝光开关；当前没有视觉观测，因此不进行视觉曝光校正。 |
| `vio.inv_expo_cov` | `0.1` | 逆曝光状态的过程噪声系数，传播时按 `inv_expo_cov × dt²` 加入相关协方差。不是实际曝光时间，当前会传入 IMU 传播模块。 |

## 7. imu：IMU 初始化与传播

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `imu.imu_en` | `true` | 启用 IMU 处理、状态传播与点云运动补偿。当前普通建图为 LiDAR + IMU。 |
| `imu.gravity_est_en` | `true` | 启用滤波传播／估计中的重力状态耦合。与初始化后旋转局部参考系的 `uav.gravity_align_en` 不同；关闭该项也不等于跳过初始 IMU 均值与重力初始化。 |
| `imu.ba_bg_est_en` | `true` | 启用加速度计和陀螺仪偏置状态与运动状态之间的估计耦合；不是读取设备出厂标定的开关。 |
| `imu.imu_int_frame` | `30` | 初始化计数阈值。虽然名称和接口写 frame，当前 `IMU_init()` 对每条 IMU 样本递增计数，超过阈值后结束初始化；不是固定等待 30 帧雷达，也不是 30 秒。 |
| `imu.acc_cov` | `0.1` | 加速度计测量噪声协方差系数，三个轴使用相同值；按实现参与状态传播噪声。代码直接使用该系数，不应把它不加区分地当成标准差。 |
| `imu.gyr_cov` | `0.1` | 陀螺仪测量噪声协方差系数，三个轴使用相同值；影响旋转等状态的传播不确定度，同样不是直接指定角速度。 |
| `imu.b_acc_cov` | `0.0001` | 预期为加速度计偏置随机游走噪声；**当前没有从 YAML 读取**，初始化代码固定向处理器传入各轴 0.0001。修改此项不会改变固定值。 |
| `imu.b_gyr_cov` | `0.0001` | 预期为陀螺仪偏置随机游走噪声；**当前没有从 YAML 读取**，初始化代码固定传入各轴 0.0001。修改此项不会改变固定值。 |

当前三项未接入读取的配置是 `time_offset.imu_time_offset`、`imu.b_acc_cov`、`imu.b_gyr_cov`。它们与现有成员默认值／固定值恰好相同，不表示这些 YAML 接口已经生效。

## 8. lio：雷达匹配与体素平面地图

| 参数 | 当前值 | 含义与单位 |
| --- | --- | --- |
| `lio.max_iterations` | `5` | 单次 LIO 迭代状态更新的最大迭代次数，允许按收敛／重匹配条件提前结束。声明、读取与 YAML 现已统一使用此名。 |
| `lio.dept_err` | `0.02` | 点测距方向的误差尺度，单位 m；构建点协方差时使用其平方。`dept_err` 是当前接口实际拼写。 |
| `lio.beam_err` | `0.05` | 光束方向角误差尺度，单位为**度**，代码先转弧度，再以正弦平方构造方向方差；不是 0.05 rad。 |
| `lio.min_eigen_value` | `0.0025` | 体素内点位置协方差最小特征值的平面判定阈值，量纲为 m²。最小特征值小于此值时认为满足平面条件；不是要求特征值大于该参数。 |
| `lio.sigma_num` | `3.0` | 点到平面残差的标准差门限倍数，无量纲；代码采用 `距离 < sigma_num × sqrt(残差方差)` 筛选匹配。不是固定 3 m 的距离阈值。 |
| `lio.voxel_size` | `0.5` | 顶层地图体素边长，单位 m；体素初始化时要求为有限正数。体素内可以继续八叉树细分，不等同于实时点云降采样边长。 |
| `lio.max_layer` | `2` | 八叉树允许的最大深度，要求非负且 `layer_init_num` 长度覆盖到该层，否则体素初始化报错退出。顶层编号为 0，因此可使用 0、1、2 层；对应边长约为 0.5、0.25、0.125 m。不是只有两个层级。 |
| `lio.max_points_num` | `50` | 单个体素树节点用于平面拟合／更新的点数上限控制；达到相关条件后会停止该平面节点更新并释放点缓存。不是整张地图只能保留 50 点，也不是全局内存限制。 |
| `lio.layer_init_num` | `[5, 5, 5, 5, 5]` | 各深度节点初始化拟合的点数阈值列表，从第 0 层开始对应；当前最大层为 2，仅用前 3 项。代码在点数超过阈值时初始化，例如阈值 5 通常需要至少 6 点。列表长度须至少为 `max_layer + 1`，初始化时检查，避免空列表或深层索引越界。 |

增大最大层数或减小体素尺寸，可能增加几何细节、计算和内存开销；这些参数不构成回环优化或全局地图优化功能。

## 9. local_map：局部地图滑动与裁剪

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `local_map.map_sliding_en` | `false` | 是否随当前位置移动地图保留区域并清理外部体素。当前关闭，不执行滑动裁剪；长时间建图的体素地图可能持续增长。 |
| `local_map.half_map_size` | `100` | 保留区域在每个坐标轴方向的半宽，代码单位是**顶层体素索引格数**。当前 `voxel_size=0.5 m` 时约相当于各方向半宽 50 m，存在索引取整／边界差异；不是半宽 100 m。仅滑动开启时使用。 |
| `local_map.sliding_thresh` | `8.0` | 当前位置相对上次滑动位置的移动距离阈值，单位 m；达到阈值才执行下一次裁剪。不是剩余地图边缘距离。当前滑动关闭，不生效。 |

## 10. uav：高频外推与重力对齐

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `uav.imu_rate_odom` | `false` | 是否在滤波更新之间利用 IMU 继续外推并发布额外里程计／状态。代码以 0.004 s 定时回调尝试发布 `/LIVO2/imu_propagate` 和 `/fast_livo2/state6_imu_prop`，实际有效输出依赖 IMU 数据。关闭时保留正常 LIO 输出；不是关闭 IMU。 |
| `uav.gravity_align_en` | `true` | IMU 初始化后只执行一次重力对齐，使局部系重力指向负 Z。要求 `imu.imu_en=true`，否则启动报错；关闭不等于不估计重力，也不提供绝对航向。先验模式用实际旋转 A 补偿最终地图初值，体素地图构建成功后才发布最终位姿供 TF 使用；无先验模式直接保留原有重力对齐建图流程。两种模式均需静止初始化。 |

## 11. publish：点云、平面与全局里程计输出

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `publish.dense_map_en` | `true` | 注册点云输出选用去畸变后的较稠密实时点云；为 `false` 时选用体素降采样后的点云。它不改变内部体素地图分辨率，但会影响消息量和后续 PCD 缓存点数。 |
| `publish.pub_effect_point_en` | `false` | 是否发布参与点到平面匹配的有效点 `/cloud_effected`，用于调试；不控制算法是否使用这些点。 |
| `publish.pub_plane_en` | `true` | 是否发布体素平面可视化标记 `/planes`，供 RViz 显示；不是是否建立平面地图的算法开关。 |
| `publish.pub_scan_num` | `1` | 视觉 RGB 点云分支在着色前累积的发布调用次数，当前为每次处理。不能把它当成所有消息的通用发布降频参数；纯 LIO 不走该累积着色分支。 |
| `publish.blind_rgb_points` | `0.0` | RGB 点云着色／输出时相对相机的最小距离，单位 m。仅视觉着色分支使用，与雷达预处理盲区独立；仍会检查点在相机前方且位于图像内。 |
| `publish.map_frame_id` | `map` | 额外地图系里程计 `/aft_mapped_in_map` 的目标坐标系，并用于查找该坐标系到 `camera_init` 的 TF。不会把局部 `/cloud_registered`、轨迹和 PCD 的坐标系统一改成 `map`，也不会自行生成地图对齐 TF。 |

局部里程计主要使用 `camera_init → aft_mapped`。没有 `map → camera_init` 时，额外地图系里程计会被跳过，普通 LIO 的局部估计和输出仍可继续。

## 12. evo：轨迹文本输出

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `evo.seq_name` | `Mid360_D405_Mapping_01` | 轨迹文本的文件名主体，启用输出后对应源码包下 `Log/result/Mid360_D405_Mapping_01.txt`；不是 ROS 节点名或地图坐标系。 |
| `evo.pose_output_en` | `false` | 是否输出供轨迹评估使用的文本，字段为时间、位置和四元数 `qx qy qz qw`。不控制 ROS 里程计／路径发布，也不会自动运行 evo 或计算误差。 |

## 13. pcd_save：观测点云累积与写盘

| 参数 | 当前值 | 含义与生效条件 |
| --- | --- | --- |
| `pcd_save.pcd_save_en` | `true` | PCD 保存总开关。普通建图由此控制；定位模式还要求 `save_in_localization=true`。当前总开关虽为 true，定位保存权限为 false，实际不累积或写出点云；不是保存完整滤波器状态或先验地图。 |
| `pcd_save.save_in_localization` | `false` | 是否允许 FAST-LIVO2 在先验地图定位模式下保存本次观测，代码默认值也为 false。有效保存条件为 `pcd_save_en && (!locate_in_prior_map || save_in_localization)`。关闭时不创建 PCD 目录、不累积保存缓存、不写整图、分段或分段位姿记录，终端打印禁用原因。普通建图忽略本开关。开启后也不会自动复制或合并先验点云。 |
| `pcd_save.output_dir` | `/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD` | PCD 输出目录，必须填写非空绝对路径，不能只填文件名或使用 `~`。有效保存开启时程序自动创建目录；整段原始／RGB 降采样文件、分段 PCD 和 `map_MMDD_HHMM_scans_pos.json` 均使用此目录。旧配置未填写此项时，代码回退到原源码包 `Log/PCD` 的绝对路径；本配置已显式使用工作区根目录 `PCD`。 |
| `pcd_save.colmap_output_en` | `false` | 是否启用配套 COLMAP 相机、图像、位姿和点信息导出流程，供后处理使用；依赖视觉及相关输出条件和目录，不等同于 PCD 保存开关。当前关闭。 |
| `pcd_save.filter_size_pcd` | `0.15` | 结束保存时生成 RGB 降采样文件所用的体素边长，单位 m。**当前纯 LIO 结束保存分支仅写原始强度点云，不执行此滤波**；不能靠修改此值缩小当前 LIO 输出 PCD。分段写盘也没有应用该滤波。 |
| `pcd_save.interval` | `-1` | 小于 0：在内存持续累积，正常结束时尝试保存整段点云；大于 0：按保存流程调用次数分段，达到间隔后写编号 PCD 并清空对应缓存。当前 LIO 中通常对应发布处理帧数，不是秒。**不要用 0 表示关闭**：缓存仍会累积，但正／负间隔写盘条件都不满足。 |

当前定位模式因 `save_in_localization=false` 不保存。切回普通建图且 `img_en=0`、`pcd_save_en=true`、`interval=-1` 时，正常退出后尝试写入以下文件。例如在 11 月 2 日 15:09 通过启动校验：

```text
/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/PCD/map_1102_1509.pcd
```

该分支不会另写降采样文件。视觉开启时，结束保存才有 RGB 原始文件 `map_1102_1509.pcd` 及按 `filter_size_pcd` 生成的 `map_1102_1509_downsampled.pcd`。保存点为本次观测转换到局部 `camera_init` 参考系的结果，不会因配置了 `map_frame_id=map` 就自动保存为地图坐标系，也不会自动把载入的先验点云拼入缓存。

2026-11-02 已增加绝对目录配置，开启保存时在初始化阶段自动创建目录，并在终端打印实际输出位置。目录不是绝对路径，或者创建失败时，节点报错退出，避免写到意外的当前工作目录。修改保存位置时只需改 YAML：

```yaml
pcd_save:
  output_dir: "/absolute/path/to/your/pcd_directory"
```

正数间隔按保存流程调用次数分段，并非按秒或空间区域划分。以 `interval=100` 为例，每累计 100 次就写盘并清空该段缓存，后续文件仅保存下一段点云。所有文件共用启动前缀：

```text
map_1102_1509_0001.pcd
map_1102_1509_0002.pcd
map_1102_1509_scans_pos.json
```

序号从 1 开始，至少四位，不足补零，超过 9999 后自然扩展。位姿记录保留原有逐行文本格式，虽然后缀为 `.json`，内容并非 JSON；每行依次对应相同序号的分段 PCD。整次建图即使跨分钟、跨日，前缀也不改变。文件名只包含月日和时分，不含年份与秒；同一分钟重启或跨年同名时，按当前约定覆盖同名文件，不清理其他文件。`output_dir` 不改变轨迹文本与 COLMAP 输出的原有位置。

`interval=-1` 需要一直保留累积缓存，内存占用随观测增长；正常停止处理循环才会走结束保存，强制杀进程不能保证写出文件。本轮只调整命名，保留既有保存时机：分段模式退出时不补存不足一个间隔的剩余点云；关闭保存应使用 `pcd_save_en=false`，不要设置 `interval=0`。

## 14. 参数之间需要区分的关系

- **四种不同的尺寸：** `filter_size_surf` 管实时点云抽样，`filter_size_map` 管先验 PCD 抽样，`lio.voxel_size` 管内部地图顶层体素，`filter_size_pcd` 只用于对应的 RGB 文件输出滤波。
- **两种重力开关：** `imu.gravity_est_en` 管重力状态估计耦合，`uav.gravity_align_en` 管初始化后的局部参考系方向。
- **两个迭代上限：** `lio.max_iterations` 管雷达更新，`vio.max_iterations` 管视觉更新。
- **三类入口：** 建图与重定位入口共用本 YAML 的模式和地图路径，分别启动各自节点；`msg_MID360_launch.py` 使用驱动自己的配置。三个入口均可不附加参数启动，但仍需分别执行启动命令，不会互相自动拉起。重定位入口在 `false` 时跳过匹配，仅提供单位地图 TF 和空点云占位输出。

## 源码依据

- 参数读取、输入订阅、模式判断、发布与保存：[LIVMapper.cpp](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/src/LIVMapper.cpp)。
- 雷达更新、误差单位、平面阈值和滑动窗口：[voxel_map.cpp](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/src/voxel_map.cpp)。
- Livox 点筛选与不同雷达的时间处理：[preprocess.cpp](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/src/preprocess.cpp)。
- 图像网格、图像块、光度残差与视觉优化：[vio.cpp](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/src/vio.cpp)。
- IMU 样本初始化计数与过程噪声：[IMU_Processing.cpp](/home/fire/Desktop/FAST_LIVO2_ROS2_relocation_ultra/src/FAST-LIVO2/src/IMU_Processing.cpp)。
