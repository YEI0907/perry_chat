import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
load_dotenv()
sys.path.append(str(Path(__file__).parent.parent / "src"))

from perry_chat.core.config.log_config import LogConfig
from perry_chat.core.config.prompt_template import PromptTemplates
from perry_chat.core.config.server_config import ServerConfig
from perry_chat.core.config.kb_config import KBConfig
from perry_chat.core.config.settings import Settings, ModelConfig

# 加载环境变量
load_dotenv()

# 方法1: 直接使用全局配置实例
from perry_chat.core.config.settings import settings

# 打印配置信息
logger.info(f"配置路径: {settings.config_path}")
logger.info(f"资源路径: {settings.resources_path}")
logger.info(f"模型根目录: {settings.model.model_root_path}")
logger.info(f"知识库根目录: {settings.kb.kb_root_path}")

# 方法2: 使用配置管理器
from perry_chat.core.config.config_manager import get_config_manager

config_manager = get_config_manager()
model_config = config_manager.get_config("model")
logger.info(f"模型温度: {model_config.temperature}")

# 重新加载配置
settings.reload()
logger.info("配置已重新加载")

logger.info("调试完成")
