from tortoise import fields
from tortoise.models import Model


class KnowledgeFileModel(Model):
    """
    知识库文件模型
    """
    id = fields.IntField(pk=True, auto=True, column_name="知识库文件id")
    file_name = fields.CharField(max_length=255, description="文件名")
    file_ext = fields.CharField(max_length=10, description="文件扩展名")
    kb_name = fields.CharField(max_length=50, description="所属知识库名称")
    document_loader_name = fields.CharField(max_length=50, description="文档加载器名称")
    text_splitter_name = fields.CharField(max_length=50, description="文本分割器名称")
    file_version = fields.IntField(default=1, description="文件版本")
    file_mtime = fields.FloatField(defualt=0.0, description="文件修改时间")
    file_size = fields.IntField(default=0, description="文件大小")
    custom_docs = fields.BooleanField(default=False, description="是否自定义docs")
    docs_count = fields.IntField(default=0, description="切分文档数量")
    create_time = fields.DatetimeField(auto_now=True, description="创建时间")

    class Meta:
        table = "knowledge_files"
        table_description = "知识库文件模型"
