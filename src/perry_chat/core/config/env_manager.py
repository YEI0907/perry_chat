#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : env_manager.py
@CreateTime : 2025/08/22 17:00:00
@Author     : Penglin.Ye
@Desc       : 环境变量管理
'''

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator


class EnvManager(BaseModel):
    """环境变量管理类"""

    # 必要的环境变量
    CONFIG_PATH: str = Field(default="", description="配置文件目录路径")
    RESOURCES_PATH: str = Field(default="", description="资源文件目录路径")

    # 可选的环境变量
    LLM_API_KEY: Optional[str] = Field(default=None, description="大模型API密钥")
    DEBUG: bool = Field(default=False, description="是否启用调试模式")
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")

    # 其他环境变量
    env_vars: Dict[str, str] = Field(default_factory=dict, description="其他环境变量")

    @classmethod
    def load(cls) -> "EnvManager":
        """加载环境变量"""
        # 加载.env文件
        load_dotenv()

        # 创建实例
        instance = cls(
            CONFIG_PATH=os.getenv("CONFIG_PATH", ""),
            RESOURCES_PATH=os.getenv("RESOURCES_PATH", ""),
            LLM_API_KEY=os.getenv("LLM_API_KEY"),
            DEBUG=os.getenv("DEBUG", "False").lower() in ("true", "1", "yes"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        )

        # 验证必要的环境变量
        instance._validate()

        return instance

    def _validate(self) -> None:
        """验证环境变量"""
        missing_vars = []

        # 检查必要的环境变量
        if not self.CONFIG_PATH:
            missing_vars.append("CONFIG_PATH")
        else:
            # 检查路径是否存在
            if not Path(self.CONFIG_PATH).exists():
                raise ValueError(f"配置目录不存在: {self.CONFIG_PATH}")

        if not self.RESOURCES_PATH:
            missing_vars.append("RESOURCES_PATH")
        else:
            # 检查路径是否存在
            if not Path(self.RESOURCES_PATH).exists():
                raise ValueError(f"资源目录不存在: {self.RESOURCES_PATH}")

        # 如果有缺失的必要环境变量，抛出异常
        if missing_vars:
            raise ValueError(f"缺少必要的环境变量: {', '.join(missing_vars)}")

    def get(self, key: str, default: str = "") -> str:
        """获取环境变量值"""
        # 首先检查类属性
        if hasattr(self, key):
            value = getattr(self, key)
            if value is not None:
                return str(value)

        # 然后检查env_vars字典
        if key in self.env_vars:
            return self.env_vars[key]

        # 最后直接从环境变量获取
        return os.getenv(key, default)

    def set(self, key: str, value: str) -> None:
        """设置环境变量值（仅在当前进程中有效）"""
        # 设置到env_vars字典
        self.env_vars[key] = value

        # 同时设置到环境变量
        os.environ[key] = value