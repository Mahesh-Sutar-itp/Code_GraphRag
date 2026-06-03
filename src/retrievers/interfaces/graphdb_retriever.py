from abc import ABC, abstractmethod

from src.agent.models import GraphEdge, GraphNode


class IRelationshipExtractor(ABC):
    """ Interface for extracting the source code and related nodes to target node """

    @abstractmethod
    def get_node_data(self, seed_ids: str) -> GraphNode | None:
        """

        """
        pass

    @abstractmethod
    def get_related_nodes(self, seed_ids: list[str], num_hops: int = 1) -> tuple[list[GraphNode], list[GraphEdge], list[str]]:
        """
        """
        pass