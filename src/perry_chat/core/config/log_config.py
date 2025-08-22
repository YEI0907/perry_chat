#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : log_config.py
@CreateTime : 2025/08/19 13:41:35
@Author     : Penglin.Ye
@Desc       : 日志配置文件
'''
import sys
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union, Any
from pydantic import BaseModel, Field, model_validator


class LogHandler(BaseModel):
    """日志处理器配置"""
    sink: str = Field(..., description="日志输出位置，可以是文件路径或stdout")
    level: Optional[str] = Field(default="INFO", description="日志级别")
    format: Optional[str] = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="日志格式"
    )
    rotation: Optional[str] = Field(default="10 MB", description="日志轮转策略")
    compression: Optional[str] = Field(default="zip", description="日志压缩格式")
    enqueue: Optional[bool] = Field(default=True, description="是否异步写入日志")
    backtrace: Optional[bool] = Field(default=True, description="是否记录回溯信息")
    diagnose: Optional[bool] = Field(default=True, description="是否记录诊断信息")

    @model_validator(mode='after')
    def transform_sink(self):
        if self.sink == "stdout":
            self.sink = sys.stdout
        return self

class LogConfig(BaseModel):
    """日志配置"""
    log_verbose: bool = Field(default=True, description="是否启用详细日志")
    log_level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="全局日志级别"
    )
    log_path: str = Field(
        default=str(Path(__file__).parent.parent.parent / "logs"),
        description="日志文件路径"
    )

    handlers: List[LogHandler] = Field(
        default_factory=lambda: [
            LogHandler(
                sink="stdout",
                level="INFO"
            ),
            LogHandler(
                sink="app.log",
                level="INFO",
                rotation="10 MB"
            )
        ],
        description="日志处理器列表"
    )

    log_kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外的日志配置参数"
    )

    @model_validator(mode='after')
    def prepare_log_kwargs(self) -> 'LogConfig':
        """准备日志配置参数"""
        # 如果没有设置handlers，则从self.handlers创建
        if "handlers" not in self.log_kwargs:
            self.log_kwargs["handlers"] = [
                handler.model_dump(exclude_none=True)
                for handler in self.handlers
            ]
        return self