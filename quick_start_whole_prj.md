# RDK 总工程：覆盖源码与编译

在 **RDK／ROS 2 Humble** 上执行。前提：依赖与 Livox-SDK2 1.5.2 已安装，旧的驱动、建图和重定位任务已退出。

| 内容 | 位置 |
| --- | --- |
| Desktop 源工程 | `~/Desktop/FAST_LIVO2_Ultra` |
| 总工作空间 | `/media/mcap_data/project_east_eleair_refactor/ros2_ws` |
| 算法包分组 | `ros2_ws/src/functions/relocalization` |
| Livox 驱动 | `ros2_ws/src/drivers/livox_ros_driver2` |
| PCD 目录 | `ros2_ws/src/functions/relocalization/FAST-LIVO2/PCD` |

表中以 `ros2_ws/` 开头的位置均相对 `/media/mcap_data/project_east_eleair_refactor`。分组目录本身不是 ROS 包；实际重定位包位于 `functions/relocalization/relocalization`。

## 1. 从 Desktop 工程覆盖到总工程

复制会覆盖目标同名文件，目标中其他文件保留，Desktop 源工程保留。整个包目录会一并复制，包括 TEASER++ 的 `colcon.pkg`。`PCD` 当前位于 Desktop 工程的 `src/FAST-LIVO2/PCD`，随 FAST-LIVO2 包一起复制；若旧 RDK checkout 根目录还留有 `PCD` 数据，下方兼容步骤会补复制到目标包内。

```bash
(
set -e
ULTRA_DIR="$HOME/Desktop/FAST_LIVO2_Ultra"
RDK_WS="/media/mcap_data/project_east_eleair_refactor/ros2_ws"
GROUP="$RDK_WS/src/functions/relocalization"

test -f "$ULTRA_DIR/src/FAST-LIVO2/package.xml"

if [ -f "$GROUP/package.xml" ]; then
  echo "functions/relocalization 当前是旧的 ROS 包目录；请先调整为包分组目录。"
  exit 1
fi
if [ -e "$GROUP/livox_ros_driver2" ]; then
  echo "请先移出分组内的旧 Livox 驱动，只在 src/drivers 下保留一份。"
  exit 1
fi

mkdir -p -- "$GROUP" "$RDK_WS/src/drivers"
for pkg in FAST-LIVO2 TEASER-plusplus relocalization rpg_vikit small_gicp; do
  cp -a -- "$ULTRA_DIR/src/$pkg" "$GROUP/"
done
cp -a -- "$ULTRA_DIR/src/livox_ros_driver2" "$RDK_WS/src/drivers/"

mkdir -p -- "$GROUP/FAST-LIVO2/PCD/"{map,priori,relocate,merge,scripts,images}
if [ -d "$ULTRA_DIR/PCD" ]; then
  cp -a -- "$ULTRA_DIR/PCD/." "$GROUP/FAST-LIVO2/PCD/"
fi
)
```

同一工作空间中每个包只保留一份；如果旧的 `src/functions` 下还留有 FAST-LIVO2、TEASER-plusplus、rpg_vikit 或 small_gicp 副本，先完成迁移再编译。

## 2. 覆盖后核对配置

共享 `mapping_relocation.yaml` 默认自动确定根目录，无需在 Desktop 与总工程之间手动切换；覆盖后目标文件为：

```text
/media/mcap_data/project_east_eleair_refactor/ros2_ws/src/functions/relocalization/FAST-LIVO2/config/mapping_relocation.yaml
```

```yaml
workspace_root: "auto"
prior_map_path: "PCD/map"
pcd_save:
  output_dir: "PCD/priori"
  output_dir_relocate: "PCD/relocate"
image_save:
  output_dir: "PCD/images"
```

上面仅列出已有字段，通常保留这些值。`auto` 使用本次编译对应的 FAST-LIVO2 源码包目录：Desktop 编译指向 Desktop 包，复制后在总工程编译则指向总工程包；建图与配准的启动日志和 `workspace_root` 参数显示实际绝对路径。也支持手动绝对目录覆盖。移动源码后重编 `fast_livo` 和 `relocalization`，仅复制 install 不会更新路径。

先验文件名由 `prior_map_name` 指定，文件必须实际位于所选包的 `PCD/map`；PCD 数据不会随 Git clone／pull 自动取得，须手动复制。现有覆盖命令也会复制 Desktop 包内已有的 PCD，同名目标地图会被覆盖。合图脚本随 `PCD/scripts` 复制，按其所在 PCD 目录寻找输入。

驱动配置位于总工作空间的 `src/drivers/livox_ros_driver2/config`。覆盖后核对 `msg_MID360.yaml` 的 `lidar_model`；RDK 现场为 `mid360s`。对应 `MID360s_config.json` 的 `host_net_info` 中 `host_ip` 应与板端网卡一致，当前现场为 `192.168.2.100`，雷达为 `192.168.2.3`。仓库默认仍为 MID360／主机 `192.168.2.50`，复制会覆盖目标同名配置。

包内 `PCD/.gitignore` 会随 FAST-LIVO2 包一并复制，用于忽略地图及其他生成数据，保留目录占位文件和 scripts 工具。源码通过 Git 同步后，地图数据仍需单独传输。

## 3. 编译这 8 个包

使用新终端，仅加载 Humble。以下不指定并发数量，并跳过测试程序的编译；目录迁移后的首次编译保留 `--cmake-clean-cache`，后续日常编译可去掉。

```bash
source /opt/ros/humble/setup.bash
cd /media/mcap_data/project_east_eleair_refactor/ros2_ws
unset CMAKE_BUILD_PARALLEL_LEVEL MAKEFLAGS

colcon build --cmake-clean-cache --packages-select \
  vikit_common vikit_ros vikit_py \
  livox_ros_driver2 small_gicp teaserpp \
  fast_livo relocalization \
  --cmake-args -DBUILD_TESTING=OFF
```

编译成功后，后续每个运行终端执行：

```bash
source /opt/ros/humble/setup.bash
source /media/mcap_data/project_east_eleair_refactor/ros2_ws/install/setup.bash
```

已有完整安装空间后，如果只改总工程中的算法 YAML，只需在上述环境下同步 fast_livo 安装配置，再重启节点：

```bash
cd /media/mcap_data/project_east_eleair_refactor/ros2_ws
colcon build --packages-select fast_livo --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

采图／先验扩图的四项任务配置和原两个一键启动命令见 [quick_start.md](/home/fire/Desktop/FAST_LIVO2_Ultra/quick_start.md)。`workspace_root: "auto"` 可供 PC、RDK Desktop 与总工程共用；运行时只加载当前测试工作空间的 install，避免同时加载 Desktop 和总工程。
