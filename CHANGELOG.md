# 项目修改记录

本文档记录本次协作起的项目修改，后续完成修改时持续更新。

## 维护约定

- 按日期倒序追加记录，保留已有历史。
- 每项记录包含问题背景、修改文件、具体改动、验证结果及尚存问题。
- 区分已验证结果与未验证事项；后续验证有新结果时补充到对应记录。
- 不将工作区中原有、未经本次协作修改的内容记为本次改动。

## 2026-11-05

### 补充 PC／RDK 环境与迁移文档（用户确认第 8 项）

**修改范围**

仅更新以下三份说明及本记录，保留本项开始前工作区中已有的代码和配置改动：

- `README.md`：区分 PC 的 Ubuntu 24.04／Jazzy 与 RDK 的 Ubuntu 22.04.5／Humble，
  补充 RDK 工程／SDK 源码路径、构建命令和迁移时需核对的根目录、型号、主机 IP。
- `quick_start.md`：提供两套运行终端环境命令，采图／扩图仍使用原两个一键 launch；
  两张任务配置表各保留原四项，地图目录说明统一相对 `workspace_root`，修正 README 风险段落链接。
- `src/livox_ros_driver2/版本.md`：补充 RDK 的 Humble 构建与 SDK 源码路径说明，
  说明 MID360S 与主机地址的现场配置差异；保留 SDK 1.5.2 固定提交及 PC 操作示例。

仓库默认仍为 MID360、主机 `192.168.2.50`；RDK 历史实例为 MID360S、主机 `192.168.2.100`。
本项没有修改这些实际配置，也未改动配准的 300 次／120 秒预算。
三份文档均明确区分 RDK 历史构建／收包记录与尚未完成的定位、扩图、频率和时间戳验收；
RViz 启动崩溃仍未排查，驱动退出崩溃仍暂不处理，两项均未修复。

**核对与验证**

- 三份说明中的 31 段 Bash 命令通过语法检查，仅使用 `bash -n`，没有执行其中的安装、卸载或构建命令。
- 10 个本地文件链接有效；quick start 的两张四项配置表与本项修改前逐字一致。
- `git diff --check` 通过；与本项开始前快照比对，三份说明和本记录之外的已有差异保持不变。
- 本项未启动实机或修改 SDK，仅文档变更，无需重新编译。RDK 运行验证仍以上述边界为准。

至此，本轮 8 项均已按用户选择处理：第 1 项同步构建修复，第 2 项核对 SDK，第 3／4 项保留配置，
第 5／8 项更新说明，第 6 项跳过，第 7 项暂不处理。本项不执行 git 提交或推送。

### 驱动退出崩溃暂不处理（用户决定停止第 7 项）

用户明确表示本次不再解决该 bug，停止后续取栈与修复工作。第 7 项标记为“暂不处理”，
已完成的初步源码观察保留，根因尚未确认，不能标记为已修复。

本轮仅在 `/tmp` 准备过 RDK 调试命令并核对 Shell／GDB 命令语法；未在 RDK 执行，
未启动被调试驱动或传感器，未修改驱动代码、SDK、launch 或参数。
本项仅追加本记录；后续进入第 8 项文档更新范围选择。

### 驱动退出崩溃的初步源码核对（第 7 项，尚未修复）

**本次范围与已知证据**

用户跳过 RViz 排查后进入驱动退出问题。本次仅阅读当前工程源码、可用本机日志与本机
`/home/fire/third_party/Livox-SDK2` 源码；SDK 源码 HEAD 为工程指定的
`c0796f04c143143899c87a773d9f6b7136453c0b`。未启动驱动、传感器或调试器，未修改驱动代码。

RDK 的原始日志路径 `/home/sunrise/.ros/log/2026-11-05-00-18-08-649087-ubuntu-49962/launch.log`
在当前本机不可用，RDK 崩溃仍仅有下方历史记录，没有调用栈。
本机 2026-11-03 与 2026-11-04 的六份对应 launch 日志均记录驱动正常退出，不能据此排除 RDK 问题。

**源码观察与判断边界**

- `src/livox_ros_driver2/src/driver_node.cpp` 的析构函数先设置退出标志，再等待两个发布线程结束。
  点云和 IMU 分发函数可能阻塞在信号量 `Wait()`；`RequestExit()` 只设置标志，不主动唤醒。
  因而在已阻塞且不再收到数据时存在退出卡住的风险，这本身不是段错误的证据。
