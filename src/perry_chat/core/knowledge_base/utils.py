import os
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed

# from text_splitter import zh_title_enhance as func_zh_title_enhance
import langchain.document_loaders
from perry_chat.core.text_splitter import zh_title_enhance as func_zh_title_enhance
from langchain.docstore.document import Document
from langchain.text_splitter import TextSplitter
from pathlib import Path
import json
from typing import List, Union, Dict, Tuple, Generator, Callable
from perry_chat.core.config import load_settings
from loguru import logger

settings = load_settings()

def get_kb_path(knowledge_base_name: str):
    return os.path.join(settings.kb.kb_root_path, knowledge_base_name)

def get_doc_path( knowledge_base_name: str):
    return os.path.join(get_kb_path(knowledge_base_name), "content")


def validate_kb_name(knowledge_base_id: str) -> bool:
    # 检查是否包含预期外的字符或路径攻击关键字
    if "../" in knowledge_base_id:
        return False
    return True


def get_vs_path(knowledge_base_name: str, vector_name: str):
    return os.path.join(get_kb_path(knowledge_base_name), "vector_store", vector_name)


def get_file_path(knowledge_base_name: str, doc_name: str):
    doc_path = Path(get_doc_path(knowledge_base_name)).resolve()
    file_path = (doc_path / doc_name).resolve()
    if str(file_path).startswith(str(doc_path)):
        return str(file_path)
    else:
        raise ValueError(f"文件路径 {file_path} 不合法")


def list_kbs_from_folder(kb_root_path: str):
    return [f for f in os.listdir(kb_root_path)
            if os.path.isdir(os.path.join(kb_root_path, f))]


def list_files_from_folder(kb_name: str):
    doc_path = get_doc_path(kb_name)
    result = []

    def is_skiped_path(path: str):
        tail = os.path.basename(path).lower()
        for x in ["temp", "tmp", ".", "~$"]:
            if tail.startswith(x):
                return True
        return False

    def process_entry(entry):
        if is_skiped_path(entry.path):
            return

        if entry.is_symlink():
            target_path = os.path.realpath(entry.path)
            with os.scandir(target_path) as target_it:
                for target_entry in target_it:
                    process_entry(target_entry)
        elif entry.is_file():
            file_path = (Path(os.path.relpath(entry.path, doc_path)).as_posix())  # 路径统一为 posix 格式
            result.append(file_path)
        elif entry.is_dir():
            with os.scandir(entry.path) as it:
                for sub_entry in it:
                    process_entry(sub_entry)

    with os.scandir(doc_path) as it:
        for entry in it:
            process_entry(entry)

    return result


LOADER_DICT = {
               "UnstructuredMarkdownLoader": ['.md'],
               "JSONLoader": [".json"],
               "JSONLinesLoader": [".jsonl"],
               "UnstructuredLightPipeline": [".pdf"],
               }

SUPPORTED_EXTS = [ext for sublist in LOADER_DICT.values() for ext in sublist]


# patch json.dumps to disable ensure_ascii
def _new_json_dumps(obj, **kwargs):
    kwargs["ensure_ascii"] = False
    return _origin_json_dumps(obj, **kwargs)


if json.dumps is not _new_json_dumps:
    _origin_json_dumps = json.dumps
    json.dumps = _new_json_dumps

from langchain_community.document_loaders import JSONLoader

