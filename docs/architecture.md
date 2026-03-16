# CI/CD 이미지 빌드 & 배포 파이프라인 에이전트 — 아키텍처

이 문서는 [프로젝트 제안서](project_proposal.md)의 아키텍처를 상세히 기술한다.
전체 설계 근거와 스펙 리뷰 결과는 [스펙 설계 문서](superpowers/specs/2026-03-16-cicd-image-pipeline-design.md)를 참조한다.

---

# 1. 전체 아키텍처

하이브리드 구조: LLM이 자연어 해석과 계획 수립을 담당하고, 고정된 실행 엔진이 도구를 순서대로 실행한다.

```
┌─────────────────────────────────────────────────┐
│                  사용자 (자연어)                    │
└──────────────────────┬──────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│                 API Layer (FastAPI)               │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│              Intent Parser (LLM)                  │
│  자연어 → 구조화된 작업 요청 추출                      │
│  (repository, branch, registry, wrap 여부, 배포 등) │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│             Plan Generator (LLM)                  │
│  추출된 정보 + 설정 → 실행 단계(steps) 리스트 생성     │
│  예: [clone, build, push, wrap, push, deploy]     │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│            Execution Engine                       │
│  Plan의 각 step을 순서대로 실행                      │
│  각 step → 대응하는 Tool 호출                       │
│  실패 시 → LLM에 재질의 (Recovery Advisor)          │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│                   Tools                           │
│  ┌─────────┐ ┌─────────┐ ┌──────────────────┐   │
│  │  Clone   │ │  Build  │ │  RegistryAuth    │   │
│  └─────────┘ └─────────┘ └──────────────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐           │
│  │  Push   │ │  Wrap   │ │  Deploy  │           │
│  └─────────┘ └─────────┘ └──────────┘           │
└──────────────────────────────────────────────────┘
```

---

# 2. 핵심 컴포넌트

## 2.1 Intent Parser (LLM)

자연어에서 `BuildRequest` 구조를 추출한다.

- 정보가 부족하면 기본값을 적용 (tag 미지정 시 `latest`, branch 미지정 시 `main`)
- 출력: `BuildRequest`

## 2.2 Plan Generator (LLM)

`BuildRequest`를 보고 필요한 step만 포함한 `ExecutionPlan`을 생성한다.

- wrap이 없으면 wrap/재push 단계 제외
- deploy가 없으면 배포 단계 제외
- 출력: `ExecutionPlan`

## 2.3 Execution Engine

Plan의 각 step을 순서대로 실행하는 고정 엔진.

- `context: dict`를 유지하며 각 step의 출력을 누적 저장
- 각 step의 `parameters`는 컨텍스트 값을 참조 가능 (예: `${build.image_id}`)
- step당 최대 3회 시도 (초기 1회 + 재시도 2회)
- 모든 step 실행 로그 보존

## 2.4 Recovery Advisor (LLM)

Tool 실행 실패 시 에러 메시지를 분석하고 `RecoveryAdvice`를 반환한다:

- `recoverable: true` → `modified_parameters`로 파라미터를 수정하여 재시도
- `recoverable: false` → 실행 중단, `explanation`을 사용자에게 반환
- 기존 step의 파라미터만 수정 가능, 새로운 step 삽입 불가

---

# 3. 데이터 흐름

```
자연어 → BuildRequest → ExecutionPlan → StepResult(s) → PipelineResult
```

---

# 4. 데이터 모델

## BuildRequest — Intent Parser 출력

```python
class BuildRequest:
    repository_url: str             # Git 레포지토리 URL
    branch: str                     # 브랜치명 (기본값: "main")
    registry_type: str              # 레지스트리 종류 ("ecr", "gcr", "acr")
    registry_url: str               # 레지스트리 전체 URL
    image_name: str                 # 이미지 이름
    image_tag: str                  # 이미지 태그 (기본값: "latest")
    wrap: WrapConfig | None         # wrapping 설정 (없으면 skip)
    deploy: DeployConfig | None     # 배포 설정 (없으면 skip)
```

## WrapConfig

```python
class WrapConfig:
    base_layers: list[str]      # 추가할 레이어 (보안 에이전트 등)
    target_platform: str        # 재패키징 대상 플랫폼
    target_registry_url: str    # wrapping 이미지 push 대상 레지스트리 URL
```

## DeployConfig

```python
class DeployConfig:
    host: str                   # 배포 서버 주소
    ssh_user: str               # SSH 사용자명
    ssh_port: int               # SSH 포트 (기본값: 22)
    ssh_key_path: str           # SSH 키 경로
    compose_file_path: str      # docker-compose 파일 경로
    service_name: str           # 업데이트할 서비스명
```

## ExecutionPlan — Plan Generator 출력

