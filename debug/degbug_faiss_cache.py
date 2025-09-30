import asyncio
import threading
import time, random
from pprint import pprint

from loguru import logger
from tortoise import Tortoise

from perry_chat.core.knowledge_base.kb_cache.faiss_cache import KBFaissPool, MemoFaissPool
from perry_chat.core.config import load_settings
from perry_chat.core.database import DataBaseMannager
from perry_chat.db.repository import KBRepository
from perry_chat.core.text_to_vec import Text2Vector


async def database_connect(settings):
    await Tortoise.init(DataBaseMannager(settings).get_tortoise_config())  # , _create_db=True)
    await Tortoise.generate_schemas()


# 修改为真正的异步方式
async def worker(kb_faiss_pool: KBFaissPool, vs_name: str, name: str):
    # vs_name = "samples"
    await asyncio.sleep(random.randint(1, 5))  # 使用 asyncio.sleep 替代 time.sleep
    embeddings = kb_faiss_pool.text2vec.get_embedding("text-embedding-v4")
    r = random.randint(1, 3)

    vector_store = await kb_faiss_pool.load_vector_store(vs_name, name, embed_model="text-embedding-v4")
    async with vector_store.async_acquire(name) as vs:
        if r == 1:  # add docs
            ids = vs.add_texts([f"text added by {name}"], embeddings=embeddings)
            pprint(ids)
        elif r == 2:  # search docs
            docs = vs.similarity_search_with_score(f"{name}", k=3, score_threshold=1.0)
            pprint(docs)
    if r == 3:  # delete docs
        logger.warning(f"清除 {vs_name} by {name}")
        cache = await kb_faiss_pool.aget(vs_name)
        if cache: await cache.async_clear()



async def main():
    settings = load_settings()
    # database = DataBaseManager(settings)
    await database_connect(settings)

    kb_repo = KBRepository()
    text2vec = Text2Vector(settings)

    kb_faiss_pool = KBFaissPool(kb_repo=kb_repo, text2vec=text2vec, cache_num=4)

    memo_faiss_pool = MemoFaissPool(kb_repo=kb_repo, text2vec=text2vec, cache_num=4)

    kb_names = ["vs1", "vs2", "vs3"]

    # 创建任务列表而不是线程
    tasks = []
    for n in range(1, 10):  # 减少任务数量以便调试
        task = worker(kb_faiss_pool, random.choice(kb_names), f"worker {n}")
        tasks.append(task)

    # 并发执行所有任务
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())