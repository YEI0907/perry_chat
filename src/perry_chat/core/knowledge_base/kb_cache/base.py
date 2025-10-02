import asyncio
import threading
from collections import OrderedDict
from contextlib import contextmanager, asynccontextmanager
from typing import List, Any, Union, Tuple, Generator, TypeVar, Generic, AsyncGenerator

from langchain_core.embeddings import Embeddings
from loguru import logger

from perry_chat.core.text_to_vec import Text2Vector
from perry_chat.db.repository import KBRepository

T = TypeVar('T')


class ThreadSafeObject(Generic[T]):
    """
    线程安全对象类，用于保证多线程环境下对象的安全访问。
    """

    def __init__(self, key: Union[str, Tuple], obj: T = None, pool: "CachePool" = None):
        self._obj = obj
        self._key = key
        self._pool = pool
        self._async_lock = asyncio.Lock()
        self._lock = threading.RLock()
        self._loaded = threading.Event()
        self._aloaded = asyncio.Event()

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"<{cls}: key: {self.key}, obj: {self._obj}>"

    @property
    def key(self):
        return self._key

    @contextmanager
    def acquire(self, owner: str = "", msg: str = "") -> Generator:
        """
        获取对象的上下文管理器，用于在多线程环境下安全地访问对象。

        参数：
        owner (str): 操作的所有者，默认为当前线程。
        msg (str): 日志消息。

        返回：
        FAISS: 向量存储对象。
        """
        owner = owner or f"thread {threading.get_native_id()}"
        try:
            self._lock.acquire()
            if self._pool is not None:
                self._pool.cache.move_to_end(self.key)
            logger.debug(f"{owner} 开始操作：{self.key}。{msg}")
            yield self._obj
        finally:
            logger.debug(f"{owner} 结束操作：{self.key}。{msg}")
            self._lock.release()

    @asynccontextmanager
    async def async_acquire(self, owner: str = "", msg: str = "") -> AsyncGenerator[T | None, None]:
        """
        获取对象的异步上下文管理器，用于在协程环境下安全地访问对象。

        参数：
        owner (str): 操作的所有者，默认为当前任务。
        msg (str): 日志消息。

        返回：
        FAISS: 向量存储对象。
        """
        owner = owner or f"task {id(asyncio.current_task())}"
        try:
            async with self._async_lock:
                if self._pool is not None:
                    self._pool.cache.move_to_end(self.key)
                logger.debug(f"{owner} 开始操作：{self.key}。{msg}")
                yield self._obj
        finally:
            logger.debug(f"{owner} 结束操作：{self.key}。{msg}")

    def start_loading(self):
        """
        开始加载对象。
        """
        self._loaded.clear()
        self._aloaded.clear()

    def finish_loading(self):
        """
        完成加载对象。
        """
        self._loaded.set()
        self._aloaded.set()

    def wait_for_loading(self):
        """
        等待对象加载完成。
        """
        self._loaded.wait()

    async def await_for_loading(self):
        """
        异步等待对象加载完成。
        """
        # 使用 asyncio.to_thread 避免在等待过程中阻塞事件循环
        if not self._aloaded.is_set():
            await asyncio.to_thread(self._loaded.wait)
        # 确保 asyncio.Event 也处于设置状态
        if not self._aloaded.is_set():
            self._aloaded.set()

    @property
    def obj(self) -> T:
        return self._obj

    @obj.setter
    def obj(self, val: T):
        self._obj = val


SafeObject = TypeVar("SafeObject", bound=ThreadSafeObject)


