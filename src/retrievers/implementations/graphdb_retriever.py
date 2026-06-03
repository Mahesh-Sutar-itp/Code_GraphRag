from src.config.graphdb_config import get_neo4j_driver
from src.retrievers.interfaces.graphdb_retriever import IRelationshipExtractor
from src.agent.models import GraphNode, GraphEdge

class RelationshipExtractor(IRelationshipExtractor):
    def __init__(self):
        self.driver = get_neo4j_driver()

    # def get_raw_source_code(self, seed_ids: list[str]) -> str:
    #     """
    #     Tier 1 Context: Traverses the sealed door to get the heavy payload.
    #     """
    #     # query = """
    #     # MATCH (node)
    #     # WHERE node.node_id IN $seed_ids
    #     # MATCH (node)-[:HAS_SOURCE_CODE]->(document:Document)
    #     # RETURN node.name AS name, document.source_code AS code
    #     # """

    #     query=""" MATCH (node) WHERE node.node_id IN $seed_ids RETURN node.name as name, node.source_code as code """
    #     with self.driver.session() as session:
    #         results = session.run(query, seed_ids=seed_ids)
            
    #         formatted_code = "### Target Nodes' Source Code\n"
    #         for record in results:
    #             formatted_code += f"**{record['name']}**\n```\n{record['code']}\n```\n"
    #         return formatted_code

    def get_node_data(self, node_id: str) -> GraphNode | None:
        """
        Retrieve complete node information for a set of node_ids.

        No graph traversal.
        No relationship expansion.

        Returns:
            {
                "nodes": List[GraphNode]
            }
        """

        if not node_id:
            return None

        with self.driver.session() as session:
            query = """
            MATCH (n) WHERE n.node_id = $node_id
            RETURN
                n.node_id AS node_id,
                n.name AS name,
                n.kind AS kind,
                n.file_path AS file_path,
                n.docstring AS docstring,
                n.source_code AS source_code,
                n.start_line AS start_line,
                n.end_line AS end_line
            """

            result = session.run(query, node_id=node_id)

            record = result.single()

            if record is None:
                return None
            else:
                return GraphNode(
                    node_id=record["node_id"],
                    properties={
                        "name": record["name"],
                        "kind": record["kind"],
                        "file_path": record["file_path"],
                        "docstring": record["docstring"] or "",
                        "source_code": record["source_code"] or "",
                        "start_line": record["start_line"] or "",
                        "end_line": record["end_line"] or ""
                    }
                )
        
    def get_related_nodes(self, seed_ids: list[str], num_hops: int = 1) -> tuple[list[GraphNode], list[GraphEdge], list[str]]:
        """
        Tier 2 Context: Maps architectural edges.
        Splits incoming and outgoing relations to guarantee accurate directional formatting.
        """
        safe_hops: int = max(1,min(int(num_hops),2))
        
        with self.driver.session() as session:    
            
            query = f"""
            MATCH (seed)
            WHERE seed.node_id IN $seed_ids

            MATCH path = (seed)-[:CALLS|INHERITS|INSTANTIATES|IMPORTS*1..{safe_hops}]-(related)

            UNWIND relationships(path) AS rel

            RETURN DISTINCT
            startNode(rel) AS caller,
            endNode(rel) AS callee,
            type(rel) AS rel_type
            """

            results = session.run(query, seed_ids=seed_ids) # type: ignore
            nodes = {}
            edge_set = set()
            edges = []
            for record in results:

                caller = record["caller"]
                callee = record["callee"]

                for neo_node in [caller, callee]:
                    props = dict(neo_node)
                    node_id = neo_node["node_id"]

                    if node_id not in nodes:

                        nodes[node_id] = GraphNode(
                            node_id=node_id,
                            properties={
                                "name": props.get("name"),
                                "kind": props.get("kind"),
                                "file_path": props.get("file_path"),
                                "docstring": props.get("docstring", "")
                            }
                        )
                edge_key = ( caller["node_id"], callee["node_id"], record["rel_type"])
                if edge_key not in edge_set:
                    edge_set.add(edge_key)

                    edges.append(
                        GraphEdge(
                            caller_node_id=caller["node_id"],
                            callee_node_id=callee["node_id"],
                            relation_type=record["rel_type"]
                        )
                    )
                
        return list(nodes.values()), edges, seed_ids

    def _format_path(self, path_nodes: list, path_rels: list) -> str:
        """Helper method to dynamically stitch the N-hop path together."""
        path_str_parts = []
        
        # Loop through the relationships to interleave nodes and relations
        for i in range(len(path_rels)):
            path_str_parts.append(f"[Node: {path_nodes[i]}]")
            # The forward arrow is now 100% accurate because the Cypher query was strictly directional
            path_str_parts.append(f" -> [{path_rels[i]}] -> ")
            
        # Add the final trailing node in the path sequence
        path_str_parts.append(f"[Node: {path_nodes[-1]}]")
        
        formatted_path = "".join(path_str_parts)
        return f"- {formatted_path}\n"