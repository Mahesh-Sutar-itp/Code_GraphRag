from abc import ABC, abstractmethod
from typing import Any, Dict, List

class ISemanticSearch(ABC):

    @abstractmethod
    def get_seeds(self, query: str) -> List[Dict[str, Any]]:
        """
        """
        pass

class IHybridRetriever(ABC):

    @abstractmethod
    def get_seed_ids( self, query: str) -> List[str]:
        """
        """
        pass

class ICodeReranker(ABC):

    @abstractmethod
    def rerank(self, query, candidates, top_k=10) -> List[dict]:
        """
        """
        pass

class IBM25Retriever(ABC):

    @abstractmethod
    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        """
        pass