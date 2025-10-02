from ..models import MessageModel
from .base_repo import BaseRepository
from typing import Dict, Optional, List


class MassageRepository(BaseRepository[MessageModel]):
    def __init__(self):
        super().__init__(MessageModel)

    async def update_message(self,
                             message_id: str,
                             response: str = None,
                             metadata: Dict = None
                             ) -> Optional[str]:
        m: MessageModel = await self.get(message_id)
        if m is not None:
            if response is not None:
                m.response = response
            if isinstance(metadata, dict):
                m.meta_data = metadata
            await m.save()
            return m.id
        else:
            return None

    async def filter_message_with_response(self, conversation_id: str, limit: int = 10) -> List[MessageModel]:
        """
        根据会话ID异步过滤消息，并限制返回记录数量
        只返回有响应内容的消息，按创建时间降序排序
        """
        result = await self.model.filter(
            conversation_id=conversation_id,
            response__not=""  # 过滤掉空响应
        ).order_by("-create_time").limit(limit).all()

        return result
