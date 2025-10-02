


class KBNameError(Exception):
    """知识库名称错误异常
    
    当提供的知识库名称无效或不符合规范时抛出此异常
    """
    def __init__(self, name: str, message: str = None):
        self.name = name
        if message is None:
            message = f"知识库名称 '{name}' 无效或不存在"
        self.message = message
        super().__init__(self.message)

class KBNotFoundError(Exception):
    """知识库未找到异常
    
    当请求的知识库在系统中不存在时抛出此异常
    """
    def __init__(self, name: str = None, message: str = None):
        self.kb_id = name
        if message is None:
            if name:
                message = f"未找到名称为 '{name}' 的知识库"
            else:
                message = "请求的知识库未找到"
        self.message = message
        super().__init__(self.message)

class KBUpdateError(Exception):
    """知识库更新异常

    当更新知识库时发生错误时抛出此异常
    """
    def __init__(self, name: str = None, message: str = None):
        self.kb_id = name
        if message is None:
            if name:
                message = f"更新名称为 '{name}' 的知识库时发生错误"
            else:
                message = "更新知识库时发生错误"
        self.message = message
        super().__init__(self.message)