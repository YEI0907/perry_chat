#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File       : settings.py
@CreateTime : 2025/08/22 16:45:00
@Author     : Penglin.Ye
@Desc       : 项目配置类
"""
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from .config_manager import get_config_manager
from .kb_config import KBConfig
from .log_config import LogConfig
from .model_config import ModelConfig
from .prompt_template import PromptTemplates
from .server_config import ServerConfig


class Settings(BaseModel):
    """项目配置类，作为所有配置的统一访问点"""

    # 类变量，存储单例实例
    _instance: ClassVar[Any] = None

    # 模型配置
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
        frozen=False
    )

    # 配置属性
    kb: KBConfig = Field(default=None, description="知识库配置")
    log: LogConfig = Field(default=None, description="日志配置")
    model: ModelConfig = Field(default=None, description="模型配置")
    prompt: PromptTemplates = Field(default=None, description="提示词配置")
    server: ServerConfig = Field(default=None, description="服务器配置")

    # 环境变量
    config_path: str = Field(default="", description="配置文件目录路径")
    resources_path: str = Field(default="", description="资源文件目录路径")

    # llm_api_key: str = Field(default="", description="大模型APIKEY")

    def __init__(self, **data):
        """初始化项目配置"""
        # 获取配置管理器
        config_manager = get_config_manager()

        # 设置环境变量
        data["config_path"] = config_manager.config_path
        data["resources_path"] = config_manager.resources_path
        # data["llm_api_key"] = config_manager.llm_api_key

        # 设置各模块配置
        data["kb"] = config_manager.kb
        data["log"] = config_manager.log
        data["model"] = config_manager.model
        data["prompt"] = config_manager.prompt
        data["server"] = config_manager.server

        super().__init__(**data)

        # 设置日志实例
        # 在实例属性中设置logger而不是作为模型字段
        self.logger = logger

    @classmethod
    def load(cls) -> "Settings":
        """加载配置的便捷方法，使用单例模式"""
        if cls._instance is None:
            try:
                cls._instance = cls()
            except Exception as e:
                logger.error(f"加载配置失败: {str(e)}")
                raise
        return cls._instance

    def reload(self) -> "Settings":
        """重新加载配置"""
        # 重新加载配置管理器
        get_config_manager().reload()

        # 重置单例
        type(self)._instance = None

        # 返回新实例
        return self.load()

# 全局配置实例
# settings = Settings.load()
