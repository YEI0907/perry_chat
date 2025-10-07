from tortoise import Tortoise, run_async
from perry_chat.core.database_manager import DataBaseManager
from perry_chat.core.config import load_settings
from perry_chat.db.models import UserModel

async def run():
    settings = load_settings()

    await Tortoise.init(DataBaseManager(settings).get_tortoise_config(), _create_db=True)
    await Tortoise.generate_schemas()

    # user_id = "asdfasdfasf"
    # print(await UserModel.check_user(user_id))


if __name__ == "__main__":
    run_async(run())