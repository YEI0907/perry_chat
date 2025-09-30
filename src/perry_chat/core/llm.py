
from perry_chat.core.config.model_config import LLMAPI
from .config import settings
from typing import Callable, List

from langchain_openai import ChatOpenAI


class LLM:
    
    @staticmethod
    def get_chat_openai(  
        model_name: str,
        temperature: float,
        max_tokens: int = None,
        streaming: bool = True,
        callbacks: List[Callable] = [],
        verbose: bool = True,
        **kwargs,
    ) -> ChatOpenAI:
        """
        定义了一个用于创建 ChatOpenAI 实例的函数 get_ChatOpenAI，并且在函数参数中指定了一些默认参数和可选参数。
        :param streaming:
        :param callbacks:
        :param model_name:要使用的模型名称
        :param temperature:采样温度
        :param max_tokens:最大输入限制
        :param verbose:是否打印详细进程
        :param kwargs:
        :return: ChatOpenAI 实例
        """
        # 首先，你要判断当前加载的是哪个模型
        # config = get_model_worker_config(model_name)
        # ChatOpenAI._get_encoding_model = MinxChatOpenAI.get_encoding_model
        api_config: LLMAPI = settings.model.llm_models.get(model_name)
        if not api_config:
            raise ValueError(f"模型 {model_name} 未在配置中找到，请检查配置文件。")
        model = ChatOpenAI(
            model=model_name,
            streaming=streaming,
            verbose=verbose,
            callbacks=callbacks,
            api_key=api_config.api_key,
            base_url=api_config.api_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            # openai_proxy=config.openai_proxy if config.type == "openai-api" else None,
            **kwargs
        )
        return model