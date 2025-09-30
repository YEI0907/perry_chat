from perry_chat.core.database_manager import DataBaseManager
from perry_chat.core.config import load_settings
from perry_chat.core.knowledge_base.kb_services.faiss_kb_service import FaissKBService
from perry_chat.core.knowledge_base.utils import KnowledgeFile
from perry_chat.db.repository import KBRepository, KnowledgeFileRepository, FileDocRepository


# 主调用代码需要被包装在一个异步函数中
async def main():
    # 创建一个 FaissKBService 对象, default 向量数据库的Collecting Name
    settings = load_settings()
    db_manager = DataBaseManager(settings)
    await db_manager.init_connect()
    kb_repo = KBRepository()
    kb_file_repo = KnowledgeFileRepository()
    embed_model_name = "text-embedding-v4"
    faiss_service = FaissKBService(
        "test",
        embed_model_name,
        "测试数据库",
        settings=settings,
        kb_repo=kb_repo,
        kb_file_repo=kb_file_repo,
        file_doc_repo=FileDocRepository()
    )
    print(f"faiss_kb_service: {faiss_service}")

    from perry_chat.core.knowledge_base.kb_services import KBServiceFactory
    kb = await KBServiceFactory.get_service_by_name("test")

    # 如果想要使用的向量数据库的collecting name 不存在，则进行创建
    if kb is None:

        # 先在Mysql中创建向量数据库的基本信息
        await kb_repo.add_kb(kb_name="test",
                           kb_info="test",
                           vs_type="faiss",
                           embed_model=embed_model_name,
                            api_endpoint=settings.model.embed_models[embed_model_name].api_base_url,
                           user_id="test_user_id")

    # 调用 add_doc 方法添加一个名为 "README.md" 的文桗，确保使用 await
    await faiss_service.add_doc(KnowledgeFile("README.md", "test"))
    print(f"添加文档完成")
    # 根据输入进行检索
    search_ans = await faiss_service.search_docs(query="hw-chat 项目的后端服务？")
    print(search_ans)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())