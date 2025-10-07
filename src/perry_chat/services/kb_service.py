import os
import urllib
from typing import Dict, List, Tuple

from langchain_core.documents import Document
from loguru import logger
from pydantic import Json
from starlette.datastructures import UploadFile

from perry_chat.core.knowledge_base.exceptions import KBNameError, KBNotFoundError, KBUpdateError
from perry_chat.core.knowledge_base.schemas import DocumentWithVSId
from perry_chat.core.knowledge_base.utils import validate_kb_name, get_file_path, run_in_thread_pool
from perry_chat.core.knowledge_base.vector_database_services import VecDBServiceFactory


class KBService:

    @staticmethod
    async def search_docs(
        query: str,
        knowledge_base_name: str,
        top_k: int = 3,
        score_threshold: float = 1.0,
        file_name: str = "",
        metadata: Dict =None
    ) -> List[DocumentWithVSId]:
        if metadata is None:
            metadata = {}

        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)

        data = []
        if kb is not None:
            if query:
                docs = await kb.search_docs(
                    query,
                    top_k=top_k,
                    score_threshold=score_threshold,
                )
                logger.debug("query==================")
                logger.debug(query)
                logger.debug("docs====================")
                logger.debug(docs)
                # data = [DocumentWithVSId(**x[0].dict(), score=x[1], id=x[0].metadata.get("id")) for x in docs]
                data = [
                    DocumentWithVSId(
                        **{**x[0].model_dump(), "id": x[0].metadata.get("id"), "score": x[1]}
                    )
                    for x in docs
                ]

            elif file_name or metadata:
                data = await kb.list_docs(file_name=file_name, metadata=metadata)
                for d in data:
                    if "vector" in d.metadata:
                        del d.metadata["vector"]
        return data

    @staticmethod
    async def update_docs_by_id(
            knowledge_base_name: str,
            docs: Dict[str, Document],
    ) -> bool:
        """更新知识库中的文件"""
        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)
        if kb is None:
            raise KBNotFoundError(knowledge_base_name)
        if kb.update_doc_by_ids(docs=docs) :
            return True
        else:
            raise KBUpdateError(knowledge_base_name)

    @staticmethod
    async def list_files(knowledge_base_name: str) -> List[str]:
        """罗列知识库中的文件"""
        if not validate_kb_name(knowledge_base_name):
            raise KBNameError(name=knowledge_base_name)
        knowledge_base_name = urllib.parse.unquote(knowledge_base_name)
        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)
        if not kb:
            raise KBNotFoundError(knowledge_base_name)
        else:
            all_doc_names = await kb.list_files()
            return all_doc_names

    @staticmethod
    def _save_files_in_thread(
        files: List[UploadFile],
        knowledge_base_name: str,
        override: bool
    ):
        """
        通过多线程将上传的文件保存到对应知识库目录内。
        生成器返回保存结果：{"code":200, "msg": "xxx", "data": {"knowledge_base_name":"xxx", "file_name": "xxx"}}
        """

        def save_file(file: UploadFile, knowledge_base_name: str, override: bool) -> dict:
            """
            保存单个文件。
            """
            filename = "未知"
            try:
                filename = file.filename
                file_path = get_file_path(knowledge_base_name=knowledge_base_name, doc_name=filename)
                data = {"knowledge_base_name": knowledge_base_name, "file_name": filename}

                file_content = file.file.read()  # 读取上传文件的内容
                if (os.path.isfile(file_path)
                        and not override
                        and os.path.getsize(file_path) == len(file_content)
                ):
                    file_status = f"文件 {filename} 已存在。"
                    logger.warning(file_status)
                    return dict(code=404, msg=file_status, data=data)

                if not os.path.isdir(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))
                with open(file_path, "wb") as f:
                    f.write(file_content)
                return dict(code=200, msg=f"成功上传文件 {filename}", data=data)
            except Exception as e:
                msg = f"{filename} 文件上传失败，报错信息为: {e}"
                logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
                return dict(code=500, msg=msg, data=data)

        params = [{
            "file": file,
            "knowledge_base_name": knowledge_base_name,
            "override": override
        } for file in files]
        for result in run_in_thread_pool(save_file, params=params):
            yield result

    # @staticmethod
    async def upload_docs(
            self,
            files: List[UploadFile],
            knowledge_base_name: str,
            override: bool,
            to_vector_store: bool,
            chunk_size: int,
            chunk_overlap: int,
            zh_title_enhance: bool = False,
            docs=None,
            not_refresh_vs_cache: bool = False
    ):
        """
        上传文档到知识库
        参数说明:
        :param files: (List[UploadFile]) 上传文件，支持多文件
        :param knowledge_base_name: (str) 知识库名称
        :param override: (bool) 覆盖已有文件
        :param to_vector_store: (bool) 上传文件后是否进行向量化
        :param chunk_size: (int) 知识库中单段文本最大长度
        :param chunk_overlap: (int) 知识库中相邻文本重合长度
        :param zh_title_enhance: (bool) 是否开启中文标题加强
        :param docs: (Json) 自定义的docs，需要转为json字符串
        :param not_refresh_vs_cache: (bool) 暂不保存向量库（用于FAISS）
        """
        if docs is None:
            docs = {}
        if not validate_kb_name(knowledge_base_name):
            raise KBNameError(name=knowledge_base_name)
        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)
        if kb is None:
            raise KBNotFoundError(knowledge_base_name)

        failed_files = {}
        file_names = list(docs.keys())


        for result in self._save_files_in_thread(files=files, knowledge_base_name=knowledge_base_name, override=override):
            filename = result["data"]["file_name"]
            if result["code"] != 200:
                failed_files[filename] = result["msg"]

            if filename not in file_names:
                file_names.append(filename)

        # 对保存的文件进行向量化
        if to_vector_store:
            result = self.update_docs(
                knowledge_base_name=knowledge_base_name,
                file_names=file_names,
                override_custom_docs=True,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                zh_title_enhance=zh_title_enhance,
                docs=docs,
                not_refresh_vs_cache=True,
            )
            failed_files.update(result.data["failed_files"])
            if not not_refresh_vs_cache:
                kb.save_vector_store()

        return dict(code=200, msg="上传成功", data={"failed_files": failed_files})

    async def update_docs(self,
        knowledge_base_name: str,
        file_names: List[str],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        zh_title_enhance: bool = False,
        override_custom_docs: bool = False,
        docs: Dict = None,
        not_refresh_vs_cache: bool = False
    ):
        """
        更新知识库中的文档。
        此异步函数使用给定的配置处理和更新文档。它允许各种自定义选项，例如
        文档块大小、重叠配置、增强的标题处理，以及是否覆盖已存在的自定义文档。
        :param knowledge_base_name: 需要更新的知识库名称。
        :type knowledge_base_name: str
        :param file_names: 文件名称, 支持多文件。
        :type file_names: List[str]
        :param chunk_size: 处理过程中使用的文档块大小。
        默认值为500。
        :type chunk_size: int, optional
        :param chunk_overlap: 文档块之间重叠的标记数量。
        默认值为50。
        :type chunk_overlap: int, optional
        :param zh_title_enhance: 是否应用中文标题增强处理。
        默认值为False。
        :type zh_title_enhance: bool, optional
        :param override_custom_docs: 是否覆盖已存在的自定义文档。
        默认值为False。
        :type override_custom_docs: bool, optional
        :param docs: 需要更新的文档字典。
        默认值为None。
        :type docs: Dict, optional
        :param not_refresh_vs_cache: 是否不刷新向量存储缓存。
        默认值为False。
        :type not_refresh_vs_cache: bool, optional
        :return: 表示文档更新过程完成状态。
        :rtype: None
        """
        if not validate_kb_name(knowledge_base_name):
            raise KBNameError(name=knowledge_base_name)
        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)
        if kb is None:
            raise KBNotFoundError(knowledge_base_name)

        failed_files = {}
        kb_files = []

    async def delete_docs(self):
        """删除文档"""
        ...

    async def update_info(self):
        """更新信息"""
        ...


    async def download_docs(self):
        """下载知识库文档"""
        ...

    async def recreate_vector_store(self):

        """
        从内容重新创建向量存储。
        当用户可以直接复制文件到content文件夹而不是通过网络上传时，这很有用。
        默认情况下，get_service_by_name只返回info.db中存在的知识库且其中有文档文件。
        将allow_empty_kb设置为True可使其应用于不在info.db中或没有文档的空知识库。
        """
        ...