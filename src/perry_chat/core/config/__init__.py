from .settings import Settings
from .kb_config import KBConfig
from .log_config import LogConfig
from .model_config import ModelConfig
from .prompt_template import PromptTemplates
from .server_config import ServerConfig


def load_settings() -> Settings:
    """加载配置"""
    return Settings.load()

__all__ = [
    "load_settings",
    "Settings",
    "KBConfig",
    "LogConfig",
    "ModelConfig",
    "PromptTemplates",
    "ServerConfig",
]