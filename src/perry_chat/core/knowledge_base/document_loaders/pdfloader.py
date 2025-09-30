from langchain_core.documents import Document

from .interface import Pipeline
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.image import partition_image
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from typing import List
from rich.progress import Progress, SpinnerColumn, TextColumn
import tempfile
import json
import warnings
from rich import print
from typing import Any
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

class UnstructuredLightPipeline(Pipeline):
    """
    轻量级文档处理管道类
    
    该类使用unstructured库来处理PDF和图像文件，提取其中的文本内容并进行分割。
    支持提取表格内容，并可将处理过程中的中间结果保存为JSON或TXT文件。
    """

    async def run_pipeline(self,
                           file_path: str,
                           options: List[str] = None,
                           debug: bool = False,
                           local: bool = True,
                           **kwargs
                           ) -> Any:
        """
        运行文档处理管道
        
        Args:
            file_path (str): 待处理文件的路径
            options (List[str], optional): 处理选项列表，默认为None
                可选值:
                - "tables": 提取表格内容
            debug (bool, optional): 是否启用调试模式，默认为False
                调试模式下会保存中间处理结果为JSON文件
            local (bool, optional): 是否在本地显示进度条，默认为True
                True时显示可视化进度条，False时只打印文本进度信息
                
        Returns:
            Any: 处理后的文档分块列表
        """
        print(f"\nRunning pipeline with unstructured_langchain \n")

        strategy = 'hi_res'
        model_name = 'yolox'

        extract_tables = False
        # Initialize options as an empty list if it is None
        options = options or []
        if "tables" in options:
            extract_tables = True

        # Extracts the elements from the PDF
        elements = self.invoke_pipeline_step(
            lambda: self.process_file(file_path, strategy, model_name),
            "Extracting elements from the document...",
            local
        )

        if debug:
            new_extension = 'json'  # You can change this to any extension you want
            new_file_path = self.change_file_extension(file_path, new_extension)

            documents = self.invoke_pipeline_step(
                lambda: self.load_text_data(elements, new_file_path, extract_tables),
                "Loading text data...",
                local
            )
        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = os.path.join(temp_dir, "file_data.json")

                documents = self.invoke_pipeline_step(
                    lambda: self.load_text_data(elements, temp_file_path, extract_tables),
                    "Loading text data...",
                    local
                )

        docs = self.invoke_pipeline_step(
            lambda: self.split_text(
                documents,
                chunk_size=self.settings.kb.chunk_size,
                overlap=self.settings.kb.overlap_size
            ),
            "Splitting text...",
            local
        )

        return docs

    @staticmethod
    def process_file(file_path, strategy, model_name):
        """
        处理文件，提取其中的元素
        
        Args:
            file_path (str): 文件路径
            strategy (str): 处理策略
            model_name (str): 使用的模型名称
            
        Returns:
            list: 提取的元素列表
        """
        elements = None

        if file_path.lower().endswith('.pdf'):
            elements = partition_pdf(
                filename=file_path,
                strategy=strategy,
                infer_table_structure=True,
                model_name=model_name,
                languages=['chi_sim', "eng"]
            )
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            elements = partition_image(
                filename=file_path,
                strategy=strategy,
                infer_table_structure=True,
                model_name=model_name,
                languages=['chi_sim', "eng"]
            )

        return elements

    def load_text_data(self, elements, file_path, extract_tables):
        """
        加载文本数据
        
        Args:
            elements (list): 元素列表
            file_path (str): 文件路径
            extract_tables (bool): 是否提取表格
            
        Returns:
            list: 加载的文档列表
        """
        # 手动将元素保存到 JSON 文件中，确保使用 ensure_ascii=False
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump([e.to_dict() for e in elements], file, ensure_ascii=False)

        # elements_to_json(elements, filename=file_path)
        text_file = self.process_json_file(file_path, extract_tables)

        loader = TextLoader(text_file)
        documents = loader.load()

        return documents

    @staticmethod
    def split_text(text, chunk_size, overlap) -> List[Document]:
        """
        分割文本
        
        Args:
            text (list): 待分割的文本
            chunk_size (int): 分块大小
            overlap (int): 重叠大小
            
        Returns:
            list: 分割后的文档列表
        """
        text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
        docs = text_splitter.split_documents(text)

        return docs

    def process_json_file(self, input_data, extract_tables):
        """
        处理JSON文件，提取所需元素
        
        Args:
            input_data (str): 输入数据文件路径
            extract_tables (bool): 是否提取表格
            
        Returns:
            str: 输出文件路径
        """
        # Read the JSON file
        with open(input_data, 'r', encoding="utf-8") as file:
            data = json.load(file)

        # Iterate over the JSON data and extract required table elements
        extracted_elements = []
        for entry in data:
            if entry["type"] == "Table":
                extracted_elements.append(entry["metadata"]["text_as_html"])
            elif entry["type"] == "Title" and extract_tables is False:
                extracted_elements.append(entry["text"])
            elif entry["type"] == "NarrativeText" and extract_tables is False:
                extracted_elements.append(entry["text"])
            elif entry["type"] == "UncategorizedText" and extract_tables is False:
                extracted_elements.append(entry["text"])

        # Write the extracted elements to the output file
        new_extension = 'txt'  # You can change this to any extension you want
        new_file_path = self.change_file_extension(input_data, new_extension)
        with open(new_file_path, 'w') as output_file:
            for element in extracted_elements:
                output_file.write(element + "\n\n")  # Adding two newlines for separation

        return new_file_path

    @staticmethod
    def change_file_extension(file_path, new_extension):
        """
        更改文件扩展名
        
        Args:
            file_path (str): 原文件路径
            new_extension (str): 新扩展名
            
        Returns:
            str: 更改后的文件路径
        """
        # Check if the new extension starts with a dot and add one if not
        if not new_extension.startswith('.'):
            new_extension = '.' + new_extension

        # Split the file path into two parts: the base (everything before the last dot) and the extension
        # If there's no dot in the filename, it'll just return the original filename without an extension
        base = file_path.rsplit('.', 1)[0]

        # Concatenate the base with the new extension
        new_file_path = base + new_extension

        return new_file_path

    def beautify_json(self, result):
        """
        美化JSON结果
        
        Args:
            result (str): JSON字符串
            
        Returns:
            str/dict: 格式化后的JSON数据或空字典
        """
        try:
            # Convert and pretty print
            data = json.loads(str(result))
            data = json.dumps(data, indent=4)
            return data
        except (json.decoder.JSONDecodeError, TypeError):
            print("The response is not in JSON format:\n")
            print(result)

        return {}

    @staticmethod
    def invoke_pipeline_step(task_call, task_description, local):
        """
        执行管道步骤
        
        Args:
            task_call (callable): 要执行的任务函数
            task_description (str): 任务描述
            local (bool): 是否在本地显示进度
            
        Returns:
            Any: 任务执行结果
        """
        if local:
            with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=False,
            ) as progress:
                progress.add_task(description=task_description, total=None)
                ret = task_call()
        else:
            print(task_description)
            ret = task_call()

        return ret