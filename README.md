# cicd-agent

자연어 요청을 받아 Git clone → Docker 빌드 → ECR push → 서버 배포를 자동화하는 CI/CD 파이프라인 에이전트.

## Overview

LLM이 자연어를 해석하여 실행 계획을 1회 수립하고, 고정된 실행 엔진이 순차 실행하는 **플랜 앤 실행(Plan & Execute)** 아키텍처. 실패 시에만 LLM이 재개입하여 복구 전략을 제안한다.

### Key Features

- **자연어 파이프라인 실행**: "api-server의 release/v2를 빌드해서 ECR에 올려줘"
- **자격증명 격리**: LLM 컨텍스트에 자격증명이 진입하지 않는 보안 모델
- **자동 실패 복구**: RecoveryAdvisor가 일시적 오류를 자동 재시도
- **SDK 우선**: Python SDK 직접 호출로 안정적인 도구 실행

## Architecture

```
사용자 (CLI)
    │
    ▼
AgentCore.parse_and_plan()  ← LLM (Native Tool Calling, 1회)
    │
    ▼
ExecutionEngine.run()       ← 순차 실행 루프
    │
    ├── CloneTool      (GitPython)
    ├── BuildTool      (docker SDK)
    ├── RegistryAuthTool (boto3)
    ├── PushTool       (docker SDK)
    └── DeployTool     (paramiko)     ← Week 4 선택
    │
    ▼
PipelineResult
```

### Credential Isolation

```
LLM 영역 (신뢰하지 않음)         도구 영역 (신뢰함)           Credential Store
─────────────────────     ─────────────────────     ─────────────────
· 사용자 요청 텍스트         · CredentialStore에서        · 환경변수 / .env
· 도구 이름 + 공개 파라미터     자격증명 직접 로드          · LLM 접근 불가 영역
· ToolResult (sanitized)   · SDK 호출 (boto3, docker)
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker
- AWS credentials (ECR 사용 시)

### Setup

```bash
# 의존성 설치
uv sync

# 환경변수 설정
cp .env.example .env
# .env 파일에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 등 설정
```

### Usage

```bash
# CLI 실행 (구현 예정)
uv run python -m cicd_agent.cli "api-server의 main 브랜치를 빌드해서 ECR에 올려줘"
```

## Project Structure

```
cicd-agent/
├── cicd_agent/
│   ├── planning/           # AgentCore, RecoveryAdvisor, 프롬프트
│   ├── execution/          # ExecutionEngine + Tools
│   ├── models/             # Pydantic 데이터 모델
│   ├── infra/              # CredentialStore, OutputSanitizer
│   └── cli.py              # Typer CLI
├── tests/
├── docs/
├── pyproject.toml
└── .env.example
```

## Development

```bash
# 테스트 실행
uv run pytest

# 린트
uv run ruff check .

# 포맷팅
uv run ruff format .
```

## Documentation

- [설계 문서](docs/superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md) — 실행 레이어 상세 설계 (최신)
- [아키텍처](docs/architecture.md) — 컴포넌트 및 데이터 모델
- [개발 계획](docs/mvp_development_plan.md) — 4주 MVP 개발 계획

## Reference

- [krafton-ai/KIRA](https://github.com/krafton-ai/KIRA) — 참고 프로젝트 (에이전트 아키텍처)

## License

See [LICENSE](LICENSE).