class JSONLinesLoader(JSONLoader):
    """
    行式 Json 加载器，要求文件扩展名为 .jsonl
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._json_lines = True

langchain.document_loaders.JSONLinesLoader = JSONLinesLoader


def get_LoaderClass(file_extension):
    for LoaderClass, extensions in LOADER_DICT.items():
        if file_extension in extensions:
            return LoaderClass
    raise ValueError(f"不支持的文件扩展名 {file_extension}")


def get_loader(loader_name: str, file_path: str, loader_kwargs: Dict = None):
    """
    根据 loader_name 和文件路径或内容返回文档加载器。

    参数：
    loader_name (str): 加载器名称。
    file_path (str): 文件路径。
    loader_kwargs (Dict): 加载器的额外参数。

    返回：
    loader: 文档加载器实例。
    """
    loader_kwargs = loader_kwargs or {}
    try:
        # 根据 loader_name 导入相应的文档加载器模块， 这是使用 自定义的，优先 ！
        if loader_name in ["UnstructuredLightPipeline"]:
            document_loaders_module = importlib.import_module('document_loaders')
        else:
            document_loaders_module = importlib.import_module('langchain_community.document_loaders')
        document_loader = getattr(document_loaders_module, loader_name)

    except Exception as e:
        # 如果加载器导入失败，记录错误日志并使用默认的 UnstructuredFileLoader
        msg = f"为文件{file_path}查找加载器{loader_name}时出错：{e}"
        logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
        document_loaders_module = importlib.import_module('langchain_community.document_loaders')
        document_loader = getattr(document_loaders_module, "UnstructuredFileLoader")

    loader = document_loader(file_path, **loader_kwargs)
    return loader


def make_text_splitter(
        splitter_name: str = settings.kb.text_splitter_name,
        chunk_size: int = settings.kb.chunk_size,
        chunk_overlap: int = settings.kb.overlap_size
):
    """
    根据参数获取特定的分词器
    """
    splitter_name = splitter_name or "SpacyTextSplitter"
    try:
        if splitter_name == "MarkdownHeaderTextSplitter":  # MarkdownHeaderTextSplitter特殊判定
            headers_to_split_on = settings.kb.text_splitters[splitter_name].headers_to_split_on
            text_splitter = langchain.text_splitter.MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on)
        else:
            try:  ## 优先使用用户自定义的text_splitter
                text_splitter_module = importlib.import_module('perry_chat.core.text_splitter')
                TextSplitter = getattr(text_splitter_module, splitter_name)
            except:  ## 否则使用langchain的text_splitter
                text_splitter_module = importlib.import_module('langchain.text_splitter')
                TextSplitter = getattr(text_splitter_module, splitter_name)

            if settings.kb.text_splitters[splitter_name].source == "tiktoken":  ## 从tiktoken加载
                try:
                    text_splitter = TextSplitter.from_tiktoken_encoder(
                        encoding_name=settings.kb.text_splitters[splitter_name].tokenizer_name_or_path,
                        pipeline="zh_core_web_sm",
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                except:
                    text_splitter = TextSplitter.from_tiktoken_encoder(
                        encoding_name=settings.kb.text_splitters[splitter_name].tokenizer_name_or_path,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
            elif settings.kb.text_splitters[splitter_name].source == "huggingface":  ## 从huggingface加载

                if settings.kb.text_splitters[splitter_name].tokenizer_name_or_path == "gpt2":
                    from transformers import GPT2TokenizerFast
                    from langchain.text_splitter import CharacterTextSplitter
                    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
                else:  ## 字符长度加载
                    from transformers import AutoTokenizer
                    tokenizer = AutoTokenizer.from_pretrained(
                        settings.kb.text_splitters[splitter_name].tokenizer_name_or_path,
                        trust_remote_code=True)
                text_splitter = TextSplitter.from_huggingface_tokenizer(
                    tokenizer=tokenizer,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            else:
                try:
                    text_splitter = TextSplitter(
                        pipeline="zh_core_web_sm",
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                except:
                    text_splitter = TextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
    except Exception as e:
        print(e)
        text_splitter_module = importlib.import_module('langchain.text_splitter')
        TextSplitter = getattr(text_splitter_module, "RecursiveCharacterTextSplitter")
        text_splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # If you use SpacyTextSplitter you can use GPU to do split likes Issue #1287
    # text_splitter._tokenizer.max_length = 37016792
    # text_splitter._tokenizer.prefer_gpu()
    return text_splitter

class KnowledgeFile:
    def __init__(
            self,
            filename: str,
            knowledge_base_name: str,
            loader_kwargs: Dict = {}
    ):
        """
        对应知识库目录中的文件，必须是磁盘上存在的才能进行向量化等操作。
        """
        self.kb_name: str = knowledge_base_name
        self.filename: str = str(Path(filename).as_posix())
        self.ext = os.path.splitext(filename)[-1].lower()
        if self.ext not in SUPPORTED_EXTS:
            raise ValueError(f"暂未支持的文件格式 {self.filename}")
        self.loader_kwargs = loader_kwargs
        self.filepath = get_file_path(knowledge_base_name, filename)
        self.docs = None
        self.splited_docs = None
        self.document_loader_name = get_LoaderClass(self.ext)
        self.text_splitter_name = settings.kb.text_splitter_name

        # 打印所有属性的值
        logger.debug(f"知识库名称: {self.kb_name}")
        logger.debug(f"文件名: {self.filename}")
        logger.debug(f"文件扩展名: {self.ext}")
        logger.debug(f"加载器参数: {self.loader_kwargs}")
        logger.debug(f"文件路径: {self.filepath}")
        logger.debug(f"文档内容 (初始值): {self.docs}")
        logger.debug(f"拆分后的文档内容 (初始值): {self.splited_docs}")
        logger.debug(f"文档加载器名称: {self.document_loader_name}")
        logger.debug(f"文本拆分器名称: {self.text_splitter_name}")

        # 打印 self.kb_name
        logger.debug(f"self.kb_name:{self.kb_name}")

    def file2docs(self, refresh: bool = False):
        if self.docs is None or refresh:
            logger.info(f"{self.document_loader_name} used for {self.filepath}")
            loader = get_loader(loader_name=self.document_loader_name,
                                file_path=self.filepath,
                                loader_kwargs=self.loader_kwargs)
            self.docs = loader.load()

        return self.docs

    def docs2texts(
            self,
            docs: List[Document] = None,
            zh_title_enhance: bool = settings.kb.zh_title_enhance,
            refresh: bool = False,
            chunk_size: int = settings.kb.chunk_size,
            chunk_overlap: int = settings.kb.overlap_size,
            text_splitter: TextSplitter = None,
    ):
        docs = docs or self.file2docs(refresh=refresh)
        if not docs:
            return []
        if self.ext not in [".csv"]:
            if text_splitter is None:
                text_splitter = make_text_splitter(splitter_name=self.text_splitter_name, chunk_size=chunk_size,
                                                   chunk_overlap=chunk_overlap)
            if self.text_splitter_name == "MarkdownHeaderTextSplitter":
                docs = text_splitter.split_text(docs[0].page_content)
            else:
                docs = text_splitter.split_documents(docs)

        if not docs:
            return []

        print(f"文档切分示例：{docs[0]}")
        if zh_title_enhance:
            docs = func_zh_title_enhance(docs)
        self.splited_docs = docs
        return self.splited_docs

    def file2text(
            self,
            zh_title_enhance: bool = settings.kb.zh_title_enhance,
            refresh: bool = False,
            chunk_size: int = settings.kb.chunk_size,
            chunk_overlap: int = settings.kb.overlap_size,
            text_splitter: TextSplitter = None,
    ):
        if self.splited_docs is None or refresh:
            docs = self.file2docs()
            self.splited_docs = self.docs2texts(docs=docs,
                                                zh_title_enhance=zh_title_enhance,
                                                refresh=refresh,
                                                chunk_size=chunk_size,
                                                chunk_overlap=chunk_overlap,
                                                text_splitter=text_splitter)
        return self.splited_docs

    def file_exist(self):
        return os.path.isfile(self.filepath)

    def get_mtime(self):
        return os.path.getmtime(self.filepath)

    def get_size(self):
        return os.path.getsize(self.filepath)

def run_in_thread_pool(
        func: Callable,
        params: List[Dict] = [],
) -> Generator:
    """
    在线程池中批量运行任务，并将运行结果以生成器的形式返回。
    请确保任务中的所有操作是线程安全的，任务函数请全部使用关键字参数。
    """
    tasks = []
    with ThreadPoolExecutor() as pool:
        for kwargs in params:
            thread = pool.submit(func, **kwargs)
            tasks.append(thread)

        for obj in as_completed(tasks):
            yield obj.result()


def files2docs_in_thread(
        files: List[Union[KnowledgeFile, Tuple[str, str], Dict]],
        chunk_size: int = settings.kb.chunk_size,
        chunk_overlap: int = settings.kb.overlap_size,
        zh_title_enhance: bool = settings.kb.zh_title_enhance,
) -> Generator:
    """
    利用多线程批量将磁盘文件转化成langchain Document.
    如果传入参数是Tuple，形式为(filename, kb_name)
    生成器返回值为 status, (kb_name, file_name, docs | error)
    """

    def file2docs(*, file: KnowledgeFile, **kwargs) -> Tuple[bool, Tuple[str, str, List[Document]]]:
        try:
            return True, (file.kb_name, file.filename, file.file2text(**kwargs))
        except Exception as e:
            msg = f"从文件 {file.kb_name}/{file.filename} 加载文档时出错：{e}"
            logger.error(f'{e.__class__.__name__}: {msg}', exc_info=e)
            return False, (file.kb_name, file.filename, msg)

    kwargs_list = []
    for i, file in enumerate(files):
        kwargs = {}
        try:
            if isinstance(file, tuple) and len(file) >= 2:
                filename = file[0]
                kb_name = file[1]
                file = KnowledgeFile(filename=filename, knowledge_base_name=kb_name)
            elif isinstance(file, dict):
                filename = file.pop("filename")
                kb_name = file.pop("kb_name")
                kwargs.update(file)
                file = KnowledgeFile(filename=filename, knowledge_base_name=kb_name)
            kwargs["file"] = file
            kwargs["chunk_size"] = chunk_size
            kwargs["chunk_overlap"] = chunk_overlap
            kwargs["zh_title_enhance"] = zh_title_enhance
            kwargs_list.append(kwargs)
        except Exception as e:
            yield False, (kb_name, filename, str(e))

    for result in run_in_thread_pool(func=file2docs, params=kwargs_list):
        yield result


if __name__ == "__main__":
    from pprint import pprint

    kb_file = KnowledgeFile(
        filename="/Users/lxw/Yplin/Projections/perry_chat/resources/knowledge_base/samples/content/invoice_1.pdf",
        knowledge_base_name="samples")
    # kb_file.text_splitter_name = "RecursiveCharacterTextSplitter"
    docs = kb_file.file2docs()
    pprint(docs[-1])