from pydantic import BaseModel, Field, field_validator

class QueryResolutionRequest(BaseModel):
    user_id: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Unique identifier for the user"
    )
    session_id: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Session identifier"
    )
    user_query: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="User's query text"
    )
    
    @field_validator('user_query')
    @classmethod
    def validate_query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or only whitespace')
        return v.strip()

class QueryResolutionResponse(BaseModel):
    status: str
    code: str
    msg: str
    node_ids: list[str]

class SubgraphRequest(BaseModel):
    node_ids: list[str] = Field(
        ..., 
        min_items=1,
        max_items=1000,
        description="List of node IDs to retrieve"
    )

class IndexRequest(BaseModel):
    url: str = Field(
        ..., 
        min_length=10, 
        max_length=500,
        description="GitHub repository URL (https://github.com/owner/repo)"
    )
    
    @field_validator('url')
    @classmethod
    def validate_github_url(cls, v):
        # Basic validation: must be HTTPS GitHub URL
        if not v.startswith('https://github.com/'):
            raise ValueError('Repository URL must be a public GitHub HTTPS URL (https://github.com/owner/repo)')
        # Check format: should have at least owner/repo
        parts = v.replace('https://github.com/', '').split('/')
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError('Repository URL must be in format: https://github.com/owner/repo')
        return v
