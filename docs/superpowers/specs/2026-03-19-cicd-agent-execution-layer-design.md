# CI/CD Agent Execution Layer Design

## 1. Overview

CI/CD 이미지 빌드 & 배포 파이프라인 에이전트의 실행 레이어 설계 문서이다. 자연어 요청을 받아 Git clone, Docker 빌드, 레지스트리 push, 서버 배포를 자동화하는 단일 에이전트를 구축한다.

### 핵심 설계 결정

- **Terminus 2를 사용하지 않는다.** tmux 기반 터미널 제어는 셸 출력 전체가 LLM 컨텍스트에 포함되어 자격증명이 노출될 위험이 있다.
- **Python SDK를 우선 사용하고, SDK가 지원하지 않는 작업만 subprocess로 폴백한다.** 이를 통해 자격증명이 LLM에 노출되는 경로 자체를 차단한다.
- **단일 에이전트 + 플랜 앤 실행 구조를 채택한다.** LLM이 계획을 1회 수립하고, 고정된 실행 엔진이 순차 실행한다. 실패 시에만 LLM이 재개입한다.

### 제약 조건

- 개발 기간: 4주, 하루 최대 2시간 (총 ~40-56시간)
- 실행 환경: 개발자 로컬 머신
- 레지스트리: ECR만 지원 (인터페이스는 추상화)
- 사이드 프로젝트 (AI Agent Platform Engineer 직무 전환 준비용)

---

## 2. Architecture

```
사용자 (CLI)
    |
    v
+--------------------------------------------------+
|                  Agent Core                       |
|                                                   |
|  +-------------+    +--------------+              |
|  |Intent Parser |-->|Plan Generator|              |
|  |   (LLM)     |    |    (LLM)    |              |
|  +-------------+    +------+-------+              |
|    (단일 LLM 호출로 통합)    |                      |
|                            v                      |
|                   +-----------------+             |
|                   |Execution Engine |             |
|                   | (순차 실행 루프)  |             |
|                   +--------+--------+             |
|                            |                      |
|              +-------------+-------------+        |
|              v             v             v        |
|         +--------+   +--------+   +--------+     |
|         | Tool A |   | Tool B |   | Tool C |     |
|         | (SDK)  |   | (SDK)  |   |(subproc)|    |
|         +----+---+   +----+---+   +----+---+     |
|              |             |             |        |
|              +-------------+-------------+        |
|                            v                      |
|              +----------------------+             |
|              |  Credential Store    |             |
|              | (환경변수 / .env)     |             |
|              | LLM 접근 불가 영역    |             |
|              +----------------------+             |
|                                                   |
|         실패 시: Recovery Advisor (LLM) 재개입      |
+--------------------------------------------------+
```

### 에이전트 루프

1. 사용자가 CLI로 자연어 요청 입력
2. `AgentCore.parse_and_plan()` — LLM이 Native Tool Calling으로 `ExecutionPlan` 생성 (1회 호출)
3. `ExecutionEngine.run(plan)` — 각 step을 순차 실행
   - 도구가 `CredentialStore`에서 자격증명을 직접 로드 (LLM 경유하지 않음)
   - 성공 시 결과 데이터를 다음 도구에 전달
   - 실패 시 `RecoveryAdvisor`가 sanitized 에러만 보고 복구 전략 제안
4. `PipelineResult` 반환 → CLI에 출력

### Terminus-KIRA와의 차이

| | Terminus-KIRA | 이 프로젝트 |
|--|--------------|-----------|
| LLM 호출 시점 | 매 에피소드마다 | 계획 1회 + 실패 시만 |
| 루프 구조 | LLM이 매번 다음 행동 결정 (리액티브) | LLM이 계획 수립, 엔진이 자동 실행 (플랜 앤 실행) |
| 도구 실행 | tmux에 셸 명령어 전송 | Python SDK 직접 호출 |
| 자격증명 | 터미널 출력에 포함될 수 있음 | LLM 컨텍스트에 진입 불가 |

---

## 3. Credential Isolation Model

### 계층 구조

