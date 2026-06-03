from pydantic import BaseModel

class QueryResolutionRequest(BaseModel):
    user_id: str
    session_id: str
    user_query: str

class QueryResolutionResponse(BaseModel):
    status: str
    code: str
    msg: str
    node_ids: list[str]

class SubgraphRequest(BaseModel):
    node_ids: list[str]

class IndexRequest(BaseModel):
    url: str