```python
class ExecutionPlan:
    steps: list[PlanStep]

class PlanStep:
    name: str                   # clone, build, push, wrap, deploy
    tool: str                   # 실행할 Tool 이름
    parameters: dict            # Tool에 전달할 파라미터
    max_attempts: int           # 최대 시도 횟수 (기본값: 3, 초기 1회 + 재시도 2회)
```

## StepResult — Tool 실행 결과

```python
class StepResult:
    step_name: str
    success: bool
    attempt_number: int         # 시도 횟수 (1부터 시작)
    output: dict                # Tool 실행 결과
    error: str | None
```

## RecoveryAdvice — Recovery Advisor 출력

```python
class RecoveryAdvice:
    recoverable: bool           # 복구 가능 여부
    modified_parameters: dict | None  # 수정된 파라미터 (재시도 시 사용)
    explanation: str            # 에러 분석 및 복구 전략 설명
```

---

# 5. 도구 시스템

## CloneTool

- Git 레포지토리를 클론하고 지정된 브랜치를 체크아웃
- **입력**: `repository_url: str`, `branch: str`
- **출력**: `local_path: str` (클론된 로컬 경로)
- **예상 에러**: 인증 실패, 네트워크 타임아웃, 브랜치 미존재

## BuildTool

- 빌드 전용 컨테이너를 띄워서 Docker 이미지 빌드
- 호스트의 Docker 소켓을 마운트하고, 소스 코드를 볼륨 마운트하여 표준 Docker CLI 이미지 컨테이너 내에서 빌드 수행
- **입력**: `source_directory_path: str`, `image_name: str`, `image_tag: str`
- **출력**: `image_id: str` (빌드된 이미지 ID)
- **전제 조건**: 레포지토리에 Dockerfile이 이미 존재해야 함
- **예상 에러**: Dockerfile 미존재, 빌드 명령 실패, 메모리 부족

## RegistryAuthTool

- 클라우드 레지스트리(ECR/GCR/ACR) 인증 수행
- **입력**: `registry_type: str`, `registry_url: str`
- **출력**: `authenticated: bool`
- 인증 정보는 `registry_type`에 따라 환경변수에서 자동으로 로드 (파라미터로 전달하지 않음)
- **예상 에러**: 인증 정보 누락, 토큰 만료, 권한 부족

## PushTool

- 빌드된 이미지를 레지스트리에 push
- **입력**: `image_name: str`, `image_tag: str`, `registry_url: str`
- **출력**: `image_uri: str` (push된 이미지 전체 URI)
- **예상 에러**: 인증 만료, 네트워크 에러, 이미지 크기 초과

## WrapTool

- 기존 이미지 위에 추가 레이어 적용 + 플랫폼 재패키징
- **입력**: `source_image_uri: str`, `base_layers: list[str]`, `target_platform: str`, `target_registry_url: str`
- **출력**: `wrapped_image_uri: str` (wrapping된 이미지 URI)
- **예상 에러**: 원본 이미지 pull 실패, 레이어 빌드 실패

## DeployTool

- SSH로 배포 서버 접속 후 docker-compose 서비스 업데이트
- **입력**: `host: str`, `ssh_user: str`, `ssh_port: int`, `ssh_key_path: str`, `compose_file_path: str`, `service_name: str`, `image_uri: str`
- **출력**: `deployed: bool`
- **예상 에러**: SSH 연결 실패, 키 인증 실패, compose 파일 미존재, 서비스명 불일치

---

# 6. LLM 역할 분담

| 역할 | 입력 | 출력 | 설명 |
|------|------|------|------|
| **Intent Parser** | 자연어 | `BuildRequest` | 자연어에서 구조화된 작업 요청 추출. 부족한 정보는 기본값 적용 |
| **Plan Generator** | `BuildRequest` | `ExecutionPlan` | 필요한 step만 포함한 실행 계획 생성 |
| **Recovery Advisor** | 에러 메시지 + 컨텍스트 | `RecoveryAdvice` | 실패 분석 및 복구 전략 제안. 파라미터 수정만 가능 |

---

# 7. 실행 엔진 상세

## 컨텍스트 관리

실행 엔진은 `context: dict`를 유지하며, 각 step의 출력을 key-value로 누적 저장한다.

```python
context = {
    "clone": {"local_path": "/tmp/repo-abc123"},
    "build": {"image_id": "sha256:abc123..."},
    "registry_auth": {"authenticated": True},
    "push": {"image_uri": "123456.dkr.ecr.ap-northeast-2.amazonaws.com/api-server:v2"},
}
```

## 템플릿 변수

각 step의 `parameters`에서 `${step_name.field}` 형식으로 이전 step의 출력을 참조한다.

