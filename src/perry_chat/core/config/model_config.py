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


class LocalChatModelConfig(BaseModel):
    """本地模型配置"""
    name: str = Field(
        ...,
        description="模型名称"
    )
    model_path: str = Field(
        ...,
        description="模型路径"
    )
    
class LocalEmbedModelConfig(BaseModel):
    """本地模型配置"""
    name: str = Field(
        ...,
        description="模型名称"
    )
    model_path: str = Field(
        ...,
        description="模型路径"
    )
    
class LocalModelConfig(BaseModel):
    embed: List[LocalEmbedModelConfig] = Field(
        default_factory=list,
        description="本地嵌入模型配置"
    )
    chat: List[LocalChatModelConfig] = Field(
        default_factory=list,
        description="本地聊天模型配置"
    )

class ZhipuAPIConfig(BaseModel):
    """智谱API配置"""
    type: Literal["zhipu-api"] = "zhipu-api"
    api_key: Optional[str] = Field(default=None, description="智谱API密钥")
    version: str = Field(default="glm-4", description="模型版本")
    provider: str = Field(default="ChatGLMWorker", description="模型提供者")


class OpenAIConfig(BaseModel):
    """OpenAI配置"""
    type: Literal["openai-api"] = "openai-api"
    # model_name: str = Field(default="gpt-4", description="模型名称")
    api_base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")
    api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_proxy: str = Field(default="", description="OpenAI代理地址")

class LLMAPI(BaseModel):
    """大模型API配置"""
    name: str = Field(..., description="API名称")
    models: List[str] = Field(..., description="支持的模型列表")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")


OnlineLLMConfigs = Union[ZhipuAPIConfig, OpenAIConfig]

class ModelConfig(BaseModel):
    """模型配置类"""

    llm_apis: List[LLMAPI] = Field(
        default=[],
        description="大模型的API配置"
    )

    llm_models: Dict[str, LLMAPI] = Field(
        default_factory=dict,
        description="大模型名称-API配置映射"
    )
    
    embedding_model_name: str = Field(
        default="",
        description="选用的Embedding模型名称"
    )
    
    embedding_device: Literal["auto", "cuda", "mps", "cpu", "xpu"] = Field(
        default="auto",
        description="Embedding模型运行设备"
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
        
        
        