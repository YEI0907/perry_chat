import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Tuple, Any, Coroutine, Union
from langchain_core.documents import Document
from loguru import logger

from perry_chat.core.config import settings, Settings
from perry_chat.core.knowledge_base.kb_services.schemas import DocumentWithVSId
from perry_chat.core.knowledge_base.utils import get_kb_path, get_doc_path, KnowledgeFile
from perry_chat.core.text_to_vec import Text2Vector, DocEmbedResult
from perry_chat.db.repository import KBRepository, KnowledgeFileRepository, FileDocRepository

class SupportedVSType:
    """受支持的向量数据库"""
    FAISS = 'faiss'
    MILVUS = 'milvus'
    DEFAULT = 'default'
    ZILLIZ = 'zilliz'
    CHROMADB = 'chromadb'


class KBService(ABC):
    """向量数据库基类"""
    def __init__(self,
        knowledge_base_name: str,
        embed_model: str,
        kb_description: str,
        settings: Settings,
        kb_repo: KBRepository,
        kb_file_repo: KnowledgeFileRepository,
        file_doc_repo: FileDocRepository
    ):
        """

        :param knowledge_base_name: 知识库名称
        :param embed_model: 嵌入模型名称
        :param kb_description: 知识库介绍
        """
        self.settings = settings
        self.text_to_vec = Text2Vector(settings)
        self.kb_name = knowledge_base_name
        self.kb_info = kb_description
        self.embed_model = embed_model
        self.kb_path = get_kb_path(self.kb_name)
        self.doc_path = get_doc_path(self.kb_name)
        self.kb_repo = kb_repo
        self.kb_file_repo = kb_file_repo
        self.file_doc_repo = file_doc_repo
        self.do_init()

    def __repr__(self) -> str:
        return f"{self.kb_name} @ {self.embed_model}"

    def save_vector_store(self):
        """
        保存向量库:FAISS保存到磁盘，milvus保存到数据库。PGVector暂未支持
        """
        pass

    async def create_kb(self) -> bool:
        """
        创建知识库
        """
        if not os.path.exists(self.doc_path):
            os.makedirs(self.doc_path)
        self.do_create_kb()
        status = await self.kb_repo.add_kb(
            kb_name=self.kb_name,
            kb_info=self.kb_info,
            vs_type=self.vs_type(),
            embed_model=self.embed_model
        )
        return status

    async def clear_vs(self):
        """
        删除向量库中所有内容
        """
        self.do_clear_vs()
        status = await self.kb_file_repo.delete_files_from_db(self.kb_name)
        return status

    async def drop_kb(self):
        """
        删除知识库
        """
        self.do_drop_kb()
        status = await self.kb_repo.delete_kb(self.kb_name)
        return status

    def _docs_to_embeddings(self, docs: List[Document]) -> DocEmbedResult:
        """
        将 List[Document] 转化为 VectorStore.add_embeddings 可以接受的参数
        """
        return self.text_to_vec.embed_documents(docs, model_name=self.embed_model)# embed_documents(docs=docs, embed_model=self.embed_model, to_query=False)

    async def add_doc(self, kb_file: KnowledgeFile, docs: List[Document] = [], **kwargs):
        """
        向知识库添加文件
        如果指定了docs，则不再将文本向量化，并将数据库对应条目标为custom_docs=True
        """

        if docs:
            custom_docs = True
            for doc in docs:
                doc.metadata.setdefault("source", kb_file.filename)
        else:

            # 执行 文档加载  -- > 文档切分两个过程。
            docs = kb_file.file2text()
            custom_docs = False

        if docs:
            # 将 metadata["source"] 由绝对路径改为相对路径
            for doc in docs:
                try:
                    source = doc.metadata.get("source", "")
                    if os.path.isabs(source):
                        rel_path = Path(source).relative_to(self.doc_path)
                        doc.metadata["source"] = str(rel_path.as_posix().strip("/"))
                except Exception as e:
                    print(f"cannot convert absolute path ({source}) to relative path. error is : {e}")

            # self.delete_doc(kb_file)
            doc_infos = self.do_add_doc(docs, **kwargs)

            status = await self.kb_file_repo.add_file_to_db(kb_file,
                                          custom_docs=custom_docs,
                                          docs_count=len(docs),
                                          doc_infos=doc_infos)
        else:
            status = False
        return status

    async def delete_doc(self, kb_file: KnowledgeFile, delete_content: bool = False, **kwargs):
        """
        从知识库删除文件
        """

        self.do_delete_doc(kb_file, **kwargs)
        status = await self.kb_file_repo.delete_file_from_db(kb_file)
        if delete_content and os.path.exists(kb_file.filepath):
            os.remove(kb_file.filepath)
        return status

    async def update_info(self, kb_info: str):
        """
        更新知识库介绍
        """
        self.kb_info = kb_info
        status = await self.kb_repo.add_kb(self.kb_name, self.kb_info, self.vs_type(), self.embed_model)
        return status

    async def update_doc(self, kb_file: KnowledgeFile, docs: List[Document] = [], **kwargs) -> bool:
        """
        使用content中的文件更新向量库
        如果指定了docs，则使用自定义docs，并将数据库对应条目标为custom_docs=True
        """
        if os.path.exists(kb_file.filepath):
            await self.delete_doc(kb_file, **kwargs)
            return await self.add_doc(kb_file, docs=docs, **kwargs)
        return False

    async def exist_doc(self, file_name: str):
        return await self.kb_file_repo.file_exists_in_db(KnowledgeFile(knowledge_base_name=self.kb_name,
                                               filename=file_name))

    async def list_files(self):
        return await self.kb_file_repo.list_files_from_db(self.kb_name)

    async def count_files(self):
        return await self.kb_file_repo.count_files_from_db(self.kb_name)

    async def search_docs(self,
                          query: str,
                          top_k: int = None,
                          score_threshold: float = None,
                          ) -> list[tuple[Document, float]]:
        """
        搜索文档
        """
        if top_k is None:
            top_k = self.settings.kb.vector_search_top_k
        if score_threshold is None:
            score_threshold = self.settings.kb.score_threshold
        docs = await self.do_search(query, top_k, score_threshold)
        return docs

    def get_doc_by_ids(self, ids: List[str]) -> List[Document]:
        return []

    def del_doc_by_ids(self, ids: List[str]) -> bool:
        raise NotImplementedError

    def update_doc_by_ids(self, docs: Dict[str, Document]) -> bool:
        """
        传入参数为： {doc_id: Document, ...}
        如果对应 doc_id 的值为 None，或其 page_content 为空，则删除该文档
        """
        self.del_doc_by_ids(list(docs.keys()))
        pending_docs = []
        ids = []
        for _id, doc in docs.items():
            if not doc or not doc.page_content.strip():
                continue
            ids.append(_id)
            pending_docs.append(doc)
        self.do_add_doc(docs=pending_docs, ids=ids)
        return True

    async def list_docs(self, file_name: str = None, metadata: Dict = {}) -> List[DocumentWithVSId]:
        """
        通过file_name或metadata检索Document
        """
        doc_infos = await self.file_doc_repo.list_docs_from_db(kb_name=self.kb_name, file_name=file_name, metadata=metadata)
        docs = []
        for x in doc_infos:
            doc_info = self.get_doc_by_ids([x["id"]])[0]
            if doc_info is not None:
                # 处理非空的情况
                doc_with_id = DocumentWithVSId(**doc_info.dict(), id=x["id"])
                docs.append(doc_with_id)
            else:
                # 处理空的情况
                # 可以选择跳过当前循环迭代或执行其他操作
                pass
        return docs

    def get_relative_source_path(self, filepath: str):
        """
        将文件路径转化为相对路径，保证查询时一致
        """
        relative_path = filepath
        if os.path.isabs(relative_path):
            try:
                relative_path = Path(filepath).relative_to(self.doc_path)
            except Exception as e:
                logger.error(f"cannot convert absolute path ({filepath}) to relative path. error is : {e}")

        relative_path = str(relative_path.as_posix().strip("/"))
        return relative_path

    @abstractmethod
    def do_create_kb(self):
        """
        创建知识库子类
        """
        pass

    # @staticmethod
    def list_kbs_type(self):
        return self.settings.kb.KB_TYPES

    @classmethod
    async def list_kbs(cls):
        repo = KBRepository()
        return await repo.list_kbs()

    async def exists(self, kb_name: str = None):
        kb_name = kb_name or self.kb_name
        return await self.kb_repo.kb_exists(kb_name)

    @abstractmethod
    def vs_type(self) -> str:
        pass

    @abstractmethod
    def do_init(self):
        pass

    @abstractmethod
    def do_drop_kb(self):
        """
        删除知识库子类
        """
        pass

    @abstractmethod
    async def do_search(self,
                  query: str,
                  top_k: int,
                  score_threshold: float,
                  ) -> List[Tuple[Document, float]]:
        """
        搜索知识库子类
        """
        pass

    @abstractmethod
    def do_add_doc(self,
                   docs: List[Document],
                   **kwargs,
                   ) -> List[Dict]:
        """
        向知识库添加文档子类
        """
        pass

    @abstractmethod
    def do_delete_doc(self, kb_file: KnowledgeFile, **kwargs):
        """
        从知识库删除文档子类
        """
        pass

    @abstractmethod
    def do_clear_vs(self):
        """
        从知识库删除全部向量子类
        """
        pass


