# AI Platform Engineering Copilot

## Week 1 개발 계획 (상세)

이 문서는 프로젝트 **Week 1의 일별 개발 계획**을 기술한다.

Week 1의 목표는 다음을 시연하는 **동작하는 에이전트 MVP**를 구축하는 것이다:

- 에이전트 워크플로우 (classify → plan → execute → validate)
- 구조화된 출력 및 검증
- FastAPI 인터페이스
- 기본 도구 통합

시스템이 **기능적으로 완벽할 필요는 없다**.\
핵심 목표는 **깔끔하고 확장 가능한 에이전트 아키텍처**를 구축하는 것이다.

------------------------------------------------------------------------

# Week 1 목표

Week 1 종료 시 시스템이 지원해야 하는 항목:

1. 에이전트 실행을 위한 FastAPI 엔드포인트
2. 에이전트 워크플로우 (분류 → 프롬프트 구성 → LLM 생성 → 구조화된 출력 → 출력 검증)
3. 하나의 실제 기능 (API 명세 작성)
4. 하나의 도구 통합
5. Pydantic 스키마 검증을 포함한 구조화된 JSON 출력
6. 요청/응답 로깅

------------------------------------------------------------------------

# 시스템 워크플로우 (목표)

```
사용자 요청
     |
     v
FastAPI 엔드포인트
     |
     v
에이전트 오케스트레이터
     |
     v
태스크 분류
     |
     v
프롬프트 구성
     |
     v
도구 호출 (선택)
     |
     v
LLM 생성
     |
     v
구조화된 출력 파싱
     |
     v
출력 검증 ---------> [검증 실패]
     |                    |
     v                    v
응답 반환           재시도 / 에러 응답
```

**출력 검증 단계**는 모든 응답이 예상된 Pydantic 스키마에 부합하는지
확인한 후 반환한다. 검증에 실패하면 시스템은 수정 프롬프트로 재시도하거나
구조화된 에러 응답을 반환할 수 있다.

------------------------------------------------------------------------

# 권장 리포지토리 구조

```
ai-platform-copilot
│
├ app
│
│  ├ api
│  │  ├ app.py
│  │  └ agent/
│  │     ├ router.py
│  │     └ schemas.py
│  │
│  ├ agent
│  │  ├ orchestrator.py
│  │  ├ classifier.py
│  │  ├ prompt_builder.py
│  │  └ output_parser.py
│  │
│  ├ tools
│  │  ├ base.py
│  │  └ template_tool.py
│  │
│  ├ schemas
│  │  ├ request.py
│  │  └ response.py
│  │
│  └ core
│     ├ config.py
│     └ llm_client.py
│
├ docs
├ examples
├ tests
└ main.py
```

------------------------------------------------------------------------

# Day 1 --- 프로젝트 셋업 및 기본 아키텍처 ✅

> **상태: 완료**

## 목표

**프로젝트 스켈레톤과 기본 인프라** 구축.

## 완료된 작업

### 1. 프로젝트 리포지토리 생성

Git 리포지토리 초기화 및 기본 디렉토리 구조 생성 완료:

```
app/
├── __init__.py
├── api/
│   ├── app.py
│   └── agent/
│       ├── router.py
│       └── schemas.py
├── agent/
│   ├── orchestrator.py
│   ├── classifier.py
│   ├── prompt_builder.py
│   └── output_parser.py
├── core/
│   ├── config.py
│   └── llm_client.py
└── tools/
    ├── base.py
    └── template_tool.py
```

### 2. Python 프로젝트 초기화

- Python 3.11+
- uv 패키지 매니저 사용
- 의존성 설치: `fastapi`, `uvicorn`, `pydantic`, `httpx`

### 3. FastAPI 서버 생성

`app/api/app.py`에 앱 팩토리 패턴 구현:

- `create_app()` 팩토리 함수
- CORS 미들웨어 설정
- 커스텀 HTTP 미들웨어
- 유효성 검증 에러 핸들러
- 비동기 lifespan 컨텍스트 매니저

### 4. 기본 엔드포인트 생성

`app/api/agent/router.py`에 스텁 엔드포인트 구현:

``` python
@router.post("/agent/run")
async def run_agent(request: AgentRequest):
    return {"status": "ok"}
```

### Day 1 결과물

- `uvicorn main:app --reload`로 서버 실행 가능
- Swagger UI에서 `POST /agent/run` 확인 가능

------------------------------------------------------------------------

# Day 2 --- 에이전트 코어 설계

## 목표

**에이전트 워크플로우 컨트롤러** 구현.

------------------------------------------------------------------------

## 태스크 분류기 구현

파일: `app/agent/classifier.py`

태스크 유형 (프로젝트 제안서 Section 5 기반):

| 태스크 유형 | 설명 | 참조 |
|---|---|---|
| `api_design` | REST API 명세 작성 | Section 5.1 |
| `deployment_checklist` | 배포 체크리스트 생성 | Section 5.2 |
| `code_review` | 코드 리뷰 지원 | Section 5.3 |
| `error_analysis` | 에러 분석 및 진단 | Section 5.4 |

초기 구현은 **규칙 기반**(키워드 매칭)으로 시작한다.

구현 가이드:

``` python
from enum import Enum

class TaskType(str, Enum):
    API_DESIGN = "api_design"
    DEPLOYMENT_CHECKLIST = "deployment_checklist"
    CODE_REVIEW = "code_review"
    ERROR_ANALYSIS = "error_analysis"

def classify_task(user_input: str) -> TaskType:
    """
    사용자 입력을 분석하여 태스크 유형을 결정한다.

    키워드 기반 분류:
    - api, endpoint, 명세, 스키마 → api_design
    - 배포, deploy, checklist, 롤백 → deployment_checklist
    - 리뷰, review, 코드 → code_review
    - 에러, error, 버그, 의존성 → error_analysis
    """
    ...
```

------------------------------------------------------------------------

## 에이전트 오케스트레이터 구현

파일: `app/agent/orchestrator.py`

오케스트레이터는 에이전트 파이프라인의 각 단계를 조율한다.

구현 가이드:

``` python
from app.agent.classifier import classify_task, TaskType
from app.agent.prompt_builder import build_prompt
from app.agent.output_parser import parse_output

class AgentOrchestrator:

    async def run(self, request: AgentRequest) -> AgentResult:
        # 1. 태스크 분류
        task_type = classify_task(request.input)

        # 2. 태스크 유형에 따른 프롬프트 구성
        prompt = build_prompt(task_type, request.input)

        # 3. LLM 호출
        raw_output = await self.llm_client.generate(prompt)

        # 4. 구조화된 출력 파싱
        result = parse_output(raw_output, task_type)

        return result
```

각 함수(`classify_task`, `build_prompt`, `parse_output`)는 해당 모듈에서
구현한다. Day 2에서는 mock LLM 출력으로 파이프라인 전체 흐름이 동작하는지
검증한다.

------------------------------------------------------------------------

### Day 2 결과물

- 태스크 분류기가 4개 태스크 유형을 정확히 분류
- 오케스트레이터가 mock LLM 출력으로 전체 파이프라인 실행
- `POST /agent/run` 요청 시 분류 결과가 응답에 포함

------------------------------------------------------------------------

# Day 3 --- 구조화된 출력 시스템

## 목표

에이전트가 항상 **검증된 구조화된 JSON 응답**을 반환하도록 보장한다.

------------------------------------------------------------------------

## 응답 스키마 정의

파일: `app/schemas/response.py`

프로젝트 제안서의 성공 기준(Section 3)을 반영한 스키마:

``` python
class AgentResult(BaseModel):
    """에이전트 응답의 기본 구조.

    성공 기준:
    - 응답 100%가 Pydantic 스키마 검증 통과
    - 에이전트 출력이 실행 가능하고 도메인에 적합
    """

    task_type: str           # 분류된 태스크 유형
    summary: str             # 결과 요약
    assumptions: list[str]   # 에이전트가 가정한 사항
    result: dict             # 태스크별 구조화된 결과
    risks: list[str]         # 식별된 리스크
    confidence: float        # 출력 신뢰도 (0.0 ~ 1.0)
```

------------------------------------------------------------------------

## 출력 파서 구현

파일: `app/agent/output_parser.py`