- `src/livox_ros_driver2/src/lds_lidar.cpp` 的退出流程调用 `LivoxLidarSdkUninit()`，
  未显式调用 `pub_handler().Uninit()`；后者留到静态处理器析构时才注销观察者并回收点云处理线程。
  退出清理顺序可以加固，但不能仅凭此认定 RDK 段错误的根因。
- 对应 SDK 的 `DataHandler::Destory()` 会清空观察者表，`RemovePointCloudObserver()` 会先查找再删除；
  对象存活时，先清空再删除本身不能作为必然崩溃的依据。

建议先在 RDK 单独运行驱动并采集退出时的全部线程调用栈，再确定修改位置。
如用户选择先加固退出流程，范围限定为显式停止回调和工作线程、唤醒等待线程、随后清理 SDK，
并进行本机验证；即使本机通过，也仍需 RDK 实机复测，不能提前标记段错误已修复。

### 跳过 RViz 崩溃排查（用户确认第 6 项）

用户选择跳过本项并进入第 7 项驱动退出崩溃。未启动 RViz，未修改其配置、launch 或依赖。
此前 RDK 的 RViz 启动 `-11` 问题保持待排查状态，本次跳过不代表已解决。

### 补充先验重定位操作说明（用户确认第 5 项）

**修改范围与内容**

按用户选择，仅更新 `quick_start.md` 与本记录；保留两个任务原有的四项配置表、启动命令、
参数和算法代码。在先验任务下补充：

- 从先验覆盖区静止启动，优先选择采图起点附近并保持相近高度和姿态。
- 自动匹配持续失败时，在配准器退出前用 RViz 的 `2D Pose Estimate` 向 `/initialpose`
  发送 `map` 坐标系下的雷达初值，转入 GICP 精配准。
- 二维初值的高度、横滚和俯仰为零；不适用时提供完整三维初值。超限退出后需要重新启动配准流程。

**核对与验证范围**

已核对现有订阅类型为 `geometry_msgs/msg/PoseWithCovarianceStamped`，回调检查地图坐标系后
将状态设为 `GICP_PHASE`，随包 RViz 的初值工具发布到 `/initialpose`。
与本项修改前快照比较，quick start 仅新增两段说明，两张配置表及其余内容保持原样；
`git diff --check` 通过。仅文档更新，无需重新编译。

本项未启动 RViz 或传感器，也未验证现场匹配效果；RViz 启动崩溃与驱动退出崩溃仍待后续单独排查。

### 保留当前配准等待预算（用户确认第 4 项）

**选择与核对结果**

用户选择保留共享 YAML 中的 `relocalization.max_attempts: 300` 与
`relocalization.timeout_seconds: 120.0`。已解析源配置确认数值；任一上限先达到都会结束配准。

本项仅追加本记录，没有修改参数、算法或验收门限，也未启动传感器，无需重新编译。
保留预算不代表此前内点不足的问题已解决；需在后续现场测试中确认地图覆盖和观测条件。
配准器超限退出后，建图节点继续等待初值，需要重新启动配准流程。

### 保留本机雷达型号与网络配置（用户确认第 3 项）

**选择与范围**

用户选择保留本机配置，不将 RDK 的 MID360S／`192.168.2.100` 设置同步到当前工程。

**核对结果**

- `src/livox_ros_driver2/config/msg_MID360.yaml` 默认型号仍为 `mid360`。
- `src/livox_ros_driver2/config/MID360s_config.json` 的 `host_ip` 仍为 `192.168.2.50`。
- 本项仅追加本记录，没有修改驱动配置、代码或已安装文件，也未启动设备；无需重新编译。
- 此选择不代表本机网络与雷达实机通信已通过验证；RDK 的历史诊断记录保持原样。

### 本机 Livox-SDK2 版本与链接核对（用户确认第 2 项）

**范围与背景**

用户选择仅核对本机 SDK 版本和驱动链接位置。本次检查目标为
`/home/fire/Desktop/FAST_LIVO2_Ultra`，不是远程 RDK；下方 RDK 的历史记录保持原样。

**只读检查结果**

| 检查项 | 结果 |
| --- | --- |
| SDK 头文件 | `/usr/local/include/livox_lidar_def.h`，版本宏为 `1.5.2` |
| 驱动 CMake 缓存 | 头文件目录 `/usr/local/include`；SDK 库 `/usr/local/lib/liblivox_lidar_sdk_shared.so` |
| 驱动实际加载的组件 | `install/livox_ros_driver2/lib/liblivox_ros_driver2.so` |
| 组件的 SDK 动态链接 | `ldd` 解析至 `/usr/local/lib/liblivox_lidar_sdk_shared.so` |
| 动态库实际版本 | 调用该库的 `GetLivoxLidarSdkVer`，返回 `1.5.2`，与头文件一致 |

