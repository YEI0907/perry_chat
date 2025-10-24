import json
import os
import uuid
import asyncio
from fastapi import Body, Request
from .kb_service import KBService
from urllib.parse import urlencode
from perry_chat.core.llm import LLM
from typing import AsyncIterable, Dict
from langchain.chains.llm import LLMChain
from perry_chat.core.config import Settings
from perry_chat.core.utils import wrap_done
from sse_starlette import EventSourceResponse
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain.callbacks import AsyncIteratorCallbackHandler
from perry_chat.db.repository.user_repo import UserRepository
from perry_chat.schemas.chat import ChatRequest, KBChatRequest, History
from perry_chat.db.repository.message_repo import MassageRepository
from perry_chat.db.repository.conversation_repo import ConversationRepository
from perry_chat.core.memory.conversation_db_buffer_mem import ConversationBufferDBMemory
from perry_chat.core.callback_handler.conversation_callback_handler import ConversationCallbackHandler
from perry_chat.core.knowledge_base.vector_database_services import VecDBServiceFactory
from perry_chat.core.knowledge_base.exceptions import (
    KBNameError,
    KBNotFoundError,
    KBUpdateError
)

class ChatService:

    def __init__(self,
                 user_repository: UserRepository,
                 massage_repository: MassageRepository,
                 conversation_repository: ConversationRepository,
                 kb_service: KBService,
                 settings: Settings
                 ):
        self.user_repository = user_repository
        self.massage_repository = massage_repository
        self.conversation_repository = conversation_repository
        self.kb_service = kb_service
        self.settings = settings

    async def add_message_to_db(self,
                                user_id: str,
                                conversation_id: str,
                                conversation_name: str,
                                prompt_name: str,
                                query: str,
                                response="",
                                metadata: Dict = {},
                                message_id: str = None,
                                ) -> str:
        """
        :param message_id:
        :param metadata:
        :param response:
        :param query: 在对话框输入的问题
        :param user_id: 用户的id（经过登录校验的）
        :param conversation_id: 对话框的id
        :param conversation_name: 对话框的名称
        :param prompt_name: 提示模板
        :return:
        """
        conversation = await self.conversation_repository.get(conversation_id)

        if not conversation:
            conversation = await self.conversation_repository.create(
                id=conversation_id,
                user_id=user_id,
                name=conversation_name,
                chat_type=prompt_name
            )

        # 要判断是否存在会话的ID
        if not message_id:
            message_id = str(uuid.uuid4())

        m = await self.massage_repository.create(
            id=message_id,
            conversation_id=conversation.id,
            chat_type=prompt_name,
            response=response,
            metadata=metadata,
            query=query
        )
        return m.id

    async def check_user(self, user_id: str):
        if not await self.user_repository.check_user(user_id):
            raise ValueError(f"user not found")

    async def load_chat_model(self, chat_request: ChatRequest|KBChatRequest):
        # 异步生成器的回调函数
        callback = AsyncIteratorCallbackHandler()
        callbacks = [callback]
        memory = None
        # 构造一个新的Message_ID记录
        message_id = await self.add_message_to_db(
            user_id=chat_request.user_id,
            conversation_id=chat_request.conversation_id,
            conversation_name=chat_request.conversation_name,
            prompt_name=chat_request.prompt_name,
            query=chat_request.query
        )

        conversation_callback = ConversationCallbackHandler(
            msg_repo=self.massage_repository,
            conversation_id=chat_request.conversation_id,
            message_id=message_id,
            chat_type=chat_request.prompt_name,
            query=chat_request.query
        )
        callbacks.append(conversation_callback)

        # 这段检查和处理代码的意义在于确保 max_tokens 的值在有效范围内。
        # 如果 max_tokens 是一个不合理的值（即小于或等于0），代码将其设置为 None，以防止后续操作中的错误或异常。
        if isinstance(chat_request.max_tokens, int) and chat_request.max_tokens <= 0:
            max_tokens = None

        model = LLM.get_chat_openai(
            model_name=chat_request.model_name,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
            callbacks=callbacks,
        )

        return message_id, model, memory, callback

    async def chat(self, chat_request: ChatRequest):
        # 先检查用户是否存在
        await self.check_user(chat_request.user_id)

        # 流式聊天
        async def chat_iterator() -> AsyncIterable[str]:

            message_id, model, memory, callback = await self.load_chat_model(chat_request)

            prompt = self.settings.prompt.llm_chat.default
            if chat_request.history:  # 优先使用前端传入的历史消息
                pass
            elif chat_request.conversation_id and chat_request.history_len > 0:  # 前端要求从数据库取历史消息
                # 使用memory 时必须 prompt 必须含有memory.memory_key 对应的变量
                prompt = self.settings.prompt.llm_chat.with_history
                # 根据conversation_id 获取message 列表进而拼凑 memory
                memory = ConversationBufferDBMemory(
                    message_repo=self.massage_repository,
                    conversation_id=chat_request.conversation_id,
                    llm=model,
                    message_limit=chat_request.history_len
                )
            else:
                pass

            chat_prompt = PromptTemplate.from_template(prompt)
            chain = LLMChain(prompt=chat_prompt, llm=model, memory=memory)

            # Begin a task that runs in the background.
            task = asyncio.create_task(wrap_done(
                chain.ainvoke({"input": chat_request.query}),
                callback.done),
            )

            if chat_request.stream:
                async for token in callback.aiter():
                    # Use server-sent-events to stream the response
                    yield json.dumps(
                        {"text": token, "message_id": message_id},
                        ensure_ascii=False)
            else:
                answer = ""
                async for token in callback.aiter():
                    answer += token
                yield json.dumps(
                    {"text": answer, "message_id": message_id},
                    ensure_ascii=False)

            await task

        return EventSourceResponse(chat_iterator())



    async def knowledge_base_chat_iterator(
            self,
            request: Request,
            chat_request: KBChatRequest,
    ) -> AsyncIterable[str]:

        message_id, model, memory, callback = await self.load_chat_model(chat_request)

        docs = await self.kb_service.search_docs(
            query=chat_request.query,
            knowledge_base_name=chat_request.knowledge_base_name,
            top_k=chat_request.top_k,
            score_threshold=chat_request.score_threshold
        )

        context = "\n".join([doc.page_content for doc in docs])

        if len(docs) == 0:  # 如果没有找到相关文档，使用empty模板
            prompt_template = self.settings.prompt.knowledge_base_chat.empty
        else:
            prompt_template = getattr(self.settings.prompt.knowledge_base_chat, chat_request.prompt_name)

        input_msg = History(role="user", content=prompt_template).to_msg_template(False)
        chat_prompt = ChatPromptTemplate.from_messages(
            [i.to_msg_template() for i in chat_request.history] \
            + [input_msg]
        )

        chain = LLMChain(prompt=chat_prompt, llm=model)

        # Begin a task that runs in the background.
        task = asyncio.create_task(wrap_done(
            chain.acall({"context": context, "question": chat_request.query}),
            callback.done),
        )

        source_documents = []
        for inum, doc in enumerate(docs):
            filename = os.path.basename(doc.metadata.get("source"))
            parameters = urlencode({"knowledge_base_name": chat_request.knowledge_base_name, "file_name": filename})
            base_url = request.base_url
            url = f"{base_url}knowledge_base/download_doc?" + parameters

            text = f"""出处 [{inum + 1}] [{filename}]({url}) \n\n{doc.page_content}\n\n"""
            source_documents.append(text)

        if len(source_documents) == 0:  # 没有找到相关文档
            source_documents.append(f"<span style='color:red'>未找到相关文档,该回答为大模型自身能力解答！</span>")

        if chat_request.stream:
            async for token in callback.aiter():
                # Use server-sent-events to stream the response
                yield json.dumps({"answer": token}, ensure_ascii=False)
            yield json.dumps({"docs": source_documents}, ensure_ascii=False)
        else:
            answer = ""
            async for token in callback.aiter():
                answer += token
            yield json.dumps({
                    "answer": answer,
                    "docs": source_documents
                },
                ensure_ascii=False
            )
        await task

    async def knowledge_base_chat(self, request: Request, chat_request: KBChatRequest):
        # 检查用户存不存在
        # 获取知识库
        kb =await VecDBServiceFactory.get_service_by_name(chat_request.knowledge_base_name)

        if kb is None:
            raise KBNotFoundError(name=chat_request.knowledge_base_name)

        return EventSourceResponse(
            self.knowledge_base_chat_iterator(
                request,
                chat_request
            )
        )


