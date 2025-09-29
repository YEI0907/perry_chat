from tortoise.models import Model
from tortoise.fields import IntField, CharField, JSONField

class FileDoc(Model):
    id = IntField(pk=True, description="ID")
    kb_name = CharField(max_length=50, description="知识库名称")
    file_name = CharField(max_length=255, description="文件名称")
    doc_id = CharField(max_length=50, description="向量文档数据库ID")
    meta_data = JSONField(default={})

    class Meta:
        table = "file_docs"
