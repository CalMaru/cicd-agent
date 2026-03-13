from app.agent.classifier import classify_task
from app.agent.output_parser import parse_output
from app.agent.prompt_builder import build_prompt
from app.api.agent.schemas import AgentRequest
from app.core.llm_client import LLMClient
from app.schemas.response import AgentResult


class AgentOrchestrator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def run(self, request: AgentRequest) -> AgentResult:
        task_type = classify_task(request.input)
        prompt = build_prompt(task_type, request.input)
        raw_result = await self.llm_client.generate(prompt)
        return parse_output(raw_result, task_type)