책임:

- LLM 출력 파싱
- Pydantic 스키마 검증
- **검증 실패 시 피드백 루프** (재시도 또는 구조화된 에러 반환)

구현 가이드:

``` python
def parse_output(raw_text: str, task_type: str) -> AgentResult:
    """LLM 출력을 파싱하고 스키마를 검증한다.

    검증 실패 시:
    1. JSON 파싱 에러 → 수정 프롬프트로 재시도
    2. 스키마 검증 에러 → 누락 필드 명시 후 재시도
    3. 재시도 실패 → 구조화된 에러 응답 반환
    """
    try:
        data = json.loads(raw_text)
        return AgentResult(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        # 피드백 루프: 에러 정보를 포함한 수정 프롬프트 생성
        ...
```

------------------------------------------------------------------------

## 프롬프트 형식 업데이트

프롬프트에 엄격한 JSON 출력을 강제하는 지시문 포함:

```
반드시 JSON 형식으로만 응답하세요.
다음 필드를 반드시 포함하세요: task_type, summary, assumptions, result, risks, confidence
```

------------------------------------------------------------------------

### Day 3 결과물

- 에이전트가 검증된 구조화된 출력을 반환
- 스키마 검증 실패 시 피드백 루프가 동작 (재시도 또는 에러 응답)
- `confidence` 필드를 통해 출력 신뢰도 표시

------------------------------------------------------------------------

# Day 4 --- API 명세 기능

## 목표

**첫 번째 실제 기능** 구현: API 명세 작성.

------------------------------------------------------------------------

## API 설계 프롬프트 빌더 추가

파일: `app/agent/prompt_builder.py`

``` python
def build_api_prompt(user_input: str) -> str:
    return f'''
당신은 백엔드 아키텍트입니다.

REST API 명세를 생성하세요.

사용자 요청:
{user_input}

JSON 형식으로만 응답하세요.
다음 항목을 포함하세요:
- endpoint: 엔드포인트 경로 및 HTTP 메서드
- request_schema: 요청 스키마 (해당시)
- response_schema: 응답 스키마
- field_naming: 필드 네이밍 제안
- risks: 설계 리스크
'''
```

------------------------------------------------------------------------

## 입력 예시

```
모델을 프로바이더별로 그룹화하여 반환하는 API를 설계해줘.
```

------------------------------------------------------------------------

## 기대 출력

``` json
{
  "endpoint": "GET /api/v1/models",
  "response_schema": {
    "providers": [
      {
        "provider": "openai",
        "models": []
      }
    ]
  },
  "field_naming": ["snake_case 사용", "복수형 컬렉션명"],
  "risks": ["프로바이더 수 증가 시 페이지네이션 필요"]
}
```

------------------------------------------------------------------------

### Day 4 결과물

에이전트가 API 명세 초안을 생성할 수 있다.

------------------------------------------------------------------------

# Day 5 --- 도구 시스템

## 목표

**도구 기반 에이전트 아키텍처** 도입.

------------------------------------------------------------------------

## 도구 인터페이스

파일: `app/tools/base.py`

``` python
class Tool:
    name: str
    description: str

    async def run(self, input: dict) -> dict:
        """도구를 실행하고 결과를 반환한다."""
        raise NotImplementedError
```

------------------------------------------------------------------------

## API 템플릿 도구

파일: `app/tools/template_tool.py`

``` python
class ApiTemplateTool(Tool):
    name = "api_template"
    description = "표준 API 응답 형식 및 에러 포맷 템플릿 제공"

    async def run(self, input: dict) -> dict:
        return {
            "standard_error_format": {
                "error_code": "string",
                "message": "string",
                "details": "object | null"
            },
            "pagination_format": {
                "items": "list",
                "total": "int",
                "page": "int",
                "page_size": "int"
            }
        }
```

------------------------------------------------------------------------

## 에이전트 도구 사용 흐름

에이전트는 LLM 호출 전에 관련 도구를 통해 템플릿과 규칙을 조회할 수 있다.
이를 통해 LLM이 도메인 특화 컨텍스트를 기반으로 더 정확한 출력을 생성한다.

------------------------------------------------------------------------

### Day 5 결과물

