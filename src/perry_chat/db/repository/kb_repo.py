from typing import List, Optional, Dict, Any, Tuple

from tortoise.transactions import atomic

from .base_repo import BaseRepository
from ..models import KnowledgeBaseModel


class KBRepository(BaseRepository[KnowledgeBaseModel]):
    def __init__(self):
        super().__init__(KnowledgeBaseModel)

    @atomic()
    async def add_kb(
            self,
            kb_name: str,
            description: str,
            vs_type: str,
            embed_model: str,
            api_endpoint: str,
            user_id: Any
    ) -> bool:
        """
        创建或更新知识库。
        这比你原来的 add_kb_to_db 方法更健壮和高效。
        """
        # update_or_create 会自动处理“存在则更新，不存在则创建”的逻辑
        # defaults 字典指定了当记录存在时需要更新的字段
        await self.model.update_or_create(
            defaults={
                "description": description,
                "vs_type": vs_type,
                "embed_model": embed_model,
                "api_endpoint": api_endpoint,
                "user_id": user_id,
            },
            kb_name=kb_name,
        )
        return True

    async def list_kbs(self, min_file_count: int = -1) -> List[str]:
        """
        列出所有知识库名称。
        """
        # values_list 是获取特定字段列表的最高效方法
        kbs = await self.model.filter(file_count__gt=min_file_count).values_list("kb_name", flat=True)
        return kbs

    async def kb_exists(self, kb_name: str) -> bool:
        """
        检查知识库是否存在。
        """
        # .exists() 是专门用于检查存在性的查询，它比获取整个对象更高效
        return await self.model.filter(kb_name__iexact=kb_name).exists()

    async def load_kb(self, kb_name: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        从数据库加载知识库的核心信息。
        """
        # get_or_none 通过唯一或主键字段获取单个对象，如果不存在则返回 None
        kb = await self.model.get_or_none(kb_name__iexact=kb_name)
        if kb:
            return kb.kb_name, kb.vs_type, kb.embed_model, kb.description
        else:
            return None, None, None, None

    async def delete_kb(self, kb_name: str) -> bool:
        """
        从数据库中删除知识库。
        """
        # 直接在查询集上调用 .delete()，无需先将对象加载到内存
        deleted_count = await self.model.filter(kb_name__iexact=kb_name).delete()
        return deleted_count > 0

    async def get_kb_detail(self, kb_name: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库的详细信息。
        """
        kb = await self.model.get_or_none(kb_name__iexact=kb_name)
        if kb:
            # Tortoise 模型实例可以直接通过 .values() 转换为字典
            # 但为了安全和明确，我们手动构造字典
            return {
                "kb_name": kb.kb_name,
                "description": kb.description,
                "vs_type": kb.vs_type,
                "embed_model": kb.embed_model,
                "file_count": kb.file_count,
                "create_time": kb.create_time,
            }
        return {}
