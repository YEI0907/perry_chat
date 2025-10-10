from typing import Union, Any

from perry_chat.core.config import load_settings
from perry_chat.db.repository import KBRepository, KnowledgeFileRepository, FileDocRepository
from .base import SupportedVSType, VecDBService


class VecDBServiceFactory:
    """
    VecDBServiceFactory 是一个工厂类，提供根据指定的向量存储类型获取不同知识库服务的方法。
    """

    @staticmethod
    def get_service(
            kb_name: str,
            vector_store_type: Union[str, SupportedVSType],
            embed_model: str = None,
            description: str = None
    ) -> Any | None:
        """
        根据向量存储类型返回一个知识库服务。

        参数：
        kb_name (str): 知识库的名称。
        vector_store_type (Union[str, SupportedVSType]): 使用的向量存储类型，可以是字符串或 SupportedVSType。
        embed_model (str): 使用的嵌入模型，默认值为 EMBEDDING_MODEL。

        返回：
        KBService: 知识库服务实例。
        """
        kb_repo = KBRepository()
        kb_file_repo = KnowledgeFileRepository()
        file_doc_repo = FileDocRepository()
        settings = load_settings()
        if isinstance(vector_store_type, str):
            vector_store_type = getattr(SupportedVSType, vector_store_type.upper())
        if SupportedVSType.FAISS == vector_store_type:
            from .faiss_kb_service import FaissVecDBService
            return FaissVecDBService(
                kb_name,
                embed_model=embed_model,
                kb_description=description,
                settings=settings,
                kb_repo=kb_repo,
                kb_file_repo=kb_file_repo,
                file_doc_repo=file_doc_repo
            )
        elif SupportedVSType.MILVUS == vector_store_type:
            from .milvus_kb_service import MilvusKBService
            return MilvusKBService(kb_name, embed_model=embed_model)
        elif SupportedVSType.ZILLIZ == vector_store_type:
            from .zilliz_kb_service import ZillizKBService
            return ZillizKBService(kb_name, embed_model=embed_model)
        elif SupportedVSType.DEFAULT == vector_store_type:
            from .milvus_kb_service import MilvusKBService
            return MilvusKBService(kb_name,
                                   embed_model=embed_model)  # other milvus parameters are set in model_config.kbs_config
        elif SupportedVSType.CHROMADB == vector_store_type:
            from server.knowledge_base.kb_service.chromadb_kb_service import ChromaKBService
            return ChromaKBService(kb_name, embed_model=embed_model)
        else:
            raise ValueError(f"Unsupported vector store type: {vector_store_type}")

    @staticmethod
    async def get_service_by_name(kb_name: str) -> VecDBService | None:
        """
        根据知识库名称获取知识库服务。

        参数：
        kb_name (str): 知识库名称。

        返回：
        KBService: 知识库服务实例，如果知识库不在数据库中则返回 None。
        """
        from perry_chat.db.repository import KBRepository
        repo = KBRepository()
        kb_name, vs_type, embed_model, description = await repo.load_kb(kb_name)
        if kb_name is None:  # kb not in db, just return None
            return None
        return VecDBServiceFactory.get_service(kb_name, vs_type, embed_model, description)

    @staticmethod
    def get_default():
        return VecDBServiceFactory.get_service("default", SupportedVSType.DEFAULT)