에이전트가 하나의 도구를 호출하고 그 결과를 프롬프트에 반영할 수 있다.

------------------------------------------------------------------------

# Day 6-7 --- 로깅, 테스트 데이터셋, 데모 준비

## 목표

관측성(observability)과 재현성(reproducibility)을 확보하고, 데모를 준비한다.

------------------------------------------------------------------------

## 요청/응답 로깅

디렉토리: `logs/`

저장 항목:

- `request.json` — 사용자 요청 원본
- `response.json` — 에이전트 응답 원본

``` python
save_request(request)
save_response(response)
```

------------------------------------------------------------------------

## 예제 입력 생성

디렉토리: `examples/`

프로젝트 제안서의 4개 핵심 유스케이스에 맞춘 테스트 파일:

| 파일 | 태스크 유형 | 설명 |
|---|---|---|
| `api_design_1.txt` | `api_design` | API 명세 작성 요청 |
| `deployment_checklist_1.txt` | `deployment_checklist` | 배포 체크리스트 생성 요청 |
| `code_review_1.txt` | `code_review` | 코드 리뷰 요청 |
| `error_case_1.txt` | `error_analysis` | 에러 분석 요청 |

------------------------------------------------------------------------

## 데모 시나리오

프로젝트 제안서 Section 5의 4개 유스케이스를 기반으로 최소 4개 시나리오를
준비한다.

### 시나리오 1 --- API 명세 작성

```
모델을 프로바이더별로 그룹화하여 반환하는 API를 설계해줘.
```

### 시나리오 2 --- 배포 체크리스트 생성

```
서비스: user-auth-service
의존성: PostgreSQL, Redis, 외부 OAuth 프로바이더
유형: 최초 배포
```

### 시나리오 3 --- 코드 리뷰

```
이 엔드포인트를 일관성 및 모범 사례 관점에서 리뷰해줘:

@router.post("/users")
async def create_user(data: dict):
    user = db.execute(f"INSERT INTO users VALUES ('{data['name']}')")
    return {"id": user.id}
```

### 시나리오 4 --- 에러 분석

```
uv add faiss 의존성 해결 에러
```

------------------------------------------------------------------------

## 최종 확인

- API 엔드포인트 동작 확인
- 구조화된 출력 스키마 검증 확인
- 출력 검증 피드백 루프 동작 확인
- 도구 사용 확인
- 4개 유스케이스 데모 시나리오 실행

------------------------------------------------------------------------

# Week 1 완료 기준

프로젝트 제안서(Section 3)의 성공 기준과 정렬:

| 기준 | 목표 | Week 1 범위 |
|---|---|---|
| 유스케이스 커버리지 | 4개 핵심 유스케이스 완전 구현 | 최소 1개 완전 구현 + 나머지 스텁 |
| 출력 유효성 | 응답 100%가 Pydantic 스키마 검증 통과 | 출력 파서 및 검증 루프 구현 |
| 도구 통합 | 각 유스케이스가 최소 1개 도구 사용 | 최소 1개 도구 통합 완료 |
| 응답 품질 | 실행 가능하고 도메인에 적합한 출력 | API 명세 유스케이스로 검증 |
| 확장성 | 새 유스케이스 추가 시 3개 미만 파일 수정 | 확장 가능한 아키텍처 설계 확인 |

Week 1은 다음 조건 충족 시 성공으로 간주한다:

- 에이전트 워크플로우 (분류 → 프롬프트 → LLM → 출력 → 검증)가 구현됨
- FastAPI 엔드포인트가 동작함
- 구조화된 출력이 Pydantic 스키마로 검증됨
- 검증 실패 시 피드백 루프 (재시도 또는 에러 응답)가 동작함
- 하나의 도구가 통합됨
- API 명세 생성 기능이 동작함

------------------------------------------------------------------------

# 주의사항

Week 1에서는 과도한 엔지니어링을 피한다.

추가하지 않는 것:

- 벡터 데이터베이스
- 멀티 에이전트 오케스트레이션
- 복잡한 플래너
- LangGraph / 무거운 프레임워크

집중하는 것:

- 깔끔한 아키텍처
- 확장 가능한 설계
- 동작하는 MVP
