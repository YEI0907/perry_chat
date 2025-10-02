#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : config_manager.py
@CreateTime : 2025/08/22 16:30:00
@Author     : Penglin.Ye
@Desc       : 配置管理器
'''

import os
import sys
import traceback
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, Type, TypeVar

import yaml
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from .kb_config import KBConfig
from .log_config import LogConfig
from .model_config import ModelConfig
from .prompt_template import PromptTemplates
from .server_config import ServerConfig

# 用于泛型类型注解
T = TypeVar('T', bound=BaseModel)


class ConfigSource(str, Enum):
    """配置来源枚举"""
    ENV = "env"  # 环境变量
    YAML = "yaml"  # YAML文件
    DEFAULT = "default"  # 默认值


class ConfigManager:
    """配置管理器，负责加载和管理所有配置"""

    _instance = None
    _initialized = False
    _logger_configured = False

    # 配置类映射
    CONFIG_CLASSES = {
        "kb": KBConfig,
        "log": LogConfig,
        "model": ModelConfig,
        "prompt": PromptTemplates,
        "server": ServerConfig
    }

    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, force_reload: bool = False):
        """初始化配置管理器"""
        if self._initialized and not force_reload:
            return

        # 加载环境变量
        load_dotenv()

        # 基础路径配置
        self.config_path = os.getenv("CONFIG_PATH", "")
        self.resources_path = os.getenv("RESOURCES_PATH", "")
        # self.llm_api_key = os.getenv("LLM_API_KEY", "")

        # 验证必要的环境变量
        self._validate_env_vars()

        # 初始化配置实例
        self.configs = {}
        self._load_all_configs()

        # 配置日志
        self._setup_logger()

        self._initialized = True

    def _validate_env_vars(self):
        """验证必要的环境变量"""
        if not self.config_path:
            raise ValueError("必须设置环境变量 CONFIG_PATH 指定配置文件目录")

        if not self.resources_path:
            raise ValueError("必须设置环境变量 RESOURCES_PATH 指定资源文件目录")

        # 确保路径存在
        config_dir = Path(self.config_path)
        if not config_dir.exists():
            raise ValueError(f"配置目录不存在: {config_dir}")

        resources_dir = Path(self.resources_path)
        if not resources_dir.exists():
            raise ValueError(f"资源目录不存在: {resources_dir}")

    def _load_all_configs(self):
        """加载所有配置"""
        for config_name, config_class in self.CONFIG_CLASSES.items():
            try:
                config = self.load_config(config_name, config_class)
                self.configs[config_name] = config
            except Exception as e:
                logger.error(f"加载配置 {config_name} 失败: {str(e)}")
                logger.error(traceback.format_exc())
                # 使用默认配置
                self.configs[config_name] = config_class()

    def load_config(self, config_name: str, config_class: Type[T]) -> T:
        """加载特定配置"""
        config_file = Path(self.config_path) / f"{config_name}.yml"

        # 读取YAML配置
        config_data = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                    logger.debug(f"从 {config_file} 加载配置")
            except Exception as e:
                logger.error(f"读取配置文件 {config_file} 失败: {str(e)}")

        # # 注入特殊配置值
        # if config_name == "model" and self.llm_api_key:
        #     if "online_llm_config" not in config_data:
        #         config_data["online_llm_config"] = {}
        #     config_data["online_llm_config"]["api_key"] = self.llm_api_key

        # 创建并返回配置实例
        try:
            return config_class(**config_data)
        except Exception as e:
            logger.error(f"验证配置 {config_name} 失败: {str(e)}")
            raise

    def _setup_logger(self):
        """配置日志"""
        if self._logger_configured:
            return

        log_config = self.configs.get("log")
        if not log_config:
            return

        log_path = Path(log_config.log_path)

        # 确保日志目录存在
        if not log_path.exists():
            log_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"日志目录已创建: {log_path}")

        # 移除默认日志配置
        logger.remove()

        # 处理日志处理器配置
        for handler in log_config.log_kwargs.get("handlers", []):
            sink = handler.get("sink")
            if sink == "stdout":
                handler["sink"] = sys.stdout
            elif isinstance(sink, str) and sink.endswith(".log"):
                handler["sink"] = str(log_path / sink)

        # 应用配置
        if log_config.log_verbose:
            logger.configure(**log_config.log_kwargs)

        self._logger_configured = True
        logger.info("日志配置已完成")

    def get_config(self, config_name: str) -> Optional[BaseModel]:
        """获取指定配置"""
        return self.configs.get(config_name)

    @property
    def kb(self) -> KBConfig:
        """获取知识库配置"""
        return self.configs["kb"]

    @property
    def log(self) -> LogConfig:
        """获取日志配置"""
        return self.configs["log"]

    @property
    def model(self) -> ModelConfig:
        """获取模型配置"""
        return self.configs["model"]

    @property
    def prompt(self) -> PromptTemplates:
        """获取提示词配置"""
        return self.configs["prompt"]

    @property
    def server(self) -> ServerConfig:
        """获取服务器配置"""
        return self.configs["server"]

    def reload(self):
        """重新加载所有配置"""
        self._initialized = False
        self.__init__(force_reload=True)
        return self


# 全局单例配置管理器
@lru_cache()
def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    return ConfigManager()