SDK 由驱动组件间接加载，因此核对了组件共享库的依赖，不能仅依据包装可执行文件的 `ldd` 输出判断。
版本查询未调用 `LivoxLidarSdkInit`，未启动驱动或传感器，未安装、卸载或替换 SDK。

**结论与尚存事项**

本机版本与链接位置符合工程要求，无需重复升级。本次仅更新本记录，没有修改工程代码或参数。
未重新核对远程 RDK 状态或 SDK 源码提交哈希，也未验证实机收包和退出行为；
配准内点不足、RViz 与驱动退出崩溃仍属于后续待排查事项。

### 将 octomap_ros 构建修复同步至本机（用户确认第 1 项）

**问题背景**

下方 RDK／Humble 记录已验证删除无用的 `octomap_ros` 强制检查可解除构建阻塞，
但当前 `/home/fire/Desktop/FAST_LIVO2_Ultra` 尚保留该检查。用户已明确确认同步第 1 项。

**修改文件与内容**

- 删除 `src/relocalization/CMakeLists.txt` 中的 `find_package(octomap_ros REQUIRED)`。
- 重新核对源码、包声明和目标链接，未发现配准代码使用该依赖。
- 本条仅记录这次依赖检查删除及验证；工作区原有的路径统一改动不计入本次修改。

**验证结果**

在本机 ROS 2 Jazzy 环境执行：

```bash
source /opt/ros/jazzy/setup.bash
source /home/fire/Desktop/FAST_LIVO2_Ultra/install/setup.bash
cd /home/fire/Desktop/FAST_LIVO2_Ultra
CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build --packages-select relocalization --executor sequential --cmake-force-configure
```

- 强制重新配置、构建及安装成功，退出码为 `0`，总耗时约 2.65 秒。
- 与修改前快照比对确认 CMake 文件仅删除了获准的一行。
- `git diff --check` 通过。
- 仍有 `CMP0074/PCL_ROOT` 开发警告，不影响本次构建；本轮未处理此警告。

**尚存问题与验证范围**

本次未启动实机传感器；不能替代 RDK 现场复测。重定位内点不足、RViz 崩溃与驱动退出崩溃
仍按原记录待排查。后续项目继续逐项等待用户选择。

### 重定位内点不足与退出崩溃排查（仅诊断和方案）

**本次范围**

按用户要求，仅阅读配置、代码和日志，提供解决方案；未修改算法代码、驱动代码或参数配置。
本次追加记录不代表以下建议已执行或问题已修复。

**证据与诊断**

- 用户提供的运行日志显示，TEASER 每帧找到约 53～80 对候选对应点，平移内点多数
  只有 2～4 个。当前要求至少 5 个内点、连续成功 3 次，才能进入 GICP 精配准。
  偶尔出现 `Success count: 1 / 3` 后，下一帧内点不足又清零，因此未完成初始化。
- `Translation estimation complete` 仅表示求解结束，不代表结果通过验收。
- 配置为 `max_attempts: 300`、`timeout_seconds: 120.0`，任意限制先达到都会退出。
  完整启动日志显示配准节点运行约 32 秒，与 10 Hz 输入下用完 300 次尝试一致；
  结合报错分支，判断本次首先触发的是尝试次数上限。
- 配准节点退出后，建图继续输出 `Waiting for initial pose...`，不能靠继续等待自动恢复。
- 实际先验为 `PCD/map/map_1103_2217.pcd`，文件约 242 MiB，PCD 头声明 7,910,858 个点。
  尚未确认这份先验与当前现场、雷达位置和观测范围是否对应，不能据日志断言地图错误。
- 后续日志说明配准已收到点云并进行计算，启动问题已从此前的本地网络绑定失败推进到配准阶段；
  尚未单独测量雷达和 IMU 频率、时间戳质量。
- Ctrl+C 后 Livox 驱动以 `-11`（SIGSEGV）退出，发生在 SDK 清理和驱动析构日志之后。
  这是独立的退出阶段问题，不是之前 TEASER 内点不足的原因；没有崩溃调用栈，具体原因未确定。
- 完整启动日志还记录 RViz 在启动后以 `-11` 退出，图形界面问题需另外排查。
  日志位置：`/home/sunrise/.ros/log/2026-11-05-00-18-08-649087-ubuntu-49962/launch.log`。

