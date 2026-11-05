# Quick Start：MID360 / MID360S + IMU

前提：工程已编译，雷达地址为 `192.168.2.3`，主机网卡与所选设备 JSON 中的地址一致，系统时间已同步。默认纯 LIO，无需相机。PC 使用 Ubuntu 24.04／Jazzy、MID360、主机 `192.168.2.50`；RDK 现场使用 Ubuntu 22.04.5／Humble、MID360S、主机 `192.168.2.100`。

`PCD` 已移入 `src/FAST-LIVO2` 包内。[mapping_relocation.yaml](/home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/config/mapping_relocation.yaml) 的 `workspace_root` 保持 `"auto"`，自动使用本次编译对应的 FAST-LIVO2 源码包目录；Desktop 和总工程分别在各自位置编译后，不必手动切换根路径。也可填写绝对目录覆盖。地图和图像目录均相对它解析，地图数据须手动复制；启动日志会显示实际根目录。移动源码后重编 `fast_livo` 和 `relocalization`，仅移动 install 不会更新路径。RDK 总工程部署见 [quick_start_whole_prj.md](/home/fire/Desktop/FAST_LIVO2_Ultra/quick_start_whole_prj.md)。修改源码 YAML 后按下方构建命令同步安装副本。

**每个运行终端按所在设备选择一组：**

PC：

```bash
source /opt/ros/jazzy/setup.bash
cd /home/fire/Desktop/FAST_LIVO2_Ultra
source install/setup.bash
```

RDK：

```bash
source /opt/ros/humble/setup.bash
cd /home/sunrise/Desktop/FAST_LIVO2_Ultra
source install/setup.bash
```

仓库驱动默认 MID360；MID360S 将驱动 [msg_MID360.yaml](/home/fire/Desktop/FAST_LIVO2_Ultra/src/livox_ros_driver2/config/msg_MID360.yaml) 的 `lidar_model` 改为 `mid360s`，并核对 [MID360s_config.json](/home/fire/Desktop/FAST_LIVO2_Ultra/src/livox_ros_driver2/config/MID360s_config.json) 的 `host_net_info` 中 `host_ip`：上述 RDK 为 `192.168.2.100`，仓库默认仍为 `192.168.2.50`。实际值以设备网络为准。

默认读取安装目录配置。**每次修改源码 YAML／JSON 后**，在上方已进入工程根目录的终端执行一次，再启动任务：

```bash
colcon build --packages-select livox_ros_driver2 fast_livo --executor sequential
```

## 1. 一键采集先验地图

直接编辑 [mapping_relocation.yaml](/home/fire/Desktop/FAST_LIVO2_Ultra/src/FAST-LIVO2/config/mapping_relocation.yaml)，修改现有字段：

| 参数 | 采集先验地图 |
| --- | --- |
| `locate_in_prior_map` | `false` |
| `prior_map_name` | 保持原值，此模式不读取先验 |
| `pcd_save.pcd_save_en` | `true` |
| `pcd_save.pcd_save_en_relocate` | `true`（此模式不参与保存判断） |

启动前请先核实上表。其余参数保留工程默认。初始化自动使用局部坐标，保存到固定 `PCD/priori`。参数修改后先按上方命令同步安装配置，再重新启动。

**一个终端启动驱动、建图与 RViz：**

```bash
ros2 launch fast_livo collect_prior.launch.py
```

保持静止完成 IMU 初始化，出现正常点云／位姿后再移动。结束时在同一终端按 **Ctrl+C**，等待地图保存完成及全部进程退出。

先验保存为 `PCD/priori/map_MMDD_HHMM.pcd`，相对 `workspace_root`。

## 2. 一键基于先验重定位并连续扩图

编辑同一个 YAML；其他参数保留第 1 节设置，仅调整：

| 参数 | 基于先验扩图并保存观测 |
| --- | --- |
| `locate_in_prior_map` | `true` |
| `prior_map_name` | 选定先验的实际文件名，如 `priori.pcd` |
| `pcd_save.pcd_save_en` | `true` |
| `pcd_save.pcd_save_en_relocate` | `true` |

默认 `prior_map_update_en=true`，完成初始化后继续扩图；设为 `false` 则只在固定先验地图中定位。

将选定 PCD 放入 `workspace_root` 下的 `PCD/map`，只改文件名，目录通常不改。其余参数保留工程默认，初始化自动使用先验 map 坐标。采集和定位的重力对齐设置保持一致。

启动时让雷达处于先验地图覆盖范围内，优先回到采图起点附近，保持相近高度和姿态，并保持静止。

**一个终端启动驱动、建图、RViz、地图 TF 和重定位：**

```bash
ros2 launch fast_livo relocate_mapping.launch.py
```

自动匹配持续失败时，在配准器退出前，将 RViz Fixed Frame 设为 `map`，用 **2D Pose Estimate** 向 `/initialpose` 发送雷达在先验地图中的大致位置与朝向，节点会进入 GICP 精配准。二维工具默认高度、横滚和俯仰为零；不适用时应发送完整三维初值。配准器若已超限退出，需重新启动配准流程后再发送。

重定位入口要求 `locate_in_prior_map=true`，配置为 false 时会提示并停止。配准器收到建图服务的“初值已接受”响应后退出。继续保持静止，直到建图节点显示以下内容、`/fast_livo2/tracking_valid` 为 `true` 后再移动：

```text
Published /fast_livo2/initial_map_pose after prior-map initialization; the device may now move.
```

实时地图位姿：`/aft_mapped_in_map`；将 RViz Fixed Frame 手动改为 `map`（随包配置默认是 `camera_init`）。同时确认位姿时间戳持续更新，不能只看保留的 `tracking_valid=true`。

结束时在同一终端按 **Ctrl+C**，等待地图保存完成及全部进程退出。

本次观测保存到 `PCD/relocate/map_MMDD_HHMM.pcd`（相对 `workspace_root`），保存内容仍仅为本次有效观测；原先验文件不覆盖，完整合图使用 `PCD/scripts/merge_maps.py`。同一输出目录内，同分钟重启可能覆盖同名文件。

保存总开关关闭时，两种模式都不写 PCD；先验定位写盘还需要定位保存开关开启。默认退出时保存本次观测；可捕获的运行异常也会尽力保存此前有效缓存。

RDK 历史记录已确认构建和配准收包，先验定位与连续扩图全流程仍待实机验收。RViz 启动 `-11` 尚未修复，可追加 `enable_rviz:=false` 无界面运行；驱动退出 `-11` 暂不处理。

首次实测建议保留原始雷达／IMU 数据与终端日志；一次采图加一次重定位仅代表当前场景主流程通过。大图保存、断流等剩余风险见 [README 的实测前复核](/home/fire/Desktop/FAST_LIVO2_Ultra/README.md:608)。
