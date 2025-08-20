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


setting = Settings.load()
setting.logger.info("完成")