# database.py

from fastapi import FastAPI
from loguru import logger
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise
from .config import Settings
# --- 在这里定义你的数据库配置 ---

# 数据库连接URL，建议从环境变量或配置文件中读取
# DATABASE_URL = "sqlite://db.sqlite3"
# DATABASE_URL = "mysql://user:password@host:port/db_name"
# DATABASE_URL = "postgres://user:password@host:port/db_name"

# 需要被 Tortoise ORM 管理的模型列表
# 格式为: "app_name.models_filename"
# 例如，如果你的模型在 "models/user_models.py", "models/item_models.py"
# 你可以写成 ["models.user_models", "models.item_models"]
MODELS = ["perry_chat.db.models"] # 假设你的所有模型都在一个名为 "models.py" 的文件中


class DataBase:
    """
    数据库管理类，用于初始化和关闭连接。
    """
    def __init__(self, settings: Settings):
        self.settings = settings

    def get_tortoise_config(self) -> dict:
        """
        生成 Tortoise ORM 的配置字典。
        """
        config = {
            "connections": {
                "default": self.settings.kb.database_url
            },
            "apps": {
                "models": {
                    "models": MODELS + ["aerich.models"], # 添加 aerich.models 以支持迁移工具
                    "default_connection": "default",
                },
            },
            "use_tz": False,  # 建议设为 False，让时区管理更明确
            "timezone": "Asia/Shanghai" # 根据需要设置时区
        }
        return config

    def init(self, app: FastAPI):
        """
        将 Tortoise ORM 注册到 FastAPI 应用。

        :param app: FastAPI 应用实例
        """
        logger.info("Initializing database...")
        register_tortoise(
            app,
            config=self.get_tortoise_config(),
            generate_schemas=True,  # 在开发环境中设为True，生产环境建议设为False并使用迁移工具
            add_exception_handlers=True,
        )
        logger.info("Database initialization complete.")

    @staticmethod
    async def close():
        """
        手动关闭数据库连接（通常由 register_tortoise 自动处理）。
        """
        logger.info("Closing database connections...")
        await Tortoise.close_connections()
        logger.info("Database connections closed.")
