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
    model_name: str = Field(default="gpt-4", description="模型名称")
    api_base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL")
    api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_proxy: str = Field(default="", description="OpenAI代理地址")


OnlineLLMConfigs = Union[ZhipuAPIConfig, OpenAIConfig]

class ModelConfig(BaseModel):
    """模型配置类"""
    model_root_path: str = Field(
        default=None,
        description="模型根目录路径"
    )
    
    temperature: float = Field(
        default=0.8,
        description="模型温度参数",
        ge=0.0,
        le=1.0
    )
    
    llm_models: List[str] = Field(
        default=[],
        description="可用的LLM模型列表"
    )
    
    local_model_config: LocalModelConfig = Field(
        default_factory=lambda: LocalModelConfig(),
        description="本地模型配置"
    )
    
    online_llm_config: OnlineLLMConfigs = Field(
        default=OpenAIConfig(),
        description="在线模型配置",
        discriminator='type'
    )
    
    embedding_model_name: str = Field(
        default="",
        description="选用的Embedding模型名称"
    )
    
    embedding_device: Literal["auto", "cuda", "mps", "cpu", "xpu"] = Field(
        default="auto",
        description="Embedding模型运行设备"
    )
        
    @model_validator(mode='after')
    def validate_and_process_paths(self) -> 'ModelConfig':
        """
        配置加载后的后处理:
        1. 确保模型根目录存在
        2. 转换相对路径为绝对路径
        3. 验证模型路径
        4. 验证LLM模型列表
        """
        # 确保模型根目录存在
        if self.model_root_path is None:
            resources_path = os.getenv("RESOURCES_PATH")
            if resources_path:
                self.model_root_path = str(Path(resources_path) / "models")
            else:
                self.model_root_path = str(Path(__file__).resolve().parent.parent / "resources" / "models")
        
        model_path = Path(self.model_root_path)
        if not model_path.exists():
            model_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created model root directory at: {model_path}")

        # 确保model_root_path是绝对路径
        self.model_root_path = str(model_path.absolute())
        
        # 获取所有可用的模型名称
        available_models = set()
        
        # 验证本地聊天模型配置
        if len(self.local_model_config.chat) > 0:
            for chat_model in self.local_model_config.chat:
                model_path = Path(chat_model.model_path)
                if not model_path.exists():
                    logger.warning(f"Local chat model path not found: {model_path}")
                available_models.add(chat_model.name)
        
        # 验证本地嵌入模型配置
        if len(self.local_model_config.embed) > 0:
            for embed_model in self.local_model_config.embed:

                model_path = Path(embed_model.model_path)
                if not model_path.exists():
                    logger.warning(f"Local embedding model path not found: {model_path}")

        # 添加在线模型到可用模型集合
        if isinstance(self.online_llm_config, ZhipuAPIConfig):
            available_models.add("zhipu-api")
        elif isinstance(self.online_llm_config, OpenAIConfig):
            available_models.add("openai-api")
        # if self.online_llm_config.api_key is None:
        #     api_key = os.environ.get("LLM_API_KEY", None)
        #     if not api_key:
        #         raise ValueError("请配置环境变量: `LLM_API_KEY`")
        #     self.online_llm_config.api_key = api_key
        
        # 验证LLM模型列表中的模型是否都可用
        if len(self.llm_models) > 0:
            for model in self.llm_models:
                if model not in available_models:
                    raise ValueError(
                        f"Model '{model}' in llm_models is not available. "
                        f"Available models are: {sorted(available_models)}"
                    )
        
        # 验证选用的Embedding模型名称是否存在
        embedding_models = {embed_model.name for embed_model in self.local_model_config.embed}
        if self.embedding_model_name and self.embedding_model_name not in embedding_models:
            raise ValueError(
                f"Embedding model '{self.embedding_model_name}' is not available. "
                f"Available embedding models are: {sorted(embedding_models)}"
            )
        
        return self
        
        
        