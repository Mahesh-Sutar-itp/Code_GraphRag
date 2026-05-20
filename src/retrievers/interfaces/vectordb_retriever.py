from abc import ABC, abstractmethod


class ISemanticSearch(ABC):

    @abstractmethod
    def get_seed_ids(self, query: str) -> list[str]:
        """
        """
        pass