```
+---------------------------------------------+
|            LLM 영역 (신뢰하지 않음)            |
|                                              |
|  - 사용자 요청 텍스트                          |
|  - 도구 이름 + 공개 파라미터 (repo, tag, branch)|
|  - ToolResult (성공/실패 + 요약 메시지)         |
+--------------------+------------------------+
                     | tool_call(name, public_params)
                     v
+---------------------------------------------+
|            도구 영역 (신뢰함)                   |
|                                              |
|  - CredentialStore에서 자격증명 직접 로드       |
|  - SDK 호출 (boto3, docker, paramiko)         |
|  - 에러 메시지에서 자격증명 패턴 제거 후 반환    |
+--------------------+------------------------+
                     | os.environ / .env
                     v
+---------------------------------------------+
|        Credential Store (환경변수)             |
|                                              |
|  AWS_ACCESS_KEY_ID=***                       |
|  AWS_SECRET_ACCESS_KEY=***                   |
|  DEPLOY_SSH_KEY_PATH=~/.ssh/id_rsa           |
|  DOCKER_HOST=unix:///var/run/docker.sock     |
+---------------------------------------------+
```

### CredentialStore

환경변수에서 자격증명을 로드한다. 필수 변수가 없으면 시작 시점에 즉시 실패한다 (fail-fast). Docker 소켓 기본값은 플랫폼에 따라 달라진다.

```python
class CredentialMissingError(Exception):
    """필수 자격증명 환경변수가 설정되지 않았을 때 발생"""
    pass

class CredentialStore:
    """환경변수에서 자격증명을 로드. LLM 컨텍스트에 노출되지 않음."""

    def _require_env(self, key: str) -> str:
        value = os.environ.get(key)
        if not value:
            raise CredentialMissingError(
                f"필수 환경변수 '{key}'가 설정되지 않았습니다. "
                f".env 파일 또는 환경변수를 확인하세요."
            )
        return value

    def get_aws_credentials(self) -> AWSCredentials:
        return AWSCredentials(
            access_key_id=self._require_env("AWS_ACCESS_KEY_ID"),
            secret_access_key=self._require_env("AWS_SECRET_ACCESS_KEY"),
            region=os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"),
        )

    def get_ssh_config(self) -> SSHConfig:
        return SSHConfig(
            key_path=self._require_env("DEPLOY_SSH_KEY_PATH"),
        )

    def get_docker_config(self) -> DockerConfig:
        default_host = (
            "npipe:////./pipe/docker_engine"
            if sys.platform == "win32"
            else "unix:///var/run/docker.sock"
        )
        return DockerConfig(
            host=os.environ.get("DOCKER_HOST", default_host),
        )

    def get_all_secret_values(self) -> list[str]:
        """OutputSanitizer에 전달할 모든 민감 값 목록"""
        secrets = []
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
            val = os.environ.get(key)
            if val:
                secrets.append(val)
        return secrets
```

### OutputSanitizer

2단계 세정 전략을 사용한다: (1) 실제 자격증명 값의 정확 매칭 (가장 확실), (2) 알려진 패턴 정규식 폴백. 모든 도구가 `ToolResult`를 반환하기 전에 sanitizer를 거친다. SDK 호출은 결과 요약만 반환하므로 세정이 거의 불필요하고, subprocess 폴백(DeployTool의 원격 명령 출력 포함)은 반드시 거친다.

```python
class OutputSanitizer:
    # 폴백 정규식 패턴
    PATTERNS = [
        r'AKIA[0-9A-Z]{16}',                        # AWS Access Key ID
        r'(?i)password[=:]\s*\S+',                   # password=xxx
        r'(?i)token[=:]\s*\S+',                      # token=xxx
        r'-----BEGIN .* KEY-----[\s\S]*?-----END .* KEY-----',  # SSH/PEM 키
    ]

    def __init__(self, credentials: CredentialStore):
        # 1단계: 실제 비밀 값을 정확 매칭으로 제거 (가장 확실)
        self._secret_values = credentials.get_all_secret_values()

    def sanitize(self, text: str) -> str:
        # 1단계: 실제 값 정확 매칭
        for secret in self._secret_values:
            text = text.replace(secret, '***REDACTED***')
        # 2단계: 정규식 패턴 폴백
        for pattern in self.PATTERNS:
            text = re.sub(pattern, '***REDACTED***', text)
        return text
```

**보안 참고:** `.env` 파일은 반드시 `.gitignore`에 포함하여 버전 관리에서 제외한다. `.env.example`만 커밋한다.

---

## 4. Tool Design

### 도구별 실행 전략

