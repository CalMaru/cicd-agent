# CI/CD 이미지 빌드 & 배포 파이프라인 에이전트 — 프로젝트 제안서

---

# 1. 프로젝트 개요

자연어 요청을 받아 Git 레포지토리에서 Docker 이미지를 빌드하고, 클라우드 레지스트리에 push하며, 필요 시 이미지를 wrapping(추가 레이어 + 플랫폼 재패키징)한 후, Docker Compose 기반 서버에 배포하는 **AI 에이전트**를 구축한다.

에이전트 아키텍처를 이론적으로만 학습하는 대신, CI/CD 도메인의 실제 문제를 해결하는 **도구 기반 AI 에이전트(tool-augmented AI agent)**를 직접 설계하고 구현한다.

---

# 2. 문제 정의

이미지 빌드와 배포 파이프라인은 반복적이고 에러가 발생하기 쉬운 작업이다:

- Git 클론 및 브랜치 체크아웃
- Docker 이미지 빌드 (Dockerfile 경로, 빌드 인자 등)
- 클라우드 레지스트리(ECR, GCR, ACR) 인증 및 push
- 이미지 wrapping (보안 레이어 추가, 플랫폼 재패키징)
- SSH를 통한 Docker Compose 서비스 업데이트

이 작업들은:

- **반복적이다** — 매번 비슷한 명령어 조합을 수동으로 실행
- **도메인 지식이 필요하다** — 레지스트리별 인증 방식, 빌드 옵션, 배포 전략이 다름
- **에러 복구가 어렵다** — 인증 만료, 네트워크 타임아웃, Dockerfile 미존재 등 다양한 실패 유형

이 에이전트는 자연어 한 문장으로 전체 파이프라인을 자동화하고, 실패 시 LLM 기반 복구 전략을 제안한다.

---

# 3. 학습 목표

- **에이전트 오케스트레이션 패턴**: LLM 기반 계획 수립 + 도구 실행 + 실패 복구 루프
- **CI/CD 도메인 지식**: 이미지 빌드, 레지스트리 관리, 컨테이너 배포 자동화
- **하이브리드 아키텍처 설계**: LLM의 유연한 해석 + 고정 실행 엔진의 안정성 결합
- **도구 기반 추론(tool-augmented reasoning)** 구현 경험

---

# 4. 실용적 목표

자연어로 다음 작업을 자동화하는 에이전트 구축:

- Git 레포지토리 클론 및 브랜치 체크아웃
- Docker 이미지 빌드
- 클라우드 레지스트리 인증 및 push
- 이미지 wrapping + 재push
- Docker Compose 기반 서버 배포

---

# 5. 핵심 기능

에이전트는 6가지 도구(Tool)를 사용하여 파이프라인을 수행한다:

| 도구 | 기능 |
|------|------|
| **CloneTool** | Git 레포지토리 클론 및 브랜치 체크아웃 |
| **BuildTool** | 빌드 컨테이너에서 Docker 이미지 빌드 |
| **RegistryAuthTool** | 클라우드 레지스트리(ECR/GCR/ACR) 인증 |
| **PushTool** | 빌드된 이미지를 레지스트리에 push |
| **WrapTool** | 이미지 위에 추가 레이어 적용 + 플랫폼 재패키징 |
| **DeployTool** | SSH를 통한 Docker Compose 서비스 업데이트 |

---

# 6. 접근 방식: 하이브리드

LLM이 자연어를 해석하여 **실행 계획(plan)**을 생성하고, **고정된 실행 엔진**이 계획을 순서대로 수행한다. 실패 시에만 LLM이 재개입하여 복구 전략을 제안한다.

```
자연어 요청 → [Intent Parser (LLM)] → BuildRequest
                                          ↓
                                    [Plan Generator (LLM)] → ExecutionPlan
                                                                ↓
                                                          [Execution Engine]
                                                            ↓ (성공)    ↓ (실패)
                                                        PipelineResult  [Recovery Advisor (LLM)]
                                                                           ↓
                                                                        RecoveryAdvice → 재시도 or 중단
```

---

# 7. 인터페이스 로드맵

단계적으로 인터페이스를 확장한다:

| 단계 | 인터페이스 | 설명 |
|------|-----------|------|
| 1 | **Core** | 핵심 에이전트 로직 (Intent Parser, Plan Generator, Execution Engine) |
| 2 | **CLI** | Typer 기반 커맨드라인 인터페이스 |
| 3 | **API** | FastAPI 기반 REST API |
| 4 | **MCP** | Model Context Protocol 서버 |

---

# 8. 기술 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.12+ |
| 데이터 검증 | Pydantic v2 |
| LLM 클라이언트 | litellm |
| CLI | Typer |
| 컨테이너 | Docker SDK for Python |
| SSH | paramiko |
| 의존성 관리 | uv |
| 코드 품질 | ruff |

---

# 9. 범위 및 제외 사항

## 범위 내 (In Scope)

- Git 레포지토리 클론 및 브랜치 체크아웃
- 빌드 컨테이너에서 Docker 이미지 빌드
- 클라우드 레지스트리(ECR, GCR, ACR) 인증 및 push
- 이미지 wrapping (추가 레이어 + 플랫폼 재패키징) 및 재push
- Docker Compose 기반 서버 배포 (SSH)

## 비목표 (Non-Goals)

- **Dockerfile 생성** — 레포지토리에 Dockerfile이 이미 존재한다고 가정
- **빌드/배포 결과 리포팅** — 향후 확장 (슬랙 알림, 웹훅 등)
- **멀티턴 대화 / 채팅 메모리** — 단일 요청 에이전트
- **프로덕션 수준 배포** — 학습과 프로토타이핑에 집중
- **프론트엔드 UI** — API 전용; 데모에는 Swagger UI로 충분

---

# 10. 성공 기준

| 기준 | 목표 |
|------|------|
| 핵심 도구 구현 | 6개 Tool 모두 동작 |
| 파이프라인 완주 | clone → build → push 기본 시나리오 성공 |
| 실패 복구 | Recovery Advisor가 재시도 가능 에러를 자동 복구 |
| 출력 유효성 | 모든 응답이 Pydantic 스키마 검증 통과 |
| 하이브리드 동작 | LLM 계획 + 고정 실행 엔진이 올바르게 분리 |

---

# 11. 관련 문서

- [아키텍처 상세](architecture.md) — 컴포넌트, 데이터 모델, 실행 흐름
- [스펙 설계 문서](superpowers/specs/2026-03-16-cicd-image-pipeline-design.md) — 스펙 리뷰 완료된 상세 설계
