# 1주차 세부 계획

**목표**: 프로젝트 기반을 세우고, CloneTool과 BuildTool이 독립적으로 동작하는 상태.

**상위 계획**: [MVP 개발 계획](mvp_development_plan.md)
**스펙**: [CI/CD 파이프라인 에이전트 설계](superpowers/specs/2026-03-16-cicd-image-pipeline-design.md)

---

## Day 1: 프로젝트 설정 + 데이터 모델

- [ ] `pyproject.toml` 의존성 정리
  - 제거: `fastapi`, `uvicorn`
  - 추가: `litellm`, `docker`, `paramiko`
  - dev 추가: `pytest-asyncio`
- [ ] `ruff.toml` 설정 확인
- [ ] `uv sync` 실행하여 의존성 설치 확인
- [ ] `app/schemas/build_request.py` 구현
  - `BuildRequest`: repository_url, branch(기본값 "main"), registry_type, registry_url, image_name, image_tag(기본값 "latest"), wrap(선택), deploy(선택)
  - `WrapConfig`: base_layers, target_platform, target_registry_url
  - `DeployConfig`: host, ssh_user, ssh_port(기본값 22), ssh_key_path, compose_file_path, service_name
- [ ] `app/schemas/plan.py` 구현
  - `PlanStep`: name, tool, parameters, max_attempts(기본값 3)
  - `ExecutionPlan`: steps
- [ ] `app/schemas/result.py` 구현
  - `StepResult`: step_name, success, attempt_number, output, error
  - `PipelineResult`: plan, results, success, error
  - `RecoveryAdvice`: recoverable, modified_parameters, explanation
- [ ] `tests/schemas/` 테스트 작성 및 통과 확인

**완료 기준:**

```python
request = BuildRequest(
    repository_url="https://github.com/myorg/api-server",
    registry_type="ecr",
    registry_url="123456.dkr.ecr.ap-northeast-2.amazonaws.com",
    image_name="api-server",
)
assert request.branch == "main"
assert request.image_tag == "latest"
assert request.wrap is None
```

---

## Day 2: Config + LLM 클라이언트 + Tool 인터페이스

- [ ] `app/core/config.py` 구현
  - 레지스트리별 환경변수 매핑 (ECR: AWS_*, GCR: GOOGLE_*, ACR: AZURE_*)
  - LLM 모델명, 기본 설정
  - Pydantic Settings 기반
- [ ] `app/core/llm_client.py` 구현
  - litellm 기반 비동기 LLM 호출 래퍼
  - `generate(prompt, response_model) → Pydantic 모델` 형태
  - 구조화 출력(structured output) 지원
- [ ] `app/tools/base.py` 구현
  - `Tool` 추상 클래스: `name`, `description` 속성
  - `execute(**parameters) → dict` 추상 메서드
  - `ToolError` 예외 클래스: tool_name, message, recoverable 필드
- [ ] `tests/core/`, `tests/tools/test_base.py` 테스트 작성 및 통과 확인

**완료 기준:**

```python
config = Settings()
assert config.llm_model is not None

client = LLMClient(config)
result = await client.generate(prompt="...", response_model=BuildRequest)
assert isinstance(result, BuildRequest)

class MyTool(Tool):
    name = "my_tool"
    async def execute(self, **params) -> dict: ...
```

---

## Day 3: CloneTool

- [ ] `app/tools/clone_tool.py` 구현
  - `Tool` 상속, name = "clone"
  - 임시 디렉터리 생성 → `git clone --branch {branch} --single-branch {url} {path}`
  - asyncio subprocess로 실행
  - 성공 시 `{"local_path": "/tmp/repo-xxx"}` 반환
  - 실패 시 `ToolError` 발생 (인증 실패, 브랜치 미존재, 네트워크 에러)
- [ ] `tests/tools/test_clone_tool.py` 구현
  - 정상 클론: 공개 레포지토리 클론 후 local_path 확인
  - 브랜치 미존재: ToolError 발생 확인
  - 잘못된 URL: ToolError 발생 확인
  - 클론된 디렉터리에 파일 존재 확인
- [ ] 테스트 실행 및 통과 확인

**완료 기준:**

```python
tool = CloneTool()
result = await tool.execute(
    repository_url="https://github.com/octocat/Hello-World",
    branch="master",
)
assert Path(result["local_path"]).exists()
```

---

## Day 4: BuildTool

- [ ] `app/tools/build_tool.py` 구현
  - `Tool` 상속, name = "build"
  - Docker SDK(`docker` 패키지)로 빌드 컨테이너 실행
    - 호스트 Docker 소켓 마운트 (`/var/run/docker.sock`)
    - 소스 디렉터리 볼륨 마운트
    - 표준 Docker CLI 이미지(`docker:cli`) 컨테이너 내에서 `docker build` 실행
  - 성공 시 `{"image_id": "sha256:xxx"}` 반환
  - 실패 시 `ToolError` 발생 (Dockerfile 미존재, 빌드 실패)
- [ ] `tests/tools/test_build_tool.py` 구현
  - 정상 빌드: mock Docker client로 image_id 반환 확인
  - Dockerfile 미존재: ToolError 발생 확인
  - 빌드 명령 실패: ToolError 발생 확인
- [ ] 테스트 실행 및 통과 확인

**완료 기준:**

```python
tool = BuildTool()
result = await tool.execute(
    source_directory_path="/tmp/repo-xxx",
    image_name="api-server",
    image_tag="v1",
)
assert result["image_id"].startswith("sha256:")
```

---

## Day 5: Clone → Build 통합 + 정리

- [ ] `tests/tools/test_clone_build_integration.py` 구현
  - CloneTool 출력(local_path) → BuildTool 입력(source_directory_path) 연결
  - 전체 흐름 정상 동작 확인
  - CloneTool 실패 시 BuildTool 미실행 확인
- [ ] 코드 정리: ruff 린트 + 포맷팅
- [ ] 테스트 커버리지 확인 및 누락된 에지 케이스 보충
- [ ] 1주차 작업 커밋 정리
- [ ] 2주차 진입 전 확인: Tool 공통 인터페이스가 나머지 4개 도구 확장에 적합한지 검토

**완료 기준:**

```python
clone_tool = CloneTool()
build_tool = BuildTool()

clone_result = await clone_tool.execute(
    repository_url="https://github.com/myorg/api-server",
    branch="main",
)
build_result = await build_tool.execute(
    source_directory_path=clone_result["local_path"],
    image_name="api-server",
    image_tag="latest",
)
assert build_result["image_id"].startswith("sha256:")
```

---

## 1주차 산출물 요약

| 산출물 | 파일 |
|--------|------|
| 데이터 모델 | `app/schemas/build_request.py`, `plan.py`, `result.py` |
| 설정 | `app/core/config.py` |
| LLM 클라이언트 | `app/core/llm_client.py` |
| Tool 인터페이스 | `app/tools/base.py` |
| CloneTool | `app/tools/clone_tool.py` |
| BuildTool | `app/tools/build_tool.py` |
| 테스트 | `tests/schemas/`, `tests/core/`, `tests/tools/` |
