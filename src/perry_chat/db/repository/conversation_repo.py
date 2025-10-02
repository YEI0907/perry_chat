from .base_repo import BaseRepository
from ..models import ConversationModel


class ConversationRepository(BaseRepository[ConversationModel]):
    def __init__(self):
        super().__init__(ConversationModel)
