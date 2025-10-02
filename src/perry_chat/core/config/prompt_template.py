#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File       : prompt.py
@CreateTime : 2025/08/19 14:38:12
@Author     : Penglin.Ye
@Desc       : 提示词配置
'''
from pydantic import BaseModel, Field


class LLMChatPrompt(BaseModel):
    """LLM聊天提示词配置"""
    default: str = Field(
        default='{{ input }}',
        description="默认提示内容"
    )
    with_history: str = Field(
        default='你可以根据用户之前的对话和提出的当前问题，提供专业和详细的技术答案。\n\n'
                '角色：AI技术顾问\n'
                '目标：能够结合历史聊天记录，提供专业、准确、详细的AI技术术语解释，增强回答的相关性和个性化。\n'
                '输出格式：详细的文本解释，包括技术定义、原理和应用案例。\n'
                '工作流程：\n'
                '  2. 分析用户当前问题：提取关键信息。\n'
                '  3. 如果存在历史聊天记录，请结合历史聊天记录和当前问题提供个性化的技术回答。\n'
                '  4. 如果问题与AI技术无关，以正常方式回应。\n\n'
                '历史聊天记录:\n'
                '{history}\n'
                '当前问题：\n'
                '{input}\n',
        description="带历史记录的提示内容"
    )


class KnowledgeBaseChat(BaseModel):
    default: str = Field(
        default='<指令>根据已知信息，简洁和专业的来回答问题。如果无法从中得到答案，请说 “根据已知信息无法回答该问题”，'
                '不允许在答案中添加编造成分，答案请使用中文。 </指令>\n'
                '<已知信息>{{ context }}</已知信息>\n'
                '<问题>{{ question }}</问题>\n',
        description="默认带上下文的提示内容提示内容"
    )
    text: str = Field(
        default='<指令>根据已知信息，简洁和专业的来回答问题。如果无法从中得到答案，请说 “根据已知信息无法回答该问题”，答案请使用中文。 </指令>\n'
                '<已知信息>{{ context }}</已知信息>\n'
                '<问题>{{ question }}</问题>\n',
        description="带上下文的提示内容",
    )
    empty: str = Field(
        default='请你回答我的问题:\n'
                '{{ question }}\n\n',
        description="没有搜索到上下文时候的提示词"
    )


class PromptTemplates(BaseModel):
    """提示词模板配置"""
    llm_chat: LLMChatPrompt = Field(
        default_factory=LLMChatPrompt,
        description="LLM聊天提示词模板"
    )
    knowledge_base_chat: KnowledgeBaseChat = Field(
        default_factory=KnowledgeBaseChat,
        description="知识库聊天提示词模板"
    )
