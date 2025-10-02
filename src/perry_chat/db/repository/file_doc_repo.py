from typing import List, Dict

from loguru import logger
from tortoise.transactions import atomic, in_transaction

from .base_repo import BaseRepository
from ..models import FileDoc


class FileDocRepository(BaseRepository[FileDoc]):
    def __init__(self):
        super().__init__(FileDoc)

    async def list_file_num_docs_id_by_kb_name_and_file_name(self,
                                                             kb_name: str,
                                                             file_name: str
                                                             ) -> List[str]:
        """
        列出某知识库某文件对应的所有Document的id。
        返回形式：[str, ...]
        """
        doc_ids = await self.model.filter(
            kb_name=kb_name,
            file_name=file_name
        ).values_list("doc_id", flat=True)

        return list(doc_ids)

    async def list_docs_from_db(self,
                                kb_name: str,
                                file_name: str = None,
                                metadata: Dict = {}
                                ) -> List[Dict]:
        """
        列出某知识库某文件对应的所有Document。
        返回形式：[{"id": str, "metadata": dict}, ...]
        """
        query = self.model.filter(kb_name__iexact=kb_name)
        if file_name:
            query = query.filter(file_name__iexact=file_name)

        for k, v in metadata.items():
            query = query.filter(meta_data__contains={k: str(v)})

        docs = await query

        return [{"id": doc.doc_id, "metadata": doc.meta_data} for doc in docs]

    @atomic()
    async def delete_docs_from_db(self,
                                  kb_name: str,
                                  file_name: str = None,
                                  ) -> List[Dict]:
        """
        删除某知识库某文件对应的所有Document，并返回被删除的Document。
        返回形式：[{"id": str, "metadata": dict}, ...]
        """
        docs = await self.list_docs_from_db(kb_name, file_name)
        query = self.model.filter(kb_name__iexact=kb_name)
        if file_name:
            query = query.filter(file_name__iexact=file_name)
        await query.delete()
        return docs

    async def add_docs_to_db(self,
                             kb_name: str,
                             file_name: str,
                             doc_infos: List[Dict]
                             ) -> bool:
        """
        添加某知识库某文件对应的Document到数据库。
        返回形式：[{"id": str, "metadata": dict}, ...]
        """
        if doc_infos is None:
            logger.warning("输入的perry_chat.db.repository.kb_file_repo.py的doc_infos参数为None")
            return False
        try:
            async with in_transaction() as connection:

                for doc_info in doc_infos:
                    obj = self.model(
                        kb_name=kb_name,
                        file_name=file_name,
                        doc_id=doc_info["id"],
                        meta_data=doc_info["metadata"]
                    )
                    await obj.save(using_db=connection)
                logger.info("文档信息成功添加到数据库")
                return True
        except Exception as e:
            logger.error(f"添加文档信息到数据库时出错：{e}")
            return False