| 도구 | 실행 방식 | 라이브러리 | 이유 |
|------|----------|-----------|------|
| CloneTool | SDK | GitPython | clone/checkout이 API로 완결 |
| BuildTool | SDK | docker (Python SDK) | `client.images.build()`로 완전 제어 |
| RegistryAuthTool | SDK | boto3 | ECR 인증 토큰을 코드 내부에서 발급, LLM에 노출 없음 |
| PushTool | SDK | docker (Python SDK) | `client.images.push()`로 완결 |
| DeployTool | SDK + subprocess 폴백 | paramiko | SSH는 paramiko, 원격 `docker compose`는 exec_command() |

### BaseTool

도구 인터페이스는 동기(sync)로 정의한다. GitPython, paramiko 등 블로킹 라이브러리를 자연스럽게 사용하기 위함이며, 순차 실행 모델에서 async의 이점이 없다. ExecutionEngine이 필요시 `asyncio.to_thread()`로 래핑한다.

```python
class BaseTool(ABC):
    def __init__(self, credentials: CredentialStore, sanitizer: OutputSanitizer):
        self._credentials = credentials
        self._sanitizer = sanitizer

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        ...

    def _safe_result(self, success: bool, message: str, **data) -> ToolResult:
        return ToolResult(
            success=success,
            tool_name=self.__class__.__name__,
            message=self._sanitizer.sanitize(message),
            data=data,
        )
```

### 도구 간 데이터 전달

도구들은 순차 실행되며, 이전 도구의 `ToolResult.data`를 ExecutionEngine이 누적 관리하여 다음 도구에 전달한다.

```
CloneTool    -> {"clone_dir": "/tmp/build/my-app"}
BuildTool    -> {"image_id": "sha256:abc123"}
RegistryAuth -> {"auth_ready": true}
PushTool     -> {"pushed_image": "123456.dkr.ecr.../my-app:v1.0"}
```

---

## 5. Data Models

```python
# --- 공유 모델 (models/) ---

class BuildRequest(BaseModel):
    """CLI가 구조화된 입력을 받을 때 사용. LLM 프롬프트에 포맷팅하여 전달."""
    repo_url: str
    branch: str = "main"
    dockerfile_path: str = "Dockerfile"
    image_name: str
    image_tag: str
    registry: str                      # e.g. "ecr"
    deploy_target: str | None = None

class ErrorType(str, Enum):
    """RecoveryAdvisor가 복구 전략을 결정할 때 사용하는 에러 분류"""
    AUTH_FAILED = "auth_failed"
    NETWORK_ERROR = "network_error"
    BUILD_FAILED = "build_failed"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

class PlanStep(BaseModel):
    tool_name: str                     # "clone_repo", "build_image", ...
    params: dict[str, Any]             # 공개 파라미터만 (자격증명 없음)
    description: str
    confirm_required: bool = False

class ExecutionPlan(BaseModel):
    steps: list[PlanStep]

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

class RecoveryAdvice(BaseModel):
    action: Literal["retry", "skip", "abort"]
    reason: str
    modified_params: dict[str, Any] | None = None
```

---

## 6. Execution Engine

```python
MAX_RETRIES_PER_STEP = 2
MAX_TOTAL_RETRIES = 3

class ExecutionEngine:
    async def run(self, plan: ExecutionPlan) -> PipelineResult:
        context = {}
        completed = []
        total_retries = 0

        for step in plan.steps:
            if step.confirm_required:
                if not await self._confirm(step):
                    return PipelineResult(
                        success=False,
                        steps_completed=completed,
                        failed_step=ToolResult(
                            success=False, tool_name=step.tool_name,
                            message="사용자가 작업을 취소했습니다.",
                        ),
                    )

            tool = self._registry[step.tool_name]
            params = {**context, **step.params}  # plan params가 context보다 우선
            result = await asyncio.to_thread(tool.execute, params)

            if result.success:
                context.update(result.data)
                completed.append(result)
                continue

            # 실패 -> Recovery Advisor
            try:
                recovery = await self._recovery_advisor.advise(
                    failed_step=result,
                    completed_steps=completed,
                    remaining_steps=plan.steps[len(completed)+1:],
                )
            except Exception:
                # Recovery Advisor LLM 호출 자체가 실패하면 abort
                return PipelineResult(
                    success=False, steps_completed=completed, failed_step=result,
                )

            if recovery.action == "retry" and total_retries < MAX_TOTAL_RETRIES:
                retry_params = {**params, **(recovery.modified_params or {})}
                for attempt in range(MAX_RETRIES_PER_STEP):
                    total_retries += 1
                    result = await tool.execute(retry_params)
                    if result.success:
                        break
                if result.success:
                    context.update(result.data)
                    completed.append(result)
                    continue
                # 재시도 모두 실패 -> abort
                return PipelineResult(
                    success=False, steps_completed=completed, failed_step=result,
                )
            elif recovery.action == "skip":
                continue
            else:  # abort 또는 재시도 한도 초과
                return PipelineResult(
                    success=False, steps_completed=completed, failed_step=result,
                )

        return PipelineResult(success=True, steps_completed=completed)
```

