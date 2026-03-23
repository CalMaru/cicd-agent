# CI/CD 파이프라인 에이전트 — 아키텍처

이 문서는 실행 레이어 설계 문서의 아키텍처를 요약한다.
상세 설계는 [실행 레이어 설계 문서](superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md)를 참조한다.

---

# 1. 전체 아키텍처

플랜 앤 실행 구조: LLM이 Native Tool Calling으로 실행 계획을 1회 수립하고, 고정된 실행 엔진이 순차 실행한다. 실패 시에만 RecoveryAdvisor(LLM)가 재개입한다.

```
사용자 (CLI)
    │
    ▼
┌──────────────────────────────────────────────────┐
│                  Agent Core                       │
│                                                   │
│  AgentCore.parse_and_plan()                       │
│  - LLM 1회 호출 (Native Tool Calling)              │
│  - Intent Parser + Plan Generator 통합             │
│  → ExecutionPlan 생성                              │
│                                                   │
│  ExecutionEngine.run(plan)                         │
│  - 각 step 순차 실행                                │
│  - 도구가 CredentialStore에서 자격증명 직접 로드       │
│  - 성공: 결과 데이터를 다음 도구에 전달               │
│  - 실패: RecoveryAdvisor가 sanitized 에러만 보고     │
│           복구 전략 제안                             │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ Tools (SDK 우선)                             │  │
│  │  CloneTool (GitPython)                       │  │
│  │  BuildTool (docker SDK)                      │  │
│  │  RegistryAuthTool (boto3)                    │  │
│  │  PushTool (docker SDK)                       │  │
│  │  DeployTool (paramiko) — Week 4 선택          │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ Credential Store (환경변수 / .env)            │  │
│  │ LLM 접근 불가 영역                            │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Terminus-KIRA와의 차이

| | Terminus-KIRA | 이 프로젝트 |
|--|--------------|-----------|
| LLM 호출 시점 | 매 에피소드마다 | 계획 1회 + 실패 시만 |
| 루프 구조 | LLM이 매번 다음 행동 결정 (리액티브) | LLM이 계획 수립, 엔진이 자동 실행 (플랜 앤 실행) |
| 도구 실행 | tmux에 셸 명령어 전송 | Python SDK 직접 호출 |
| 자격증명 | 터미널 출력에 포함될 수 있음 | LLM 컨텍스트에 진입 불가 |

---

# 2. 핵심 컴포넌트

## 2.1 AgentCore (Intent Parser + Plan Generator 통합)

단일 LLM 호출로 자연어 요청에서 `ExecutionPlan`을 직접 생성한다.

- Native Tool Calling 사용 (`create_pipeline_plan` function)
- LLM이 tool_call 대신 텍스트를 반환하면 `PlanGenerationError` 발생
- 출력: `ExecutionPlan`

## 2.2 Execution Engine

Plan의 각 step을 순서대로 실행하는 고정 엔진.

- `context: dict`를 유지하며 각 step의 `ToolResult.data`를 누적
- 이전 도구의 출력을 다음 도구 파라미터에 병합 (`{**context, **step.params}`)
- step 실행 전 `confirm_required` 확인
- 실패 시 RecoveryAdvisor 호출
- step당 최대 2회 재시도, 전체 최대 3회 재시도

## 2.3 Recovery Advisor (LLM)

실패한 도구의 sanitized 에러 메시지만 LLM에게 전달하여 복구 전략 결정.

- `retry`: 일시적 오류 → 재시도 (modified_params 가능)
- `skip`: 선택적 단계 → 건너뛰기
- `abort`: 치명적 오류 → 중단

---

# 3. Credential Isolation Model

### 계층 구조

```
LLM 영역 (신뢰하지 않음)              도구 영역 (신뢰함)
───────────────────────         ───────────────────────
· 사용자 요청 텍스트                · CredentialStore에서 자격증명 직접 로드
· 도구 이름 + 공개 파라미터          · SDK 호출 (boto3, docker, paramiko)
· ToolResult (sanitized)          · 에러 메시지에서 자격증명 패턴 제거 후 반환
         │                                    │
         │ tool_call(name, public_params)      │ os.environ / .env
         ▼                                    ▼
                              Credential Store (환경변수)
