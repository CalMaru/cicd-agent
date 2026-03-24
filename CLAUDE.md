# CLAUDE.md

## Project Overview

CI/CD 이미지 빌드 & 배포 파이프라인 에이전트. 자연어 요청을 받아 Git clone, Docker 빌드, ECR push, 서버 배포를 자동화하는 단일 에이전트.

- **참고 프로젝트**: [krafton-ai/KIRA](https://github.com/krafton-ai/KIRA) — `../KIRA`에 clone됨
- **설계 문서**: `docs/superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md`

## Architecture

**플랜 앤 실행 구조**: LLM이 계획을 1회 수립하고, 고정된 실행 엔진이 순차 실행. 실패 시에만 LLM이 재개입.

```
사용자 (CLI) → AgentCore.parse_and_plan() [LLM 1회] → ExecutionPlan
                                                          ↓
                                                   ExecutionEngine.run()
                                                     ↓ (성공)    ↓ (실패)
                                                 PipelineResult  RecoveryAdvisor [LLM]
```

### Key Design Decisions

- **Python SDK 우선**: SDK가 지원하지 않는 작업만 subprocess로 폴백
- **자격증명 격리**: CredentialStore에서 도구가 직접 로드, LLM 컨텍스트에 진입 불가
- **동기 도구**: GitPython, paramiko 등 블로킹 라이브러리를 자연스럽게 사용. ExecutionEngine이 필요시 `asyncio.to_thread()`로 래핑

## Project Structure (Target)

```
cicd-agent/
├── cicd_agent/
│   ├── config.py            # Settings (pydantic-settings), get_settings()
│   ├── planning/            # 계획 수립 도메인
│   │   ├── agent.py         # AgentCore (parse_and_plan)
│   │   ├── recovery.py      # RecoveryAdvisor
│   │   └── prompts.py       # 시스템 프롬프트
│   ├── execution/           # 실행 도메인
│   │   ├── engine.py        # ExecutionEngine
│   │   └── tools/
│   │       ├── base.py      # BaseTool ABC
│   │       ├── clone.py     # CloneTool (GitPython)
│   │       ├── build.py     # BuildTool (docker SDK)
│   │       ├── registry_auth.py  # RegistryAuthTool (boto3)
│   │       ├── push.py      # PushTool (docker SDK)
│   │       └── deploy.py    # DeployTool (paramiko) — Week 4 선택
│   ├── models/              # 공유 데이터 모델
│   │   ├── request.py       # BuildRequest
│   │   ├── plan.py          # ExecutionPlan, PlanStep
│   │   ├── result.py        # ToolResult, PipelineResult
│   │   └── recovery.py      # RecoveryAdvice
│   ├── infra/               # 횡단 관심사
│   │   ├── models.py        # GCRCredentials, AWSCredentials, SSHConfig, DockerConfig
│   │   ├── credentials.py   # CredentialStore, CredentialMissingError
│   │   └── sanitizer.py     # OutputSanitizer (2단계 세정)
│   └── cli.py               # Typer CLI
├── tests/
│   ├── test_planning/
│   ├── test_execution/
│   └── test_infra/
├── pyproject.toml
├── .env.example
└── .gitignore
```

### Module Dependencies

```
planning/  → models/, infra/
execution/ → models/, infra/
planning/  ✗ execution/   (서로 의존하지 않음)
```

## Tech Stack

- Python 3.12+, Pydantic v2, pydantic-settings, litellm, Typer
- GitPython, docker (Python SDK), boto3, paramiko
- Dev: ruff, pytest, pytest-asyncio

## Tools

| Tool | Method | Library | Purpose |
|------|--------|---------|---------|
| CloneTool | SDK | GitPython | clone/checkout |
| BuildTool | SDK | docker SDK | `client.images.build()` |
| RegistryAuthTool | SDK | boto3 | ECR 인증 토큰 발급 |
| PushTool | SDK | docker SDK | `client.images.push()` |
| DeployTool | SDK+subprocess | paramiko | SSH + 원격 docker compose |

## Conventions

- 레지스트리: GCR(기본) + ECR 선택 지원 (`registry_type` 설정)
- 실행 환경: 개발자 로컬 머신
- `.env` 파일은 `.gitignore`에 포함, `.env.example`만 커밋
- 모든 도구 출력은 `OutputSanitizer`를 거쳐 자격증명 제거 후 LLM에 전달

## Current State

- Day 1 완료: 의존성 정리, Pydantic v2 데이터 모델 구현
- Day 2 완료: `app/` → `cicd_agent/` 패키지 구조 전환, 새 설계 기준 데이터 모델 재작성
  - `cicd_agent/models/` — 4개 모델 파일 구현 (request, plan, result, recovery)
  - `tests/test_models/` — 18개 테스트 통과
  - `pyproject.toml` — 프로젝트명 `cicd-agent`, 의존성 추가 (gitpython, boto3, python-dotenv, typer)
  - isort 제거 → ruff `"I"` 규칙으로 대체
- Day 3 완료: pydantic-settings 기반 설정 관리 + 자격증명 격리
  - `cicd_agent/config.py` — Settings (pydantic-settings BaseSettings, frozen, SecretStr)
  - `cicd_agent/infra/models.py` — GCRCredentials, AWSCredentials, SSHConfig, DockerConfig
  - `cicd_agent/infra/credentials.py` — CredentialStore (GCR/ECR 멀티 레지스트리)
  - `cicd_agent/infra/sanitizer.py` — OutputSanitizer (2단계 세정: 정확 매칭 + 정규식)
  - `tests/` — 56개 테스트 통과 (기존 18 + 새 38)
  - `python-dotenv` → `pydantic-settings` 의존성 교체