---

## 7. LLM Integration

### 통합된 Intent Parser + Plan Generator

Intent Parser와 Plan Generator를 단일 LLM 호출로 통합한다. Native Tool Calling을 사용하여 구조화된 `ExecutionPlan`을 직접 생성한다.

```python
class AgentCore:
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "create_pipeline_plan",
                "description": "CI/CD 파이프라인 실행 계획을 생성합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "tool_name": {
                                        "type": "string",
                                        "enum": ["clone_repo", "build_image",
                                                 "auth_registry", "push_image",
                                                 "deploy"]
                                    },
                                    "params": {"type": "object"},
                                    "description": {"type": "string"},
                                    "confirm_required": {"type": "boolean"}
                                },
                                "required": ["tool_name", "params", "description"]
                            }
                        }
                    },
                    "required": ["steps"]
                }
            }
        }
    ]

    async def parse_and_plan(self, user_request: str) -> ExecutionPlan:
        response = await litellm.acompletion(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_request},
            ],
            tools=self.TOOLS,
        )
        # 방어적 접근: LLM이 tool_call 대신 텍스트를 반환할 수 있음
        message = response.choices[0].message
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            raise PlanGenerationError(
                f"LLM이 실행 계획을 생성하지 못했습니다: {message.content or '(empty)'}"
            )
        plan_data = json.loads(message.tool_calls[0].function.arguments)
        return ExecutionPlan(**plan_data)
```

### Recovery Advisor

실패한 도구의 sanitized 에러 메시지만 LLM에게 전달하여 복구 전략을 결정한다.

```python
class RecoveryAdvisor:
    async def advise(self, failed_step, completed_steps, remaining_steps) -> RecoveryAdvice:
        prompt = f"""
파이프라인 실행 중 오류가 발생했습니다.

완료된 단계: {[s.tool_name for s in completed_steps]}
실패한 단계: {failed_step.tool_name}
에러: {failed_step.message}
남은 단계: {[s.tool_name for s in remaining_steps]}

다음 중 하나를 선택하세요:
- retry: 재시도 (일시적 오류인 경우)
- skip: 건너뛰기 (선택적 단계인 경우)
- abort: 중단 (치명적 오류인 경우)
"""
        # LLM 호출 -> RecoveryAdvice 반환
```

---

## 8. Project Structure

```
cicd-agent/
├── cicd_agent/
│   ├── planning/                 # 계획 수립 도메인
│   │   ├── __init__.py
│   │   ├── agent.py              # AgentCore (parse_and_plan)
│   │   ├── recovery.py           # RecoveryAdvisor
│   │   └── prompts.py            # 시스템 프롬프트 관리
│   ├── execution/                # 실행 도메인
│   │   ├── __init__.py
│   │   ├── engine.py             # ExecutionEngine
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── base.py           # BaseTool ABC
│   │       ├── clone.py          # CloneTool (GitPython)
│   │       ├── build.py          # BuildTool (docker SDK)
│   │       ├── registry_auth.py  # RegistryAuthTool (boto3)
│   │       ├── push.py           # PushTool (docker SDK)
│   │       └── deploy.py         # DeployTool (paramiko) - Week 4 선택
│   ├── models/                   # 공유 데이터 모델
│   │   ├── __init__.py
│   │   ├── request.py            # BuildRequest
│   │   ├── plan.py               # ExecutionPlan, PlanStep
│   │   ├── result.py             # ToolResult, PipelineResult
│   │   └── recovery.py           # RecoveryAdvice
│   ├── infra/                    # 횡단 관심사
│   │   ├── __init__.py
│   │   ├── credentials.py        # CredentialStore
│   │   └── sanitizer.py          # OutputSanitizer
│   └── cli.py                    # Typer CLI
├── tests/
│   ├── test_planning/
│   ├── test_execution/
│   └── test_infra/
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

### 의존 방향

```
planning/  --> models/
execution/ --> models/
planning/  --> infra/
execution/ --> infra/
planning/  -x-> execution/   (서로 의존하지 않음)
execution/ -x-> planning/    (서로 의존하지 않음)
```

---

## 9. Dependencies

```toml
[project]
name = "cicd-agent"
requires-python = ">=3.12"
dependencies = [
    "litellm",
    "pydantic>=2.0",
    "typer[all]",
    "gitpython",
    "docker",
    "boto3",
    "python-dotenv",
]