class CachePool(Generic[SafeObject]):
    """
    缓存池类，用于管理线程安全对象的缓存。
    """

    def __init__(self, kb_repo: KBRepository, text2vec: Text2Vector, cache_num: int = -1):
        self.kb_repo = kb_repo
        self.text2vec = text2vec
        self._cache_num = cache_num
        self.cache = OrderedDict[Any, SafeObject]()
        self.atomic = threading.RLock()
        self.async_atomic = asyncio.Lock()

    def keys(self) -> List[str]:
        return list(self.cache.keys())

    def _check_count(self):
        """
        检查缓存数量，并在超过限制时移除最旧的缓存。
        """
        if isinstance(self._cache_num, int) and self._cache_num > 0:
            while len(self.cache) > self._cache_num:
                self.cache.popitem(last=False)

    def get(self, key: Union[str, Tuple[str, str | None]]) -> SafeObject | None:
        """
        根据键获取缓存对象，并等待对象加载完成。

        参数：
        key (str): 缓存对象的键。

        返回：
        ThreadSafeObject: 线程安全对象。
        """
        if cache := self.cache.get(key):
            cache.wait_for_loading()
            return cache
        return None

    async def aget(self, key: Union[str, Tuple[str, str | None]]) -> SafeObject | None:
        if cache := self.cache.get(key):
            await cache.await_for_loading()
            return cache
        return None

    def set(self, key: Union[str, Tuple[str, str | None]], obj: SafeObject) -> SafeObject:
        """
         设置缓存对象。

         参数：
         key (str): 缓存对象的键。
         obj (ThreadSafeObject): 线程安全对象。

         返回：
         ThreadSafeObject: 设置的线程安全对象。
        """
        self.cache[key] = obj
        self._check_count()
        return obj

    def pop(self, key: Union[str, Tuple[str, str | None]] = None) -> tuple[Any, SafeObject] | None:
        """
        移除并返回缓存对象。

        参数：
        key (str): 缓存对象的键，如果为空则移除最旧的缓存。

        返回：
        ThreadSafeObject: 移除的线程安全对象。
        """
        if key is None:
            return self.cache.popitem(last=False)
        else:
            return self.cache.pop(key, None)

    def acquire(self, key: Union[str, Tuple], owner: str = "", msg: str = ""):
        """
        获取缓存对象的上下文管理器，用于在多线程环境下安全地访问对象。

        参数：
        key (Union[str, Tuple]): 缓存对象的键。
        owner (str): 操作的所有者，默认为当前线程。
        msg (str): 日志消息。

        返回：
        上下文管理器: 缓存对象的上下文管理器。
        """
        cache = self.get(key)
        if cache is None:
            raise RuntimeError(f"请求的资源 {key} 不存在")
        elif isinstance(cache, ThreadSafeObject):
            self.cache.move_to_end(key)
            return cache.acquire(owner=owner, msg=msg)
        return None

    async def async_acquire(self, key: Union[str, Tuple], owner: str = "", msg: str = ""):
        """
        获取缓存对象的异步上下文管理器，用于在协程环境下安全地访问对象。

        参数：
        key (Union[str, Tuple]): 缓存对象的键。
        owner (str): 操作的所有者，默认为当前任务。
        msg (str): 日志消息。

        返回：
        上下文管理器: 缓存对象的上下文管理器。
        """
        cache = self.get(key)
        if cache is None:
            raise RuntimeError(f"请求的资源 {key} 不存在")
        elif isinstance(cache, ThreadSafeObject):
            self.cache.move_to_end(key)
            return cache.async_acquire(owner=owner, msg=msg)
        return None

    async def load_kb_embeddings(
            self,
            kb_name: str,
            default_embed_model: str = None,
    ) -> Embeddings:
        """
        加载知识库嵌入模型。

        参数：
        kb_name (str): 知识库名称。
        embed_device (str): 嵌入设备。
        default_embed_model (str): 默认嵌入模型。

        返回：
        Embeddings: 嵌入模型对象。
        """

        kb_detail = await self.kb_repo.get_kb_detail(kb_name)

        embed_model = kb_detail.get("embed_model", default_embed_model)

        logger.debug(f"这是查询到的load_kb_embeddings的参数：{kb_detail}")
        return self.text2vec.get_embedding(embed_model)
