from tortoise import Tortoise, run_async
from perry_chat.core.database import DataBase

async def run():
    await Tortoise.init(DataBase.get_tortoise_config(), _create_db=True)
    await Tortoise.generate_schemas()

if __name__ == "__main__":
    run_async(run())