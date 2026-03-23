# CI/CD 파이프라인 에이전트 — 프로젝트 제안서

---

# 1. 프로젝트 개요

자연어 요청을 받아 Git 레포지토리에서 Docker 이미지를 빌드하고, ECR에 push하며, Docker Compose 기반 서버에 배포하는 **AI 에이전트**를 구축한다.

KIRA(krafton-ai/KIRA)의 에이전트 아키텍처를 참고하되, **플랜 앤 실행 구조**와 **자격증명 격리 모델**을 핵심 차별점으로 설계한다.

---

# 2. 문제 정의

이미지 빌드와 배포 파이프라인은 반복적이고 에러가 발생하기 쉬운 작업이다:

- Git 클론 및 브랜치 체크아웃
- Docker 이미지 빌드 (Dockerfile 경로, 빌드 인자 등)
- 클라우드 레지스트리(ECR) 인증 및 push
- SSH를 통한 Docker Compose 서비스 업데이트

이 에이전트는 자연어 한 문장으로 전체 파이프라인을 자동화하고, 실패 시 LLM 기반 복구 전략을 제안한다.

---

# 3. 학습 목표

- **에이전트 오케스트레이션 패턴**: 플랜 앤 실행 구조 (LLM 계획 1회 + 고정 실행 엔진)
- **자격증명 격리 설계**: LLM 컨텍스트에 자격증명이 진입하지 않는 보안 모델
- **CI/CD 도메인 지식**: 이미지 빌드, 레지스트리 관리, 컨테이너 배포 자동화
- **SDK 기반 도구 구현**: Python SDK 직접 호출로 안정적이고 보안적인 도구 실행

---

# 4. 실용적 목표

자연어로 다음 작업을 자동화하는 에이전트 구축:

- Git 레포지토리 클론 및 브랜치 체크아웃
- Docker 이미지 빌드
- ECR 인증 및 push
- Docker Compose 기반 서버 배포 (선택)

---

# 5. 핵심 기능

에이전트는 4개 핵심 도구(+1 선택)를 사용하여 파이프라인을 수행한다:

| 도구 | 실행 방식 | 기능 |
|------|----------|------|
| **CloneTool** | GitPython | Git 레포지토리 클론 및 브랜치 체크아웃 |
| **BuildTool** | docker SDK | Docker 이미지 빌드 |
| **RegistryAuthTool** | boto3 | ECR 인증 토큰 발급 |
| **PushTool** | docker SDK | 빌드된 이미지를 ECR에 push |
| **DeployTool** (선택) | paramiko | SSH를 통한 Docker Compose 배포 |

---

# 6. 접근 방식: 플랜 앤 실행

LLM이 Native Tool Calling으로 실행 계획을 1회 수립하고, 고정된 실행 엔진이 순차 실행한다. 실패 시에만 RecoveryAdvisor(LLM)가 재개입.

```
자연어 요청 → [AgentCore.parse_and_plan (LLM 1회)] → ExecutionPlan
                                                         ↓
                                                   [ExecutionEngine]
                                                     ↓ (성공)    ↓ (실패)
                                                 PipelineResult  [RecoveryAdvisor (LLM)]
                                                                     ↓
                                                                 retry / skip / abort
```

### Terminus-KIRA와의 차이

| | Terminus-KIRA | 이 프로젝트 |
|--|--------------|-----------|
| LLM 호출 | 매 에피소드마다 | 계획 1회 + 실패 시만 |
| 도구 실행 | tmux 셸 명령어 | Python SDK 직접 호출 |
| 자격증명 | 터미널 출력에 포함 가능 | LLM 컨텍스트 진입 불가 |

---

# 7. 인터페이스

| 우선순위 | 인터페이스 | 설명 |
|---------|-----------|------|
| MVP | **CLI** | Typer 기반 커맨드라인 인터페이스 |
| Week 4 옵션 A | **MCP** | Model Context Protocol 서버 변환 |
| Week 4 옵션 B | **API** | FastAPI 기반 REST API |

---

# 8. 기술 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.12+ |
| 데이터 검증 | Pydantic v2 |
| LLM 클라이언트 | litellm |
| CLI | Typer |
| Git | GitPython |
| 컨테이너 | Docker SDK for Python |
| AWS | boto3 |
| SSH | paramiko |
| 환경변수 | python-dotenv |
| 의존성 관리 | uv |
| 코드 품질 | ruff |

---

# 9. 범위 및 제외 사항

## 범위 내 (In Scope)

- Git 레포지토리 클론 및 브랜치 체크아웃
- Docker 이미지 빌드 (SDK)
- ECR 인증 및 push
- 자격증명 격리 (CredentialStore + OutputSanitizer)
- Docker Compose 기반 서버 배포 (선택, Week 4)

## 비목표 (Non-Goals)

- **Dockerfile 생성** — 레포지토리에 Dockerfile이 이미 존재한다고 가정
- **멀티 레지스트리** — ECR만 지원 (인터페이스는 추상화)
- **이미지 wrapping** — MVP 범위에서 제외
- **멀티턴 대화 / 채팅 메모리** — 단일 요청 에이전트
- **프로덕션 수준 배포** — 학습과 프로토타이핑에 집중
- **프론트엔드 UI**

---

# 10. 제약 조건

- 개발 기간: 4주, 하루 최대 2시간 (총 ~40-56시간)
- 실행 환경: 개발자 로컬 머신
- 사이드 프로젝트 (AI Agent Platform Engineer 직무 전환 준비용)

---

# 11. 성공 기준

| 기준 | 목표 |
|------|------|
| 핵심 도구 구현 | 4개 Tool (Clone, Build, RegistryAuth, Push) 동작 |
| 파이프라인 완주 | clone → build → push 기본 시나리오 성공 |
| 자격증명 격리 | 자동화 테스트로 LLM 메시지에 자격증명 미포함 검증 |
| 실패 복구 | RecoveryAdvisor가 재시도 가능 에러를 자동 복구 |
| 출력 유효성 | 모든 응답이 Pydantic 스키마 검증 통과 |
| 플랜 앤 실행 분리 | LLM 계획 + 고정 실행 엔진이 올바르게 분리 |

---

# 12. 관련 문서

- [아키텍처 상세](architecture.md) — 컴포넌트, 데이터 모델, 실행 흐름
- [실행 레이어 설계](superpowers/specs/2026-03-19-cicd-agent-execution-layer-design.md) — 상세 설계 (최신)
- [개발 계획](mvp_development_plan.md) — 4주 MVP 개발 일정
