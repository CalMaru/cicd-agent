# MVP 개발 계획

MVP 범위: 스펙 문서에 정의된 Core(인터페이스 로드맵 1단계) 전체 구현.

- 스펙: [CI/CD 파이프라인 에이전트 설계](superpowers/specs/2026-03-16-cicd-image-pipeline-design.md)
- 아키텍처: [아키텍처 상세](architecture.md)

---

## 전체 일정

3주 (2026-03-17 ~ 2026-04-04)

| 주차 | 기간 | 목표 |
|------|------|------|
| 1주차 | 03-17 ~ 03-21 | 기반 구조 + 데이터 모델 + 기본 도구 (Clone, Build) |
| 2주차 | 03-24 ~ 03-28 | 나머지 도구 (RegistryAuth, Push, Wrap, Deploy) |
| 3주차 | 03-31 ~ 04-04 | 에이전트 계층 (Intent Parser, Plan Generator, Execution Engine, Recovery Advisor) + 통합 |

---

## 1주차: 기반 구조 + 기본 도구

### 목표

프로젝트 기반을 세우고, 가장 핵심적인 도구 2개(Clone, Build)가 독립적으로 동작하는 상태.

### 작업 항목

**1. 의존성 정리 및 프로젝트 설정**
- `pyproject.toml` 업데이트: 불필요한 의존성 제거(fastapi, uvicorn), 신규 추가(litellm, docker, paramiko)
- ruff, pytest 설정 확인

**2. 데이터 모델 (Pydantic schemas)**
- `app/schemas/build_request.py` — BuildRequest, WrapConfig, DeployConfig
- `app/schemas/plan.py` — ExecutionPlan, PlanStep
- `app/schemas/result.py` — StepResult, PipelineResult, RecoveryAdvice
- 각 모델의 기본값, 검증 규칙 포함
- 테스트: 모델 생성, 직렬화, 검증 실패 케이스

**3. 설정 및 LLM 클라이언트**
- `app/core/config.py` — 레지스트리 환경변수, SSH 설정 로드
- `app/core/llm_client.py` — litellm 기반 LLM 호출 래퍼
- 테스트: 설정 로드, mock LLM 호출

**4. Tool 인터페이스**
- `app/tools/base.py` — Tool 추상 클래스 (입력 → 출력, 에러 처리 표준화)

**5. CloneTool**
- `app/tools/clone_tool.py` — Git clone + branch checkout
- subprocess로 git 명령 실행, 임시 디렉터리에 클론
- 테스트: 정상 클론, 브랜치 미존재 에러, 잘못된 URL 에러

**6. BuildTool**
- `app/tools/build_tool.py` — Docker SDK로 빌드 컨테이너 실행
- Docker 소켓 마운트 + 소스 볼륨 마운트 → 컨테이너 내 docker build
- 테스트: 정상 빌드, Dockerfile 미존재 에러

### 1주차 마일스톤

```
CloneTool.execute(repository_url, branch) → {"local_path": "/tmp/repo-xxx"}
BuildTool.execute(source_directory_path, image_name, image_tag) → {"image_id": "sha256:xxx"}
```

---

## 2주차: 나머지 도구

### 목표

6개 도구 전체가 독립적으로 동작하는 상태.

### 작업 항목

**1. RegistryAuthTool**
- `app/tools/registry_auth_tool.py` — ECR/GCR/ACR 인증
- 레지스트리 타입별 환경변수 로드 → Docker SDK login
- 테스트: 인증 성공 (mock), 환경변수 누락 에러

**2. PushTool**
- `app/tools/push_tool.py` — Docker SDK로 이미지 push
- 태그 지정 → push → image URI 반환
- 테스트: 정상 push (mock), 인증 만료 에러

**3. WrapTool**
- `app/tools/wrap_tool.py` — 이미지 wrapping (추가 레이어 + 플랫폼 재패키징)
- 원본 이미지 pull → 추가 레이어 적용 → 재빌드 → 대상 레지스트리에 push
- 테스트: 정상 wrapping (mock), 원본 이미지 pull 실패 에러

