from ..models import UserModel
from .base_repo import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    def __init__(self):
        super().__init__(UserModel)

    async def check_user(self, user_id: str) -> bool:
        out = await self.model.get_or_none(id=user_id)
        return out is not None
