from tortoise.models import Model
from tortoise import fields
from .user_model import UserModel


class KnowledgeBaseModel(Model):
     id = fields.IntField(pk=True, description="知识库ID")
     kb_name = fields.CharField(max_length=50, description="知识库名称")
     kb_info = fields.CharField(max_length=200, description="知识库简介(AGENT)")
     vs_type = fields.CharField(max_length=50, description="数据库类型")
     embed_model = fields.CharField(max_length=50, description="嵌入模型名称")
     api_endpoint = fields.CharField(max_length=200, description="嵌入模型地址(base_url)")
     description = fields.CharField(default="", null=True, max_length=500, description="知识库描述")
     file_count = fields.IntField(default=0, description="文件数量")
     create_time = fields.DatetimeField(auto_now=True, description="创建时间")
     user: fields.ForeignKeyRelation[UserModel] = fields.ForeignKeyField(
         "models.UserModel", related_name="knowledge_base"
     )

     class Meta:
         table = "knowledge_base"
         table_description = "知识库管理表"