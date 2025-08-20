from tortoise import models, fields

from .conversation_model import ConversationModel


class MessageModel(models.Model):
    """
    聊天记录模型，表示会话中的一条聊天记录
    """
    id = fields.CharField(primary_key=True, max_length=36, description="聊天记录ID")

    chat_type = fields.CharField(max_length=50, description="聊天类型chat/agent_chat等")
    query = fields.TextField(description="用户提问")
    response = fields.TextField(description="模型回答")
    meta_data = fields.JSONField(default={}, description="记录知识库id等，以便后续扩展")
    feedback_score = fields.IntField(default=-1, description="用户评分")
    feedback_reason = fields.TextField(default="", description="用户评分理由")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    # update_time = fields.DatetimeField(auto_now=True)

    conversation: fields.ForeignKeyRelation[ConversationModel] = fields.ForeignKeyField(
        "models.ConversationModel",     # 1. 关联的模型名称 (推荐使用字符串格式)
        related_name="messages",        # 2. 在 ConversationModel 中的反向关系名称
        to_field="id",                  # 3. 指定关联到 ConversationModel 的哪个字段
        on_delete=fields.CASCADE        # 4. 当会话被删除时，级联删除所有消息
    )

    class Meta:
        table = "message"
        table_description = "聊天记录模型，表示会话中的一条聊天记录"

    # def __repr__(self):
    #     return f"<Message(id='{self.id}', chat_type='{self.chat_type}', query='{self.query}', response='{self.response}', meta_data='{self.meta_data}', feedback_score='{self.feedback_score}', feedback_reason='{self.feedback_reason}', create_time='{self.create_time}')>"