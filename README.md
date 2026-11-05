# FAST_LIVO2_Ultra

MID360 / MID360S + IMU 的 ROS 2 建图、先验地图定位与连续扩图工作空间。PC 环境为 **Ubuntu 24.04、ROS 2 Jazzy**；RDK 现场环境为 **Ubuntu 22.04.5、ROS 2 Humble**，两者均使用 **Livox-SDK2 1.5.2**。RDK 的构建记录与尚未完成的实机验收见第 2.1 节。

本文件是工程的统一操作与维护文档，合并原中英文 README、差异记录、注意事项及本地参数／重定位说明。驱动与 SDK 配套另见 [版本.md](/home/fire/Desktop/FAST_LIVO2_Ultra/src/livox_ros_driver2/版本.md)。源代码和实际 YAML 是运行状态的依据。第三方库的许可证、上游 README 和引用资料保留在各自目录。

## 1. 工程做什么

| 模式 | `locate_in_prior_map` | `prior_map_update_en` | 后续操作 |
| --- | --- | --- | --- |
| 普通建图 | `false` | 任意 | 使用实时观测初始化并持续更新体素地图 |
| 固定先验定位 | `true` | `false` | 加载先验并接受重定位初值；固定体素地图，不插入新观测，禁用滑动 |
| 先验重定位后连续扩图 | `true` | `true` | 加载先验并接受重定位初值；成功匹配后将新观测加入在线地图 |

外部重定位用于启动时确定初始地图位姿。默认先用 TEASER++ 求粗配准，再用 small_gicp 的 VGICP 精配准。它没有替换普通建图的 LIO 算法，也不执行回环、全局图优化、RTK 融合或在线外参标定。

扩图复用现有 LIO：先与已有地图匹配，成功后插入本帧完整下采样点集，包括尚未在旧图中出现的区域。沿途新增体素形成平面后，可以为离开旧先验覆盖区的后续扫描提供约束。失败帧不入图、不保存。仍需相邻扫描有足够重叠和可用几何，不能跳过无约束区域；本次不增加回环或丢失后的自动重定位。

推荐按 [quick_start.md](/home/fire/Desktop/FAST_LIVO2_Ultra/quick_start.md) 核实配置后，使用一键入口：

| 任务 | 命令 | 启动内容 |
| --- | --- | --- |
| 采集先验地图 | `ros2 launch fast_livo collect_prior.launch.py` | Livox 驱动、建图、可选 RViz／图像解压 |
| 基于先验定位／扩图并保存观测 | `ros2 launch fast_livo relocate_mapping.launch.py` | 上述内容、地图 TF 发布器、配准器 |

两个组合入口共用现有 YAML。采集前核实 `locate_in_prior_map=false`；先验入口要求该项为 true，配置不符时停止。驱动与算法的配置作用域隔离；建图与配准读取同一份算法配置。默认启动实机驱动，回放时可追加 `start_driver:=false`；无界面运行可追加 `enable_rviz:=false`。定位入口沿用配准器默认 5 秒启动延时，仍需保持静止直到建图最终初始化成功。

单独调试时，可分别使用以下独立入口：

| 入口 | 命令 | 进程 |
| --- | --- | --- |
| 雷达驱动 | `ros2 launch livox_ros_driver2 msg_MID360_launch.py` | Livox 驱动 |
| 建图／持续定位 | `ros2 launch fast_livo mapping_relocation.launch.py` | `laserMapping`，可选 RViz、可选图像解压 |
| 启动重定位 | `ros2 launch relocalization relocalization.launch.py` | TF 发布器，延时启动配准器 |

当前配置为先验模式、`prior_map_update_en=true` 连续扩图、重力对齐开启和观测保存开启。新增开关在 C++ 中缺省为 false，旧配置不增加该项时保持固定先验定位；本工程 YAML 显式启用扩图。参数在启动时读取，更改后重新构建并重启。固定目录分别为 `PCD/priori`（采集输出）、`PCD/relocate`（定位观测输出）、`PCD/map`（先验输入）；通常只修改 `prior_map_name` 选择地图。

`PCD` 已放在 `src/FAST-LIVO2` 包内；`mapping_relocation.yaml` 默认 `workspace_root: "auto"`，自动使用本次编译对应的 FAST-LIVO2 源码包目录。Desktop 调试与 RDK 总工程分别在各自位置编译后，无需手动切换根路径；总工程部署见 [quick_start_whole_prj.md](/home/fire/Desktop/FAST_LIVO2_Ultra/quick_start_whole_prj.md)。`PCD/map`、`PCD/priori`、`PCD/relocate` 和 `PCD/images` 均相对它解析，不受终端当前目录或安装目录层级影响。地图文件仍需手动复制，`prior_map_name` 单独选择文件。

建图和配准共用 FAST-LIVO2 导出的编译源码路径，启动日志及节点的 `workspace_root` 参数显示解析后的绝对目录。也可填写绝对 `workspace_root` 或单独的绝对目录覆盖。复制／移动源码后应重编 `fast_livo` 和 `relocalization`；仅移动已编译的 install 不会更新路径。自动根目录不存在时明确报错，不搜索其他工作空间。

## 2. 获取、依赖与构建

仓库本身就是 colcon 工作空间，不需要再套一层 `humble/src`。下方及后文未单独注明的 `/home/fire/...`、`/opt/ros/jazzy/...` 命令属于 PC 示例；RDK 按第 2.1 节加载 Humble，并使用板端实际路径。

PC 获取与构建：

```bash
cd /home/fire/Desktop
git clone https://github.com/fireup14/FAST_LIVO2_Ultra.git
cd /home/fire/Desktop/FAST_LIVO2_Ultra
source /opt/ros/jazzy/setup.bash
CMAKE_BUILD_PARALLEL_LEVEL=2 MAKEFLAGS=-j2 colcon build --executor sequential
source /home/fire/Desktop/FAST_LIVO2_Ultra/install/setup.bash
```

构建使用系统 PCL、Eigen3、OpenCV、Sophus、fmt、Boost、OpenMP，以及 ROS 的 rclcpp、rclpy、cv_bridge、image_transport、pcl_ros、pcl_conversions、tf2 等依赖。Sophus 须提供当前代码使用的 `sophus/so3.hpp` 和 CMake 导出；旧 README 的 Humble 目录、`build.sh humble`、临时移出重定位包以及古老 Sophus 提交／`so2.cpp` 补丁不再是当前构建步骤。

源码已包含适配版 Livox 驱动、Vikit、small_gicp、TEASER++，作为普通源码目录管理。TEASER++ 包内 `colcon.pkg` 自动开启 FPFH；不要删除此文件。TEASER++ 初次构建可能通过 FetchContent 下载上游依赖，离线环境需提前准备下载缓存。

Vikit 通过 CMake/ament 导出链接，不依赖工作空间目录层级。内部算法库显式静态链接，安装后的程序不依赖构建目录中的内部 `.so`。主程序和 Vikit 不启用会改变 Eigen 分配 ABI 的 x86 `-march=native`；保留有限值检查，ARM 不使用 `-ffast-math`。

已构建后，只更新算法与配置可用：

```bash
cd /home/fire/Desktop/FAST_LIVO2_Ultra
source /opt/ros/jazzy/setup.bash
colcon build --packages-select fast_livo relocalization
source /home/fire/Desktop/FAST_LIVO2_Ultra/install/setup.bash
```

若修改 Vikit 或驱动，需同时重建对应依赖包；不能仅构建 fast_livo。每个运行终端均须 source 同一工作空间。不要同时 source 旧 Ultra 和本工程，否则包查找与动态库可能混用。

### 2.1 RDK 环境与迁移配置

| 项目 | PC 当前配置 | RDK 现场记录 |
| --- | --- | --- |
| 系统／ROS | Ubuntu 24.04／Jazzy | Ubuntu 22.04.5／Humble |
| colcon 工作空间 | `/home/fire/Desktop/FAST_LIVO2_Ultra` | `/home/sunrise/Desktop/FAST_LIVO2_Ultra` |
| SDK 源码目录 | `/home/fire/third_party/Livox-SDK2` | `/home/sunrise/third_party/Livox-SDK2` |
| 雷达型号 | MID360 | MID360S |
| 主机网卡 IP | `192.168.2.50` | `192.168.2.100` |
| 雷达 IP | `192.168.2.3` | `192.168.2.3` |

这些是两台设备的配置实例，IP 须以实际网卡和雷达为准。当前仓库保留 PC 默认值，迁移到 RDK 时核对：

- 算法 YAML 的 `workspace_root` 保持 `"auto"`，在板端目标目录重新编译后自动指向该处 FAST-LIVO2 包；地图和图像相对目录通常不改。总工程嵌套部署路径见 quick_start_whole_prj.md。
- 驱动 `config/msg_MID360.yaml` 的 `lidar_model` 选为 `mid360s`。
- 驱动 `config/MID360s_config.json` 的 `host_net_info` 中 `host_ip` 与板端网卡一致，记录中的 RDK 为 `192.168.2.100`；雷达 IP 保持与设备实际地址一致。

RDK 已获取工程并安装依赖后，在板端构建：

