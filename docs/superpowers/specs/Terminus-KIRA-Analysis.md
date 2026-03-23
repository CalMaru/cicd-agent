# Terminus-KIRA 심층 분석

> Terminus-KIRA가 정확히 무엇을 하는 에이전트인지, 어떤 구조로 동작하는지를 코드 기반으로 분석한 문서입니다.

---

## 목차

1. [한줄 요약](#1-한줄-요약)
2. [무엇을 하는 에이전트인가?](#2-무엇을-하는-에이전트인가)
3. [핵심 배경 개념](#3-핵심-배경-개념)
4. [프로젝트 구조](#4-프로젝트-구조)
5. [클래스 구조와 상속](#5-클래스-구조와-상속)
6. [에이전트 루프 상세 분석](#6-에이전트-루프-상세-분석)
7. [5가지 핵심 기능 분석](#7-5가지-핵심-기능-분석)
8. [프롬프트 설계 분석](#8-프롬프트-설계-분석)
9. [에러 처리와 복원력](#9-에러-처리와-복원력)
10. [실행 환경과 성능](#10-실행-환경과-성능)

---

## 1. 한줄 요약

**Terminus-KIRA는 LLM이 Linux 터미널을 자율적으로 조작하여 복잡한 CLI 작업을 해결하는 AI Agent이며, Terminal-Bench 벤치마크에서 최고 수준의 성능(75.7%)을 달성한 에이전트 하네스(harness)입니다.**

---

## 2. 무엇을 하는 에이전트인가?

### 2.1 목적

사람이 터미널에서 수행하는 복잡한 작업을 AI가 **완전 자율적으로** 수행합니다. 사람의 개입 없이 작업을 분석하고, 명령어를 실행하고, 결과를 확인하며, 최종적으로 작업을 완료합니다.

### 2.2 구체적인 동작 예시

```
[작업 지시] "주어진 C 소스 코드의 컴파일 에러를 수정하고 테스트를 통과시켜라"

[Terminus-KIRA의 행동]
Episode 1: ls → 파일 구조 파악
Episode 2: cat main.c → 소스 코드 읽기
Episode 3: gcc main.c -o main → 컴파일 시도, 에러 확인
Episode 4: vi main.c → 에러 수정
Episode 5: gcc main.c -o main → 재컴파일 성공
Episode 6: ./main → 실행 확인
Episode 7: task_complete (1차) → 체크리스트 확인
Episode 8: task_complete (2차) → 완료 확정
```

### 2.3 작업 유형

Terminal-Bench에 포함된 작업들:
- 파일 조작 및 텍스트 처리
- 소스 코드 컴파일 및 디버깅
- 시스템 관리 및 설정
- 네트워크 도구 사용
- 스크립트 작성 및 실행
- 이미지/멀티미디어 파일 분석

### 2.4 Terminus 2와의 관계

```
Terminus 2 (Harbor 프레임워크)     Terminus-KIRA (확장)
────────────────────────────      ────────────────────────
ICL 기반 JSON/XML 파싱             Native Tool Calling
프롬프트에 응답 형식 명세 포함       12줄 짧은 프롬프트
텍스트만 처리                      이미지 분석 지원 (멀티모달)
고정 대기 시간                     마커 기반 조기 완료 감지
단순 완료 확인                     이중 확인 + QA 체크리스트
캐싱 없음                         Anthropic 프롬프트 캐싱
```

Terminus-KIRA는 Terminus 2의 **취약점을 최소한의 수정으로 개선**한 것입니다. 복잡한 추론 모듈이나 계획 시스템을 추가한 것이 아니라, 하네스 수준의 간결한 개선만으로 큰 성능 향상을 달성했습니다.

---

## 3. 핵심 배경 개념

### 3.1 Terminal-Bench

[Terminal-Bench](https://github.com/laude-institute/terminal-bench)는 AI Agent가 터미널에서 복잡한 작업을 수행하는 능력을 측정하는 **벤치마크**입니다. 현재 v2.0이 사용됩니다.

- 다양한 난이도의 CLI 작업을 포함
- Docker/Daytona/Runloop 등의 샌드박스 환경에서 실행
- 자동 채점 시스템으로 정확도 측정

### 3.2 Harbor 프레임워크

Harbor는 자율 에이전트를 학습/평가하기 위한 프레임워크로, 다음을 제공합니다:

| 컴포넌트 | 역할 |
|----------|------|
| `BaseEnvironment` | 작업 실행 환경 추상 인터페이스 (Docker, Daytona 등) |
| `Terminus2` | 터미널 기반 에이전트 베이스 클래스 |
| `TmuxSession` | tmux를 통한 터미널 세션 관리 |
| `Chat` | 대화 히스토리 및 토큰 카운터 관리 |
| `AgentContext` | 에이전트 실행 컨텍스트 |
| Trajectory 모델 | 에이전트 행동 기록 (Step, Metrics, Observation 등) |

### 3.3 에이전트 하네스(Harness)란?

LLM 자체는 텍스트만 생성합니다. **하네스**는 LLM의 출력을 실제 행동(명령어 실행)으로 변환하고, 실행 결과를 다시 LLM에게 전달하는 **중개 시스템**입니다.

```
┌─────────────┐         ┌────────────────┐         ┌──────────────┐
│    LLM      │ ──────→ │   Harness      │ ──────→ │  Environment │
│ (텍스트 생성) │         │ (행동으로 변환)  │         │ (터미널 실행)  │
│             │ ←────── │ (결과를 전달)    │ ←────── │              │
└─────────────┘         └────────────────┘         └──────────────┘
```

Terminus-KIRA가 바로 이 하네스입니다.

---

## 4. 프로젝트 구조

```
KIRA/
├── terminus_kira/
│   ├── __init__.py                  # TerminusKira 클래스 export
│   └── terminus_kira.py             # 메인 에이전트 (1,161줄)
│       ├── TOOLS (Line 136-209)     # 3개 툴 정의 (JSON Schema)
│       ├── TerminusKira 클래스       # Terminus2 상속
│       ├── _execute_commands()      # 마커 기반 명령어 실행
│       ├── _execute_image_read()    # 멀티모달 이미지 분석
│       ├── _call_llm_with_tools()   # LLM API 호출 (tools 파라미터)
│       ├── _extract_tool_calls()    # 응답에서 tool_calls 추출
│       ├── _parse_tool_calls()      # tool_calls → 실제 명령 변환
│       ├── _handle_llm_interaction()# LLM 상호작용 총괄
│       └── _run_agent_loop()        # 메인 에이전트 루프 (핵심)
│
├── prompt-templates/
│   └── terminus-kira.txt            # 시스템 프롬프트 (12줄)
│
├── run-scripts/
│   ├── run_docker.sh                # 로컬 Docker 실행 (동시 4개)
│   ├── run_daytona.sh               # 클라우드 Daytona 실행 (동시 50개)
│   └── run_runloop.sh               # 클라우드 Runloop 실행
│
├── anthropic_caching.py             # Anthropic 프롬프트 캐싱 유틸 (63줄)
├── pyproject.toml                   # 의존성: harbor, litellm, anthropic, tenacity
└── README.md                        # 프로젝트 문서
```

### 의존성

```toml
# pyproject.toml
requires-python = ">=3.12"
dependencies = [
    "anthropic",      # Anthropic API (프롬프트 캐싱용)
    "harbor>=0.1.44", # 에이전트 프레임워크 (Terminus2 베이스 클래스)
    "litellm",        # LLM 통합 레이어 (Claude, GPT, Gemini 등 지원)
    "tenacity",       # 재시도 로직 (지수 백오프)
]
```

---

## 5. 클래스 구조와 상속

### 5.1 상속 계층

```
harbor.agents.terminus_2.Terminus2     (Harbor 프레임워크 베이스)
         │
         ▼
    TerminusKira                       (Terminus-KIRA 확장)
```

### 5.2 오버라이드한 메서드들

```python
class TerminusKira(Terminus2):

    # 초기화 - 마커 시퀀스와 시간 절약 카운터 추가
    def __init__(self, *args, **kwargs)

    # 파서 비활성화 - Native Tool Calling을 사용하므로 ICL 파서 불필요
    def _get_parser(self) → None

    # 프롬프트 경로 - terminus-kira.txt 지정
    def _get_prompt_template_path(self) → Path

    # 에러 메시지 - "valid tool calls" 요청
    def _get_error_response_type(self) → str

    # 완료 확인 메시지 - QA 체크리스트 포함
    def _get_completion_confirmation_message(terminal_output) → str

    # LLM 상호작용 - Native Tool Calling으로 완전 재작성
    async def _handle_llm_interaction(...) → tuple

    # 에이전트 루프 - image_read 지원 추가
    async def _run_agent_loop(...) → int
```

### 5.3 새로 추가한 메서드들

```python
# 인프라 타임아웃 보호
async def _with_block_timeout(coro, timeout_sec=600)

# 마커 기반 명령어 실행
async def _execute_commands(commands, session) → (bool, str)

# LLM API 직접 호출 (tools 파라미터 포함)
async def _call_llm_with_tools(messages) → ToolCallResponse

# 이미지 분석용 LLM 호출
async def _call_llm_for_image(messages, model, temperature, max_tokens)

# 멀티모달 이미지 읽기 실행
async def _execute_image_read(image_read, chat, original_instruction) → str

# 응답에서 tool_calls 추출
def _extract_tool_calls(response) → list[dict]

# 사용량 정보 추출
def _extract_usage_info(response) → UsageInfo | None

# tool_calls를 Command 객체로 변환
def _parse_tool_calls(tool_calls) → tuple
```

### 5.4 데이터 모델

```python
@dataclass
class ToolCallResponse:
    content: str | None              # LLM의 텍스트 응답
    tool_calls: list[dict[str, Any]] # 호출된 툴 목록
    reasoning_content: str | None    # 추론 과정 (Extended Thinking)
    usage: UsageInfo | None          # 토큰 사용량 + 비용

@dataclass
class ImageReadRequest:
    file_path: str                   # 이미지 파일 경로
    image_read_instruction: str      # 분석 지시사항

# Harbor에서 가져온 모델
Command(keystrokes: str, duration_sec: float)  # 실행할 명령어
Step(step_id, timestamp, source, message, ...)  # 궤적 기록 단위
```

---

## 6. 에이전트 루프 상세 분석

> `_run_agent_loop()` (Line 833-1160) — 에이전트의 심장부

### 6.1 전체 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                    초기화 (Line 833-852)                     │
│  - AgentContext, TmuxSession 확인                           │
│  - 토큰 카운터 초기화                                        │
│  - initial_prompt = 시스템 프롬프트 + 작업 지시 + 터미널 상태    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              for episode in range(max_episodes):            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. 세션 생존 확인 (Line 856-858)                      │   │
│  │    if not session.is_session_alive(): break           │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             ▼                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 2. 사전 요약 검사 (Line 860-871)                      │   │
│  │    컨텍스트가 너무 길면 선제적으로 요약                    │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             ▼                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 3. LLM 호출 (Line 881-891)                           │   │
│  │    _handle_llm_interaction()                          │   │
│  │    ├─ 메시지 구성 (히스토리 + 현재 프롬프트)              │   │
│  │    ├─ Anthropic 캐싱 적용                              │   │
│  │    ├─ litellm.acompletion(tools=TOOLS) 호출            │   │
│  │    ├─ tool_calls 추출 및 파싱                           │   │
│  │    └─ 반환: commands, is_task_complete, image_read     │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             ▼                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 4. 분기 (Line 981 / 1065)                            │   │
│  │                                                      │   │
│  │  image_read가 있으면:                                  │   │
│  │    ├─ _execute_image_read() 실행                      │   │
│  │    ├─ base64로 이미지 읽기 → 멀티모달 LLM 호출          │   │
│  │    └─ 분석 결과를 다음 프롬프트에 포함                    │   │
│  │                                                      │   │
│  │  그렇지 않으면 (일반 명령어):                            │   │
│  │    ├─ _execute_commands() 실행                        │   │
│  │    ├─ tmux에 명령어 전송 + 마커 기반 폴링               │   │
│  │    └─ 터미널 출력을 다음 프롬프트에 포함                  │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             ▼                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 5. 완료 확인 (Line 990-1000 / 1076-1083)             │   │
│  │                                                      │   │
│  │  is_task_complete == True?                           │   │
│  │    ├─ 1차 호출: 체크리스트 제시 (pending=True)         │   │
│  │    └─ 2차 호출: 실제 완료 → return episode            │   │
│  │                                                      │   │
│  │  is_task_complete == False?                          │   │
│  │    └─ pending 리셋, 다음 에피소드 계속                  │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             ▼                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 6. 궤적 기록 (Line 1038-1059 / 1132-1153)           │   │
│  │    Step 객체 생성: 분석, 계획, 툴호출, 관찰, 메트릭      │   │
│  │    _dump_trajectory() 호출                            │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             │                               │
│                      prompt = observation                    │
│                      (실행 결과가 다음 턴의 입력이 됨)          │
│                             │                               │
│                    ─────── loop ───────                      │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 에피소드 1회의 데이터 흐름

```
prompt (터미널 출력)
    │
    ▼
_handle_llm_interaction()
    │
    ├─ messages = [히스토리...] + [{"role": "user", "content": prompt}]
    │
    ├─ litellm.acompletion(messages=messages, tools=TOOLS)
    │       │
    │       ▼
    │   LLM 응답:
    │   {
    │     "content": "분석 텍스트...",
    │     "tool_calls": [{
    │       "function": {
    │         "name": "execute_commands",
    │         "arguments": "{\"analysis\":\"...\", \"plan\":\"...\", \"commands\":[...]}"
    │       }
    │     }]
    │   }
    │
    ├─ _extract_tool_calls() → [{id, function: {name, arguments}}]
    │
    ├─ _parse_tool_calls() → (commands, is_task_complete, feedback, analysis, plan, image_read)
    │
    ▼
_execute_commands(commands, session)
    │
    ├─ 각 command에 대해:
    │   ├─ session.send_keys(keystrokes)     # 명령어 전송
    │   ├─ session.send_keys("echo marker")  # 완료 마커 전송
    │   ├─ while not marker in output:       # 마커 감지까지 폴링
    │   │       sleep(0.5)
    │   └─ 마커 줄 제거                       # LLM에게 깨끗한 출력 전달
    │
    ▼
observation = 터미널 출력 (30KB 제한)
    │
    ▼
prompt = observation  →  다음 에피소드로
```

---

## 7. 5가지 핵심 기능 분석

### 7.1 Native Tool Calling

> ICL 파싱을 LLM API의 `tools` 파라미터로 대체한 핵심 혁신

**Before (Terminus 2 — ICL 방식):**
```
시스템 프롬프트에 응답 형식을 길게 설명:
"다음 JSON 형식으로 응답하세요:
{
  "analysis": "...",
  "plan": "...",
  "commands": [{"keystrokes": "...", "duration": ...}]
}
절대 다른 형식을 사용하지 마세요..."

→ LLM이 자유 텍스트로 JSON 출력 → 정규식/파서로 추출 (깨지기 쉬움)
```

**After (Terminus-KIRA — Native 방식):**
```python
# 프롬프트에는 형식 설명이 없음 (12줄만)
# 대신 API 레벨에서 도구 정의:

response = await litellm.acompletion(
    model="anthropic/claude-opus-4-6",
    messages=messages,
    tools=TOOLS,      # ← 여기서 JSON Schema로 구조화된 도구 전달
)

# LLM이 구조화된 tool_calls로 응답 → 파싱 불필요
tool_calls = response.choices[0].message.tool_calls
```

**효과:**
- 프롬프트가 12줄로 극단적으로 짧아짐 (토큰 절약)
- JSON 파싱 실패 없음 (LLM이 구조화된 형태로 직접 반환)
- 모든 LLM 제공자가 지원하는 표준 방식

### 7.2 마커 기반 명령어 실행 최적화

> `_execute_commands()` (Line 232-286)

**문제:** `ls` 같은 즉시 명령은 0.01초만에 끝나지만, 설정된 duration(예: 1초)만큼 무조건 대기하면 시간 낭비.

**해결:**
```python
async def _execute_commands(self, commands, session):
    for command in commands:
        self._marker_seq += 1
        marker = f"__CMDEND__{self._marker_seq}__"   # 고유 마커 생성

        await session.send_keys(command.keystrokes)    # 명령어 실행
        await session.send_keys(f"echo '{marker}'\n")  # 마커 echo 추가

        # 마커가 나타나면 즉시 다음으로 진행
        while time.monotonic() - start < command.duration_sec:
            pane_content = await session.capture_pane()
            if marker in pane_content:
                break                 # 조기 완료!
            await asyncio.sleep(0.5)  # 0.5초 간격으로 폴링

        # 시간 절약량 기록
        saved = command.duration_sec - elapsed
        self._total_time_saved += saved

    # 마커 줄을 출력에서 제거 (LLM이 보지 않도록)
    output = await session.get_incremental_output()
    lines = [line for line in output.split("\n")
             if not any(m in line for m in markers)]
```

**원리:**
```
터미널에서 일어나는 일:

$ gcc main.c -o main                    ← 실제 명령어
$ echo '__CMDEND__1__'                  ← 바로 뒤에 마커 echo
__CMDEND__1__                           ← 명령어 끝나면 마커 출력됨

에이전트 로직:
- 0.5초마다 화면 체크
- "__CMDEND__1__" 발견 → 즉시 다음 명령어로
- 1초 duration이 설정되었어도 0.5초만에 넘어감 → 0.5초 절약
```

### 7.3 이중 확인(Double Confirmation) 메커니즘

> `_get_completion_confirmation_message()` (Line 318-333)

LLM이 `task_complete`를 호출하면 바로 끝내지 않고, **체크리스트를 제시**합니다.

**1차 task_complete 호출 시 LLM에게 전달되는 메시지:**
```
Original task:
{작업 지시 전문}

Current terminal state:
{현재 터미널 출력}

Are you sure you want to mark the task as complete?

[!] Checklist
- Does your solution meet the requirements in the original task above? [TODO/DONE]
- Does your solution account for potential changes in numeric values,
  array sizes, file contents, or configuration parameters? [TODO/DONE]
- Have you verified your solution from the all perspectives of:
  - test engineer [TODO/DONE]
  - QA engineer [TODO/DONE]
  - user who requested this task [TODO/DONE]

After this point, solution grading will begin and no further edits will be possible.
If everything looks good, call task_complete tool again.
```

**흐름:**
```python
if is_task_complete:
    if self._pending_completion:  # 2차 호출
        return episode + 1       # 진짜 완료!
    else:                         # 1차 호출
        self._pending_completion = True
        observation = 체크리스트 메시지  # LLM에게 재확인 요청
else:
    self._pending_completion = False  # 리셋
```

**효과:** 조급한 완료 선언을 방지하고, 다각적 관점(테스트 엔지니어, QA, 사용자)에서 재검증하도록 유도합니다.

### 7.4 멀티모달 이미지 분석

> `_execute_image_read()` (Line 484-567)

터미널 작업 중 이미지 파일을 분석해야 할 때 사용합니다 (예: 차트, 스크린샷, 다이어그램).

```python
async def _execute_image_read(self, image_read, chat, original_instruction):
    # 1. 컨테이너에서 이미지를 base64로 읽기
    result = await self._session.environment.exec(
        command=f"base64 {image_read.file_path}"
    )
    b64 = result.stdout.replace("\n", "")

    # 2. MIME 타입 결정
    ext = Path(file_path).suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ...}.get(ext)

    # 3. 멀티모달 메시지 구성
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": image_read.image_read_instruction},
            {"type": "image_url", "image_url": {
                "url": f"data:{mime};base64,{b64}"
            }}
        ]
    }]

    # 4. LLM에 이미지 분석 요청 (tools 없이, 텍스트 응답만)
    response = await self._call_llm_for_image(messages, ...)
    return response["choices"][0]["message"]["content"]
```

**지원 포맷:** PNG, JPG, JPEG, GIF, WEBP

### 7.5 Anthropic 프롬프트 캐싱

> `anthropic_caching.py` (63줄)

```python
def add_anthropic_caching(messages, model_name):
    # Anthropic/Claude 모델만 적용
    if "anthropic" not in model_name.lower() and "claude" not in model_name.lower():
        return messages

    # 최근 3개 메시지에 cache_control 추가
    for msg in messages[-3:]:
        for content_item in msg["content"]:
            content_item["cache_control"] = {"type": "ephemeral"}

    return cached_messages
```

**효과:**
- 반복되는 시스템 프롬프트와 최근 컨텍스트를 캐싱
- API 호출 시 입력 토큰 비용 절감
- 응답 지연 시간 감소

---

## 8. 프롬프트 설계 분석

> `prompt-templates/terminus-kira.txt` — 단 12줄

```
You are an AI assistant tasked with solving command-line tasks
in a Linux environment. You will be given a task description and
the output from previously executed commands. Your goal is to solve
the task by providing batches of shell commands.

Your plan MUST account that you as an AI agent must complete the
entire task without any human intervention, and you should NOT
expect any human interventions. Also, you do NOT have eyes or ears,
so you MUST resort to various programmatic/AI tools to understand
multimedia files.

Before calling task_complete, verify minimal state changes: [...]

Task Description:
{instruction}

Current terminal state:
{terminal_state}
```

### 왜 12줄만으로 충분한가?

| 기존 Terminus 2 | Terminus-KIRA |
|-----------------|---------------|
| 프롬프트에 JSON 형식 명세 포함 | 도구 정의가 API `tools` 파라미터로 분리됨 |
| "이 형식을 반드시 지켜라" 지시 필요 | LLM이 자동으로 구조화된 응답 반환 |
| 프롬프트가 수백 줄 | **12줄** |

### 프롬프트의 3가지 핵심 지시

1. **완전 자율성**: "인간 개입 없이 전체 작업을 완수하라"
2. **도구 활용**: "눈과 귀가 없으니 프로그래밍/AI 도구를 사용하라" (image_read 유도)
3. **최소 변경 원칙**: "요구된 파일만 변경하고, 그 외 시스템 상태는 원래 그대로 유지하라"

---

## 9. 에러 처리와 복원력

### 9.1 재시도 로직 (tenacity)

```python
@retry(
    stop=stop_after_attempt(5),                          # 최대 5회 시도
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4), # 0.5 → 1 → 2 → 4초
    retry=retry_if_not_exception_type(BadRequestError),   # 잘못된 요청은 재시도 안함
)
async def _call_llm_with_tools(self, messages):
    ...
```

### 9.2 컨텍스트 길이 초과 복구

```
ContextLengthExceededError 발생
    │
    ▼
요약(summarization) 활성화 여부 확인
    │
    ├─ 활성화: 대화 히스토리 요약 → 요약된 컨텍스트로 재시도
    └─ 비활성화: 예외 전파
```

### 9.3 출력 길이 초과 복구

```
OutputLengthExceededError 발생
    │
    ▼
"응답이 잘렸습니다. 더 짧게 답변해주세요."
    │
    ▼
재시도
```

### 9.4 인프라 블록 타임아웃

```python
BLOCK_TIMEOUT_SEC = 600  # 10분

async def _with_block_timeout(self, coro, timeout_sec=600):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_sec)
    except asyncio.TimeoutError:
        raise BlockError(f"Infrastructure blocked for {timeout_sec}s")
```

Docker, Daytona 등 인프라 API가 10분 이상 응답하지 않으면 에러를 발생시킵니다.

### 9.5 출력 크기 제한

```python
def _limit_output_length(self, output, max_bytes=30000):  # 30KB 제한
```

터미널 출력이 너무 길면 잘라서 컨텍스트 윈도우를 보호합니다.

---

## 10. 실행 환경과 성능

### 10.1 실행 방법

```bash
# 로컬 Docker (동시 4개 작업)
uv run harbor run \
    --agent-import-path "terminus_kira.terminus_kira:TerminusKira" \
    -d "terminal-bench@2.0" \
    -m "anthropic/claude-opus-4-6" \
    -e docker \
    --n-concurrent 4

# 클라우드 Daytona (동시 50개 작업)
uv run harbor run \
    --agent-import-path "terminus_kira.terminus_kira:TerminusKira" \
    -d "terminal-bench@2.0" \
    -m "anthropic/claude-opus-4-6" \
    -e daytona \
    --n-concurrent 50
```

### 10.2 실행 환경 옵션

| 환경 | 동시성 | 설명 |
|------|--------|------|
| `docker` | 4개 | 로컬 Docker 컨테이너 |
| `daytona` | 50개 | Daytona 클라우드 샌드박스 |
| `runloop` | 50개 | Runloop 클라우드 샌드박스 |

### 10.3 벤치마크 성능

| 모델 | Terminal-Bench 정확도 |
|------|---------------------|
| Claude Opus 4.6 | **75.7%** |
| Codex 5.3 | 75.5% |
| Gemini 3.1 Pro | 74.8% |

### 10.4 진화 과정 (9단계 마일스톤)

| # | 마일스톤 | 설명 |
|---|---------|------|
| 1 | Genesis | Terminus 2를 복사하여 시작점으로 사용 |
| 2 | Native Tool Use | ICL JSON/XML 파싱을 LLM `tools` 파라미터로 교체 |
| 3 | Output Limiting | 터미널 출력을 30KB로 제한하여 컨텍스트 보호 |
| 4 | Autonomy & Constraints | 에이전트 자율성과 환경 제약을 프롬프트에 반영 |
| 5 | Completion Confirmation | 완료 확인 시 원본 작업 지시를 포함 |
| 6 | Multimodal | `image_read` 툴로 이미지 분석 지원 |
| 7 | Completion Checklist | 다각적 QA 체크리스트 (테스트/QA/사용자 관점) |
| 8 | Execution Optimization | 마커 기반 폴링 + 블록 타임아웃 보호 |
| 9 | Temperature Fix | reasoning_effort 사용 시 temperature=1 강제 |

### 10.5 궤적(Trajectory) 기록

모든 에피소드는 상세한 Step 객체로 기록됩니다:

```python
Step(
    step_id=1,
    timestamp="2026-03-17T...",
    source="agent",
    model_name="anthropic/claude-opus-4-6",
    message="Analysis: ... Plan: ...",
    reasoning_content="(Extended Thinking 내용)",
    tool_calls=[
        ToolCall(function_name="bash_command",
                 arguments={"keystrokes": "ls -la\n", "duration": 0.1})
    ],
    observation=Observation(
        results=[ObservationResult(content="drwxr-xr-x ...")]
    ),
    metrics=Metrics(
        prompt_tokens=1500,
        completion_tokens=300,
        cached_tokens=1200,
        cost_usd=0.0042,
    ),
)
```

이 궤적 데이터는 에이전트의 행동을 분석하고, 디버깅하고, 벤치마크 결과를 제출하는 데 사용됩니다.
