import os
import urllib
from loguru import logger
from typing import Dict, List, Any
from perry_chat.core.config import Settings
from langchain_core.documents import Document
from starlette.datastructures import UploadFile
from perry_chat.db.repository import KnowledgeFileRepository
from perry_chat.core.knowledge_base.exceptions import (
    KBNameError,
    KBNotFoundError,
    KBUpdateError
)

from perry_chat.core.knowledge_base.utils import (
    validate_kb_name,
    get_file_path,
    run_in_thread_pool,
    KnowledgeFile,
    files2docs_in_thread,
    list_files_from_folder
)
from perry_chat.core.knowledge_base.schemas import DocumentWithVSId
from perry_chat.core.knowledge_base.vector_database_services import (
    VecDBServiceFactory,
    VecDBService
)


class KBService:

    def __init__(
            self,
            kb_file_repo: KnowledgeFileRepository,
            settings: Settings
    ):
        self.kb_file_repo = kb_file_repo
        self.settings = settings

    @staticmethod
    def _valid_kb_name(knowledge_base_name: str):
        if not validate_kb_name(knowledge_base_name):
            raise KBNameError(name=knowledge_base_name)

    @staticmethod
    async def _get_kb_by_name(knowledge_base_name: str) -> VecDBService:
        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)
        if kb is None:
            raise KBNotFoundError(knowledge_base_name)
        return kb

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


    async def update_docs_by_id(
            self,
            knowledge_base_name: str,
            docs: Dict[str, Document],
    ) -> bool:
        """更新知识库中的文件"""
        kb = await self._get_kb_by_name(knowledge_base_name)
        if kb.update_doc_by_ids(docs=docs) :
            return True
        else:
            raise KBUpdateError(knowledge_base_name)

    async def list_files(self, knowledge_base_name: str) -> List[str]:
        """罗列知识库中的文件"""
        self._valid_kb_name(knowledge_base_name)

        knowledge_base_name = urllib.parse.unquote(knowledge_base_name)
        kb = await self._get_kb_by_name(knowledge_base_name)
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
        self._valid_kb_name(knowledge_base_name)
        kb = await self._get_kb_by_name(knowledge_base_name)

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
    ) -> dict[str, dict[Any, Any]]:
        """
        更新知识库中的文档。
        此异步函数使用给定的配置处理和更新文档。它允许各种自定义选项，例如
        文档块大小、重叠配置、增强的标题处理，以及是否覆盖已存在的自定义文档。
        :param knowledge_base_name: 需要更新的知识库名称。
        :param file_names: 文件名称, 支持多文件。
        :param chunk_size: 处理过程中使用的文档块大小。 默认值为500。
        :param chunk_overlap: 文档块之间重叠的标记数量。 默认值为50。
        :param zh_title_enhance: 是否应用中文标题增强处理。 默认值为False。
        :param override_custom_docs: 是否覆盖已存在的自定义文档。 默认值为False。
        :param docs: 需要更新的文档字典。 默认值为None。
        :param not_refresh_vs_cache: 是否不刷新向量存储缓存。 默认值为False。
        :return: 表示文档更新过程完成状态。
        """
        self._valid_kb_name(knowledge_base_name)
        kb = await VecDBServiceFactory.get_service_by_name(knowledge_base_name)
        if kb is None:
            raise KBNotFoundError(knowledge_base_name)

        failed_files = {}
        kb_files = []
        # 生成需要加载docs的文件列表
        for file_name in file_names:
            file_detail = await self.kb_file_repo.get_file_detail(knowledge_base_name, file_name)
            # 如果该文件之前使用了自定义docs, 则根据参数是决定略过或者覆盖
            if file_detail.get("custom_docs") and not override_custom_docs:
                continue
            if file_name not in docs:
                try:
                    kb_files.append(KnowledgeFile(filename=file_name, knowledge_base_name=knowledge_base_name))
                except Exception as e:
                    msg = f"加载文档 {file_name}时出错: {e}"
                    logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
                    failed_files[file_name] = msg

        # 从文件生成docs，并进行向量化。
        # 这里利用了KnowledgeFile的缓存功能，在多线程中加载Document，然后传给KnowledgeFile
        for status, result in files2docs_in_thread(kb_files,
                                                   chunk_size=chunk_size,
                                                   chunk_overlap=chunk_overlap,
                                                   zh_title_enhance=zh_title_enhance):
            if status:
                kb_name, file_name, new_docs = result
                kb_file = KnowledgeFile(filename=file_name,
                                        knowledge_base_name=knowledge_base_name)
                kb_file.splited_docs = new_docs
                await kb.update_doc(kb_file, not_refresh_vs_cache=True)
            else:
                kb_name, file_name, error = result
                failed_files[file_name] = error

        # 将自定义的docs进行向量化
        for file_name, v in docs.items():
            try:
                v = [x if isinstance(x, Document) else Document(**x) for x in v]
                kb_file = KnowledgeFile(filename=file_name, knowledge_base_name=knowledge_base_name)
                await kb.update_doc(kb_file, docs=v, not_refresh_vs_cache=True)
            except Exception as e:
                msg = f"为 {file_name} 添加自定义docs时出错：{e}"
                logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e )
                failed_files[file_name] = msg

        if not not_refresh_vs_cache:
            kb.save_vector_store()

        return {"failed_files": failed_files}

    async def delete_docs(self,
          knowledge_base_name: str,
          file_names: List[str],
          delete_content: bool = False,
          not_refresh_vs_cache: bool = False,
    ):
        """
        删除文档
        :param knowledge_base_name: 知识库名称
        :param file_names: 文件名称
        :param delete_content: 内容检测
        :param not_refresh_vs_cache: 暂不保存向量库（用于FAISS）
        """
        self._valid_kb_name(knowledge_base_name)
        kb = await self._get_kb_by_name(knowledge_base_name)

        failed_files = {}
        for file_name in file_names:
            if not await kb.exist_doc(file_name):
                failed_files[file_name] = f"未找到文件 {file_name}"

            try:
                kb_file = KnowledgeFile(filename=file_name,
                                        knowledge_base_name=knowledge_base_name)
                await kb.delete_doc(kb_file, delete_content, not_refresh_vs_cache=True)
            except Exception as e:
                msg = f"{file_name} 文件删除失败，错误信息：{e}"
                logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
                failed_files[file_name] = msg

        if not not_refresh_vs_cache:
            kb.save_vector_store()

        return {"failed_files": failed_files}

    async def update_info(self,
        knowledge_base_name: str,
        description: str
    ) -> bool:
        """
        更新信息
        :param knowledge_base_name: 知识库名称
        :param description: 知识库介绍
        :return:
        """
        self._valid_kb_name(knowledge_base_name)
        kb = await self._get_kb_by_name(knowledge_base_name)
        res = await kb.update_info(description)
        return res

    async def get_kb_file(self,
        knowledge_base_name: str,
        file_name: str,
    ) -> KnowledgeFile:
        """
        下载知识库文档
        :param knowledge_base_name: 知识库名称
        :param file_name: 文件名称
        """
        self._valid_kb_name(knowledge_base_name)
        await self._get_kb_by_name(knowledge_base_name)
        kb_file = KnowledgeFile(filename=file_name,
                                knowledge_base_name=knowledge_base_name)
        if not os.path.exists(kb_file.filepath):
            raise  KBNotFoundError(kb_file.filepath)
        return kb_file


    async def recreate_vector_store(self,
        knowledge_base_name: str,
        allow_empty_kb: bool = True,
        vs_type: str | None = None,
        embed_model: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        zh_title_enhance: bool | None = None,
        not_refresh_vs_cache: bool | None = False,
    ):
        """
        从内容重新创建向量存储。
        当用户可以直接复制文件到content文件夹而不是通过网络上传时，这很有用。
        默认情况下，get_service_by_name只返回info.db中存在的知识库且其中有文档文件。
        将allow_empty_kb设置为True可使其应用于不在info.db中或没有文档的空知识库。
        """
        if vs_type is None:
            vs_type = self.settings.kb.vs_type
        if embed_model is None:
            embed_model = list(self.settings.model.embed_models.keys())[0]
        if chunk_size is None:
            chunk_size = self.settings.kb.chunk_size
        if chunk_overlap is None:
            chunk_overlap = self.settings.kb.chunk_overlap
        if zh_title_enhance is None:
            zh_title_enhance = self.settings.kb.zh_title_enhance

        kb = await VecDBServiceFactory.get_service(knowledge_base_name, vs_type, embed_model)
        if kb is None and not allow_empty_kb:
            raise KBNotFoundError(knowledge_base_name)

        if await kb.exists():
            await kb.clear_vs()
        await kb.create_kb()
        files = list_files_from_folder(knowledge_base_name)
        kb_files = [(file, knowledge_base_name) for file in files]
        i = 0
        for status, result in files2docs_in_thread(kb_files,
                                                   chunk_size=chunk_size,
                                                   chunk_overlap=chunk_overlap,
                                                   zh_title_enhance=zh_title_enhance):
            if status:
                kb_name, file_name, docs = result
                kb_file = KnowledgeFile(filename=file_name, knowledge_base_name=kb_name)
                kb_file.splited_docs = docs
                yield {
                    "msg": f"({i + 1} / {len(files)}): {file_name}",
                    "total": len(files),
                    "finished": i + 1,
                    "doc": file_name,
                }
                await kb.add_doc(kb_file, not_refresh_vs_cache=True)
            else:
                kb_name, file_name, error = result
                msg = f"添加文件‘{file_name}’到知识库‘{knowledge_base_name}’时出错：{error}。已跳过。"
                logger.error(msg)
                yield {
                    "msg": msg,
                    "total": len(files),
                    "finished": i,
                    "doc": file_name,
                }
            i += 1
        if not not_refresh_vs_cache: kb.save_vector_store()