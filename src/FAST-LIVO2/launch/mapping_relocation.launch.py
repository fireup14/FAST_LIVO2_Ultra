#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    # Find path
    config_file_dir = os.path.join(get_package_share_directory("fast_livo"), "config")
    rviz_config_file = os.path.join(get_package_share_directory("fast_livo"), "rviz_cfg", "fast_livo2.rviz")

    # Load parameters
    mapping_config_cmd = os.path.join(config_file_dir, "mapping_relocation.yaml")
    camera_config_cmd = os.path.join(config_file_dir, "camera_parameter.yaml")

    # Launch arguments
    enable_rviz_arg = DeclareLaunchArgument(
        "enable_rviz",
        default_value="true",
        description="是否启动 RViz。",
    )

    mapping_config_arg = DeclareLaunchArgument(
        "config_file",
        default_value=mapping_config_cmd,
        description="FAST-LIVO2 参数 YAML，运行模式由节点读取。",
    )

    camera_config_arg = DeclareLaunchArgument(
        "camera_file",
        default_value=camera_config_cmd,
        description="相机模型参数 YAML。",
    )

    mapping_params_file = LaunchConfiguration("config_file")
    camera_params_file = LaunchConfiguration("camera_file")
    enable_rviz = LaunchConfiguration("enable_rviz")

    return LaunchDescription([
        enable_rviz_arg,
        mapping_config_arg,
        camera_config_arg,

        # FAST-LIVO2 mapping / localization
        # locate_in_prior_map 由节点自身读取；本入口不启动外部重定位节点。
        Node(
            package="fast_livo",
            executable="fastlivo_mapping",
            name="laserMapping",
            parameters=[
                mapping_params_file,
                camera_params_file,
            ],
            output="screen",
            emulate_tty=True,
        ),

        # RViz
        Node(
            condition=IfCondition(enable_rviz),
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            arguments=["-d", rviz_config_file],
            output="screen",
        ),
    ])
