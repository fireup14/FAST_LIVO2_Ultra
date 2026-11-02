# 暂不用的配置与启动文件

当前 `old` 位于工作区根目录，与 `src` 同级，供后续对照和按需迁移。

```text
FAST_LIVO2_ROS2_relocation_ultra/
├── src/
│   ├── FAST-LIVO2/
│   │   ├── config/
│   │   │   ├── mapping_relocation.yaml
│   │   │   ├── camera_parameter.yaml
│   │   │   └── mapping_relocation参数说明.md
│   │   └── launch/mapping_relocation.launch.py
│   └── relocalization/launch/relocalization.launch.py
└── old/
    ├── config/                  # 原 AVIA、MARS 和相机配置
    ├── launch_livo/             # 原 FAST-LIVO2 启动入口
    ├── launch_relocalization/   # 原 ICP、TEASER、SAC-IA 入口
    └── launch_top/              # 原顶层组合示例
```

当前建图与重定位入口分别为 `ros2 launch fast_livo mapping_relocation.launch.py` 和 `ros2 launch relocalization relocalization.launch.py`，默认共用活动建图配置中的模式和地图路径。

`old` 不再列入活动包安装规则。本轮未调整归档 launch 内部的历史路径；它们仅供源码对照，不保证移动后可直接启动，也不代表已通过实机验证。当前三终端启动方法见工作区 `readme.zh.md`。