```python
# push step의 parameters 예시
{
    "image_name": "api-server",
    "image_tag": "v2",
    "registry_url": "123456.dkr.ecr.ap-northeast-2.amazonaws.com"
}
# 이 값들은 BuildRequest에서 오지만, image_id 같은 값은 context에서 참조
```

## 재시도 로직

1. Tool 실행 실패 시 Recovery Advisor(LLM)에 에러 전달
2. `RecoveryAdvice` 수신 → `modified_parameters`로 수정 후 재시도
3. step당 최대 `max_attempts`회 시도 (기본값: 3, 초기 1회 + 재시도 2회)
4. `attempt_number > max_attempts`이면 중단
5. `recoverable: false` 시 즉시 실행 중단 + 에러 반환

---

# 8. 인증 방식

현재는 환경변수 및 설정 파일에서 credential을 로드한다. 향후 시크릿 매니저(Vault, AWS Secrets Manager) 연동으로 확장 가능하다.

## 레지스트리별 필요 환경변수

| 레지스트리 | 환경변수 |
|-----------|---------|
| ECR | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` |
| GCR | `GOOGLE_APPLICATION_CREDENTIALS` (서비스 계정 키 파일 경로) |
| ACR | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` |

## SSH 인증

배포 서버 접속을 위한 SSH 설정은 `DeployConfig`의 `ssh_user`, `ssh_port`, `ssh_key_path` 필드로 관리한다.

---

# 9. API 엔드포인트

## `POST /pipeline/run`

자연어 요청을 받아 파이프라인을 실행한다.

**요청:**

```json
{
  "input": "github.com/myorg/api-server의 release/v2 브랜치를 빌드해서 ECR에 올려줘"
}
```

**응답 (성공):**

```json
{
  "plan": {
    "steps": [...]
  },
  "results": [
    {"step_name": "clone", "success": true, "attempt_number": 1, "output": {...}, "error": null},
    {"step_name": "build", "success": true, "attempt_number": 1, "output": {...}, "error": null},
    {"step_name": "registry_auth", "success": true, "attempt_number": 1, "output": {...}, "error": null},
    {"step_name": "push", "success": true, "attempt_number": 1, "output": {...}, "error": null}
  ],
  "success": true,
  "error": null
}
```

**응답 (실패):**

```json
{
  "plan": {
    "steps": [...]
  },
  "results": [
    {"step_name": "clone", "success": true, "attempt_number": 1, "output": {...}, "error": null},
    {"step_name": "build", "success": false, "attempt_number": 3, "output": {}, "error": "Dockerfile not found"}
  ],
  "success": false,
  "error": "build 단계에서 실패: Dockerfile not found (3회 시도 후 중단)"
}
```

---

# 10. 프로젝트 구조

```
ai-platform-engineering-copilot/
├── app/
│   ├── agent/
│   │   ├── intent_parser.py      # 자연어 → BuildRequest
│   │   ├── plan_generator.py     # BuildRequest → ExecutionPlan
│   │   ├── execution_engine.py   # Plan 순서대로 실행
│   │   └── recovery_advisor.py   # 실패 시 LLM 복구 전략
│   ├── api/
│   │   ├── app.py                # FastAPI 앱
│   │   └── agent/
│   │       ├── router.py         # 엔드포인트
│   │       └── schemas.py        # API 스키마
│   ├── core/
│   │   ├── config.py             # 설정 (레지스트리, 인증 등)
│   │   └── llm_client.py         # LLM 추상화
│   ├── schemas/
│   │   ├── build_request.py      # BuildRequest, WrapConfig, DeployConfig
│   │   ├── plan.py               # ExecutionPlan, PlanStep
│   │   └── result.py             # StepResult
│   └── tools/
│       ├── base.py               # Tool 인터페이스
│       ├── clone_tool.py         # Git 클론
│       ├── build_tool.py         # 빌드 컨테이너에서 이미지 빌드
│       ├── registry_auth_tool.py # 레지스트리 인증
│       ├── push_tool.py          # 이미지 push
│       ├── wrap_tool.py          # 이미지 wrapping
│       └── deploy_tool.py        # Docker Compose 배포
├── tests/
├── docs/
├── main.py
├── pyproject.toml
└── ruff.toml
```

---

# 11. 향후 확장

- **사용자 확인 단계**: Plan 생성 후 사용자에게 보여주고 승인받은 뒤 실행
- **프라이빗 레지스트리 지원**: Harbor, Nexus 등
- **시크릿 매니저 연동**: Vault, AWS Secrets Manager
- **빌드 결과 리포팅**: 슬랙 알림, 웹훅 등
- **멀티 플랫폼 빌드**: `buildx`를 활용한 다중 아키텍처 지원
