#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : server_config.py
@CreateTime : 2025/08/19 14:52:35
@Author     : Penglin.Ye
@Desc       : 服务器配置文件
'''
import os
import shutil
import sys
import tempfile
from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from loguru import logger

class APIServerConfig(BaseModel):
    """API服务器配置"""
    host: str = Field(
        default="127.0.0.1",
        description="API服务器主机地址"
    )
    port: int = Field(
        default=6006,
        description="API服务器端口"
    )

class FsChatModelWorkerConfig(BaseModel):
    """模型工作器配置"""
    host: str = Field(
        default="127.0.0.1",
        description="工作器主机地址"
    )
    port: int = Field(
        default=20002,
        description="工作器端口"
    )
    device: Literal["auto", "cuda", "cpu"] = Field(
        default="auto",
        description="模型运行设备"
    )

class FsChatControllerConfig(BaseModel):
    """控制器配置"""
    host: str = Field(
        default="127.0.0.1",
        description="控制器主机地址"
    )
    port: int = Field(
        default=20001,
        description="控制器端口"
    )
    dispatch_method: Literal["shortest_queue"] = Field(
        default="shortest_queue",
        description="调度方法"
    )

class OpenAIAPIConfig(BaseModel):
    """OpenAI API代理配置"""
    host: str = Field(
        default="127.0.0.1",
        description="OpenAI API代理主机地址"
    )
    port: int = Field(
        default=20000,
        description="OpenAI API代理端口"
    )

class ServerConfig(BaseModel):
    """服务器总配置"""
    llm_device: Literal["auto", "cuda", "cpu"] = Field(
        default="auto",
        description="LLM模型运行设备"
    )
    
    httpx_timeout: float = Field(
        default=300.0,
        description="HTTPX请求超时时间(秒)"
    )
    
    base_temp_dir: str = Field(
        default=os.path.join(tempfile.gettempdir(), "chatchat"),
        description="临时文件目录，主要用于文件对话"
    )
    
    default_bind_host: str = Field(
        default="127.0.0.1" if sys.platform != "win32" else "127.0.0.1",
        description="默认绑定主机地址"
    )
    
    api_server: APIServerConfig = Field(
        default_factory=APIServerConfig,
        description="API服务器配置"
    )
    
    model_workers: Dict[str, FsChatModelWorkerConfig] = Field(
        default_factory=dict,
        description="模型工作器配置字典"
    )
    
    controller: FsChatControllerConfig = Field(
        default_factory=FsChatControllerConfig,
        description="控制器配置"
    )
    
    openai_api: OpenAIAPIConfig = Field(
        default_factory=OpenAIAPIConfig,
        description="OpenAI API代理配置"
    )
    
    @model_validator(mode='after')
    def validate_and_process(self) -> 'ServerConfig':
        """
        配置加载后的后处理:
        1. 设置默认主机地址
        2. 验证端口配置
        3. 验证设备配置
        """
        # 确保所有服务使用相同的默认主机地址
        if not self.api_server.host:
            self.api_server.host = self.default_bind_host
            
        if not self.controller.host:
            self.controller.host = self.default_bind_host
            
        if not self.openai_api.host:
            self.openai_api.host = self.default_bind_host
            
        # 设置默认工作器配置
        if "default" not in self.model_workers:
            self.model_workers["default"] = FsChatModelWorkerConfig(
                host=self.default_bind_host,
                port=20002,
                device=self.llm_device
            )
            
        # 验证所有端口是否在有效范围内
        all_ports = [
            self.api_server.port,
            self.controller.port,
            self.openai_api.port
        ] + [worker.port for worker in self.model_workers.values()]
        
        for port in all_ports:
            if not 1024 <= port <= 65535:
                raise ValueError(f"Invalid port number: {port}. Port must be between 1024 and 65535")
                
        # 验证端口是否有重复
        if len(set(all_ports)) != len(all_ports):
            raise ValueError("Duplicate port numbers detected")
        
        # 清空文件临时文件地址
        try:
            shutil.rmtree(self.base_temp_dir)
        except Exception:
            pass
        os.makedirs(self.base_temp_dir, exist_ok=True)

        return self