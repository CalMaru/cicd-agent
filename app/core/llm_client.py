import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...


MOCK_RESPONSES = {
    "api_design": {
        "task_type": "api_design",
        "summary": "프로바이더별 모델 목록 API",
        "assumptions": [
            "클라이언트 UI가 프로바이더별로 모델을 그룹화하여 표시",
            "프로바이더 목록은 서버에서 관리",
        ],
        "result": {
            "endpoint": "GET /api/v1/models",
            "request_schema": {"query_params": {"provider": "string (optional)"}},
            "response_example": {
                "providers": [
                    {
                        "provider": "openai",
                        "models": [
                            {"id": "gpt-4", "name": "GPT-4", "type": "chat"},
                        ],
                    },
                ],
            },
            "naming_conventions": [
                "리소스명은 복수형 사용 (models)",
                "URL path는 kebab-case",
                "응답 필드는 snake_case",
            ],
        },
        "risks": [
            "프로바이더 enum 일관성 유지 필요",
            "모델 목록이 클 경우 페이지네이션 필요",
        ],
        "confidence": 0.85,
    },
    "deployment_checklist": {
        "task_type": "deployment_checklist",
        "summary": "서비스 배포 체크리스트",
        "assumptions": [
            "컨테이너 기반 배포 환경",
            "CI/CD 파이프라인 구성 완료",
        ],
        "result": {
            "pre_deployment": [
                "DB 마이그레이션 스크립트가 멱등성을 보장하는지 확인",
                "프로덕션 부하에 맞는 커넥션 풀 설정 확인",
            ],
            "env_check": [
                "DATABASE_URL",
                "REDIS_URL",
                "API_SECRET_KEY",
            ],
            "rollback_plan": {
                "strategy": "blue-green",
                "steps": [
                    "로드 밸런서를 이전 배포로 전환",
                    "롤백 DB 마이그레이션 존재 여부 확인",
                ],
            },
            "monitoring": [
                "첫 30분간 5xx 비율 > 1% 알림 설정",
                "응답 레이턴시 p99 모니터링",
            ],
        },
        "risks": [
            "DB 마이그레이션 롤백 불가 시 데이터 손실 가능",
            "외부 의존성 헬스 체크 누락 가능",
        ],
        "confidence": 0.90,
    },
    "code_review": {
        "task_type": "code_review",
        "summary": "코드 리뷰 결과",
        "assumptions": [
            "FastAPI 기반 프로젝트",
            "Pydantic v2 사용",
        ],
        "result": {
            "issues": [
                {
                    "severity": "critical",
                    "type": "security",
                    "description": "문자열 보간을 통한 SQL 인젝션 취약점",
                    "suggestion": "파라미터화된 쿼리 또는 ORM 메서드 사용",
                },
                {
                    "severity": "warning",
                    "type": "validation",
                    "description": "요청 바디에 타입이 없는 dict 대신 Pydantic 모델 사용 필요",
                    "suggestion": "필드 검증이 포함된 CreateUserRequest 스키마 정의",
                },
                {
                    "severity": "info",
                    "type": "error_handling",
                    "description": "에러 처리 없음",
                    "suggestion": "적절한 HTTP 상태 코드와 함께 try/except 추가",
                },
            ],
        },
        "risks": [
            "보안 취약점이 프로덕션에 노출될 수 있음",
        ],
        "confidence": 0.92,
    },
    "error_analysis": {
        "task_type": "error_analysis",
        "summary": "의존성 해결 에러 분석",
        "assumptions": [
            "Python 3.12 환경",
            "uv 패키지 매니저 사용",
        ],
        "result": {
            "suspected_cause": "해당 패키지의 wheel이 현재 Python 버전에서 사용 불가",
            "troubleshooting_steps": [
                "패키지의 Python 버전 호환성 확인",
                "대체 패키지 검색 (예: faiss → faiss-cpu)",
                "Python 버전 다운그레이드 고려",
            ],
            "recommended_fix": "faiss-cpu를 사용하거나 호환되는 Python 버전으로 전환",
        },
        "risks": [
            "대체 패키지의 API가 다를 수 있음",
            "Python 다운그레이드 시 다른 의존성 충돌 가능",
        ],
        "confidence": 0.80,
    },
}


class MockLLMClient:
    async def generate(self, prompt: str) -> str:
        lower = prompt.lower()

        task_keywords = {
            "api_design": ["api design", "api 설계", "api specification", "api 명세"],
            "deployment_checklist": ["deployment", "배포", "checklist", "체크리스트"],
            "code_review": ["code review", "코드 리뷰", "review"],
            "error_analysis": ["error analysis", "에러 분석", "error", "에러"],
        }

        for task_type, keywords in task_keywords.items():
            if any(kw in lower for kw in keywords):
                return json.dumps(MOCK_RESPONSES[task_type], ensure_ascii=False)

        return json.dumps(MOCK_RESPONSES["error_analysis"], ensure_ascii=False)
