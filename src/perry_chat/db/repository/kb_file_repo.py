from typing import List, Dict

from loguru import logger
from tortoise.transactions import atomic

from .base_repo import BaseRepository
from .file_doc_repo import FileDocRepository
from ..models import KnowledgeFileModel, KnowledgeBaseModel
from ...core.knowledge_base.utils import KnowledgeFile


class KnowledgeFileRepository(BaseRepository[KnowledgeFileModel]):
    def __init__(self):
        super().__init__(KnowledgeFileModel)

    async def count_files_from_db(self, kb_name: str) -> int:
        """
        查询数据库文件数量
        :param kb_name:
        :return:
        """
        return await self.model.filter(kb_name__iexact=kb_name).count()

    async def list_files_from_db(self, kb_name: str) -> List[str]:
        """罗列数据库文件"""
        files = await self.model.filter(kb_name__iexact=kb_name).values_list("file_name", flat=True)
        return files

    @atomic()
    async def add_file_to_db(self,
                             kb_file: KnowledgeFile,
                             docs_count: int = 0,
                             custom_docs: bool = False,
                             doc_infos: List[Dict] = []
                             ) -> bool:
        """
        将文件添加到数据库中。如果文件已经存在，则更新文件信息和版本号。

        参数：
            kb_file: 知识文件对象，包含文件的相关信息。
            docs_count: 文档数量。
            custom_docs: 是否为自定义文档。
            doc_infos: 文档信息列表，形式为：[{"id": str, "metadata": dict}, ...]

        返回：
            bool: 如果操作成功，返回True。
        """
        logger.debug(f"开始查询 KnowledgeBase...")
        kb = await KnowledgeBaseModel.filter(kb_name__iexact=kb_file.kb_name).first()
        logger.debug(f"查询 KnowledgeBase 完成: {kb}")

        if kb:
            logger.debug(f"KnowledgeBase 存在, 开始查询 KnowledgeFile...")
            existing_file = await self.model.filter(
                kb_name__iexact=kb_file.kb_name,
                file_name__iexact=kb_file.filename
            ).first()
            logger.debug(f"查询 KnowledgeFile 完成: {existing_file}")

            mtime = kb_file.get_mtime()
            size = kb_file.get_size()
            logger.debug(f"获取文件时间和大小：mtime={mtime}, size={size}")

            if existing_file:
                logger.debug(f"文件存在，更新文件信息...")
                await existing_file.update_from_dict(
                    {
                        "file_mtime": mtime,
                        "file_size": size,
                        "docs_count": docs_count,
                        "custom_docs": custom_docs,
                        "file_version": existing_file.file_version + 1
                    }
                )
                await existing_file.save()

                logger.debug(f"文件信息更新完成")
            else:
                logger.debug(f"文件不存在，创建新文件...")
                new_file = await self.model.create(
                    file_name=kb_file.filename,
                    file_ext=kb_file.ext,
                    kb_name=kb_file.kb_name,
                    document_loader_name=kb_file.document_loader_name,
                    text_splitter_name=kb_file.text_splitter_name or "SpacyTextSplitter",
                    file_mtime=mtime,
                    file_size=size,
                    docs_count=docs_count,
                    custom_docs=custom_docs
                )
                await kb.update_from_dict(dict(file_count=kb.file_count + 1))
                logger.debug(f"新文件添加完成")

            logger.debug(f"开始添加文档信息...")
            # 假设有一个添加文档信息的方法
            file_doc_repo = FileDocRepository()
            await file_doc_repo.add_docs_to_db(
                kb_name=kb_file.kb_name,
                file_name=kb_file.filename,
                doc_infos=doc_infos
            )

            logger.debug(f"文档信息添加完成")
            return True
        else:
            logger.debug(f"KnowledgeBase 不存在，无法添加文件")
            return False

    @atomic()
    async def delete_file_from_db(self, kb_file: KnowledgeFile) -> bool:
        """
        从数据库中删除文件及其相关文档。

        参数:
            kb_file: 知识文件对象，包含文件的相关信息。

        返回:
            bool: 如果操作成功，返回True。
        """
        # 查询文件是否存在
        existing_file = await self.model.filter(
            file_name__iexact=kb_file.filename,
            kb_name__iexact=kb_file.kb_name
        ).first()

        if existing_file:
            logger.debug(f"找到要删除的文件: {existing_file.file_name}")

            # 删除文件
            await existing_file.delete()

            # 删除关联的文档
            file_doc_repo = FileDocRepository()
            await file_doc_repo.delete_docs_from_db(
                kb_name=kb_file.kb_name,
                file_name=kb_file.filename
            )

            # 更新知识库文件计数
            kb = await KnowledgeBaseModel.filter(
                kb_name__iexact=kb_file.kb_name
            ).first()

            if kb:
                logger.debug(f"更新知识库 {kb.kb_name} 的文件计数")
                kb.file_count -= 1
                await kb.save()

            logger.info(f"成功从数据库删除文件 {kb_file.filename}")
            return True

        logger.warning(f"未找到要删除的文件: {kb_file.filename}")
        return True

    @atomic()
    async def delete_files_from_db(self, knowledge_base_name: str):
        """
        删除数据库中所有的文件
        """
        await self.model.filter(kb_name__iexact=knowledge_base_name).delete()
        file_doc_repo = FileDocRepository()
        await file_doc_repo.delete_docs_from_db(knowledge_base_name)
        kb = await KnowledgeBaseModel.filter(kb_name__iexact=knowledge_base_name).first()
        if kb:
            kb.file_count = 0
            await kb.save()
        return True

    async def file_exists_in_db(self, kb_file: KnowledgeFile) -> bool:
        """
        数据库中是否有指定文件存在
        """
        flag = await self.model.filter(
            file_name__iexact=kb_file.filename,
            kb_name__iexact=kb_file.kb_name
        ).exists()
        return flag if flag else False

    async def get_file_detail(self, kb_name: str, filename: str) -> dict:
        file: KnowledgeFileModel = await self.model.filter(
            kb_name__iexact=kb_name,
            file_name__iexact=filename
        ).first()

        if file:
            return {
                "kb_name": file.kb_name,
                "file_name": file.file_name,
                "file_ext": file.file_ext,
                "file_version": file.file_version,
                "document_loader": file.document_loader_name,
                "text_splitter": file.text_splitter_name,
                "create_time": file.create_time,
                "file_mtime": file.file_mtime,
                "file_size": file.file_size,
                "custom_docs": file.custom_docs,
                "docs_count": file.docs_count,
            }
        else:
            return {}
