from tortoise import models, fields

class UserModel(models.Model):
    """
    用户模型
    """
    id = fields.CharField(pk=True, max_length=32, description='用户ID')
    username = fields.CharField(max_length=255, unique=True, description='用户名')
    password_hash = fields.CharField(max_length=255, description='密码的哈希值')

    def __str__(self):
        return f"UserModel {self.id}: {self.username}"

    class Meta:
        table = "user"
        table_description = "用户表"