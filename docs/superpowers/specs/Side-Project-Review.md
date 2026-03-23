# 사이드 프로젝트 제안서 평가 및 아키텍처 분석

> CI/CD 이미지 빌드 & 배포 파이프라인 에이전트 제안서에 대한 평가와, AI Agent Platform Engineer 직무 전환을 위한 아키텍처 선택 가이드입니다.

---

## 목차

1. [제안서 종합 평가](#1-제안서-종합-평가)
2. [현실적 시간 분석](#2-현실적-시간-분석)
3. [단일 에이전트 vs 멀티 에이전트 분석](#3-단일-에이전트-vs-멀티-에이전트-분석)
4. [권장 아키텍처와 스코프 조정안](#4-권장-아키텍처와-스코프-조정안)
5. [참고 레포지토리 추천](#5-참고-레포지토리-추천)
6. [이직 준비 관점의 조언](#6-이직-준비-관점의-조언)

---

## 1. 제안서 종합 평가

### 1.1 잘한 점

| 항목 | 평가 |
|------|------|
| **문제 정의** | CI/CD 파이프라인은 반복적이고 에러가 잦은 실제 문제. 에이전트 적용에 적합한 도메인 선택 |
| **하이브리드 아키텍처** | LLM(계획 수립) + 고정 실행 엔진(안정성) 분리는 프로덕션 수준의 설계 판단. KIRA의 Terminus-KIRA가 정확히 이 패턴 |
| **스코프 관리** | 비목표(Non-Goals)가 명확하여 "무엇을 안 하는지"가 분명함 |
| **인터페이스 로드맵** | Core → CLI → API → MCP 단계적 확장은 좋은 전략 |
| **기술 스택** | litellm(멀티 LLM), Pydantic v2(검증), uv(모던 의존성 관리) 모두 현업에서 선호하는 선택 |
| **학습 목표** | 면접에서 설명 가능한 키워드들이 잘 정리됨 (오케스트레이션, 도구 기반 추론, 하이브리드 아키텍처) |

### 1.2 우려 사항

| 항목 | 문제 | 위험도 |
|------|------|--------|
| **시간** | 4주 × 2시간 = 최대 56시간. 인터페이스 4단계 전부는 비현실적 | 높음 |
| **멀티 레지스트리** | ECR/GCR/ACR 3개 동시 지원은 인증 로직만 3배 | 중간 |
| **이미지 Wrapping** | 니치한 기능. 학습/포트폴리오 가치 대비 구현 비용이 큼 | 중간 |
| **SSH 배포** | 네트워킹/보안 이슈. 로컬 개발 환경에서 테스트가 어려움 | 중간 |
| **테스트 전략 부재** | 성공 기준은 있지만, 어떻게 검증할지 구체적 계획이 없음 | 낮음 |
| **참조 문서 미작성** | architecture.md, specs 문서가 아직 존재하지 않음 | 낮음 |

### 1.3 KIRA 프로젝트와의 유사성

제안서의 아키텍처는 실제로 **Terminus-KIRA의 패턴과 매우 유사**합니다:

```
제안서의 구조:
  자연어 → Intent Parser(LLM) → Plan Generator(LLM) → Execution Engine → Recovery Advisor(LLM)

Terminus-KIRA의 구조:
  작업 지시 → LLM(analysis+plan) → execute_commands(터미널) → LLM(다음 판단)
```

차이점은 Terminus-KIRA가 모든 단계를 하나의 LLM 루프에서 처리하는 반면, 제안서는 Intent Parser / Plan Generator / Recovery Advisor를 명시적으로 분리했다는 것입니다. 이 분리는 좋은 설계이지만, 시간 제약을 고려하면 **처음에는 하나로 합쳐도 됩니다**.

---

## 2. 현실적 시간 분석

### 2.1 가용 시간

```
4주 × 5일(평일) × 2시간 = 40시간 (현실적 추정)
4주 × 7일(주말 포함) × 2시간 = 56시간 (최대)
```

### 2.2 각 단계별 예상 소요 시간

| 단계 | 내용 | 예상 시간 |
|------|------|----------|
| 프로젝트 셋업 | 레포 생성, 의존성, 구조 설계 | 3시간 |
| 데이터 모델 | Pydantic 모델 (BuildRequest, ExecutionPlan 등) | 3시간 |
| Intent Parser | LLM으로 자연어 → BuildRequest 변환 | 4시간 |
| Plan Generator | BuildRequest → ExecutionPlan 생성 | 4시간 |
| CloneTool | Git clone + checkout 구현 | 3시간 |
| BuildTool | Docker SDK로 이미지 빌드 | 5시간 |
| RegistryAuthTool | ECR 인증 (1개만) | 3시간 |
| PushTool | 이미지 push | 3시간 |
| Execution Engine | 계획 순차 실행 + 에러 처리 | 5시간 |
| Recovery Advisor | 실패 시 LLM 재개입 | 4시간 |
| CLI (Typer) | 커맨드라인 인터페이스 | 3시간 |
| **소계 (핵심)** | | **40시간** |
| WrapTool | 이미지 wrapping | 4시간 |
| DeployTool | SSH + Docker Compose | 5시간 |
| API (FastAPI) | REST API | 4시간 |
| MCP 서버 | Model Context Protocol | 5시간 |
| 테스트/문서 | 테스트 작성, README | 4시간 |
| **소계 (확장)** | | **22시간** |
| **총합** | | **62시간** |

### 2.3 결론

**56시간으로 62시간 분량을 전부 하는 것은 불가능합니다.**

핵심(40시간)만 해도 가용 시간을 거의 다 소진합니다. 따라서 **스코프 축소가 필수**입니다.

---

## 3. 단일 에이전트 vs 멀티 에이전트 분석

### 3.1 이 프로젝트에 적합한 것은?

**결론: 단일 에이전트가 압도적으로 적합합니다.**

이유:

| 판단 기준 | 분석 |
|----------|------|
| **파이프라인 특성** | clone → build → push → deploy는 본질적으로 **순차적**. 병렬 처리할 단계가 없음 |
| **도구 수** | 6개는 단일 에이전트가 충분히 관리 가능한 수준. KIRA-Slack이 멀티로 간 이유는 도구가 50개+이기 때문 |
| **비용 최적화 필요성** | 벤치마크처럼 비용이 중요하지 않음. 1회 실행 에이전트이므로 모델 계층화 불필요 |
| **시간 제약** | 멀티 에이전트의 라우팅/큐/상태 전달 구현에만 추가 20시간+ 소요 |
| **복잡도** | 멀티로 가면 디버깅이 급격히 어려워짐. 포트폴리오에서 "동작하지 않는 복잡한 시스템"은 역효과 |

### 3.2 KIRA에서 배우는 아키텍처 선택 기준

```
"언제 단일?"
  ✓ 작업이 순차적 파이프라인
  ✓ 도구가 10개 이하
  ✓ 하나의 도메인 (CI/CD)
  ✓ 비용 최적화 불필요
  ✓ 시간/리소스 제한
  → Terminus-KIRA 패턴

"언제 멀티?"
  ✓ 입력이 다양하고 분류가 필요 (간단한 인사 vs 복잡한 리서치)
  ✓ 도구가 30개+
  ✓ 다중 도메인 (Slack + Email + Jira + 번역 + ...)
  ✓ 24/7 상시 운영으로 비용 중요
  ✓ 응답 속도가 UX에 직결
  → KIRA-Slack 패턴
```

### 3.3 그러나 면접에서 멀티 에이전트를 설명할 수 있어야 한다

단일로 구현하되, **문서와 면접에서 멀티로 확장하는 방법을 설명**할 수 있으면 됩니다.

```
면접 예상 질문: "이 시스템을 멀티 에이전트로 확장한다면 어떻게 하겠습니까?"

답변 예시:
"현재는 순차 파이프라인이라 단일 에이전트가 최적입니다.
하지만 여러 팀이 동시에 빌드 요청을 보내는 상황이라면,

1) Coordinator Agent: 요청 분류 + 우선순위 결정
2) Builder Agent: 빌드 전문 (Docker SDK)
3) Deployer Agent: 배포 전문 (SSH + Docker Compose)
4) Monitor Agent: 배포 후 상태 감시

로 분리하고, 메시지 큐(asyncio.Queue)로 연결하겠습니다.
KIRA-Slack의 3-Tier 큐 시스템(채널 큐 → 오케스트레이터 큐 → 메모리 큐)이
좋은 참고 패턴입니다."
```

---

## 4. 권장 아키텍처와 스코프 조정안

### 4.1 4주 안에 끝낼 수 있는 스코프

```
[필수 - Week 1~3] Core + CLI
  ✓ 데이터 모델 (Pydantic)
  ✓ Intent Parser (LLM → BuildRequest)
  ✓ Plan Generator (BuildRequest → ExecutionPlan)
  ✓ CloneTool, BuildTool, RegistryAuthTool(ECR만), PushTool
  ✓ Execution Engine (순차 실행 + 에러 처리)
  ✓ Recovery Advisor (실패 시 LLM 재개입)
  ✓ Typer CLI

[선택 - Week 4] 둘 중 하나
  옵션 A: MCP 서버 (AI Agent Platform Engineer에 가장 임팩트)
  옵션 B: DeployTool + FastAPI (DevOps 경험 어필)
```

### 4.2 제거/축소 권장 항목

| 항목 | 권장 | 이유 |
|------|------|------|
| **WrapTool** | 제거 | 니치한 기능. 면접에서 설명할 가치 낮음 |
| **GCR/ACR 인증** | 축소 → ECR만 | 인터페이스만 추상화하고, 구현은 ECR 하나만 |
| **DeployTool** | Week 4 선택 | SSH 복잡도가 높고 로컬 테스트 어려움 |
| **FastAPI** | Week 4 선택 | CLI만으로도 데모 충분 |

### 4.3 권장 아키텍처 (Terminus-KIRA 패턴 기반)

```python
# 제안하는 핵심 구조 (단일 에이전트 + 도구 기반)

# 1) 도구 정의 — Terminus-KIRA의 TOOLS 패턴
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "clone_repo",
            "description": "Git 레포지토리를 클론하고 브랜치를 체크아웃합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string"},
                    "branch": {"type": "string"},
                    "target_dir": {"type": "string"}
                },
                "required": ["repo_url"]
            }
        }
    },
    # build_image, auth_registry, push_image ...
]

# 2) 에이전트 루프 — Terminus-KIRA의 _run_agent_loop 패턴
async def agent_loop(user_request: str):
    plan = await call_llm(user_request, tools=TOOLS)  # LLM이 계획 + 도구 호출 결정

    for tool_call in plan.tool_calls:
        result = await execute_tool(tool_call)         # 도구 실행
        if result.failed:
            recovery = await call_llm(                 # 실패 시 LLM 재개입
                f"Tool {tool_call.name} failed: {result.error}",
                tools=TOOLS
            )
            # retry or abort

    return PipelineResult(...)
```

### 4.4 Week 4에 MCP를 선택하는 경우의 구조

```python
# MCP 서버로 변환 — KIRA-Slack의 @tool 데코레이터 패턴
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("clone_repo", "Git 레포를 클론합니다", {
    "type": "object",
    "properties": {
        "repo_url": {"type": "string"},
        "branch": {"type": "string"}
    },
    "required": ["repo_url"]
})
async def clone_repo(args):
    # 기존 CloneTool 로직 재사용
    result = await git_clone(args["repo_url"], args.get("branch"))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

# MCP 서버 생성
cicd_tools = [clone_repo, build_image, auth_registry, push_image]
def create_cicd_mcp_server():
    return create_sdk_mcp_server(name="cicd-pipeline", version="1.0.0", tools=cicd_tools)
```

이렇게 하면 **Claude Code나 다른 MCP 호환 에이전트에서 바로 사용 가능한 도구 서버**가 됩니다. AI Agent Platform Engineer 면접에서 가장 임팩트 있는 결과물입니다.

### 4.5 주차별 계획 제안

```
Week 1 (10시간): 기반 구축
  ├─ 프로젝트 셋업 (레포, uv, ruff, 디렉토리 구조)
  ├─ Pydantic 데이터 모델 (BuildRequest, ExecutionPlan, ToolResult 등)
  ├─ CloneTool 구현 + 단위 테스트
  └─ BuildTool 구현 (Docker SDK)

Week 2 (10시간): 파이프라인 완성
  ├─ RegistryAuthTool (ECR) + PushTool
  ├─ Intent Parser (litellm + TOOLS)
  ├─ Plan Generator (LLM → ExecutionPlan)
  └─ 기본 에이전트 루프 (순차 실행)

Week 3 (10시간): 복구 + CLI
  ├─ Recovery Advisor (실패 시 LLM 재개입)
  ├─ Execution Engine 에러 처리 고도화
  ├─ Typer CLI 구현
  └─ E2E 테스트 (clone → build → push 시나리오)

Week 4 (10시간): MCP 또는 Deploy
  ├─ 옵션 A: MCP 서버 변환 + Claude Code에서 테스트
  └─ 옵션 B: DeployTool + FastAPI
  ├─ README 작성
  └─ 포트폴리오 정리
```

---

## 5. 참고 레포지토리 추천

### 5.1 에이전트 아키텍처 학습 (가장 추천)

| 레포 | 핵심 학습 포인트 | 링크 |
|------|-----------------|------|
| **anthropics/claude-agent-sdk-python** | @tool 데코레이터, MCP 서버 생성, 에이전트 루프 자동화. KIRA-Slack이 사용하는 핵심 SDK | [GitHub](https://github.com/anthropics/claude-agent-sdk-python) |
| **anthropics/claude-agent-sdk-demos** | Claude Agent SDK 데모 모음. 커스텀 도구 → MCP 서버 변환의 실제 예시 | [GitHub](https://github.com/anthropics/claude-agent-sdk-demos) |
| **google/adk-python** | Google Agent Development Kit. 멀티 에이전트 오케스트레이션, MCP 호환, 모델 비종속적 설계. 면접에서 "여러 프레임워크를 비교 분석했다"고 말할 수 있음 | [GitHub](https://github.com/google/adk-python) |

### 5.2 도구 기반 에이전트 설계 참고

| 레포 | 핵심 학습 포인트 | 링크 |
|------|-----------------|------|
| **block/goose** | MCP 기반 범용 AI 에이전트. 다양한 LLM 지원 + 확장 가능한 도구 시스템. Terminus-KIRA처럼 단일 에이전트 + 다중 도구 패턴 | [GitHub](https://github.com/block/goose) |
| **google/adk-samples** | ADK 기반 샘플 에이전트 모음. 고객 서비스, 데이터 엔지니어링 등 다양한 도메인 | [GitHub](https://github.com/google/adk-samples) |

### 5.3 DevOps AI 에이전트 참고

| 레포 | 핵심 학습 포인트 | 링크 |
|------|-----------------|------|
| **ruvnet/ruflo** | Claude 기반 멀티 에이전트 오케스트레이션 플랫폼. CI/CD 연동, 스웜 지능 | [GitHub](https://github.com/ruvnet/ruflo) |

### 5.4 KIRA 자체가 최고의 참고서

이미 분석한 KIRA 코드를 적극 활용하세요:

| 참고 대상 | 활용 포인트 |
|----------|------------|
| Terminus-KIRA의 `TOOLS` 정의 | 도구 JSON Schema 설계 패턴 |
| Terminus-KIRA의 `_run_agent_loop` | 에이전트 루프 + 에러 복구 패턴 |
| Terminus-KIRA의 `_parse_tool_calls` | LLM 응답 → 실행 명령 변환 |
| KIRA-Slack의 `@tool` 데코레이터 | MCP 서버 변환 패턴 (Week 4) |
| KIRA-Slack의 `build_tool_usage_rules` | 시스템 프롬프트에 도구 사용 규칙 주입 |

---

## 6. 이직 준비 관점의 조언

### 6.1 AI Agent Platform Engineer가 보여줘야 하는 역량

| 역량 | 이 프로젝트에서 증명하는 방법 |
|------|---------------------------|
| **에이전트 루프 설계** | LLM → 도구 호출 → 결과 관찰 → 다음 행동 사이클 직접 구현 |
| **도구(Tool) 정의** | JSON Schema 기반 도구 정의 + Pydantic 검증 |
| **LLM 통합** | litellm으로 멀티 LLM 지원 (Claude, GPT, Gemini 스위칭) |
| **MCP 이해** | Week 4에 MCP 서버 변환으로 프로토콜 표준 이해 증명 |
| **에러 복구** | Recovery Advisor 패턴으로 프로덕션 수준의 복원력 |
| **하이브리드 아키텍처** | LLM(유연성) + 고정 엔진(안정성) 분리 설계 |

### 6.2 면접에서 이 프로젝트를 설명하는 프레임

```
"CI/CD 파이프라인 자동화를 위한 도구 기반 AI 에이전트를 설계·구현했습니다.

[아키텍처]
자연어 요청을 LLM이 해석하여 실행 계획을 수립하고,
도구 기반 실행 엔진이 순차적으로 파이프라인을 수행합니다.
실패 시 LLM이 복구 전략을 제안하는 하이브리드 구조입니다.

[기술적 결정]
- 단일 에이전트를 선택한 이유: 순차적 파이프라인에서 멀티 에이전트는 오버엔지니어링
- litellm을 선택한 이유: 모델 비종속적 설계로 벤더 종속 방지
- MCP 서버로 변환한 이유: 표준 프로토콜 호환으로 다른 에이전트에서 재사용 가능

[KIRA 오픈소스 분석]
Terminus-KIRA(단일 에이전트)와 KIRA-Slack(멀티 에이전트)을 코드 수준에서 분석하여
단일 vs 멀티 아키텍처의 트레이드오프를 이해하고, 프로젝트에 적용했습니다.

[확장 방향]
멀티 에이전트로 확장한다면 Coordinator-Builder-Deployer-Monitor 구조로 분리하고,
비동기 큐로 연결하겠습니다."
```

### 6.3 프로젝트 제목 제안

현재 제목 "CI/CD 이미지 빌드 & 배포 파이프라인 에이전트"도 좋지만, 레포 이름으로는 좀 더 임팩트 있는 이름을 추천합니다:

- `pipeline-agent` — 간결하고 명확
- `cicd-agent` — 도메인이 즉시 드러남
- `forge` — "단조하다"의 의미. 코드를 이미지로 단조(forge)하는 에이전트

### 6.4 최종 정리

```
현재 제안서:    6개 도구 + 4단계 인터페이스 + 멀티 레지스트리
권장 조정안:    4개 도구 + Core/CLI + ECR만 + (Week 4에 MCP)

감점 요인 없음: 스코프를 줄인 것이 아니라 "의도적으로 집중"한 것
가점 요인:     MCP 서버 변환은 AI Agent Platform Engineer 면접에서 차별화 포인트
```

Sources:
- [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)
- [anthropics/claude-agent-sdk-demos](https://github.com/anthropics/claude-agent-sdk-demos)
- [google/adk-python](https://github.com/google/adk-python)
- [google/adk-samples](https://github.com/google/adk-samples)
- [block/goose](https://github.com/block/goose)
- [ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Agent SDK Overview - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