**建议操作顺序（尚未执行）**

1. 确认先验来自当前现场，雷达处于地图覆盖范围；优先回到采图起点附近，保持相近高度和姿态，
   选择有墙角、立柱等明显结构的位置，并在重定位及 IMU 初始化完成前保持静止。
2. 自动匹配仍失败时，使用已有 `/initialpose` 接口提供手动初值。节点收到有效初值后直接转入 GICP。
   RViz 中设置 Fixed Frame 为 `map`，使用发布到 `/initialpose` 的 `2D Pose Estimate`。
   初值表示雷达在先验地图中的位姿；高度、横滚和俯仰不可忽略时，应提供完整三维初值。
   本次 RViz 已崩溃，需先恢复界面或使用另一台已配置 ROS 通信的主机；初值必须在配准节点退出前发送。
3. 需要更多操作时间时，可将共享 YAML 中原有 `relocalization.max_attempts` 改为 `3000`、
   `relocalization.timeout_seconds` 改为 `300.0`，其他参数保留。此建议仅延长预算，不能改善匹配质量。
   不建议仅为通过验收而把内点门限从 5 降至 2～3。
4. 配准节点已超限退出时需重新启动配准流程。验收应依次确认配准成功、建图服务接受初值、
   先验初始化完成、`tracking_valid=true` 且位姿时间戳持续更新，再移动设备。

如自行调整源码 YAML，可直接指定配置启动，无需仅为 YAML 更改重新编译：

```bash
source /opt/ros/humble/setup.bash
cd ~/Desktop/FAST_LIVO2_Ultra
source install/setup.bash
ros2 launch fast_livo relocate_mapping.launch.py \
  config_file:="$HOME/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/config/mapping_relocation.yaml"
```

**退出崩溃的临时操作方案（不是修复）**

将雷达驱动单独运行，重试建图和配准时保留驱动进程，减少重复启停。每个终端先加载上述 ROS 和工作区环境。

终端一：

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

终端二：

```bash
ros2 launch fast_livo relocate_mapping.launch.py start_driver:=false
```

若同时采用源码 YAML 参数调整，在终端二命令中追加上述 `config_file:=...` 参数。
结束时先停止建图和配准，等待保存完成，再停止驱动。该方式不保证消除驱动自身退出崩溃，
彻底定位仍需要崩溃调用栈。

**当前状态**

重定位成功、手动初值效果、参数调整效果、RViz 恢复和驱动正常退出均未验证；本次只更新本文档。

### 排查并修正 MID360S 启动时的 bind failed

**问题与原因**

启动 `msg_MID360_launch.py` 后，SDK 已解析配置，但报告 `bind failed` 和
`Failed to init livox lidar sdk`。源码与安装目录的 MID360S 配置均将
`host_ip` 设为 `192.168.2.50`，而本机 `eth0` 实际地址为
`192.168.2.100/24`，不存在配置中的本机地址。SDK 在本地 socket 的
`bind()` 失败处输出该错误。

**检查结果**

- 已安装 SDK 动态库查询及头文件版本均为 **1.5.2**。
- `/home/sunrise/third_party/Livox-SDK2` 的 HEAD 为指定提交
  `c0796f04c143143899c87a773d9f6b7136453c0b`；此前 SDK 版本更新待办已由用户完成。
- 到配置雷达地址 `192.168.2.3` 的路由使用 `eth0`，源地址为 `192.168.2.100`。
- 检查时未发现 UDP 56101、56201、56301、56401、56501 被占用。
- 启动失败后的驱动进程仍存在，应用新配置需要先在原启动终端按 `Ctrl+C`，再重新启动。

**修改内容**

- 将 [MID360s_config.json](src/livox_ros_driver2/config/MID360s_config.json) 中
  `host_ip` 从 `192.168.2.50` 改为 `192.168.2.100`，匹配本机网卡。
- 雷达地址仍按现有配置使用 `192.168.2.3`；本次尚未确认设备实际地址或收包情况。

**验证状态**

- 执行 `source /opt/ros/humble/setup.bash` 后运行
  `colcon build --packages-select livox_ros_driver2 --executor sequential`，构建成功，退出码为 `0`。
- JSON 解析与比对通过：源码和安装目录配置一致，`host_ip` 均为 `192.168.2.100`。
- `git diff --check` 通过。
- 修复当时尚未重启现有驱动；后续用户日志已显示配准节点收到点云并开始计算，详见上方重定位排查记录。
  实机话题频率和时间戳质量仍待验证。

