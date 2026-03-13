from pydantic import BaseModel


class AgentResult(BaseModel):
    task_type: str
    summary: str
    assumptions: list[str]
    result: dict
    risks: list[str]
    confidence: float
