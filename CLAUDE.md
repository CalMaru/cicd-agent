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
│   ├── planning/          # 계획 수립 도메인
│   │   ├── agent.py       # AgentCore (parse_and_plan)
│   │   ├── recovery.py    # RecoveryAdvisor
│   │   └── prompts.py     # 시스템 프롬프트
│   ├── execution/         # 실행 도메인
│   │   ├── engine.py      # ExecutionEngine
│   │   └── tools/
│   │       ├── base.py    # BaseTool ABC
│   │       ├── clone.py   # CloneTool (GitPython)
│   │       ├── build.py   # BuildTool (docker SDK)
│   │       ├── registry_auth.py  # RegistryAuthTool (boto3)
│   │       ├── push.py    # PushTool (docker SDK)
│   │       └── deploy.py  # DeployTool (paramiko) — Week 4 선택
│   ├── models/            # 공유 데이터 모델
│   │   ├── request.py     # BuildRequest
│   │   ├── plan.py        # ExecutionPlan, PlanStep
│   │   ├── result.py      # ToolResult, PipelineResult
│   │   └── recovery.py    # RecoveryAdvice
│   ├── infra/             # 횡단 관심사
│   │   ├── credentials.py # CredentialStore
│   │   └── sanitizer.py   # OutputSanitizer
│   └── cli.py             # Typer CLI
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

- Python 3.12+, Pydantic v2, litellm, Typer
- GitPython, docker (Python SDK), boto3, paramiko
- python-dotenv
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

- 레지스트리: ECR만 지원 (인터페이스는 추상화)
- 실행 환경: 개발자 로컬 머신
- `.env` 파일은 `.gitignore`에 포함, `.env.example`만 커밋
- 모든 도구 출력은 `OutputSanitizer`를 거쳐 자격증명 제거 후 LLM에 전달

## Current State

- Day 1 완료: 의존성 정리, Pydantic v2 데이터 모델 구현 (아직 구 `app/` 구조)
- `cicd_agent/` 패키지로 리팩토링 예정
