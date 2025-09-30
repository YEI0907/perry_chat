#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : kb_config.py
@CreateTime : 2025/08/19 13:41:54
@Author     : Penglin.Ye
@Desc       : 知识库配置    
'''
import os
from typing import Any, List, Literal, Tuple, Union, Dict
from loguru import logger
from pydantic import BaseModel, Field, model_validator
from abc import ABC
from pathlib import Path

class KBInfo(BaseModel):
    """每个知识库的初始化介绍, 用于在初始化知识库时显示和Agent调用, 没写则没有介绍, 不会被Agent调用。"""
    name: str = Field(
        ...,
        description="知识库名称"
    )
    description: str = Field(
        ...,
        description="知识库介绍"
    )

class VectorDatabaseConfig(ABC, BaseModel):
    pass

class FaissConfig(VectorDatabaseConfig):
    type: Literal["faiss"] = "faiss"
    cached_vs_num: int = Field(
        default=1,
        description="缓存向量库数量"
    )
    cached_memo_vs_num: int = Field(
        default=1,
        description="缓存临时向量库数量, 用于文件对话"
    )

class MilvusKwargs(BaseModel):
    search_params: dict = Field(
        default={},
        description="搜索参数"
    )
    index_params: dict = Field(
        default={},
        description="索引参数"
    )

class MilvusConfig(VectorDatabaseConfig):
    type: Literal["milvus"] = "milvus"
    host: str = Field(
        default="localhost",
        description="Milvus数据库的主机地址"
    )
    port: str = Field(
        default="19530",
        description="Milvus数据库的端口地址"
    )
    user: str = Field(
        default="",
        description="Milvus数据库的用户名"
    )
    password: str = Field(
        default="",
        description="Milvus数据库的密码"
    )
    secure: bool = Field(
        default=False,
        description="是否启用安全连接"
    )
    kwargs: MilvusKwargs = Field(
        default_factory=lambda: MilvusKwargs(),
        description="Milvus数据库的额外参数"
    )

class ZillizConfig(VectorDatabaseConfig):
    type: Literal["zilliz"] = "zilliz"
    host: str = Field(
        default="localhost",
        description="Zilliz数据库的主机地址"
    )
    port: str = Field(
        default="19530",
        description="Zilliz数据库的主机地址"
    )
    user: str = Field(
        default="",
        description="Zilliz数据库的主机地址"
    )
    password: str = Field(
        default="",
        description="Zilliz数据库的密码"
    )
    secure: bool = Field(
        default=False,
        description="是否启用安全连接"
    )
    
class PGConfig(VectorDatabaseConfig):
    type: Literal["pg"] = "pg"
    host: str = Field(
        default="localhost",
        description="PostgreSQL数据库的主机地址"
    )
    port: str = Field(
        default="5432",
        description="PostgreSQL数据库的端口地址"
    )
    user: str = Field(
        default="",
        description="PostgreSQL数据库的用户名"
    )
    password: str = Field(
        default="",
        description="PostgreSQL数据库的密码"
    )
    database_name: str = Field(
        default="",
        description="PostgreSQL数据库的数据库名"
    )

class TextSplitterConfig(ABC, BaseModel):
    """文本切分器的基础配置类"""
    pass

class ChineseRecursiveConfig(TextSplitterConfig):
    """
    中文递归切分器配置
    type: Literal["ChineseRecursiveTextSplitter"] = "ChineseRecursiveTextSplitter"
    """
    source: Literal["huggingface", "tiktoken"] = Field(
        default="huggingface",
        description="tokenizer来源"
    )
    tokenizer_name_or_path: str = Field(
        default="",
        description="tokenizer的名称或路径"
    )

class SpacyConfig(TextSplitterConfig):
    """
    Spacy切分器配置
    type: Literal["SpacyTextSplitter"] = "SpacyTextSplitter"
    """
    source: Literal["huggingface"] = Field(
        default="huggingface",
        description="tokenizer来源"
    )
    tokenizer_name_or_path: str = Field(
        default="gpt2",
        description="tokenizer的名称或路径"
    )

class RecursiveCharacterConfig(TextSplitterConfig):
    """
    递归字符切分器配置
    type: Literal["RecursiveCharacterTextSplitter"] = "RecursiveCharacterTextSplitter"
    """
    source: Literal["tiktoken"] = Field(
        default="tiktoken",
        description="tokenizer来源"
    )
    tokenizer_name_or_path: str = Field(
        default="cl100k_base",
        description="tokenizer的名称或路径"
    )

class MarkdownHeaderConfig(TextSplitterConfig):
    """
    Markdown标题切分器配置
    # type: Literal["MarkdownHeaderTextSplitter"] = "MarkdownHeaderTextSplitter"
    """

    headers_to_split_on: List[Tuple[str, str]] = Field(
        default=[
            ("#", "head1"),
            ("##", "head2"),
            ("###", "head3"),
            ("####", "head4"),
        ],
        description="Markdown标题切分规则"
    )

# 联合类型，用于类型提示
AllTextSplitterConfigs = Union[
    ChineseRecursiveConfig,
    SpacyConfig,
    RecursiveCharacterConfig,
    MarkdownHeaderConfig
]

AllVectorStoreConfigs = Union[FaissConfig, MilvusConfig, ZillizConfig, PGConfig]

class KBConfig(BaseModel):
    """知识库的配置类, 包含sql数据库以及向量数据库"""
    KB_TYPES: list[str] =  ["faiss", "milvus", "zilliz", "pg"]

    # sql数据库设置
    database_type: str = Field(
        default="mysql",
        description="Sql数据库类型"
    )

    username: str = Field(
        default="user",
        description="Username for the SQLdatabase"
    )
    password: str = Field(
        default="password",
        description="Password for the SQLdatabase"
    )
    host: str = Field(
        default="localhost",
        description="Host for the SQLdatabase"
    )
    port: int = Field(
        default=3306,
        description="Port for the SQLdatabase"
    )

    zh_title_enhance: bool = Field(
        default=False,
        description="""
        是否开启中文标题加强，以及标题增强的相关配置
        通过增加标题判断，判断哪些文本为标题，并在metadata中进行标记；
        然后将文本与往上一级的标题进行拼合，实现文本信息的增强。
        """
    )
    
    # 向量数据库
    default_knowledge_base: str = Field(
        default="",
        description="默认使用的知识库"
    )
    
    vector_search_top_k: int = Field(
        default=3,
        description="向量搜索时返回的最相关文档数量"
    )
    
    score_threshold: float = Field(
        default=1.0,
        description="向量搜索时的分数阈值"
    )
    
    chunk_size: int = Field(
        default=500,
        description="每个文本块的大小, 不适用MarkdownHeaderTextSplitter"
    )
    overlap_size: int = Field(
        default=50,
        description="文本块之间的重叠大小, 不适用MarkdownHeaderTextSplitter"
    )
    
    kb_root_path: str = Field(
        default=None,
        description="知识库根目录的路径"
    )
    
    # 向量数据库配置
    # Pydantic 会根据输入数据中 'type' 字段的值，自动选择 AllVectorStoreConfigs 中的一个进行解析
    vector_store: AllVectorStoreConfigs = Field(
        default=FaissConfig(type="faiss"), 
        discriminator='type', 
        description="向量数据库的配置"
    )

    text_splitter_name: Literal[
        "ChineseRecursiveTextSplitter",
        "SpacyTextSplitter",
        "RecursiveCharacterTextSplitter",
        "MarkdownHeaderTextSplitter"
    ] = Field(
        default="ChineseRecursiveTextSplitter",
        description="文本切分器的名称"
    )
    
    text_splitters: Dict[
        Literal[
            "ChineseRecursiveTextSplitter",
            "SpacyTextSplitter",
            "RecursiveCharacterTextSplitter",
            "MarkdownHeaderTextSplitter"
        ],
        AllTextSplitterConfigs
    ] = Field(
        default={
            "ChineseRecursiveTextSplitter": ChineseRecursiveConfig(),
            "SpacyTextSplitter": SpacyConfig(),
            "RecursiveCharacterTextSplitter": RecursiveCharacterConfig(),
            "MarkdownHeaderTextSplitter": MarkdownHeaderConfig()
        },
        description="文本切分器的配置"
    )
    
    embedding_kword_file: str = Field(
        default="embedding_keywords.txt",
        description="Embedding模型定制词语的词表文件"
    )
    
    kb_info: KBInfo = Field(
        default=lambda: KBInfo(),
        description="每个知识库的初始化介绍, 用于在初始化知识库时显示和Agent调用,没写则没有介绍,不会被Agent调用。"
    )

    @property
    def database_url(self):
        return f"{self.database_type}://{self.username}:{self.password}@{self.host}:{self.port}/perry_chat"
    
    @model_validator(mode='after')
    def validate_and_process_paths(self) -> 'KBConfig':
        """
        配置加载后的后处理:
        1. 确保知识库根目录存在
        2. 转换相对路径为绝对路径
        3. 其他必要的初始化检查
        """
        # 确保知识库根目录存在
        if self.kb_root_path is None:
            resources_path = os.getenv("RESOURCES_PATH")
            if resources_path:
                self.kb_root_path = str(Path(resources_path) / "knowledge_base")
            else:
                resources_path = Path(__file__).resolve().parent.parent / "resources"
                self.kb_root_path = str(resources_path / "knowledge_base")

        kb_path = Path(self.kb_root_path)
        if not kb_path.is_absolute():
            raise ValueError(f"知识库地址请使用绝对地址: {self.kb_root_path}")
        if not kb_path.exists():
            kb_path.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Created knowledge base directory at: {kb_path}")
        else:
            logger.debug(f"Knowledge base directory exists at: {kb_path}")

        # 确保kb_root_path是绝对路径
        if not kb_path.is_absolute():
            self.kb_root_path = str(kb_path.absolute())

        # 如果embedding关键词文件路径是相对路径，转换为绝对路径
        if self.embedding_kword_file and not os.path.isabs(self.embedding_kword_file):
            self.embedding_kword_file = str(kb_path / self.embedding_kword_file)

        return self
