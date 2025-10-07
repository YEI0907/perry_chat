import asyncio
import os
import shutil
from typing import List, Dict, Tuple

from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from loguru import logger

from perry_chat.db.repository import KBRepository, KnowledgeFileRepository, FileDocRepository
from .base import KBService, SupportedVSType
# from perry_chat.core.text_to_vec import Text2Vector
from ..kb_cache.faiss_cache import ThreadSafeFaiss, KBFaissPool
from ..utils import KnowledgeFile, get_kb_path, get_vs_path
from ...config import Settings


class FaissKBService(KBService[KBFaissPool]):
    """
     FaissKBService 是一个继承自 KBService 的类，用于管理和操作使用 FAISS 的知识库服务。
     """
    vs_path: str  # 向量存储的文件路径。
    kb_path: str  # 知识库文件的路径。
    vector_name: str = None  # 向量名称，默认为 None，可以在初始化时设置。

    def __init__(self,
                 knowledge_base_name: str,
                 embed_model: str,
                 kb_description: str,
                 settings: Settings,
                 kb_repo: KBRepository,
                 kb_file_repo: KnowledgeFileRepository,
                 file_doc_repo: FileDocRepository, ):
        # kwargs.update({"pool_class": KBFaissPool})
        super().__init__(
            knowledge_base_name=knowledge_base_name,
            embed_model=embed_model,
            kb_description=kb_description,
            settings=settings,
            kb_repo=kb_repo,
            kb_file_repo=kb_file_repo,
            file_doc_repo=file_doc_repo,
            pool_class=KBFaissPool,
        )

    def vs_type(self) -> str:
        """
        返回向量存储类型。
        """
        return SupportedVSType.FAISS

    def get_vs_path(self):
        """
        获取向量存储路径。
        """
        return get_vs_path(self.kb_name, self.vector_name)

    def get_kb_path(self):
        """
        获取知识库路径。
        """
        return get_kb_path(self.kb_name)

    async def load_vector_store(self) -> ThreadSafeFaiss:
        """
        加载向量存储。
        """
        return await self.pool.load_vector_store(kb_name=self.kb_name,
                                                 vector_name=self.vector_name,
                                                 embed_model=self.embed_model)

    async def save_vector_store(self):
        """
        保存向量存储。
        """
        if o := await self.load_vector_store(): await o.save(self.vs_path)

    async def get_doc_by_ids(self, ids: List[str]) -> List[Document]:
        """
        根据 ID 列表获取文档。

        参数：
        ids (List[str]): 文档 ID 列表。

        返回：
        List[Document]: 文档列表。
        """
        vec_store = await self.load_vector_store()
        async with vec_store.async_acquire() as vs:
            return [vs.docstore._dict.get(id) for id in ids]

    async def del_doc_by_ids(self, ids: List[str]) -> bool:
        """
        根据 ID 列表删除文档。

        参数：
        ids (List[str]): 文档 ID 列表。

        返回：
        bool: 删除操作是否成功。
        """
        vec_store = await self.load_vector_store()
        async with vec_store.async_acquire() as vs:
            vs.delete(ids)

    def do_init(self):
        """
        初始化服务，设置向量名称、知识库路径和向量存储路径。
        """
        self.vector_name = self.vector_name or self.embed_model
        self.kb_path = self.get_kb_path()
        self.vs_path = self.get_vs_path()

    async def do_create_kb(self):
        """
        创建知识库，如果向量存储路径不存在，则创建该路径，并加载向量存储。
        """
        if not os.path.exists(self.vs_path):
            os.makedirs(self.vs_path)
        await self.load_vector_store()

    def do_drop_kb(self):
        """
        删除知识库，清除向量存储，并删除知识库路径。
        """
        self.clear_vs()
        try:
            shutil.rmtree(self.kb_path)
        except Exception:
            logger.error(f"删除知识库 {self.kb_name} 失败")

    async def do_search(self,
                        query: str,
                        top_k: int,
                        score_threshold: float = None,
                        ) -> List[Tuple[Document, float]]:
        """
        搜索与查询最相似的文档。

        参数：
        query (str): 查询字符串。
        top_k (int): 返回的最相似文档的数量。
        score_threshold (float): 分数阈值，默认为 SCORE_THRESHOLD。

        返回：
        List[Tuple[Document, float]]: 与查询最相似的文档及其分数的列表。
        """
        if not score_threshold: score_threshold = self.settings.kb.score_threshold
        # 实例化一个 Embedding 实例，用来将用户Query转化成 Embedding后再进行查询
        # 获取问题的Embedding
        embeddings = await self.text_to_vec.aembed_query(query, model_name=self.embed_model)

        vector_store: ThreadSafeFaiss = await self.load_vector_store()

        async with vector_store.async_acquire() as vs:
            vs: FAISS
            # print(vs.distance_strategy)
            docs = await vs.asimilarity_search_with_score_by_vector(embeddings, top_k)# , score_threshold=score_threshold)
        return docs

    async def do_add_doc(self,
                         docs: List[Document],
                         **kwargs,
                         ) -> List[Dict]:
        """
        添加文档到向量存储。

        参数：
        docs (List[Document]): 文档列表。
        **kwargs: 其他可选参数。

        返回：
        List[Dict]: 添加的文档信息。
        """

        #data = await asyncio.to_thread(self._docs_to_embeddings, docs)  # 将向量化单独出来可以减少向量库的锁定时间
        data = await self._adocs_to_embeddings(docs)

        # 使用 await 来获取异步函数的结果
        vector_store = await self.load_vector_store()

        async with vector_store.async_acquire() as vs:
            vs: FAISS
            # https://api.python.langchain.com/en/latest/_modules/langchain_community/vectorstores/faiss.html#FAISS
            # 接收文本和嵌入向量的对，并将它们存储在一个向量存储中，并返回添加文本后的唯一 ID 列表
            ids = vs.add_embeddings(text_embeddings=zip(data.texts, data.embeddings),
                                    metadatas=data.metadatas,
                                    ids=kwargs.get("ids"))
            if not kwargs.get("not_refresh_vs_cache"):
                # 将 FAISS 索引、文档存储（docstore）和索引到文档存储 ID 的映射（index_to_docstore_id）保存到本地磁盘。这是一个持久化操作
                vs.save_local(self.vs_path)
        doc_infos = [{"id": id, "metadata": doc.metadata} for id, doc in zip(ids, docs)]
        return doc_infos

    async def do_delete_doc(self,
                            kb_file: KnowledgeFile,
                            **kwargs):
        """
        删除指定文件名的文档。

        参数：
        kb_file (KnowledgeFile): 知识文件对象。
        **kwargs: 其他可选参数。

        返回：
        List[str]: 被删除的文档 ID 列表。
        """
        # 使用 await 来获取异步函数的结果
        vector_store = await self.load_vector_store()

        async with vector_store.async_acquire() as vs:
            vs: FAISS
            ids = [k for k, v in vs.docstore._dict.items() if
                   v.metadata.get("source").lower() == kb_file.filename.lower()]
            if len(ids) > 0:
                vs.delete(ids)
            if not kwargs.get("not_refresh_vs_cache"):
                vs.save_local(self.vs_path)
        return ids

    async def do_clear_vs(self):
        """
        清除向量存储。
        """
        async with self.pool.async_atomic:
            self.pool.pop((self.kb_name, self.vector_name))
        try:
            shutil.rmtree(self.vs_path)
        except Exception as e:
            logger.error(f"删除向量存储 {self.kb_name} 失败: {e}")
        os.makedirs(self.vs_path, exist_ok=True)

    def exist_doc(self, file_name: str):
        """
        检查文档是否存在。

        参数：
        file_name (str): 文件名。

        返回：
        str: 返回 "in_db" 如果在数据库中，"in_folder" 如果在文件夹中，否则返回 False。
        """
        if super().exist_doc(file_name):
            return "in_db"

        content_path = os.path.join(self.kb_path, "content")
        if os.path.isfile(os.path.join(content_path, file_name)):
            return "in_folder"
        else:
            return False
