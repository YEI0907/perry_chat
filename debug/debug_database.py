from tortoise import Tortoise, run_async
from perry_chat.core.database import DataBaseMannager
from perry_chat.db.models import UserModel

async def run():
    await Tortoise.init(DataBaseMannager.get_tortoise_config())# , _create_db=True)
    await Tortoise.generate_schemas()

    # user_id = "asdfasdfasf"
    # print(await UserModel.check_user(user_id))


if __name__ == "__main__":
    run_async(run())