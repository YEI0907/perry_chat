import warnings
from abc import ABC, abstractmethod
from typing import Any
from typing import List

from perry_chat.core.config import Settings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# Abstract Interface
class Pipeline(ABC):

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def run_pipeline(self,
                     payload: str,
                     query_inputs: List[str],
                     query_types: List[str],
                     keywords: List[str],
                     query: str,
                     file_path: str,
                     index_name: str,
                     options: List[str] = None,
                     group_by_rows: bool = True,
                     update_targets: bool = True,
                     debug: bool = False,
                     local: bool = True) -> Any:
        pass
