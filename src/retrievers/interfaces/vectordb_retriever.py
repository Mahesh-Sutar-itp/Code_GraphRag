from abc import ABC, abstractmethod
from typing import Dict, List

class ISemanticSearch(ABC):

    @abstractmethod
    def get_seeds(self, query: str) -> List[Dict[str]]:
        """
        """
        pass