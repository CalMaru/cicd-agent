from fastapi import APIRouter

from app.agent.orchestrator import AgentOrchestrator
from app.api.agent.schemas import AgentRequest
from app.core.llm_client import MockLLMClient
from app.schemas.response import AgentResult

router = APIRouter(tags=["Agent"])

orchestrator = AgentOrchestrator(llm_client=MockLLMClient())


@router.post("/agent/run", response_model=AgentResult)
async def run_agent(request: AgentRequest):
    return await orchestrator.run(request)


agent_router = router
