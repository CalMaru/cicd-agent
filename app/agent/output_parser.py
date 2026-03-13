import json

from app.agent.classifier import TaskType
from app.schemas.response import AgentResult


def parse_output(raw_text: str, task_type: TaskType) -> AgentResult:
    data = json.loads(raw_text)
    data["task_type"] = task_type.value
    return AgentResult.model_validate(data)
