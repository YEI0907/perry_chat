#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : config_loader.py
@CreateTime : 2025/08/22 17:15:00
@Author     : Penglin.Ye
@Desc       : 配置文件加载工具
'''

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import yaml
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class ConfigLoader:
    """配置文件加载工具"""

    @staticmethod
    def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """加载YAML文件"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"YAML文件解析失败: {e}")

    @staticmethod
    def load_config(config_file: Union[str, Path], config_class: Type[T]) -> T:
        """加载配置文件并转换为配置对象"""
        config_data = ConfigLoader.load_yaml(config_file)
        return config_class(**config_data)

    @staticmethod
    def save_yaml(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
        """保存数据到YAML文件"""
        file_path = Path(file_path)

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def save_config(config: BaseModel, file_path: Union[str, Path]) -> None:
        """保存配置对象到YAML文件"""
        # 将配置对象转换为字典
        config_data = config.model_dump(exclude_none=True)
        ConfigLoader.save_yaml(config_data, file_path)