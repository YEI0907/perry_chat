import asyncio
import json
import uuid
import sys
from pathlib import Path
from tortoise import Tortoise
# sys.path.append(str(Path(__file__).parent.parent / "src"))
from perry_chat.db.repository.kb_file_repo import KnowledgeFileRepository
from perry_chat.services.kb_service import KBService
from perry_chat.core.config import load_settings
from perry_chat.core.database_manager import DataBaseManager
from perry_chat.services.chat_service import ChatService
from perry_chat.db.repository.user_repo import UserRepository
from perry_chat.db.repository.message_repo import MassageRepository
from perry_chat.db.repository.conversation_repo import ConversationRepository

from perry_chat.schemas.chat import ChatRequest

async def run_chat_demo():
    settings = load_settings()
    await Tortoise.init(DataBaseManager(settings).get_tortoise_config())
    await Tortoise.generate_schemas()
    # 初始化所需的仓库
    user_repo = UserRepository()
    message_repo = MassageRepository()
    conversation_repo = ConversationRepository()
    if not await user_repo.check_user("yepenglin"):
        await user_repo.create(
        id="yepenglin",
        username="叶鹏林",
        password_hash=hash("1234567")
    )

    # 创建聊天服务实例
    chat_service = ChatService(
        kb_service=KBService(
            kb_file_repo=KnowledgeFileRepository(),
            settings=settings
        ),
        user_repository=user_repo,
        massage_repository=message_repo,
        conversation_repository=conversation_repo,
        settings=settings
    )

    # 创建聊天请求
    chat_request = ChatRequest(
        query="你好，请介绍一下你自己",
        user_id="yepenglin",
        conversation_id=str(uuid.uuid4()),
        conversation_name="测试对话",
        prompt_name="default",
        model_name="qwen-flash",
        temperature=0.7,
        stream=True
    )

    print(settings.model)

    # 发送聊天请求
    response = await chat_service.chat(chat_request)

    # 处理响应
    async for chunk in response.body_iterator:
        data = json.loads(chunk)["text"]
        print(f"{data}", end="", flush=True)

    print("\n聊天完成")


if __name__ == "__main__":
    asyncio.run(run_chat_demo())