```

- **CredentialStore**: 환경변수에서 자격증명 로드. 필수 변수 없으면 fail-fast.
- **OutputSanitizer**: 2단계 세정 (실제 값 정확 매칭 + 정규식 패턴 폴백). 모든 도구가 ToolResult 반환 전에 sanitizer를 거침.

---

# 4. 데이터 모델

## BuildRequest — CLI 입력

```python
class BuildRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    dockerfile_path: str = "Dockerfile"
    image_name: str
    image_tag: str
    registry: str                      # e.g. "ecr"
    deploy_target: str | None = None
```

## ExecutionPlan — AgentCore 출력

```python
class PlanStep(BaseModel):
    tool_name: str          # "clone_repo", "build_image", ...
    params: dict[str, Any]  # 공개 파라미터만 (자격증명 없음)
    description: str
    confirm_required: bool = False

class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
```

## ToolResult — Tool 실행 결과

```python
class ToolResult(BaseModel):
    success: bool
    tool_name: str
    message: str                       # sanitized
    data: dict[str, Any] = {}
    error_type: ErrorType | None = None

class PipelineResult(BaseModel):
    success: bool
    steps_completed: list[ToolResult]
    failed_step: ToolResult | None = None
```

## RecoveryAdvice — RecoveryAdvisor 출력

```python
class RecoveryAdvice(BaseModel):
    action: Literal["retry", "skip", "abort"]
    reason: str
    modified_params: dict[str, Any] | None = None
```

---

# 5. 도구 시스템

## 실행 전략

| 도구 | 실행 방식 | 라이브러리 | 이유 |
|------|----------|-----------|------|
| CloneTool | SDK | GitPython | clone/checkout이 API로 완결 |
| BuildTool | SDK | docker SDK | `client.images.build()`로 완전 제어 |
| RegistryAuthTool | SDK | boto3 | ECR 인증 토큰을 코드 내부에서 발급 |
| PushTool | SDK | docker SDK | `client.images.push()`로 완결 |
| DeployTool | SDK+subprocess | paramiko | SSH + 원격 docker compose |

## BaseTool

도구 인터페이스는 동기(sync). ExecutionEngine이 필요시 `asyncio.to_thread()`로 래핑.

```python
class BaseTool(ABC):
    def __init__(self, credentials: CredentialStore, sanitizer: OutputSanitizer):
        ...
    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        ...
```

## 도구 간 데이터 전달

```
CloneTool    → {"clone_dir": "/tmp/build/my-app"}
BuildTool    → {"image_id": "sha256:abc123"}
RegistryAuth → {"auth_ready": true}
PushTool     → {"pushed_image": "123456.dkr.ecr.../my-app:v1.0"}
```

---

# 6. 프로젝트 구조

```
cicd-agent/
├── cicd_agent/
│   ├── planning/           # AgentCore, RecoveryAdvisor, 프롬프트
│   ├── execution/          # ExecutionEngine + Tools
│   ├── models/             # Pydantic 데이터 모델
│   ├── infra/              # CredentialStore, OutputSanitizer
│   └── cli.py              # Typer CLI
├── tests/
│   ├── test_planning/
│   ├── test_execution/
│   └── test_infra/
├── pyproject.toml
├── .env.example
└── .gitignore
```

### 의존 방향

```
planning/  → models/, infra/
execution/ → models/, infra/
planning/  ✗ execution/   (서로 의존하지 않음)
```

---

# 7. 인증 방식

환경변수에서 credential을 로드한다. ECR만 지원하며, 인터페이스는 추상화하여 향후 확장 가능.

| 항목 | 환경변수 |
|------|---------|
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` |
| SSH | `DEPLOY_SSH_KEY_PATH` |
| Docker | `DOCKER_HOST` (기본값: unix 소켓) |

---

# 8. 향후 확장

- **MCP 서버 변환**: execution/tools/를 MCP 도구로 변환 (Week 4 옵션 A)
- **FastAPI**: REST API 인터페이스 (Week 4 옵션 B)
- **프라이빗 레지스트리 지원**: Harbor, Nexus 등
- **시크릿 매니저 연동**: Vault, AWS Secrets Manager
