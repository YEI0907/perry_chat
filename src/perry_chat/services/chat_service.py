import asyncio
import json
import uuid
from typing import AsyncIterable, Dict

from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from sse_starlette import EventSourceResponse

from perry_chat.core.llm import LLM
from perry_chat.core.callback_handler.conversation_callback_handler import ConversationCallbackHandler
from perry_chat.core.memory.conversation_db_buffer_mem import ConversationBufferDBMemory
from perry_chat.core.utils import wrap_done
from perry_chat.db.repository.conversation_repo import ConversationRepository
from perry_chat.db.repository.message_repo import MassageRepository
from perry_chat.db.repository.user_repo import UserRepository
from perry_chat.schemas.chat import ChatRequest
from perry_chat.core.config import settings



class ChatService:

    def __init__(self,
             user_repository: UserRepository,
             massage_repository: MassageRepository,
            conversation_repository: ConversationRepository
         ):
        self.user_repository = user_repository
        self.massage_repository = massage_repository
        self.conversation_repository = conversation_repository

    async def add_message_to_db(self,
        user_id: str,
        conversation_id: str,
        conversation_name: str,
        prompt_name: str,
        query: str,
        response="",
        metadata: Dict = {},
        message_id: str=None,
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
                id = conversation_id,
                user_id = user_id,
                name = conversation_name,
                chat_type=prompt_name
            )

        # 要判断是否存在会话的ID
        if not message_id:
            message_id = str(uuid.uuid4())

        m = await self.massage_repository.create(
            id = message_id,
            conversation_id = conversation.id,
            chat_type = prompt_name,
            response = response,
            metadata = metadata,
            query = query
        )
        return m.id


    async def check_user(self, user_id: str):
        if not await self.user_repository.check_user(user_id):
            raise ValueError(f"user not found")


    async def chat(self, request: ChatRequest):
        await self.check_user(request.user_id)

        async def chat_iterator() -> AsyncIterable[str]:

            callback = AsyncIteratorCallbackHandler()
            callbacks = [callback]
            memory = None


            # 构造一个新的Message_ID记录
            message_id = await self.add_message_to_db(user_id=request.user_id,
                                                      conversation_id=request.conversation_id,
                                                      conversation_name=request.conversation_name,
                                                      prompt_name=request.prompt_name,
                                                      query=request.query
                                                      )

            conversation_callback = ConversationCallbackHandler(
                msg_repo=self.massage_repository,
                conversation_id=request.conversation_id,
                message_id=message_id,
                chat_type=request.prompt_name,
                query=request.query
            )
            callbacks.append(conversation_callback)

            # 这段检查和处理代码的意义在于确保 max_tokens 的值在有效范围内。
            # 如果 max_tokens 是一个不合理的值（即小于或等于0），代码将其设置为 None，以防止后续操作中的错误或异常。
            if isinstance(request.max_tokens, int) and request.max_tokens <= 0:
                max_tokens = None


            model = LLM.get_chat_openai(
                model_name=request.model_name,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                callbacks=callbacks,
            )

            prompt = settings.prompt.llm_chat.default
            if request.history:  # 优先使用前端传入的历史消息
                pass
            elif request.conversation_id and request.history_len > 0:  # 前端要求从数据库取历史消息
                # 使用memory 时必须 prompt 必须含有memory.memory_key 对应的变量
                prompt = settings.prompt.llm_chat.with_history
                # 根据conversation_id 获取message 列表进而拼凑 memory
                memory = ConversationBufferDBMemory(
                    message_repo=self.massage_repository,
                    conversation_id=request.conversation_id,
                    llm=model,
                    message_limit=request.history_len
                )
            else:
                pass



            chat_prompt = PromptTemplate.from_template(prompt)
            chain = LLMChain(prompt=chat_prompt, llm=model, memory=memory)

            # Begin a task that runs in the background.
            task = asyncio.create_task(wrap_done(
                chain.acall({"input": request.query}),
                callback.done),
            )

            if request.stream:
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

    async def knowledge_base_chat(self, request: ChatRequest):