# 아키텍처 상세 (Architecture Details)

이 문서는 [프로젝트 제안서](project_proposal.md) Section 7에서 요약된
아키텍처의 상세 내용을 다룬다.

------------------------------------------------------------------------

# 1. 컴포넌트 상세

## 1.1 API 계층 (API Layer)

에이전트 엔드포인트를 노출하는 FastAPI 서버.

담당:

-   요청 검증
-   세션 처리
-   응답 전달

엔드포인트 예시:

    POST /agent/run

------------------------------------------------------------------------

## 1.2 에이전트 오케스트레이터 (Agent Orchestrator)

에이전트 워크플로우를 관리하는 중앙 컴포넌트.

담당:

-   태스크 분류
-   프롬프트 구성
-   도구 호출
-   LLM 상호작용
-   구조화된 출력 파싱

------------------------------------------------------------------------

## 1.3 태스크 분류기 (Task Classifier)

어떤 워크플로우를 실행할지 결정한다.

태스크 유형:

    api_design
    deployment_checklist
    code_review
    error_analysis

------------------------------------------------------------------------

## 1.4 도구 시스템 (Tool System)

LLM을 지원하는 도메인 특화 도구.

도구가 제공하는 것:

-   재사용 가능한 템플릿
-   규칙 검증
-   엔지니어링 지식

도구 예시:

-   API Template Tool
-   Naming Advisor Tool
-   Deployment Checklist Tool
-   Code Review Rule Tool
-   Error Knowledge Tool

------------------------------------------------------------------------

## 1.5 LLM 클라이언트 (LLM Client)

LLM 프로바이더에 대한 추상화 계층.

담당:

-   프롬프트 제출
-   응답 수신
-   모델 전환

가능한 프로바이더:

-   OpenAI
-   로컬 LLM
-   기타 API

------------------------------------------------------------------------

## 1.6 출력 파서 (Output Parser)

LLM 응답이 엄격한 구조화된 형식을 따르도록 보장한다.

이를 통해:

-   결정적 처리
-   디버깅 용이성
-   신뢰할 수 있는 다운스트림 사용

------------------------------------------------------------------------

# 2. 프로젝트 구조

    ai-platform-copilot
    │
    ├─ app
    │
    │  ├─ api
    │  │  └─ agent_router.py
    │
    │  ├─ agent
    │  │  ├─ orchestrator.py
    │  │  ├─ classifier.py
    │  │  ├─ prompt_builder.py
    │  │  └─ output_parser.py
    │
    │  ├─ tools
    │  │  ├─ base.py
    │  │  ├─ template_tool.py
    │  │  ├─ checklist_tool.py
    │  │  └─ review_rule_tool.py
    │
    │  ├─ schemas
    │  │  ├─ request.py
    │  │  └─ response.py
    │
    │  └─ core
    │     ├─ config.py
    │     └─ llm_client.py
    │
    ├─ examples
    ├─ tests
    └─ main.py

------------------------------------------------------------------------

# 3. 데이터 모델

## AgentRequest

| 필드 | 설명 |
|---|---|
| id | 요청 ID |
| session_id | 대화 세션 |
| input | 사용자 질의 |
| task_type | 분류된 태스크 |
| created_at | 타임스탬프 |

------------------------------------------------------------------------

## AgentResponse

| 필드 | 설명 |
|---|---|
| id | 응답 ID |
| request_id | 연관된 요청 |
| summary | 간단한 설명 |
| assumptions | 가정한 사항 |
| result | 구조화된 결과 |
| risks | 설계 리스크 |

------------------------------------------------------------------------

## ToolCallLog

도구 사용을 추적한다.

| 필드 | 설명 |
|---|---|
| tool_name | 사용된 도구 |
| input | 도구 입력 |
| output | 도구 출력 |
| success | 실행 결과 |

------------------------------------------------------------------------

# 4. 구조화된 출력 형식

에이전트는 항상 JSON 형식으로 응답을 반환한다.

예시:

``` json
{
  "task_type": "api_design",
  "summary": "프로바이더별 모델 목록 API",
  "assumptions": [
    "클라이언트 UI가 프로바이더별로 모델을 그룹화"
  ],
  "result": {
    "endpoint": "GET /api/v1/models"
  },
  "risks": [
    "프로바이더 enum 일관성 유지 필요"
  ]
}
```

이점:

-   일관된 응답
-   검증 용이
-   통합 용이