**4. DeployTool**
- `app/tools/deploy_tool.py` — paramiko SSH → docker-compose up
- SSH 연결 → compose 파일 내 이미지 태그 교체 → docker compose up -d
- 테스트: 정상 배포 (mock), SSH 연결 실패 에러

### 2주차 마일스톤

6개 Tool 모두 개별 테스트 통과:

```
CloneTool      → {"local_path": "..."}
BuildTool      → {"image_id": "..."}
RegistryAuthTool → {"authenticated": true}
PushTool       → {"image_uri": "..."}
WrapTool       → {"wrapped_image_uri": "..."}
DeployTool     → {"deployed": true}
```

---

## 3주차: 에이전트 계층 + 통합

### 목표

자연어 입력 → 전체 파이프라인 자동 실행이 동작하는 상태.

### 작업 항목

**1. Intent Parser**
- `app/agent/intent_parser.py` — LLM에 자연어 전달 → BuildRequest 구조화 출력
- 프롬프트 설계: 필수/선택 필드, 기본값 적용 규칙
- 테스트: 다양한 자연어 입력 → BuildRequest 변환 검증

**2. Plan Generator**
- `app/agent/plan_generator.py` — BuildRequest → ExecutionPlan 생성
- wrap/deploy 포함 여부에 따른 조건부 step 생성
- 테스트: wrap 있는 경우, 없는 경우, deploy 있는 경우 등

**3. Execution Engine**
- `app/agent/execution_engine.py` — Plan의 step을 순서대로 실행
- context 관리: 각 step 출력 누적
- 템플릿 변수 치환: `${step_name.field}` → context 값
- 재시도 로직: 실패 시 Recovery Advisor 호출 → 파라미터 수정 → 재실행
- 테스트: 정상 흐름, 재시도 성공, 재시도 실패 후 중단

**4. Recovery Advisor**
- `app/agent/recovery_advisor.py` — 에러 메시지 분석 → RecoveryAdvice 반환
- 프롬프트 설계: 에러 유형 분류, 파라미터 수정 제안
- 테스트: 복구 가능 에러, 복구 불가 에러

**5. 통합 테스트**
- 자연어 → Intent Parser → Plan Generator → Execution Engine → PipelineResult
- 시나리오 1: clone → build → push (기본)
- 시나리오 2: clone → build → push → wrap → push (wrapping 포함)
- 시나리오 3: 실패 → Recovery Advisor → 재시도 → 성공

### 3주차 마일스톤

```python
result = await pipeline.run("github.com/myorg/api-server의 release/v2 브랜치를 빌드해서 ECR에 올려줘")
assert result.success is True
assert len(result.results) == 4  # clone, build, registry_auth, push
```

---

## 완료 기준

| 기준 | 확인 방법 |
|------|-----------|
| 6개 Tool 모두 동작 | 각 Tool 단위 테스트 통과 |
| 기본 파이프라인 완주 | clone → build → push 통합 테스트 통과 |
| 실패 복구 동작 | Recovery Advisor 재시도 통합 테스트 통과 |
| Pydantic 스키마 검증 | 모든 입출력이 스키마 검증 통과 |
| LLM-실행 엔진 분리 | Intent Parser/Plan Generator는 LLM, Execution Engine은 고정 로직 |

---

## 리스크

| 리스크 | 대응 |
|--------|------|
| Docker SDK 빌드가 환경에 따라 동작이 다를 수 있음 | BuildTool은 mock 테스트 + 실제 Docker 환경에서 수동 검증 병행 |
| LLM 구조화 출력의 일관성 부족 | Pydantic 검증 + 재시도 로직으로 보완 |
| WrapTool의 플랫폼 재패키징 복잡도 | 단일 플랫폼(linux/amd64)부터 구현 후 점진적 확장 |
| SSH 기반 배포의 네트워크 의존성 | DeployTool은 mock 테스트 위주, 실제 서버 테스트는 별도 수행 |
