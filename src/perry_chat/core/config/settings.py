import os
import sys
from typing import Any
from loguru import logger

import yaml
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from .kb_config import KBConfig
from .log_config import LogConfig
from .model_config import ModelConfig
from .prompt_template import PromptTemplates
from .server_config import ServerConfig
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()  # 加载环境变量

class Settings(BaseSettings):

    logger: Any = Field(default_factory=lambda: logger, description="日志配置")

    kb: KBConfig = Field(default_factory=KBConfig, description="知识库配置")
    log: LogConfig = Field(default_factory=LogConfig, description="日志配置")
    model: ModelConfig = Field(default_factory=ModelConfig, description="模型配置")
    prompt: PromptTemplates = Field(default_factory=PromptTemplates, description="提示词配置")
    server: ServerConfig = Field(default_factory=ServerConfig, description="服务器配置")
    
    # 从环境变量 CONFIG_PATH 中读取配置目录路径
    config_path: str = Field(
        description="配置文件目录路径",
        env="CONFIG_PATH"
    )

    resources_path: str = Field(
        description="资源文件目录路径",
        env="RESOURCES_PATH"
    )

    llm_api_key: str = Field(
        description="资源文件目录路径",
        env="LLM_API_KEY"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    def __init__(self, **data: Any):

        try:
            super().__init__(**data)
        except ValueError as e:
            # 检查是否是因为 resources_path 缺失而报错
            if "resources_path" in str(e):
                raise ValueError("必须设置环境变量 RESOURCE_PATH 指定资源文件目录") from e
            if "config_path" in str(e):
                raise ValueError("必须设置环境变量 CONFIG_PATH 指定配置文件目录") from e
            raise
        if self.config_path:
            self._load_configs()
            self._config_logger()

    def _load_configs(self) -> None:
        """加载所有子配置文件"""
        config_dir = Path(self.config_path)
        if not config_dir.exists():
            logger.warning(f"配置目录不存在: {config_dir}, 将使用默认配置")
            return
            
        # 子配置文件名与对应的配置类映射
        config_mapping = {
            'kb': (KBConfig, self.kb),
            'log': (LogConfig, self.log),
            'model': (ModelConfig, self.model),
            'prompt': (PromptTemplates, self.prompt),
            'server': (ServerConfig, self.server)
        }
        
        # 加载每个子配置文件
        for config_name, (config_class, default_config) in config_mapping.items():
            config_file = config_dir / f"{config_name}.yml"
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        if config_class == ModelConfig:
                            config_data['online_llm_config']['api_key'] = self.llm_api_key
                    
                    # 获取当前配置实例的所有字段值
                    current_values = default_config.model_dump()


                    # 合并YAML中的配置与当前配置
                    merged_config = {**current_values, **config_data}
                    
                    try:
                        # 尝试使用合并后的配置创建新实例
                        config_instance = config_class(**merged_config)
                        setattr(self, config_name, config_instance)
                        logger.info(f"已加载配置文件: {config_file}")
                    except Exception as e:
                        logger.error(f"配置验证失败 {config_file}: {str(e)}")
                        logger.info(f"保持使用默认配置: {config_name}")
                        
                except yaml.YAMLError as e:
                    logger.error(f"YAML解析失败 {config_file}: {str(e)}")
                    logger.info(f"使用默认配置: {config_name}")
                except Exception as e:
                    logger.error(f"加载配置文件失败 {config_file}: {str(e)}")
                    logger.info(f"使用默认配置: {config_name}")
            else:
                logger.info(f"配置文件不存在: {config_file}, 使用默认配置")
    
    @classmethod
    def load(cls) -> "Settings":
        """加载配置的便捷方法"""
        try:
            return cls()
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            raise
        
    
    def _config_logger(self):
        """
        配置加载后的后处理:
        1. 使用 LogConfig 配置 logger
        """
        # 配置日志路径和格式
        log_config = self.log
        log_path = Path(log_config.log_path)
        
        # 确保日志目录存在
        if not log_path.exists():
            log_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"日志目录已创建: {log_path}")
        
        # 配置 logger
        self.logger.remove()  # 移除默认的日志配置
        # self.logger.add(
        #     log_path / "app.log",
        #     level=log_config.log_level,
        #     enqueue=True,  # 异步写入日志
        #     backtrace=True,  # 捕获完整的回溯信息
        #     diagnose=True,  # 捕获详细的诊断信息
        #     rotation="10 MB"
        # )

        for handler in log_config.log_kwargs.get("handlers", []):
            if handler["sink"] == "stdout":
                handler["sink"] = sys.stdout
            elif handler["sink"].endswith(".log"):
                handler["sink"] = str(log_path / handler["sink"])


        # 添加控制台日志处理器（如果需要详细日志输出）
        if log_config.log_verbose:
            self.logger.configure(**log_config.log_kwargs)
            
        self.logger.info("日志配置已完成")        
        return self

settings = Settings.load()
        
    