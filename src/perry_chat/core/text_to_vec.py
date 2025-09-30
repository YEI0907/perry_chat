import numpy as np
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from perry_chat.core.config import Settings
from typing import List, Dict, Optional, Tuple, Any

from pydantic import BaseModel, Field

def normalize(embeddings: List[List[float]] | List[float]) -> np.ndarray:
    """
    sklearn.preprocessing.normalize 的替代（使用 L2），避免安装 scipy, scikit-learn
    """
    embeds = np.array(embeddings)
    if embeds.ndim == 1:
        embeds = embeds.reshape(1, -1)
    norm = np.linalg.norm(embeds, axis=1)
    norm = np.reshape(norm, (norm.shape[0], 1))
    norm = np.tile(norm, (1, len(embeds[0])))
    return np.divide(embeddings, norm)

class DocEmbedResult(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    texts: List[str] = Field(default=[], description="文本列表")
    embeddings: Optional[np.ndarray] = Field(default=None, description="文本向量数组")
    metadatas: List[Dict] = Field(default=[], description="元数据列表")


class Text2Vector:
    """
    文本向量化
    """
    def __init__(self,
        settings: Settings
    ):
        self.settings = settings
        if len(self.settings.model.embed_models) < 1:
            raise ValueError("未配置嵌入模型, 请至少配置1个嵌入模型")
        self.embeddings = {
            k: OpenAIEmbeddings(
                model=k,
                base_url=v.api_base_url,
                api_key=v.api_key,
                dimensions=v.dimensions,
                check_embedding_ctx_length=False
            )
            for k,v in self.settings.model.embed_models.items()
        }
        logger.debug(f"初始化文本向量化模型: {list(self.embeddings.keys())}")

    def _validate_model_name(self, model_name: str) -> str:
        """
        验证模型名称
        """
        if model_name and model_name not in self.embeddings:
            raise ValueError(f"嵌入模型: {model_name} 未在模型列表中找到: {list(self.embeddings.keys())}")
        if not model_name:
            model_name = list(self.embeddings.keys())[0]
            logger.warning(f"未指定嵌入模型, 使用默认模型: {model_name}")
        return model_name

    def get_embedding(self, model_name: str = None):
        """
        获取嵌入模型
        """
        model_name = self._validate_model_name(model_name)
        return self.embeddings[model_name]

    def embed_texts(self,
        texts: List[str],
        model_name: str = None
    ) -> np.ndarray:
        """
        将文本列表转换为向量列表
        """
        model_name = self._validate_model_name(model_name)
        return normalize(self.embeddings[model_name].embed_documents(texts))

    def embed_documents(
            self,
            docs: List[Document],
            model_name: str,
    ) -> DocEmbedResult | None:
        """
        将 List[Document] 向量化，转化为 VectorStore.add_embeddings 可以接受的参数
        """
        texts = [x.page_content for x in docs]
        metadatas = [x.metadata for x in docs]
        embeddings = self.embed_texts(texts=texts, model_name=model_name)
        if embeddings is not None:
            return DocEmbedResult(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        return None

    async def aembed_documents(
            self,
            docs: List[Document],
            embed_model: str,
    ) -> DocEmbedResult | None:
        """
        将 List[Document] 向量化，转化为 VectorStore.add_embeddings 可以接受的参数
        """
        texts = [x.page_content for x in docs]
        metadatas = [x.metadata for x in docs]
        embeddings = await self.aembed_texts(texts=texts, model_name=embed_model)
        if embeddings is not None:
            return DocEmbedResult(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        return None

    async def aembed_texts(self,
        texts: List[str],
        model_name: str = None
    ) -> np.ndarray:
        """
        将文本列表转换为向量列表
        """
        model_name = self._validate_model_name(model_name)
        return normalize(await self.embeddings[model_name].aembed_documents(texts))

    def embed_query(self,
        text: str,
        model_name: str = None
    ) -> np.ndarray:
        """
        将文本转换为向量
        """
        model_name = self._validate_model_name(model_name)
        return normalize(self.embeddings[model_name].embed_query(text)).reshape(-1)

    async def aembed_query(self,
        text: str,
        model_name: str = None
    ) ->  np.ndarray:
        """
        将文本转换为向量
        """
        model_name = self._validate_model_name(model_name)
        return normalize(await self.embeddings[model_name].aembed_query(text)).reshape(-1)


if __name__ == "__main__":
    from perry_chat.core.config import load_settings
    settings = load_settings()
    text2vec = Text2Vector(settings)
    texts = [
        "这是一个测试文本"
    ]
    vectors = text2vec.embed_texts(texts)
    print(vectors)
    print(vectors.shape)
    # print(vectors[0].__len__())