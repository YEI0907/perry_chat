from tortoise import Tortoise, run_async
from perry_chat.core.database import DataBase
from perry_chat.db.models import UserModel

async def run():
    await Tortoise.init(DataBase.get_tortoise_config())
    await Tortoise.generate_schemas()

    user_id = "asdfasdfasf"
    print(await UserModel.check_user(user_id))


if __name__ == "__main__":
    run_async(run())