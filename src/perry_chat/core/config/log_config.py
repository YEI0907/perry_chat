#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : log_config.py
@CreateTime : 2025/08/19 13:41:35
@Author     : Penglin.Ye
@Desc       : 日志配置文件
'''
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class LogConfig(BaseModel):
    """日志配置"""
    log_verbose: bool = Field(default=True, description="Enable verbose logging")
    # log_level: Literal["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Log level")
    log_path: str = Field(
        default=str(Path(__file__).parent.parent.parent / "logs"),
        description="Log file path"
    )

    log_kwargs: dict = Field(
        default_factory=lambda: {},
        description="Log 参数"
    )