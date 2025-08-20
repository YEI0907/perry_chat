import uuid

from tortoise import models, fields

from .user_model import UserModel


class ConversationModel(models.Model):
    id = fields.CharField(
        max_length=36,
        default=lambda: str(uuid.uuid4()),
        pk=True,
        description="会话ID"
    )

    name = fields.CharField(max_length=50, description="对话框名称")
    chat_type = fields.CharField(max_length=50, description="聊天类型")
    created_at = fields.DatetimeField(
        auto_now_add=True,
        description="聊天创建时间"
    )

    user: fields.ForeignKeyRelation[UserModel] = fields.ForeignKeyField(
        "models.UserModel", related_name="conversations", description="所属用户"
    )

    def __str__(self):
        return f"Conversation {self.id}"

    class Meta:
        table = "conversation"
        table_description = "对话表"