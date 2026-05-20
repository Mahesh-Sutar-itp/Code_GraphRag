from opentelemetry import trace

from src.config.graphdb_config import get_neo4j_driver
from src.retrievers.interfaces.graphdb_retriever import IRelationshipExtractor

# tracer=trace.get_tracer(__name__)

class RelationshipExtractor(IRelationshipExtractor):
    def __init__(self):
        self.driver = get_neo4j_driver()

    # @tracer.start_as_current_span("RelationshipExtractor.get_raw_source_code")
    def get_raw_source_code(self, seed_ids: list[str]) -> str:
        """
        Tier 1 Context: Traverses the sealed door to get the heavy payload.
        """
        # query = """
        # MATCH (node)
        # WHERE node.node_id IN $seed_ids
        # MATCH (node)-[:HAS_SOURCE_CODE]->(document:Document)
        # RETURN node.name AS name, document.source_code AS code
        # """

        query="""
        MATCH (node)
        WHERE node.node_id IN $seed_ids
        RETURN node.name as name, node.source_code as code
        """
        with self.driver.session() as session:
            results = session.run(query, seed_ids=seed_ids)
            
            formatted_code = "### Target Nodes' Source Code\n"
            for record in results:
                formatted_code += f"**{record['name']}**\n```\n{record['code']}\n```\n"
            return formatted_code

    # @tracer.start_as_current_span("RelationshipExtractor.get_related_nodes")
    def get_related_nodes(self, seed_ids: list[str], num_hops: int = 1) -> str:
        """
        Tier 2 Context: Maps architectural edges.
        Splits incoming and outgoing relations to guarantee accurate directional formatting.
        """
        safe_hops: int = max(1,min(int(num_hops),2))
        formatted_structure = f"### Structural Dependencies \n"
        
        with self.driver.session() as session:
            
            # =========================================================
            # PASS 1: Seed is the Callee (Incoming / Impact)
            # What components depend ON our seed node? (A -> B -> Seed)
            # =========================================================
            query_incoming = f"""
            MATCH (seed) WHERE seed.node_id IN $seed_ids
            MATCH path = (caller)-[:CALLS|INHERITS|INSTANTIATES|IMPORTS*1..{safe_hops}]->(seed)
            RETURN 
            [n IN nodes(path) | {{
                node_id: n.node_id,
                name: n.name,
                kind: n.kind,
                file_path: n.file_path,
                start_line: n.start_line,
                end_line: n.end_line,
                docstring: n.docstring
            }}] AS path_nodes,


            [rel IN relationships(path) | type(rel)] AS path_rels
            """
            results_incoming = session.run(query_incoming, seed_ids=seed_ids) # type: ignore
            
            formatted_structure += "\n#### Impact (Nodes that depend on this code):\n"
            for record in results_incoming:
                formatted_structure += self._format_path(record['path_nodes'], record['path_rels'])

            # =========================================================
            # PASS 2: Seed is the Caller (Outgoing / Dependencies)
            # What components does our seed node depend ON? (Seed -> C -> D)
            # =========================================================
            query_outgoing = f"""
            MATCH (seed) WHERE seed.node_id IN $seed_ids
            MATCH path = (seed)-[:CALLS|INHERITS|INSTANTIATES|IMPORTS*1..{safe_hops}]->(callee)
            RETURN             
            [n IN nodes(path) | {{
                node_id: n.node_id,
                name: n.name,
                kind: n.kind,
                file_path: n.file_path,
                start_line: n.start_line,
                end_line: n.end_line,
                docstring: n.docstring
            }}] AS path_nodes,

            [rel IN relationships(path) | type(rel)] AS path_rels
            """
            results_outgoing = session.run(query_outgoing, seed_ids=seed_ids) # type: ignore
            
            formatted_structure += "\n#### Dependencies (Code that this node relies on):\n"
            for record in results_outgoing:
                formatted_structure += self._format_path(record['path_nodes'], record['path_rels'])
                
        return formatted_structure

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