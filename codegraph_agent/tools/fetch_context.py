from src.retrievers.retrieval_pipeline import RetrievalPipeline


def fetch_codebase_and_relationship_context(user_query: str) -> str:
    """
    Use this tool to find relevant code implementations and map their architectural impact (blast radius). 
    
    This function performs a semantic search against the codebase to find the most relevant components 
    based on the user's natural language question, and then executes a structural graph traversal to 
    fetch their dependencies.

    Args:
        user_query (str): The user's natural language question regarding the codebase logic or architecture. Never tamper with the user_query. Pass the exact query user asked for.

    Returns:
        str: A formatted Markdown string containing a "Tiered Context" payload:
             - Tier 1: Target Node Source Code (the raw, executable code of the matched components).
             - Tier 2: Structural Dependencies (the 1-hop/N-hop architectural edges, showing what calls this code and what this code relies on).
    """

    retriever=RetrievalPipeline()
    return retriever.execute_pipeline(user_query)