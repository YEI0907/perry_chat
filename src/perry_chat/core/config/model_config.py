#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : model_config.py
@CreateTime : 2025/08/19 13:41:35
@Author     : Penglin.Ye
@Desc       : 模型配置文件
'''
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator
from loguru import logger

class LLMAPI(BaseModel):
    """大模型API配置"""
    name: str = Field(..., description="API名称")
    models: List[str] = Field(..., description="支持的模型列表")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")

class EmbedAPI(BaseModel):
    name: str = Field(..., description="API名称")
    models: List[str] = Field(..., description="支持的模型列表")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    dimensions: Optional[int] = Field(default=None, description="嵌入模型维度")
    api_base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")


# OnlineLLMConfigs = Union[ZhipuAPIConfig, OpenAIConfig]

class ModelConfig(BaseModel):
    """模型配置类"""

    llm_apis: List[LLMAPI] = Field(
        default=[],
        description="大模型的API配置"
    )

    embed_apis: List[EmbedAPI] = Field(
        default=[],
        description="嵌入模型的API配置"
    )

    embed_models: Dict[str, EmbedAPI] = Field(
        default_factory=dict,
        description="嵌入模型-API配置映射"
    )

    llm_models: Dict[str, LLMAPI] = Field(
        default_factory=dict,
        description="大模型名称-API配置映射"
    )
    
    @model_validator(mode="after")
    def load_llm_models(self) -> "ModelConfig":
        """
        配置加载后的后处理:
        加载模型列表
        """
        if self.llm_apis:
            logger.info(f"正在配置{len(self.llm_apis)}个大模型API")
            for llm_api in self.llm_apis:
                for model in llm_api.models:
                    self.llm_models[model] = llm_api
        return self

    @model_validator(mode="after")
    def load_embed_models(self) -> "ModelConfig":
        if self.embed_apis:
            logger.info(f"正在配置{len(self.embed_apis)}个嵌入模型API")
            for embed_api in self.embed_apis:
                for model in embed_api.models:
                    self.embed_models[model] = embed_api

        return self
        
    # @model_validator(mode='after')
    # def validate_and_process_paths(self) -> 'ModelConfig':
    #     """
    #     配置加载后的后处理:
    #     加载模型列表
    #     """

        
    #     # 验证选用的Embedding模型名称是否存在
    #     embedding_models = {embed_model.name for embed_model in self.local_model_config.embed}
    #     if self.embedding_model_name and self.embedding_model_name not in embedding_models:
    #         raise ValueError(
    #             f"Embedding model '{self.embedding_model_name}' is not available. "
    #             f"Available embedding models are: {sorted(embedding_models)}"
    #         )
        
    #     return self
        
        
        