[dependency-groups]
dev = [
    "ruff",
    "pytest",
    "pytest-asyncio",
]
```

---

## 10. Testing Strategy

### 단위 테스트

- **도구 테스트**: 각 Tool의 `execute()`를 mock된 SDK 클라이언트로 테스트. 실제 Docker 데몬이나 AWS 계정 불필요.
- **LLM 테스트**: `litellm.acompletion()`을 mock하여 고정된 tool_call 응답을 반환. LLM 호출 없이 AgentCore와 RecoveryAdvisor 로직 검증.
- **sanitizer 테스트**: 알려진 자격증명 값과 패턴이 출력에서 제거되는지 검증.

### 자격증명 격리 검증 테스트

프로젝트의 핵심 보안 속성을 자동화된 테스트로 검증한다:

```python
def test_llm_context_never_contains_credentials():
    """LLM에 전달되는 모든 메시지에 자격증명이 포함되지 않음을 검증"""
    captured_messages = []
    original_acompletion = litellm.acompletion

    async def mock_acompletion(**kwargs):
        captured_messages.append(kwargs["messages"])
        return mock_tool_call_response(...)

    # 파이프라인 실행 후
    for messages in captured_messages:
        for msg in messages:
            content = str(msg.get("content", ""))
            assert "AKIA" not in content
            assert os.environ["AWS_SECRET_ACCESS_KEY"] not in content
```

### 통합 테스트

- E2E 테스트는 로컬 Docker 데몬 필요 (CI에서는 skip 가능)
- AWS 통합 테스트는 실제 ECR 계정 필요 (수동 실행, CI에서는 mock)

---

## 11. 4-Week Schedule

```
Week 1: 기반 + 도구 1개
  - 프로젝트 셋업 (uv, ruff, 디렉토리)
  - models/ (Pydantic 전체 모델)
  - infra/ (credentials.py, sanitizer.py)
  - execution/tools/base.py (BaseTool ABC)
  - execution/tools/clone.py (GitPython) + 단위 테스트

Week 2: 도구 3개 + 에이전트 코어
  - execution/tools/build.py (docker SDK)
  - execution/tools/registry_auth.py (boto3, ECR)
  - execution/tools/push.py (docker SDK)
  - planning/agent.py (AgentCore - parse_and_plan)
  - planning/prompts.py (시스템 프롬프트)

Week 3: 엔진 + 복구 + CLI
  - execution/engine.py (ExecutionEngine)
  - planning/recovery.py (RecoveryAdvisor)
  - cli.py (Typer CLI)
  - E2E 테스트 (clone -> build -> push)
  - 자격증명 격리 검증 테스트

Week 4: 택 1
  옵션 A: MCP 서버 변환 (AI Agent Platform Engineer 면접 최고 임팩트)
    - execution/tools/를 MCP 도구로 변환
    - create_sdk_mcp_server()로 패키징
    - Claude Code에서 연동 테스트
  옵션 B: execution/tools/deploy.py + FastAPI
```

---

## 12. Success Criteria

| 기준 | 목표 |
|------|------|
| 핵심 도구 구현 | 4개 Tool (Clone, Build, RegistryAuth, Push) 동작 |
| 파이프라인 완주 | clone -> build -> push 기본 시나리오 성공 |
| 자격증명 격리 | 자동화 테스트로 LLM 메시지에 자격증명 미포함을 검증 |
| 실패 복구 | RecoveryAdvisor가 재시도 가능 에러를 자동 복구 |
| 출력 유효성 | 모든 응답이 Pydantic 스키마 검증 통과 |
| 플랜 앤 실행 분리 | LLM 계획 + 고정 실행 엔진이 올바르게 분리 |