```bash
source /opt/ros/humble/setup.bash
cd /home/sunrise/Desktop/FAST_LIVO2_Ultra
CMAKE_BUILD_PARALLEL_LEVEL=2 MAKEFLAGS=-j2 colcon build --executor sequential
source /home/sunrise/Desktop/FAST_LIVO2_Ultra/install/setup.bash
```

每个 RDK 运行终端均先加载上述 Humble 和板端安装空间；两个一键 launch 命令与 PC 相同。修改源码 YAML／JSON 后，先重建对应包同步安装配置，再启动。SDK 安装前缀两端均为 `/usr/local`；已安装指定版本时无需重装。

依据 [CHANGELOG.md](/home/fire/Desktop/FAST_LIVO2_Ultra/CHANGELOG.md) 的 RDK 历史记录：Humble 下全部 8 个包曾构建通过，SDK 已核对为 1.5.2，修正主机 IP 后配准器已收到点云。先验配准成功、连续扩图、频率与时间戳质量尚未完成实机验收。RDK 的 RViz 启动 `-11` 尚未排查，驱动退出 `-11` 暂不处理；两项均未修复。

## 3. Livox 驱动、SDK 与网口

使用工程内适配驱动，版本宏为 1.2.6；仅宏相同的上游驱动不能替代本地适配。该版本包含 ROS 2 包布局、Humble／Jazzy typesupport、SDK 设备枚举兼容及 Sampling 状态修复。

配套 SDK：**Livox-SDK2 1.5.2，提交 `c0796f04c143143899c87a773d9f6b7136453c0b`**，安装前缀 `/usr/local`。SDK 是系统共享依赖，不是某个工作空间的私有安装。

查询已安装版本：

```bash
python3 -c 'import ctypes as c; v=(c.c_int*3)(); c.CDLL("/usr/local/lib/liblivox_lidar_sdk_shared.so").GetLivoxLidarSdkVer(v); print("Livox-SDK2 %d.%d.%d" % tuple(v))'
```

需要首次安装时，可在独立 third_party 目录下载固定版本并构建：

```bash
mkdir -p /home/fire/third_party
git clone https://github.com/Livox-SDK/Livox-SDK2.git /home/fire/third_party/Livox-SDK2
git -C /home/fire/third_party/Livox-SDK2 checkout --detach c0796f04c143143899c87a773d9f6b7136453c0b
cmake -S /home/fire/third_party/Livox-SDK2 -B /home/fire/third_party/Livox-SDK2/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local
cmake --build /home/fire/third_party/Livox-SDK2/build --parallel 4
sudo cmake --install /home/fire/third_party/Livox-SDK2/build
sudo ldconfig
```

已有 SDK 1.5.2 时无需重复卸载。升级需先停止所有使用 SDK 的驱动，再核对旧安装清单；不要为了普通调试删除 `/usr/local` 或源码目录。原版本文档的卸载步骤是历史重装操作，不是启动前置条件。

驱动配置：`src/livox_ros_driver2/config/msg_MID360.yaml`。

| `lidar_model` | 配置 JSON | JSON 设备键 |
| --- | --- | --- |
| `mid360` | `MID360_config.json` | `MID360` |
| `mid360s` | `MID360s_config.json` | `Mid360s` |

型号忽略大小写，其他值明确报错。一次选一种型号；更换后停止原驱动再启动。仓库内两份 JSON 默认均为雷达 `192.168.2.3`、主机 `192.168.2.50`，电脑接雷达的网卡需配置对应主机地址；第 2.1 节的 RDK 实例使用 MID360S，其 JSON 的主机地址需改为实际板端地址 `192.168.2.100`。两台同时在线时不能共用同一设备 IP。

`driver_parameters.xfer_format=1` 输出 CustomMsg，`multi_topic=0` 使用 `/livox/lidar` 与 `/livox/imu`，`publish_freq=10.0`。设备型号由驱动选择，算法里的 `lidar_type=1` 只表示 Livox CustomMsg 预处理分支。

默认读取安装目录中的配置；修改源码 YAML 或设备 JSON 后先重新构建驱动，再使用默认命令：

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

设备 JSON 仍从安装目录读取，修改 JSON 后重建驱动。MID360S 支持不代表其外参可直接沿用 MID360 标定。

## 4. 普通建图独立入口：两个终端

编辑 `src/FAST-LIVO2/config/mapping_relocation.yaml`：

```yaml
locate_in_prior_map: false
```

保留其余配置，按需选择 `uav.gravity_align_en`。正常结束保存地图时设置 `pcd_save.pcd_save_en=true`、`interval=-1`。重新构建 fast_livo，使安装副本更新。

两个终端分别先执行：

```bash
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_Ultra/install/setup.bash
```

终端 1：

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

终端 2：

```bash
ros2 launch fast_livo mapping_relocation.launch.py
```

保持静止完成 IMU 初始化，再缓慢移动。纯 LIO (`common.img_en=0`) 不读取相机模型、不创建图像订阅，也不要求启动相机。普通建图不需要重定位进程和先验地图。

普通建图只使用局部 `camera_init` 坐标系。重定位入口仅用于有先验模式，不再提供单位位姿和空点云占位输出。

结束时先在终端 2 按 Ctrl+C，等待保存成功及进程正常退出，再停止驱动。强制杀进程不能保证缓存写盘。

## 5. 先验定位独立入口：三个终端

共享 YAML 中设置：

```yaml
locate_in_prior_map: true
prior_map_update_en: true  # false=固定先验定位，true=重定位后继续扩图
prior_map_name: "priori.pcd"
```

将选定的先验 PCD 放入固定的 `PCD/map` 目录，文件名填写到 `prior_map_name`；目录配置通常不改。保留 `preprocess.filter_size_map=0.1`。生成与使用同一地图时遵守重力对齐模式一致的操作约定；程序不恢复已撤销的 `prior_map_is_gravity_align` 参数，也不修改原 PCD。

终端 1、2 使用上一节的驱动和建图命令。看到 `Waiting for initial pose...` 后，在已 source 本工作空间的终端 3 执行：

```bash
ros2 launch relocalization relocalization.launch.py
```

默认延时 5 秒启动配准器；可追加 `start_delay:=0.0`。延时不意味着定位已成功，不会自动启动建图。

设备必须保持静止，直到建图日志显示：

```text
Published /fast_livo2/initial_map_pose after prior-map initialization; the device may now move.
```

再检查 `/fast_livo2/tracking_valid=true`、有效匹配点和静止位姿。配准成功和建图服务接受初值，都不能代替建图初始化完成。

初始化先检查地图路径、有限点、降采样及体素参数；**先验必须有实际有效平面**。没有平面就返回错误码 1，不发布最终位姿或地图 TF。固定先验定位禁止滑动裁剪；扩图模式遵循 `local_map.map_sliding_en`，当前默认 false。输入先验 PCD 不会被覆盖。

运行中约束不足或求解产生非有限值时，发布无效状态，跳过本帧位姿、注册云、状态输出、地图更新和保存。告警包含模式、失败原因、有效约束数和连续失败次数。两种有先验模式连续失败达到 `localization.max_unconstrained_frames` 后仍报错退出；退出前尽力保存此前有效观测缓存，保留原错误与非零退出码。若保存也失败会额外报告。固定模式走出旧图可能失配；扩图模式依赖沿途已建立的新图，不能通过取消失配保护替代正常匹配。检查先验、初值、外参和输入时间后重新启动；当前不在旧滤波状态上自动重置／重定位。

结束顺序：建图 Ctrl+C 并等保存完成 → 重定位入口 → 雷达驱动。

只观察外部配准的调试结果时可以不启动建图，但无法完成初值服务交付：即使配准计算成功，配准器也会在等待建图接受超时后报错退出，默认最长再等待 30 秒。提前打开 RViz，Fixed Frame 设为 `map`，添加 `/prior_map` 与 `/transformed_cloud`。此时 TF 发布器等待建图最终结果，没有 `map → camera_init` 是预期行为；两个点云本身仍可在 map 中显示。要验证完整成功流程，需要启动建图服务。

## 6. 配置读取与可选视觉启动

默认两个算法入口读取安装目录同一份 `fast_livo/config/mapping_relocation.yaml`，无需手动指定配置路径。修改源码 YAML 后，先同步安装副本，再重启相关节点：

```bash
cd /home/fire/Desktop/FAST_LIVO2_Ultra
colcon build --packages-select livox_ros_driver2 fast_livo --executor sequential
```

默认启动命令：

```bash
ros2 launch fast_livo mapping_relocation.launch.py enable_rviz:=false
```

```bash
ros2 launch relocalization relocalization.launch.py
```

两个 launch 不会相互传递参数，也不热更新。可以用 `ros2 pkg prefix fast_livo` 确认当前包来源。

启用视觉需 `common.img_en=1`，启动外部相机，核对时间、图像话题、内参、外参及分辨率。相机 YAML 默认是 D405 640×360 的历史标定，不应当作所有设备的通用标定。

相机参数支持 `camera.model/width/height/fx/...` 与 `cam_model/cam_width/cam_fx/...` 别名，并可由 YAML 或 ROS 命令行覆盖。缺失必需内参立即报错；不再反复查询同一份不完整参数。图像会按相机模型的目标尺寸调整，空图像与转换失败被丢弃。