## 2026-11-04

### 核对 Livox 驱动与 SDK 的版本配套要求

**阅读依据**

- [src/livox_ros_driver2/版本.md](src/livox_ros_driver2/版本.md)
- 驱动源码版本宏、已安装 SDK 头文件、SDK 动态库版本查询结果及驱动 CMake 缓存。

**本机核对结果**

| 项目 | 本机现状 | 工程要求及后续动作 |
| --- | --- | --- |
| ROS 驱动 | 工程内 `livox_ros_driver2`，源码版本宏为 `1.2.6` | 保留本地适配包，不用上游同版本包覆盖 |
| Livox-SDK2 | 动态库查询和头文件宏均为 `1.4.3` | 按版本文档更新到 `1.5.2`，固定提交 `c0796f04c143143899c87a773d9f6b7136453c0b` |
| SDK 使用位置 | CMake 缓存指向 `/usr/local/include` 和 `/usr/local/lib/liblivox_lidar_sdk_shared.so` | 更新 `/usr/local` 中的 SDK 后重新编译工程 |
| 系统与 ROS | Ubuntu 22.04.5、ROS 2 Humble | 本机命令使用 `/opt/ros/humble/setup.bash` |
| 工作区 | `/home/sunrise/Desktop/FAST_LIVO2_Ultra` | 文档中的 `/home/fire/...` 路径需按本机位置替换 |
| 雷达型号配置 | 源码及安装目录的 `msg_MID360.yaml` 均为 `mid360s` | 启动前核实实际设备型号及对应 JSON 中的网络配置 |

**结论与待办**

- 需要更新的是底层 **Livox-SDK2：1.4.3 → 1.5.2**；工程内 ROS 驱动保留，SDK 更新后重新编译。
- 该结论来自工程指定的配套版本要求，不表示已证明 SDK 1.4.3 无法使用 MID360S。
  当前头文件已有 MID360S 类型定义，先前全量构建也已通过；编译通过仍不代表满足指定配套要求或实机验证通过。
- `版本.md` 中的 Ubuntu 24.04 / Jazzy 和 `/home/fire` 是原环境信息，不能直接照搬本机执行命令；本次没有提出升级操作系统或 ROS 的要求。
- 版本文档没有指定雷达固件升级版本，本次没有依据要求更新雷达固件。
- 本次仅完成只读检查和本文档更新，**尚未安装、卸载或更新 SDK，也未进行实机收包验证**。
- 后续执行 SDK 更新前需停止相关驱动进程；`/usr/local` 中的 SDK 由多个工作区共享，更新后需核对其他使用方。

### 修复 relocalization 因 octomap_ros 缺失导致的构建失败

**问题背景**

在 ROS 2 Humble 环境下运行 `colcon build`，其余 7 个包构建成功，
`relocalization` 在 CMake 配置阶段失败，提示找不到
`octomap_rosConfig.cmake` 或 `octomap_ros-config.cmake`。

**修改文件**

- [src/relocalization/CMakeLists.txt](src/relocalization/CMakeLists.txt)

**具体改动与依据**

删除以下强制依赖检查：

```cmake
find_package(octomap_ros REQUIRED)
```

检查确认 `relocalization` 的 C++ 源码未使用 `octomap_ros`，构建目标也未声明
对它的链接依赖，因此删除该多余检查即可解除构建阻塞，无需额外安装该包。
包内 `rviz/loam_livox.rviz` 中存在 OctoMap 显示插件配置；该显示配置与这里移除的
CMake 依赖检查不同，本次未修改或验证其运行效果。

**验证结果**

在项目根目录执行：

```bash
source /opt/ros/humble/setup.bash
colcon build
```

- 构建退出码为 `0`。
- 全部 8 个包构建成功，总耗时约 2 分 49 秒。
- `relocalization` 完成编译、链接及安装。
- `git diff --check` 通过。

**尚存问题与验证范围**

- 构建仍输出 CMake `CMP0074` 开发警告：未设置该策略，`PCL_ROOT=/usr`
  被忽略。此警告未阻止本次构建，暂未处理。
- 本次验证限于构建，未启动传感器、建图或重定位进行运行验证。

### 建立持续维护的修改文档

- 新增根目录 [CHANGELOG.md](CHANGELOG.md)，记录修复依据、实际验证结果和后续维护约定。
- 后续项目修改继续追加到本文档。
