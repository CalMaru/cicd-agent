# MVP 개발 계획

MVP 범위: 4개 핵심 도구 + 플랜 앤 실행 에이전트 + CLI.

- 설계: [실행 레이어 설계 문서](superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md)
- 아키텍처: [아키텍처 상세](architecture.md)

---

## 전체 일정

4주 (2026-03-17 ~ 2026-04-11), 하루 최대 2시간

| 주차 | 기간 | 목표 |
|------|------|------|
| 1주차 | 03-17 ~ 03-21 | 기반 구조 + models/ + infra/ + CloneTool |
| 2주차 | 03-24 ~ 03-28 | BuildTool + RegistryAuthTool + PushTool + AgentCore |
| 3주차 | 03-31 ~ 04-04 | ExecutionEngine + RecoveryAdvisor + CLI + E2E 테스트 |
| 4주차 | 04-07 ~ 04-11 | 택 1: MCP 서버 변환 또는 DeployTool + FastAPI |

---

## 1주차: 기반 + CloneTool

### 목표

프로젝트 기반을 세우고, `cicd_agent/` 패키지 구조와 CloneTool이 동작하는 상태.

### 작업 항목

**1. 프로젝트 셋업**
- `pyproject.toml` 업데이트: 프로젝트명 `cicd-agent`, 의존성 추가 (gitpython, boto3, python-dotenv, typer)
- `cicd_agent/` 패키지 구조 생성 (planning/, execution/, models/, infra/)
- ruff, pytest 설정 확인

**2. 데이터 모델 (models/)**
- `models/request.py` — BuildRequest
- `models/plan.py` — ExecutionPlan, PlanStep
- `models/result.py` — ToolResult, PipelineResult, ErrorType
- `models/recovery.py` — RecoveryAdvice
- 테스트: 모델 생성, 직렬화, 검증

**3. 인프라 (infra/)**
- `infra/credentials.py` — CredentialStore (환경변수 로드, fail-fast)
- `infra/sanitizer.py` — OutputSanitizer (2단계 세정)
- 테스트: 자격증명 로드, sanitizer 동작 검증

**4. 도구 기반**
- `execution/tools/base.py` — BaseTool ABC (sync execute, _safe_result)

**5. CloneTool**
- `execution/tools/clone.py` — GitPython 기반 clone + checkout
- 테스트: 정상 클론, 브랜치 미존재, 잘못된 URL

### 1주차 마일스톤

```python
store = CredentialStore()
sanitizer = OutputSanitizer(store)
tool = CloneTool(store, sanitizer)
result = tool.execute({"repo_url": "https://github.com/octocat/Hello-World", "branch": "master"})
assert result.success
assert "clone_dir" in result.data
```

---

## 2주차: 도구 3개 + AgentCore

### 목표

4개 핵심 도구 전체 + LLM 계획 수립이 동작하는 상태.

### 작업 항목

**1. BuildTool**
- `execution/tools/build.py` — docker SDK `client.images.build()`
- 테스트: 정상 빌드 (mock), Dockerfile 미존재

**2. RegistryAuthTool**
- `execution/tools/registry_auth.py` — boto3 ECR 인증 토큰 발급
- 테스트: 인증 성공 (mock), 환경변수 누락

**3. PushTool**
- `execution/tools/push.py` — docker SDK `client.images.push()`
- 테스트: 정상 push (mock), 인증 만료

**4. AgentCore**
- `planning/agent.py` — `parse_and_plan()` (litellm + Native Tool Calling)
- `planning/prompts.py` — 시스템 프롬프트
- 테스트: mock LLM → ExecutionPlan 생성

### 2주차 마일스톤

4개 Tool 모두 개별 테스트 통과 + AgentCore가 자연어 → ExecutionPlan 변환.

---

## 3주차: 엔진 + 복구 + CLI

### 목표

자연어 입력 → 전체 파이프라인 자동 실행이 동작하는 상태.

### 작업 항목

**1. ExecutionEngine**
- `execution/engine.py` — 순차 실행 루프, context 관리, confirm 처리
- step당 최대 2회 재시도, 전체 최대 3회
- 테스트: 정상 흐름, 재시도 성공, 재시도 실패 후 중단

**2. RecoveryAdvisor**
- `planning/recovery.py` — sanitized 에러 → retry/skip/abort 판단
- 테스트: 일시적 오류 → retry, 치명적 오류 → abort

**3. CLI**
- `cli.py` — Typer CLI
- 테스트: CLI 호출 → PipelineResult 출력

**4. E2E 테스트**
- clone → build → push 기본 시나리오
- 자격증명 격리 검증 테스트 (LLM 메시지에 자격증명 미포함)

### 3주차 마일스톤

```bash
uv run python -m cicd_agent.cli "api-server의 main 브랜치를 빌드해서 ECR에 올려줘"
# → clone → build → registry_auth → push 성공
```

---

## 4주차: 택 1

### 옵션 A: MCP 서버 변환 (권장 — AI Agent Platform Engineer 면접 최고 임팩트)

- execution/tools/를 MCP 도구로 변환
- `create_sdk_mcp_server()`로 패키징
- Claude Code에서 연동 테스트

### 옵션 B: DeployTool + FastAPI

- `execution/tools/deploy.py` — paramiko SSH 배포
- FastAPI REST API 인터페이스

---

## 완료 기준

| 기준 | 확인 방법 |
|------|-----------|
| 4개 핵심 Tool 동작 | 각 Tool 단위 테스트 통과 |
| 파이프라인 완주 | clone → build → push E2E 테스트 통과 |
| 자격증명 격리 | 자동화 테스트로 LLM 메시지에 자격증명 미포함 검증 |
| 실패 복구 | RecoveryAdvisor 재시도 통합 테스트 통과 |
| Pydantic 검증 | 모든 입출력이 스키마 검증 통과 |
| 플랜 앤 실행 분리 | AgentCore(LLM) ↔ ExecutionEngine(고정) 분리 |

---

## 리스크

| 리스크 | 대응 |
|--------|------|
| Docker SDK가 환경에 따라 동작이 다를 수 있음 | mock 테스트 + 실제 Docker 환경에서 수동 검증 |
| LLM의 Native Tool Calling 응답 불안정 | Pydantic 검증 + PlanGenerationError 방어 |
| SSH 기반 배포의 네트워크 의존성 | DeployTool은 Week 4 선택, mock 테스트 위주 |
