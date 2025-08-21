from typing import Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
from langchain.prompts.chat import ChatMessagePromptTemplate


class History(BaseModel):
    """
    对话历史
    可从dict生成，如
    h = History(**{"role":"user","content":"你好"})
    也可转换为tuple，如
    h.to_msy_tuple = ("human", "你好")
    """
    role: str = Field(...)
    content: str = Field(...)

    def to_msg_tuple(self):
        return "ai" if self.role == "assistant" else "human", self.content

    def to_msg_template(self, is_raw=True) -> ChatMessagePromptTemplate:
        role_maps = {
            "ai": "assistant",
            "human": "user",
        }
        role = role_maps.get(self.role, self.role)
        if is_raw:  # 当前默认历史消息都是没有input_variable的文本。
            content = "{% raw %}" + self.content + "{% endraw %}"
        else:
            content = self.content

        return ChatMessagePromptTemplate.from_template(
            content,
            "jinja2",
            role=role,
        )

    @classmethod
    def from_data(cls, h: Union[List, Tuple, Dict]) -> "History":
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            h = cls(role=h[0], content=h[1])
        elif isinstance(h, dict):
            h = cls(**h)

        return h


class ChatRequest(BaseModel):
    """
    聊天路由的请求体
    :param query: 用户输入的问题
    :param model_name: 使用哪个大模型作为后端服务
    :param temperature: 采样温度
    :param max_tokens: 最大输入Token限制
    """
    query: str = Field(..., description="用户的输入")
    model_name: str = Field("qwen-flash", description="LLM 模型名称。")

    user_id: str = Field("", description="用户ID")
    conversation_id: str = Field("", description="对话框ID")
    conversation_name: str = Field("", description="对话框名称")
    history_len: int = Field(-1, description="从数据库中取历史消息的数量")
    history: Union[int, List[History]] = Field([],
                                               description="历史对话，设为一个整数可以从数据库中读取历史消息",
                                               examples=[[
                                                   {"role": "user",
                                                    "content": "我们来玩成语接龙，我先来，生龙活虎"},
                                                   {"role": "assistant", "content": "虎头虎脑"}]]
                                               )
    stream: bool = Field(False, description="流式输出")
    temperature: float = Field(0.8, description="LLM 采样温度", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, description="限制LLM生成Token数量，默认None代表模型最大值")
    prompt_name: str = Field("default", description="使用的prompt模板名称(在configs/prompt_config.py中配置)")

