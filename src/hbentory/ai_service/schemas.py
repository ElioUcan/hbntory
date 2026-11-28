from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    output: str = Field(min_length=1)
    session_id: str | None = Field(min_length=1)

class QueryAgent(BaseModel):
    query: str = Field(min_length=1)
    session_id: str | None = Field(min_length=1)
