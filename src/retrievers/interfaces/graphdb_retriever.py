from abc import ABC, abstractmethod


class IRelationshipExtractor(ABC):
    """ Interface for extracting the source code and related nodes to target node """

    @abstractmethod
    def get_raw_source_code(self, seed_ids: list[str], num_hops: int = 1) -> str:
        """

        """
        pass

    @abstractmethod
    def get_related_nodes(self, seed_ids: list[str]) -> str:
        """
        """
        pass