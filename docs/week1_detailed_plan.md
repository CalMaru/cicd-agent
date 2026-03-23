# 1주차 세부 계획

**목표**: 프로젝트 기반을 세우고, `cicd_agent/` 패키지 구조와 CloneTool이 독립적으로 동작하는 상태.

**상위 계획**: [MVP 개발 계획](mvp_development_plan.md)
**설계**: [실행 레이어 설계 문서](superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md)

---

## Day 1: 프로젝트 설정 + 데이터 모델 ✅

- [x] `pyproject.toml` 의존성 정리
  - 제거: `fastapi`, `uvicorn`
  - 추가: `litellm`, `docker`, `paramiko`
  - dev 추가: `pytest-asyncio`
- [x] Pydantic v2 데이터 모델 구현 (`app/schemas/`)
- [x] 테스트 작성 및 통과 확인

> **Note**: Day 1은 구 `app/` 구조로 완료됨. 이후 `cicd_agent/` 패키지로 리팩토링 필요.

---

## Day 2: 패키지 리팩토링 + 인프라

- [ ] `app/` → `cicd_agent/` 패키지 구조 전환
  - `cicd_agent/models/` — 데이터 모델 (기존 `app/schemas/` 에서 이동)
  - `cicd_agent/infra/` — 횡단 관심사
  - `cicd_agent/execution/` — 실행 도메인
  - `cicd_agent/planning/` — 계획 수립 도메인
- [ ] `pyproject.toml` 업데이트
  - 프로젝트명: `cicd-agent`
  - 의존성 추가: `gitpython`, `boto3`, `python-dotenv`, `typer[all]`
- [ ] 데이터 모델 업데이트 (새 설계에 맞춤)
  - `models/request.py` — BuildRequest (repo_url, dockerfile_path, registry 등)
  - `models/plan.py` — ExecutionPlan, PlanStep (tool_name, confirm_required 등)
  - `models/result.py` — ToolResult, PipelineResult, ErrorType
  - `models/recovery.py` — RecoveryAdvice (action: retry/skip/abort)

**완료 기준:**

```python
from cicd_agent.models.request import BuildRequest
from cicd_agent.models.result import ToolResult, ErrorType

request = BuildRequest(
    repo_url="https://github.com/myorg/api-server",
    image_name="api-server",
    image_tag="v1.0",
    registry="ecr",
)
assert request.branch == "main"
assert request.dockerfile_path == "Dockerfile"
```

---

## Day 3: CredentialStore + OutputSanitizer

- [ ] `cicd_agent/infra/credentials.py` 구현
  - CredentialStore: 환경변수에서 자격증명 로드
  - `get_aws_credentials()` → AWSCredentials
  - `get_ssh_config()` → SSHConfig
  - `get_docker_config()` → DockerConfig
  - 필수 변수 누락 시 `CredentialMissingError` (fail-fast)
- [ ] `cicd_agent/infra/sanitizer.py` 구현
  - OutputSanitizer: 2단계 세정
  - 1단계: 실제 비밀 값 정확 매칭
  - 2단계: 정규식 패턴 폴백 (AKIA*, password=*, token=*, PEM 키)
- [ ] `.env.example` 생성
- [ ] `tests/test_infra/` 테스트 작성 및 통과 확인

**완료 기준:**

```python
os.environ["AWS_ACCESS_KEY_ID"] = "AKIAIOSFODNN7EXAMPLE"
store = CredentialStore()
creds = store.get_aws_credentials()
assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"

sanitizer = OutputSanitizer(store)
assert "***REDACTED***" in sanitizer.sanitize("Key is AKIAIOSFODNN7EXAMPLE")
```

---

## Day 4: BaseTool + CloneTool

- [ ] `cicd_agent/execution/tools/base.py` 구현
  - BaseTool ABC: `__init__(credentials, sanitizer)`, `execute(params) → ToolResult`
  - `_safe_result(success, message, **data)` — sanitizer 적용 후 ToolResult 반환
- [ ] `cicd_agent/execution/tools/clone.py` 구현
  - GitPython 기반: `Repo.clone_from(url, path, branch=branch)`
  - 임시 디렉터리에 클론
  - 성공 시 `{"clone_dir": "/tmp/build/my-app"}` 반환
  - 실패 시 error_type 분류 (AUTH_FAILED, NOT_FOUND, NETWORK_ERROR)
- [ ] `tests/test_execution/test_clone.py` 작성 및 통과 확인

**완료 기준:**

```python
store = CredentialStore()
sanitizer = OutputSanitizer(store)
tool = CloneTool(store, sanitizer)
result = tool.execute({"repo_url": "https://github.com/octocat/Hello-World", "branch": "master"})
assert result.success
assert Path(result.data["clone_dir"]).exists()
```

---

## Day 5: 정리 + 자격증명 격리 검증

- [ ] 자격증명 격리 기본 검증 테스트
  - ToolResult.message에 자격증명 패턴이 포함되지 않음
  - CredentialStore의 값이 sanitizer를 거치면 모두 마스킹됨
- [ ] 코드 정리: ruff 린트 + 포맷팅
- [ ] 테스트 커버리지 확인
- [ ] 1주차 커밋 정리

**완료 기준:**

모든 테스트 통과 + CloneTool이 GitPython으로 동작 + 자격증명이 ToolResult에 노출되지 않음.

---

## 1주차 산출물 요약

| 산출물 | 파일 |
|--------|------|
| 데이터 모델 | `cicd_agent/models/request.py`, `plan.py`, `result.py`, `recovery.py` |
| 인프라 | `cicd_agent/infra/credentials.py`, `sanitizer.py` |
| Tool 인터페이스 | `cicd_agent/execution/tools/base.py` |
| CloneTool | `cicd_agent/execution/tools/clone.py` |
| 환경변수 예시 | `.env.example` |
| 테스트 | `tests/test_infra/`, `tests/test_execution/` |