相机外参使用 `extrin_calib.Rcl`（按行排列的 9 个旋转矩阵元素）和 `extrin_calib.Pcl`（3 个平移分量），满足 `p_camera = Rcl * p_lidar + Pcl`。长度、有限性、旋转矩阵正交性及行列式都经过检查。视觉噪声及离群阈值接受整数或浮点值。

仅有压缩图像时可启用可选解压：

```bash
ros2 launch fast_livo mapping_relocation.launch.py republish_compressed:=true use_respawn:=true
```

输入为 `common.img_topic + /compressed`，输出为 `common.img_topic` 的原始 Image；不同输入基话题可用 `image_input_topic:=/your/input`。需要 image_transport 的 compressed 插件；若 raw 话题已有发布者，不要重复转发。`use_respawn` 只控制解压进程，间隔 2 秒、最多重试 5 次，不重启滤波器，不检测算法丢失。纯 LIO 下开启解压会明确报错。

这里的压缩是 JPEG/PNG 图像编码：原始话题类型为 `sensor_msgs/msg/Image`，压缩话题类型为 `sensor_msgs/msg/CompressedImage`。建图节点直接订阅前者，压缩输入通过独立解压进程转换后进入建图，不是把 `common.img_topic` 改成压缩话题就能直接接收。[ROS image_transport 教程](https://github.com/ros-perception/image_transport_tutorials)

当前 `common.img_en=0`，图像链路默认关闭。启用视觉并解压时，默认使用以下映射：

| 设置／数据 | 当前默认值 |
| --- | --- |
| `common.img_topic`，算法接收的原始图像 | `/camera/camera/color/image_raw` |
| 实际压缩输入 | `/camera/camera/color/image_raw/compressed` |
| `image_input_topic` | 留空时使用 `common.img_topic`；填写时给基话题，不带 `/compressed` |

例如压缩输入为 `/bag/front/image/compressed` 时，可传 `image_input_topic:=/bag/front/image`，解压输出仍取 `common.img_topic`。相机名称不固定，但本 launch 的 compressed 插件按“基话题 + /compressed”订阅；其他命名需要额外 ROS remap。本机 Jazzy 的解压节点通过 `in_transport=compressed`、`out_transport=raw` 参数配置，并将 `in/compressed` 显式映射到实际压缩话题。解压保留图像头信息，不负责纠正曝光时间、标定或传感器同步。JPEG 会引入有损误差，解压也消耗 CPU；已有原始图像时可直接使用。


## 7. 坐标系与重力数学约定

`T_A_B` 将 B 系点转换到 A 系。L 是雷达，I0 是初始 IMU，I(t) 是当前 IMU，C 是固定局部系 `camera_init`，M 是原先验 `map`。

```text
E = T_imu_lidar                     p_imu = R * p_lidar + t
F = T_map_lidar                     原始点云配准结果
P = T_map_I0 = F * inverse(E)        /icp_result
A = T_camera_init_I0                本次初始化实际重力旋转；关闭对齐时为 I
B = T_map_camera_init = P * inverse(A)
先验：p_camera_init = inverse(B) * p_map
实时：p_camera_init = T_camera_init_imu(t) * E * p_lidar(t)
全局位姿：T_map_imu(t) = B * T_camera_init_imu(t)
```

`imu.gravity_est_en` 控制重力状态估计耦合；`uav.gravity_align_en` 控制初始化后一次性旋转局部参考系，让重力沿负 Z。关闭后仍做 IMU 重力补偿；开启不提供绝对 yaw。两次都开启也不能省掉本次 A，因为设备启动姿态可能不同。

配准器内部、手动 `/initialpose` 及对齐调试云保持雷达位姿语义；提交给建图服务的初值及诊断话题 `/icp_result` 已换算为 IMU 位姿，不要重复补外参。建图用自己实际的 A 计算 B，并在先验有效平面初始化成功后才发布最终 B。

现在所有有先验模式的 TF 都等待建图最终结果，重力开关不影响这项就绪约束。TF 发布器校验 frame、有限位置和四元数，并固定首个有效结果。

`map → camera_init` 的独立静态 TF 发布器 `transform_publisher` 由 `relocalization.launch.py` 启动；它固定订阅建图完成先验初始化后发布的 `/fast_livo2/initial_map_pose`，使用 Reliable + Transient Local、depth=1，不再提供输入话题／QoS 切换参数。收到首个有效对齐结果后发布 `/tf_static`（`tf2_msgs/msg/TFMessage`）并继续常驻，供晚加入的订阅者获取静态 TF。`mapping_relocation.launch.py` 启动的建图节点自身广播 `camera_init → aft_mapped` 动态 TF，两者分工不同。

地图滑动是内存体素地图的窗口裁剪：设备相对上次裁剪位置移动达到 `sliding_thresh` 后，删除当前窗口外的体素，以限制普通建图的内存增长。它不修改坐标系或原始 PCD。当前 `half_map_size=100`、`voxel_size=0.5 m`，窗口每轴半宽约 50 m，`sliding_thresh=8.0 m`。固定先验定位不插入实时观测，因此强制关闭滑动。普通建图与先验扩图遵循 `local_map.map_sliding_en`，当前默认 false；开启时裁剪远处在线体素，不裁剪已经缓存的保存点云。被裁区域没有自动重载机制，关闭时在线地图内存随扩图增长，保存缓存也独立增长。

平面拟合从体素点云的协方差求法向、中心及不确定性，为点到平面的匹配残差提供几何约束，既参与建图也参与定位。原实现用通用 `EigenSolver`，主要按最小特征值判断是否平面；当前改为适用于实对称协方差的 `SelfAdjointEigenSolver`，并检查求解结果、第二特征值及其与最小值的间隔，排除近似直线／点和不稳定法向，避免不确定性计算中接近零的分母。这项改动会影响可用平面及匹配点的选择，不能等同于已经证明实机精度提高。[Eigen 求解器说明](https://libeigen.gitlab.io/eigen/docs-nightly/classEigen_1_1SelfAdjointEigenSolver.html)


## 8. 话题、时间戳与可靠性

| 话题 | 类型／坐标 | 说明 |
| --- | --- | --- |
| `/livox/lidar` | CustomMsg，雷达系 | 驱动 → 建图、配准器 |
| `/livox/imu` | Imu，IMU 系 | 驱动 → 建图 |
| `/initialpose` | PoseWithCovarianceStamped，map | 人工雷达位姿，进入精配准 |
| `/icp_result` | PoseWithCovarianceStamped，map | 初始 IMU 位姿 P，仅供查看；建图不订阅此话题，发布者退出后不保留 |
| `/fast_livo2/initial_map_pose` | 同上，map | 建图完成先验初始化后发布的最终局部系位姿 B；transform_publisher 订阅，Reliable + Transient Local，depth=1 |
| `/tf_static` | map → camera_init | TF 发布器常驻维护 |
| `/aft_mapped_to_init` | Odometry，camera_init / aft_mapped | 测量时间的局部 IMU 位姿、机体系 twist 和协方差 |
| `/aft_mapped_in_map` | Odometry，map / aft_mapped | 同一测量时刻的全局 pose；旋转 pose 协方差，twist 保持 child frame |
| `/cloud_registered` | PointCloud2，camera_init | 本次观测，不是始终处于当前机体系 |
| `/cloud_effected` | PointCloud2，camera_init | 有效点面匹配点，仅受显示开关控制 |
| `/Laser_map` | PointCloud2，camera_init | 初始化时换系后的先验快照；不会逐帧重发完整扩展地图，新增区域可查看 `/cloud_registered` 或 `/planes` |
| `/planes` | MarkerArray，camera_init | 持久 ID、完整快照、限频发布；清理旧标记 |
| `/prior_map` | PointCloud2，map | 配准用地图；Transient Local，发布者存活期间保留 |
| `/transformed_cloud` | PointCloud2，map | 配准调试结果，提前订阅 |
| `/fast_livo2/tracking_valid` | Bool，Transient Local | 最近一次约束更新是否有效；启动及约束丢失时为 false。当前断流不会主动改为 false，使用时还须检查里程计时间戳是否持续更新 |
| `/fast_livo2/state6` | Float32MultiArray | 兼容原接口：机体系去偏角速度 3 维 + 世界负 Z 单位向量在机体系的投影 3 维 |
| `/fast_livo2/state6_stamped` | fast_livo/State6Stamped | 新接口，包含测量时间、机体系 frame、两向量和 valid |
| `/fast_livo2/state6_imu_prop[_stamped]` | 对应原始／新消息 | 高频外推状态，需开启 `imu_rate_odom` |
| `/LIVO2/imu_propagate` | Odometry，camera_init / aft_mapped | IMU 外推；有效频率由输入决定，不保证恒定 250 Hz |

`state6` 的六个数按 `[wx, wy, wz, gx, gy, gz]` 排列：前三项是机体系去偏角速度，单位 rad/s；后三项是局部世界系负 Z 单位向量经 `Rᵀ` 投影到机体系后的方向，无量纲。它不含位置／速度，也不表示六个姿态角；关闭重力对齐时，负 Z 不保证与物理重力一致。新消息增加时间、frame 和 valid；独立的 `tracking_valid` 可报告失去约束，而失效帧会停止正常状态输出。外推版本需要开启 `uav.imu_rate_odom`，它提供估计量，不自动执行控制。

Odometry 的 pose 在 header.frame_id 中，twist 在 child_frame_id 中。因此将局部 pose 转换到 map 时，不能把已经在机体系表达的 twist 再旋转一次。全局 TF 按里程计测量时间查询；静态 B 在所有测量时刻有效。初始配准协方差仍是占位近似，没有被当作额外滤波观测；全局输出协方差条件于该固定 B，不包含全局配准自身的不确定性。

先验初值到来前根本不创建传感器订阅，避免 DDS 累积旧输入。接受有效初值后才订阅：雷达深度 10、IMU 200、图像 5，使用 SensorDataQoS。IMU 时间修正为 `消息时间 - imu_time_offset`，图像为 `消息时间 + img_time_offset + exposure_time_init`。IMU 大于 0.2 秒前跳会告警并推进时间水位，后续消息可以恢复。

初始位姿通过服务 `/fast_livo2/set_initial_pose`（`fast_livo/srv/SetInitialPose`）交付：建图是服务端，配准器是客户端。请求包含 `request_id` 和 `geometry_msgs/PoseWithCovarianceStamped pose`；响应包含 `bool accepted` 和 `string message`。建图校验 frame、有限位置／协方差和非零有限四元数，归一化姿态、保存初值并创建传感器订阅后，才返回 `accepted=true`。该确认仅表示初值已接受，不等待 IMU、重力对齐或先验体素初始化；后续仍须保持静止，等待 `/fast_livo2/initial_map_pose` 和有效跟踪。

配准成功后停止求解，异步等待服务与明确响应，默认最多 `initial_pose_timeout_seconds=30` 秒；收到 `accepted=true` 后立即正常退出。单次响应超过 2 秒未到达则重发相同 ID 和完全相同的位姿；建图对相同请求返回已接受，避免重复初始化，拒绝其他初值或同 ID 的不同内容。被明确拒绝或等待超过总时限时以错误码退出，绝不把消息发布或 DDS ACK 当成业务成功。等待不会阻塞 ROS 回调。两个进程可以任意顺序启动，但建图必须在初值交付超时前就绪，期间设备保持静止。原先固定保留 5 秒的退出逻辑与 `result_hold_seconds` 参数已移除。

## 9. 保存、命名与坐标选择

有效保存条件：

```text
pcd_save.pcd_save_en && (!locate_in_prior_map || pcd_save.pcd_save_en_relocate)
```

禁用时不创建 PCD 输出目录、不累积保存缓存、不写 PCD 和位姿记录。独立重定位进程始终只读先验。保存本次观测不意味着更新、复制或合并先验。

| `pcd_save.type` | 保存坐标 | 用途 |
| --- | --- | --- |
| `-1` | 初始化时按模式选择 | 无先验解析为 0，有先验解析为 2；不在逐帧保存时切换 |
| `0` | 局部 camera_init | 本次局部观测 |
| `1` | 每一帧自己的 IMU 系 | 离线逐帧处理；运动时不能把这些点直接叠成一张地图 |
| `2` | 先验 map；无先验时回退 camera_init | 在原先验坐标中保存本次观测，应用一次 B |

无先验保存到固定 `PCD/priori`，先验模式保存到固定 `PCD/relocate`，开启有效保存时自动创建所选目录。启动用系统本地时间固定 `map_MMDD_HHMM` 前缀，与 ROS `/clock` 无关；跨分钟、跨日不改名。同分钟重启可能覆盖同名文件，保留既定覆盖约定，不删除其他地图。

| 条件 | 文件 |
| --- | --- |
| `interval<0`，正常或可捕获异常退出 | `map_MMDD_HHMM.pcd` |
| `interval>0`，达到处理帧数 | `map_MMDD_HHMM_0001.pcd`、`_0002.pcd`… |
| 正数间隔退出时还有缓存 | `map_MMDD_HHMM_remainder.pcd`，现在会补存尾部 |
| RGB 整图／尾部保存 | 另有 `_downsampled.pcd`，使用 `filter_size_pcd` |
| 分段位姿 | `map_MMDD_HHMM_scans_pos.txt`，每段一行 `x y z qw qx qy qz` |
| 运行元数据 | `map_MMDD_HHMM_metadata.yaml`，坐标类型、重力开关、定位模式、`prior_map_update_en` 及 B |

`interval` 对有无先验两种模式都生效，是有效保存调用／处理帧数，不是秒；负数退出保存整图，正数分段并在退出时补存尾部；可捕获异常也尽力保存此前有效缓存，保存失败明确报错。0 被拒绝，关闭保存使用总开关；先验模式还需 `pcd_save.pcd_save_en_relocate=true`。纯 LIO 保存保留强度，不另外按 `filter_size_pcd` 降采样。写盘错误会报错，不打印虚假的保存成功。整图累计内存随观测增加，长时间采集宜使用分段保存。

独立图像保存使用 `image_save.img_save_en/interval/output_dir`，需要开启视觉，与 PCD 总开关独立。输入地图、两种 PCD 输出和图像输出的相对目录均以 `workspace_root` 为基准，进入任何终端目录启动均得到同一组路径。COLMAP 导出需要视觉、Pinhole 模型、有效 PCD 保存及 `type=0`；输出到当前会话的 `_colmap` 子目录，使用 filesystem 创建，不运行 ROS1 命令，不清空其他会话。

先验扩图更新的是在线体素地图；`PCD/relocate` 仍只保存本次有效观测，不自动拼入旧先验。`pcd_save.type=-1` 在两种先验模式下仍解析为 2，输出保持原 `map` 坐标。完整地图使用下方离线 merge 脚本生成。

### 离线拼接先验与 relocate 地图

脚本：[PCD/scripts/merge_maps.py](/home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/PCD/scripts/merge_maps.py)。仅需 Python 3，无需启动 ROS。在脚本顶部选择两个文件：

```python
PRIOR_PCD_NAME = "map_1103_2217.pcd"       # PCD/priori 下的先验文件
RELOCATE_PCD_NAME = "map_1103_2221.pcd"    # PCD/relocate 下的文件
```

然后直接运行，无需传入文件路径：

```bash
python3 /home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/PCD/scripts/merge_maps.py
```

两份输入必须已在同一套坐标基准下；本工程先验定位使用 `pcd_save.type=-1`（初始化解析为 2）时，relocate 文件已满足此条件，不要再套一次地图变换。

结果固定保存到 `PCD/merge/`，按“先验时间 + relocate 时间”自动命名，例如上述输入生成 `merged_1103_2217_1103_2221.pcd`；时间取自输入文件名，去掉 `map_` 前缀和 `.pcd` 扩展名。已有同名输出时，将 `OVERWRITE_OUTPUT` 改为 True 才允许替换；原始输入始终受保护。路径相对脚本位置解析，从任何目录运行均可；仍支持可选命令行输入路径、`-o` 和 `--force`，传入其他输入路径时也按实际文件名生成输出名。

脚本流式拼接，保留全部字段（含强度／法向量等）和重叠点，输出点数等于两份输入之和；不做配准、变换、去重或体素降采样。支持两份字段结构及编码一致的 `DATA binary` 或 `ascii` PCD，不支持 `binary_compressed`。拼接先写临时文件，完成后发布成最终文件。保存地图后再运行；该工具不会改变在线定位地图或当前配置。

### 系统时间检查

`time_check.enabled=true` 默认只读调用 Linux `adjtimex(modes=0)`。系统未报告同步、有时钟错误或查询失败，建图以错误码 1 退出，尚不接收传感器。检查不会联网校时、等待同步或修改系统时间；它也不检查传感器时钟一致性。回放或隔离测试可显式关闭，但会提示命名时间未经校验。独立雷达与配准节点不受该开关控制。

## 10. 配准算法、参数与性能

保留五个可执行名，并共用同一份校验、坐标转换、QoS、成功收尾和资源限制实现，避免旧接口互相漂移：

| 可执行程序／`algorithm` | 算法 | 初值 |
| --- | --- | --- |
| `teaser_gicp_node`／`teaser_gicp` | TEASER++ → GICP/VGICP | 自动粗配准，也接受手动初值 |
| `small_gicp_node`／`gicp` | GICP/VGICP | 接近真值的初值，默认单位变换 |
| `icp_node`／`icp` | PCL ICP | 接近真值的初值 |
| `teaser_node`／`teaser` | TEASER++ 粗配准 | 自动特征匹配，精度按场景验证 |
| `sac_ia_gicp`／`sac_ia_icp` | SAC-IA → PCL ICP | 自动粗配准；历史可执行名兼容保留，实际精配准是 ICP |

统一 launch 选择算法：

```bash
ros2 launch relocalization relocalization.launch.py algorithm:=sac_ia_icp
```

不要再使用已删除的 old/example 启动文件。直接 `ros2 run` 启动配准节点时，须提供当前 `prior_map_path`（绝对目录，或相对 `workspace_root` 的目录）、`prior_map_name`（文件名）和外参参数；`workspace_root` 未配置时同样自动使用 FAST-LIVO2 的编译源码包目录。配准节点仅用于先验定位，不再读取模式或重力对齐开关，重力对齐仍由建图节点完成。原 `map_path/target_pcd_file` 等分裂接口已被统一。标准点云可在共享 YAML 的 `relocalization.pcl_type` 设为 `standard`，输入 `/pointcloud2`；默认 Livox 输入为原始雷达点，不能用改话题名称把 CustomMsg 当成 PointCloud2，也不要把已经注册到世界系的点云重复当原始雷达云。

| 配准参数 | launch 默认值 | 含义 |
| --- | --- | --- |
| `map_voxel_leaf_size / cloud_voxel_leaf_size` | 0.4 / 0.4 m | 粗配准地图／实时云降采样 |
| `gicp_map_voxel_leaf_size / gicp_cloud_voxel_leaf_size` | 0.2 / 0.1 m | 精配准地图／实时云降采样 |
| `fpfh_normal_radius / fpfh_feature_radius` | 0.8 / 1.2 m | 法线／描述子半径，后者须更大 |
| `noise_bound` | 0.3 m | TEASER 噪声范围；SAC-IA 最小采样距离 |
| `teaser_solver_max_iter / rotation_gnc_factor` | 100 / 1.4 | 粗配准迭代上限及 GNC 因子 |
| `teaser_inlier_threshold / teaser_success_count` | 5 / 3 | 平移内点数下限及连续成功次数 |
| `gicp_solver_max_iter` | 50 | 现在实际传给精配准器的迭代上限 |
| `registration_type` | VGICP | GICP 或 VGICP |
| `max_correspondence_distance` | 5.0 m | 对应点搜索距离 |
| `fitness_score_thre` | 0.2 | 均方距离分数阈值，越小越严格 |
| `converged_count_thre` | 10 | 现在恰好连续 10 次合格后成功，使用 `>=` |
| `num_threads` | 4 | 配准及 OpenMP 线程数 |
| `max_attempts / timeout_seconds` | 300 / 120 s | 配准输入帧尝试上限／配准计算阶段时间预算 |
| `initial_pose_timeout_seconds` | 30 s | 配准成功后等待建图服务接受初值的最长时间；响应成功即退出 |

共享 YAML 的 `relocalization` 子节可覆盖这些配准参数。`relocalization.launch.py` 要求共享 YAML 中 `locate_in_prior_map=true`，为 false 时明确报错停止。配准器已删除无先验分支、单位位姿／空点云发布和占位定时器；普通建图使用采集入口即可。

真实配准不是“只计算一次”。地图加载、FPFH、匹配、鲁棒求解和 GICP 都可能占用大量 CPU／内存。失败可回退重试，但现在有预算上限；单次库调用不能中途被计时器抢占，因此时间预算在回调／库调用边界检查，不能当作硬实时强制中断。

旧 16 线程满载对应 top 约 1600% 只是显示换算，不是实测。本版本默认 4 线程；不要据此声称实机峰值或精度已测量。可用 `pidstat -u -r -C teaser_gicp 1` 结合 LIO 耗时观察。先确认地图和有效约束，再调整阈值，不应只为得到成功日志而放宽匹配门限。

## 11. 运行配置参数

下表由当前 YAML 与代码消费关系核对；固定地图目录不逐项展开，通常只调整 prior_map_name。当前值不一定等于 C++ 缺省值。单位说明保留 `dept_err`、`patch_pyrimid_level` 等既有接口拼写。

| 参数 | 当前值 | 含义 |
| --- | --- | --- |
| `workspace_root` | `"auto"` | 未配置或 auto 时使用本次编译对应的 FAST-LIVO2 源码包目录；建图、配准均写回实际绝对路径并打印日志。也接受手动绝对目录；空字符串、其他相对路径、~ 和环境变量替换不支持。移动源码后重编两包，自动源码目录不存在时明确报错。 |
| `locate_in_prior_map` | `true` | `false`：实时观测初始化建图；`true`：加载先验，通过初值服务重定位后按扩图开关运行。不会自动启动外部配准节点。 |
| `prior_map_update_en` | `true` | 仅 `locate_in_prior_map=true` 时决定是否将成功扫描加入在线地图；false 为固定先验定位，true 为连续扩图。C++ 缺省 false，本 YAML 显式 true；不覆盖输入 PCD，不改变本次观测保存范围。 |
| `prior_map_path` | `"PCD/map"` | 相对 workspace_root 的先验输入目录，再与 prior_map_name 拼成完整路径；也兼容绝对目录，建图与配准共用同一根目录。 |
| `prior_map_name` | `"map_1103_2217.pcd"` | 先验文件名，不含目录；通常只需修改此项。文件须已放入上述输入目录，建图与配准器共用。 |
| `time_check.enabled` | `true` | FAST-LIVO2 启动时只读检查 Linux 系统时钟同步状态。未同步、时钟异常或查询失败时立即打印原因并以错误码 1 退出，不创建输出文件、不订阅传感器或进入建图。关闭时打印“时间校验已关闭”，允许使用未经校验的当前系统时间继续运行。代码默认值也为 `true`。 |
| `common.img_topic` | `"/camera/camera/color/image_raw"` | 原始 sensor_msgs/Image 话题；仅 img_en=1 时创建订阅。不会启动相机。 |
| `common.lid_topic` | `"/livox/lidar"` | 雷达输入话题。当前 `lidar_type=1` 时使用 `livox_ros_driver2/msg/CustomMsg`，需要驱动输出类型匹配。 |
| `common.imu_topic` | `"/livox/imu"` | IMU 输入话题，消息类型为 `sensor_msgs/msg/Imu`。 |
| `common.img_en` | `0` | 整数开关，0 关闭视觉观测，1 启用视觉；不是 `locate_in_prior_map` 的同义开关。启用视觉时还需有效图像、相机内参、外参和时间对齐。 |
| `common.lidar_en` | `1` | 整数开关，1 启用雷达输入。与图像、IMU 开关共同影响节点模式选择；当前组合进入 LIO 分支。不能据此认为任意关闭传感器的组合都已验证。 |
| `common.ros_driver_bug_fix` | `false` | 针对驱动时间戳整秒错位的兼容处理。启用后，IMU 回调会将时间加上 `round(最近雷达时间 − IMU时间)` 秒；不是通用时间同步、硬件同步或连续偏移标定。当前保持关闭。 |
| `extrin_calib.extrinsic_T` | `[-0.011, -0.02329, 0.04412]` | LiDAR 到 IMU 的平移，表示雷达原点在 IMU 系中的位置，单位 m，参与点云运动补偿和坐标变换。定位模式也供重定位节点进行初值换算，要求 3 个有限数值。 |
| `extrin_calib.extrinsic_R` | `长度 9，见 YAML` | LiDAR 到 IMU 的旋转矩阵，9 个数按行排列；不能直接填欧拉角。定位模式也供重定位初值换算，并校验有限值、正交性及行列式 +1（容差 `1e-6`）。 |
| `extrin_calib.Rcl` | `长度 9，见 YAML` | LiDAR 到相机的旋转矩阵，9 个数按行排列，用于投影与视觉几何计算。当前关闭视觉，不参与实时视觉观测更新。 |
| `extrin_calib.Pcl` | `[0.031768816365067, -0.108594539194672, 0.016584619676391]` | LiDAR 到相机的平移，单位 m；与 `Rcl` 配套使用。当前关闭视觉，不参与实时视觉观测更新。 |
| `time_offset.imu_time_offset` | `0.0` | IMU 时间偏移，秒；实际使用消息时间减去本值。 |
| `time_offset.img_time_offset` | `0.1` | 图像时间偏移，单位 s；代码使用 `图像消息时间 + img_time_offset`，正值使参与同步的图像时刻后移。当前关闭视觉，不参与实时图像融合。 |
| `time_offset.exposure_time_init` | `0.0` | 在图像同步分支中继续加到图像时刻上的时间修正，单位 s，即捕获时刻按 `消息时间 + img_time_offset + exposure_time_init` 使用。它不设置相机硬件曝光，也不是逆曝光状态的初始数值。当前关闭视觉。 |
| `preprocess.lidar_type` | `1` | 雷达数据处理类型。当前枚举值 1 对应代码中的 `AVIA`／Livox CustomMsg 分支，本工程也用该分支处理当前 MID360 数据；它不是驱动 JSON 中的设备型号选择。 |
| `preprocess.scan_line` | `4` | 允许的扫描线数量；当前 Livox 处理会保留 `point.line < 4` 的点，并据此组织扫描线缓存。不控制雷达输出频率。 |
| `preprocess.scan_rate` | `10` | 预处理中的扫描频率参数，单位 Hz。部分标准旋转雷达分支用它推算点时间；**当前 Livox 分支使用点的 `offset_time`，不使用此值推算时间**。修改它不会改变 Livox 驱动的发布频率。 |
| `preprocess.blind` | `0.6` | 最小点距离，单位 m；当前处理将距离小于 0.6 m 的近点剔除。 |
| `preprocess.point_filter_num` | `3` | 均匀抽样间隔。当前关闭特征提取时，对通过扫描线条件的点计数，每 3 个取 1 个，再检查盲区；不是每三帧取一帧。 |
| `preprocess.filter_size_surf` | `0.1` | 实时点云体素降采样边长，单位 m，供 LIO 匹配／地图更新的点云使用。调大通常减少点数及计算量，同时减少几何细节。 |
| `preprocess.filter_size_map` | `0.1` | 加载先验 PCD 时使用的体素降采样边长，单位 m；先验加载时要求转换为滤波器使用的浮点数后仍为有限正数，否则建图报错退出。当前值已由用户改为 0.1，解决旧图在 0.5 下过稀、无法建立有效平面的问题。普通建图模式不加载先验地图；实时体素地图分辨率由 `lio.voxel_size` 控制。独立重定位使用其 launch 中的两阶段降采样参数，不读取本项。 |
| `preprocess.feature_extract_enabled` | `false` | 是否走预处理中的扫描线几何特征提取分支。当前关闭，使用筛选、抽样后的点云；不代表后面的 LIO 不使用平面几何约束。 |
| `vio.max_iterations` | `5` | 视觉迭代优化的最大迭代次数，图像金字塔各层按此上限优化，满足停止条件时可提前结束。与 LIO 的迭代次数独立。 |
| `vio.outlier_threshold` | `1000` | 浮点光度离群阈值；与 patch_size² 相乘，比较块内残差平方和。 |
| `vio.img_point_cov` | `1000` | 浮点光度观测噪声权重；增大降低视觉观测相对先验的权重。接受旧整数 YAML。 |
| `vio.patch_size` | `8` | 图像块边长，单位像素；当前每块为 8×8，共 64 个采样像素。块越大通常计算越多。 |
| `vio.patch_pyrimid_level` | `4` | 图像块金字塔层数，当前使用层号 0～3。`pyrimid` 是现有代码实际读取的拼写，不能自行改成 `pyramid`。 |
| `vio.grid_size` | `5` | 图像网格尺寸控制参数；**只有大于 10 时才直接按像素边长使用**。当前 5 走另一分支，以 `图像高度 / grid_n_height` 重新计算边长，不等于使用 5 像素网格。 |
| `vio.grid_n_height` | `17` | 当前上述分支中的纵向网格数量参考值。以当前相机高度 360 计算，整数网格边长为 `360 / 17 = 21` 像素，代码再计算网格数量；若 `grid_size > 10`，此值则被重新计算。 |
| `vio.normal_en` | `true` | 在视觉图像块变换／参考观测处理中使用平面法向几何信息。它不是 IMU 重力估计开关。 |
| `vio.raycast_en` | `false` | 是否启用视觉地图检索中的射线采样补充流程，用于寻找投影网格对应的地图点。不是控制雷达发射或驱动功能。 |
| `vio.inverse_composition_en` | `false` | 是否采用反向组合的视觉优化分支；当前使用常规前向计算分支。不改变外参矩阵的定义方向。 |
| `vio.exposure_estimate_en` | `true` | 允许估计视觉光度模型中的逆曝光／亮度尺度状态，并启用对应传播噪声。不是相机驱动的自动曝光开关；当前没有视觉观测，因此不进行视觉曝光校正。 |
| `vio.inv_expo_cov` | `0.1` | 逆曝光状态的过程噪声系数，传播时按 `inv_expo_cov × dt²` 加入相关协方差。不是实际曝光时间，当前会传入 IMU 传播模块。 |
| `imu.imu_en` | `true` | 启用 IMU 处理、状态传播与点云运动补偿。当前普通建图为 LiDAR + IMU。 |
| `imu.gravity_est_en` | `true` | 启用滤波传播／估计中的重力状态耦合。与初始化后旋转局部参考系的 `uav.gravity_align_en` 不同；关闭该项也不等于跳过初始 IMU 均值与重力初始化。 |
| `imu.ba_bg_est_en` | `true` | 启用加速度计和陀螺仪偏置状态与运动状态之间的估计耦合；不是读取设备出厂标定的开关。 |
| `imu.imu_int_frame` | `30` | 初始化计数阈值。虽然名称和接口写 frame，当前 `IMU_init()` 对每条 IMU 样本递增计数，超过阈值后结束初始化；不是固定等待 30 帧雷达，也不是 30 秒。 |
| `imu.acc_cov` | `0.1` | 加速度计测量噪声协方差系数，三个轴使用相同值；按实现参与状态传播噪声。代码直接使用该系数，不应把它不加区分地当成标准差。 |
| `imu.gyr_cov` | `0.1` | 陀螺仪测量噪声协方差系数，三个轴使用相同值；影响旋转等状态的传播不确定度，同样不是直接指定角速度。 |
| `imu.b_acc_cov` | `0.0001` | 加速度计偏置随机游走噪声，实际传给 IMU 模块；要求有限非负。 |
| `imu.b_gyr_cov` | `0.0001` | 陀螺仪偏置随机游走噪声，实际传给 IMU 模块；要求有限非负。 |
| `lio.max_iterations` | `5` | 单次 LIO 迭代状态更新的最大迭代次数，允许按收敛／重匹配条件提前结束。声明、读取与 YAML 现已统一使用此名。 |
| `lio.min_effective_points` | `6` | 每次 LIO 更新的最少有效点面约束数；不足则返回无效，不做伪更新。 |
| `lio.dept_err` | `0.02` | 点测距方向的误差尺度，单位 m；构建点协方差时使用其平方。`dept_err` 是当前接口实际拼写。 |
| `lio.beam_err` | `0.05` | 光束方向角误差尺度，单位为**度**，代码先转弧度，再以正弦平方构造方向方差；不是 0.05 rad。 |
| `lio.min_eigen_value` | `0.0025` | 点位置协方差最小特征值的平面阈值，m²；还拒绝零面积／线状几何及不稳定特征值间隔。 |
| `lio.sigma_num` | `3.0` | 点到平面残差的标准差门限倍数，无量纲；代码采用 `距离 < sigma_num × sqrt(残差方差)` 筛选匹配。不是固定 3 m 的距离阈值。 |
| `lio.voxel_size` | `0.5` | 顶层地图体素边长，单位 m；体素初始化时要求为有限正数。体素内可以继续八叉树细分，不等同于实时点云降采样边长。 |
| `lio.max_layer` | `2` | 八叉树允许的最大深度，要求非负且 `layer_init_num` 长度覆盖到该层，否则体素初始化报错退出。顶层编号为 0，因此可使用 0、1、2 层；对应边长约为 0.5、0.25、0.125 m。不是只有两个层级。 |
| `lio.max_points_num` | `50` | 单个体素树节点用于平面拟合／更新的点数上限控制；达到相关条件后会停止该平面节点更新并释放点缓存。不是整张地图只能保留 50 点，也不是全局内存限制。 |
| `lio.layer_init_num` | `长度 5，见 YAML` | 各深度节点初始化拟合的点数阈值列表，从第 0 层开始对应；当前最大层为 2，仅用前 3 项。代码在点数超过阈值时初始化，例如阈值 5 通常需要至少 6 点。列表长度须至少为 `max_layer + 1`，初始化时检查，避免空列表或深层索引越界。 |
| `local_map.map_sliding_en` | `false` | 普通建图和先验扩图遵循此项；固定先验定位启动时强制关闭并告警。 |
| `local_map.half_map_size` | `100` | 保留区域在每个坐标轴方向的半宽，代码单位是**顶层体素索引格数**。当前 `voxel_size=0.5 m` 时约相当于各方向半宽 50 m，存在索引取整／边界差异；不是半宽 100 m。仅滑动开启时使用。 |
| `local_map.sliding_thresh` | `8.0` | 当前位置相对上次滑动位置的移动距离阈值，单位 m；达到阈值才执行下一次裁剪。不是剩余地图边缘距离。当前滑动关闭，不生效。 |
| `uav.imu_rate_odom` | `false` | 是否在滤波更新之间利用 IMU 继续外推并发布额外里程计／状态。代码以 0.004 s 定时回调尝试发布 `/LIVO2/imu_propagate` 和 `/fast_livo2/state6_imu_prop`，实际有效输出依赖 IMU 数据。关闭时保留正常 LIO 输出；不是关闭 IMU。 |
| `uav.gravity_align_en` | `true` | IMU 初始化后只执行一次重力对齐，使局部系重力指向负 Z。要求 `imu.imu_en=true`，否则启动报错；关闭不等于不估计重力，也不提供绝对航向。先验模式用实际旋转 A 补偿最终地图初值，体素地图构建成功后才发布最终位姿供 TF 使用；无先验模式直接保留原有重力对齐建图流程。两种模式均需静止初始化。 |
| `publish.dense_map_en` | `true` | 注册点云输出选用去畸变后的较稠密实时点云；为 `false` 时选用体素降采样后的点云。它不改变内部体素地图分辨率，但会影响消息量和后续 PCD 缓存点数。 |
| `publish.pub_effect_point_en` | `false` | 是否发布参与点到平面匹配的有效点 `/cloud_effected`，用于调试；不控制算法是否使用这些点。 |
| `publish.pub_plane_en` | `true` | 是否显示有效体素平面 Marker；不控制平面拟合或 LIO 几何约束。 |
| `publish.plane_publish_period` | `0.2` | 平面 Marker 完整快照最短发布间隔，秒；不再在算法线程中 sleep。 |
| `publish.pub_scan_num` | `1` | 视觉 RGB 点云分支在着色前累积的发布调用次数，当前为每次处理。不能把它当成所有消息的通用发布降频参数；纯 LIO 不走该累积着色分支。 |
| `publish.blind_rgb_points` | `0.0` | RGB 点云着色／输出时相对相机的最小距离，单位 m。仅视觉着色分支使用，与雷达预处理盲区独立；仍会检查点在相机前方且位于图像内。 |
| `publish.map_frame_id` | `"map"` | 先验／全局位姿的目标 frame，默认 map；两个算法入口及 TF 发布器使用同一值。 |
| `evo.seq_name` | `"Mid360_D405_Mapping_01"` | 轨迹文本的文件名主体，启用输出后对应源码包下 `Log/result/Mid360_D405_Mapping_01.txt`；不是 ROS 节点名或地图坐标系。 |
| `evo.pose_output_en` | `false` | 是否输出供轨迹评估使用的文本，字段为时间、位置和四元数 `qx qy qz qw`。不控制 ROS 里程计／路径发布，也不会自动运行 evo 或计算误差。 |
| `pcd_save.pcd_save_en` | `true` | PCD 保存总开关；先验模式还需 pcd_save_en_relocate=true。保存本次观测，不合并先验。 |
| `pcd_save.type` | `-1` | 初始化时无先验解析为 0、有先验解析为 2；也可显式指定 0=局部 camera_init、1=逐帧 IMU、2=先验 map（无先验时回退局部系）。修改 YAML 后重启生效。 |
| `pcd_save.pcd_save_en_relocate` | `true` | 允许先验定位保存本次观测；普通建图不受此开关影响。代码缺省 false，当前 YAML 为 true。 |
| `pcd_save.colmap_output_en` | `false` | Pinhole 视觉 COLMAP 导出；要求有效 PCD 保存且 type=0，输出到独立会话目录。 |
| `pcd_save.filter_size_pcd` | `0.15` | RGB 整图／尾部降采样附图边长，米；不对纯 LIO 强度整图再次降采样。 |
| `pcd_save.interval` | `-1` | 负数退出保存整图；正数按调用／处理帧数分段并在退出补存尾部；可捕获异常尽力保存此前有效缓存，0 被拒绝。 |
| `log.sensor` | `false` | 雷达／IMU／图像时间及预处理点数日志；false 时关闭高频 INFO。 |
| `log.lio` | `false` | LIO 特征、地图更新日志与调试状态文本；告警独立保留。 |
| `log.timing` | `false` | 逐帧 LIO 阶段耗时表。 |
| `log.map_sliding` | `false` | 普通建图滑动阈值、裁剪数量和耗时日志。 |
| `localization.max_unconstrained_frames` | `5` | 两种有先验模式连续估计失败的帧数上限；达到后尽力保存有效缓存，再保留原错误退出，需要核查并重启。 |
| `image_save.img_save_en` | `false` | 独立图像保存开关；要求 img_en=1，不依赖 PCD 总开关。 |
| `image_save.interval` | `1` | 每隔多少次图像／RGB 发布调用保存图像，正整数。 |
| `image_save.output_dir` | `"PCD/images"` | 图像保存目录，相对 workspace_root 解析，也兼容绝对目录；启用时自动创建。 |
| `relocalization.num_threads` | `4` | 配准器和 OpenMP 线程数，正整数；默认从 16 收敛为 4。 |
| `relocalization.max_attempts` | `300` | 真实配准输入帧尝试次数上限，正整数。 |
| `relocalization.timeout_seconds` | `120.0` | 真实配准计算阶段时间预算，秒；在库调用／回调边界检查。 |
| `relocalization.initial_pose_timeout_seconds` | `30.0` | 配准成功后等待建图服务接受初值的最长时间，秒；不等待先验初始化完成。 |

相机外参只读取 `extrin_calib.Rcl/Pcl`。相机文件的 `camera.model/width/height/scale/fx/fy/cx/cy/d0/d1/d2/d3` 分别为模型、目标图像尺寸、比例、焦距、主点和畸变参数；焦距和主点单位像素。当前 Pinhole 640×360、scale=1.0，实际内参见 `camera_parameter.yaml`。

关键区别：先验 `filter_size_map`、实时 `filter_size_surf`、内部 `lio.voxel_size`、RGB 输出 `filter_size_pcd` 是四个不同尺度。平面发布开关不关闭几何拟合。`half_map_size` 单位是根体素索引格数，0.5 m 体素时 100 约为半宽 50 m。`imu_int_frame` 在实现中按 IMU 样本累加，不是等待 30 帧雷达。

## 12. 离线工具

### COLMAP 目录工具

```bash
ros2 run fast_livo colmap_output.sh /absolute/path/to/new_colmap_directory
```

只创建 images 和 sparse/0，保留既有文件，不依赖 rospack，不删除旧数据。正常视觉导出由建图原生创建会话目录，无需先运行此工具。

### 网格融合

```bash
ros2 run fast_livo mesh.py /absolute/path/to/per_scan_pcd --poses /absolute/path/to/poses.txt --input-frame world --output /absolute/path/to/mesh.ply
```

可选 `--voxel-size`、`--sdf-trunc`、`--min-weight` 和 `--preview`。依赖 NumPy、SciPy、Open3D、VDBFusion；它不是 LIO 或 PCD 保存的前置依赖。

输入按文件名字典序排序，每个 PCD 必须有对应的 `x y z qw qx qy qz` 传感器位姿。world 输入已经在同一世界系；body 输入先应用对应姿态。传给 VDBFusion 的是世界系点和三维传感器原点，不能拿单位 4×4 矩阵替代真实观测原点。[VDBFusion API 约定](https://github.com/PRBonn/vdbfusion#usage)

不要把累积的整图或包含多帧、多观测原点的分段云，当作有精确单一视点的一帧扫描；若需要可靠 TSDF 重建，应采集逐帧点云及对应位姿。缺少真实姿态时程序拒绝静默使用全单位位姿。

Vikit Python 包已改为 setuptools / ament_python，`RosNode` 使用 `ros2 run`、点号参数与字面量 argv，不执行拼接 shell；CPU 信息按 Python 3 文本读取，深度图异常类型已补全。

## 13. 故障定位与历史依据

| 现象 | 检查与处理 |
| --- | --- |
| 启动提示时间校验失败 | 检查系统同步状态；回放／测试时显式关闭 time_check，不修改传感器时间参数来绕过系统时间问题 |
| 等不到初值 | 检查先验模式、共享 YAML、/fast_livo2/set_initial_pose 服务和两个进程的 ROS_DOMAIN_ID；根据拒绝／超时日志处理，保持静止 |
| 提示 zero valid planes | 首先确认先验 filter_size_map=0.1 和地图几何；不要把“有体素”误认为“有可用平面” |
| 配准成功后定位无效 | 检查有效点、初值 IMU 语义、外参及先验密度；ACK 不是持续匹配正常的证明 |
| 没有 map 系里程计 | 检查最终建图初值和 TF 发布器；普通建图缺少 map TF 时局部输出仍可正常工作 |
| 找不到 small_gicp / TEASER 特征目标 | 首次完整构建，保留 teaserpp 的 colcon.pkg，确认 source 当前安装空间 |
| Livox SDK 动态库缺失 | 检查固定版本安装、`ldconfig -p`、/usr/local/lib 与程序动态链接，勿混用其他工作空间库 |
| Livox 启动 bind failed | 核对所选 JSON 的 `host_ip` 是否为当前主机网卡已有的地址；RDK 现场为 `192.168.2.100`，仓库默认仍为 `192.168.2.50`；修改 JSON 后重建驱动 |
| RDK RViz 启动后 -11 | 尚未排查，未修复；可用 `enable_rviz:=false` 进行无界面运行，这不代表图形问题已解决 |
| RDK 驱动 Ctrl+C 后 -11 | 暂不处理，根因未确认，驱动正常退出尚未通过实机验收 |
| compressed 插件缺失 | 安装当前 ROS 发行版的 compressed image transport 插件，仅视觉解压需要 |
| 保存没有生成文件 | 检查两个权限开关、有效观测、workspace_root 及解析后的目录、interval 和终端保存结果；先验模式不自动合并旧图 |
| CPU 高或延迟增加 | 检查配准预算、线程数、地图点数及日志开关；关闭不需要的平面显示、图像解压和视觉输入 |

历史实机证据：2026-10-30 用户确认普通 LIO 正常；2026-11-02 用户确认旧图 1549、关闭重力、先验滤波 0.1 时持续定位不再漂移。此前 0.5 先验滤波曾把约 220 万点降成 528 点，实际体素没有有效平面。该旧图已不在当前仓库，不能直接沿用旧命令路径。

历史地图中，2327 与 posteriori 字节相同，2329 与 priori 字节相同；文件名不能证明采集方式。当前旧地图已由用户移除，新流程按需采集并把选定文件放入固定输入目录；开发回归只使用临时地图。

本轮提供核心函数、合成 ROS 流程及离线工具回归，不把历史测试计数机械相加为当前实机验收。开启视觉、MID360S 实机完整流程、TEASER/SAC-IA 的跨场景成功率、重力开启后长期定位精度和 CPU 峰值，仍需对应设备／数据验证。

## 14. 回归检查

```bash
cd /home/fire/Desktop/FAST_LIVO2_Ultra
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_Ultra/install/setup.bash
colcon test --packages-select fast_livo
colcon test-result --verbose
python3 /home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/test/ros_regression.py --install /home/fire/Desktop/FAST_LIVO2_Ultra/install --shutdown-repeats 20
python3 /home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/test/bringup_regression.py --install /home/fire/Desktop/FAST_LIVO2_Ultra/install
python3 /home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/test/workspace_root_ros_regression.py --install /home/fire/Desktop/FAST_LIVO2_Ultra/install
python3 /home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/test/prior_extension_ros_regression.py --install /home/fire/Desktop/FAST_LIVO2_Ultra/install
MPLBACKEND=Agg python3 /home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/test/tool_regression.py
```

合成 ROS 检查默认使用独立域 179、仅本机发现，不启动雷达或相机，所有测试点云写临时目录。core_regression 与 prior_extension_regression 直接调用实际算法／保存函数；扩图 DDS 脚本使用域 191，验证未知区域扫描与异常退出保图；ROS 脚本运行已安装程序；工具检查使用真实 Open3D 文件读写及受控 TSDF 替身，**不声称已经运行真实 VDBFusion 重建**。

2026-11-05 自动根目录验证：本机 Jazzy 下两包构建通过，68 项核心检查、110 项扩图核心检查、14 种两节点根目录参数场景通过；组合入口覆盖 6 种手动／auto／缺省传参检查、无先验配置拒绝和 2 种合成运行／退出保存。建图与配准的实际参数均自动解析为同一个 FAST-LIVO2 源码包目录，支持带空格的手动目录；临时布局覆盖 Desktop 与嵌套总工程，缺失自动源码目录会拒绝。新增节点参数脚本使用域 185，组合入口使用域 183；未启动硬件、未改写项目地图，RDK 两处实际部署仍需重新编译验证。

2026-11-03 先验专用精简后验证：relocalization 重新编译通过，95 项隔离 ROS 合成检查和 5 项启动入口场景通过。新增覆盖无先验配置拒绝、五个配准入口的有效先验启动、TF 固定订阅及其输入／输出双方晚启动交付；此前 43 项核心函数检查已通过，建图算法代码本轮未修改。初值服务检查覆盖非法位姿拒绝、接受后才创建订阅、重复请求不重复初始化、建图晚启动、响应丢失后的相同请求重试、明确拒绝与超时，以及配准器在先验初始化完成前凭接受响应正常退出。原有重力开／关、普通／先验流程、约束丢失、最终 TF、视觉启动和 JPEG/PNG 解压检查也通过；组合入口实际运行时关闭硬件驱动，验证定位及单次 SIGINT 退出保存，所有地图只写临时目录。

2026-11-04 连续扩图验证：fast_livo 编译通过，43 项原核心检查、110 项新增核心检查、29 项扩图 DDS 检查、95 项原 ROS 检查及 5 个组合启动场景通过。新增核心检查使用已知预测位姿的重叠扫描，覆盖普通／固定先验／扩图三种模式、离开原先验后的新体素匹配、非单位地图变换、滑动裁剪、失败帧隔离、异常退出保图和保存失败仍保留原错误。扩图 DDS 检查运行实际节点，核对初值服务、最终 TF、地图位姿、成功扫描与保存点数一致及先验文件未改变；启动场景使用分离的正交平面，避免小角点跨体素边界导致的几何歧义。测试均未启动实机驱动，不能代替真实路线的漂移、重影和长时间运行验收。

2026-11-04 统一路径根目录验证：fast_livo 和 relocalization 构建通过，59 项核心配置／保存检查、110 项扩图核心检查、29 项扩图 DDS 检查、95 项原 ROS 检查及 5 个组合启动场景通过。覆盖更换根目录、普通／先验输出切换、相对路径归一化、带空格目录、旧绝对路径覆盖、非法根目录拒绝，以及实际建图与配准共用根目录加载地图、异常退出保存观测。全部使用本机隔离 ROS 域和临时点云，未在 RDK 实机执行。

先前适配还通过了完整工作空间构建、7 项离线工具检查、20 次 SIGINT 压力检查、独立 launch、实际 launch 图像传输及含空格先验文件名检查。真实 VDBFusion 后端未安装，网格检查仅覆盖封装、坐标和实际文件 I/O；合成检查不代表已经验证实机精度或长期运行表现。


### 14.1 实测前复核与已知风险（2026-11-04）

文档已核对默认配置、安装副本、两个一键入口、初值服务和固定 TF 输入，文档链接与 Bash 语法检查通过。新增单独使用当前默认 TEASER+VGICP 参数，在 6128 点、已知非单位变换的合成场景下完成配准并交付给测试服务；这只补充配准链路验证，不是实机精度测试，也不替代实际建图服务的联调。

本次已修复约束丢失抛异常绕过末尾保存的问题：可捕获的运行异常会尽力写出此前有效缓存，随后保留原错误及非零退出码；写盘错误单独报告。不能保证 SIGKILL、进程崩溃或内存耗尽时能够保存。

以下仍是当前代码的未修复项，不能以一次正常启动或一次定位成功排除：

| 优先级 | 问题及证据 | 建议修改 |
| --- | --- | --- |
| 大图采集前优先处理 | 建图 launch 未设置退出宽限时间，当前 Jazzy launch 默认 SIGINT 后约 5 秒升级 SIGTERM，再约 5 秒升级 SIGKILL。写盘较慢时可能被强杀；默认整图缓存和关闭的地图滑动也会持续占内存。 | 延长建图节点的写盘退出宽限，实测大图保存耗时；较长采集评估正数 interval 的分段方案，使用前确认后续合图方式。 |
| 建议修复 | 配准器 Livox 回调直接按 `point_num` 索引 `points`，缺少长度检查。合成复现：`point_num=1`、数组为空导致退出码 -11；实机驱动通常提供一致数据，但异常发布者或格式异常的回放数据仍可能触发。 | 使用数组长度边界，点数不一致时明确丢弃并告警。 |
| 建议修复 | 断流后没有主动失效通知。合成复现：停止输入 1.2 秒后节点仍存活，里程计不更新，但最后的 `tracking_valid` 仍为 true。 | 增加传感器新鲜度检查和断流失效通知；使用方同时检查位姿时间戳，不能只看缓存 Bool。 |
| 操作时必须注意 | 固定 `map_MMDD_HHMM` 名称会在同目录、同分钟重启时覆盖 PCD 或元数据；先验分数／收敛也不能排除重复结构中的误配准。 | 同分钟重试前备份输出；可增加重名检测。首次重定位需核对现场位置、朝向和地图重合，而非只看成功日志。 |

2026-11-03 的风险复现仅使用临时目录和隔离 ROS 域，点数异常测试禁用了 core dump；本次扩图及保存修改也未启动实机驱动。未实测项目仍包括实际传感器同步、长时间内存增长、完整实图保存耗时，以及不同场景的配准可靠性。

首次实测建议保留原始 `/livox/lidar`、`/livox/imu` 数据和终端日志，并保存生成地图的 metadata.yaml 及本次配置。最低验收范围：

1. 采图：静止初始化后运行一段代表性路线并回到起点，检查漂移／重影；正常退出后确认 PCD 可以重新读取，点数、范围及文件大小合理。
2. 重定位与扩图：先完成“配准 → 服务接受 → 先验初始化 → map 位姿持续输出”，核对已知地标和朝向，再沿连续路线从已知区域进入未知区域并返回；检查地图接缝、重影、位姿跳变与数据更新，退出后确认本次观测包含新区域且可读取。固定先验模式应另外在旧地图范围内验证。
3. 重启复测：至少换一个起点或明显不同的朝向，再做一次定位；同时检查较长运行和正常退出保存。避免同分钟覆盖上次输出。

完成一次采图和一次先验定位，可以记录为“当前设备、配置和场景的主流程实测通过”。重复启动、不同起点、断流和大图／长时间运行未覆盖前，不应写为“工程已无问题”。误差是否合格应依据实测地标或外部参考与实际使用要求判断。

## 15. 来源与许可证

基于 [FAST-LIVO2](https://github.com/hku-mars/FAST-LIVO2)、[FAST-LIVO2 ROS 2 移植](https://github.com/SuperLDG/FASTLIVO2_ROS2)、[Fast-LIO2-Localization](https://github.com/PolarisXQ/Fast-LIO2-Localization)，并集成 [small_gicp](https://github.com/koide3/small_gicp)、[TEASER++](https://github.com/MIT-SPARK/TEASER-plusplus)、[Livox ROS Driver 2](https://github.com/Livox-SDK/livox_ros_driver2) 和 Vikit。各目录的许可证及原作者声明继续适用；应分别核对学术与商业使用条件，不将整合工程视为统一重新授权。
