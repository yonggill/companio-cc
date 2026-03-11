# Companio

경량 개인 AI 어시스턴트 프레임워크.

ReAct 에이전트 루프 기반으로, Telegram 연동과 다양한 내장 도구를 제공하는 자율형 AI 비서입니다.

---

## 목차

- [주요 기능](#주요-기능)
- [요구사항](#요구사항)
- [설치 가이드](#설치-가이드)
  - [비개발자용 (사용자)](#비개발자용-사용자)
  - [개발자용](#개발자용)
- [빠른 시작](#빠른-시작)
- [설정 파일](#설정-파일)
  - [설정 항목 레퍼런스](#설정-항목-레퍼런스)
  - [환경 변수](#환경-변수)
- [CLI 명령어](#cli-명령어)
- [내장 도구](#내장-도구)
  - [기본 도구](#기본-도구)
  - [조건부 도구](#조건부-도구)
  - [MCP 도구](#mcp-도구)
- [스킬 시스템](#스킬-시스템)
  - [내장 스킬](#내장-스킬)
  - [커스텀 스킬 만들기](#커스텀-스킬-만들기)
- [지원 LLM](#지원-llm)
- [아키텍처](#아키텍처)
  - [ReAct 에이전트 루프](#react-에이전트-루프)
  - [2계층 메모리](#2계층-메모리)
  - [하트비트](#하트비트)
  - [크론 스케줄러](#크론-스케줄러)
  - [서브에이전트](#서브에이전트)
  - [세션 관리](#세션-관리)
- [보안](#보안)
- [개발](#개발)
- [라이선스](#라이선스)

---

## 주요 기능

- **ReAct 에이전트 루프** — 세션별 잠금, 최대 40회 도구 반복
- **LLM 지원** — Anthropic, OpenAI, Gemini ([LiteLLM](https://docs.litellm.ai/) 기반)
- **Telegram 연동** — 봇을 통한 채팅 인터페이스
- **내장 도구** — 파일 CRUD, 쉘 실행, 웹 검색/페치, 메시지, 서브에이전트, 크론, Obsidian, MCP
- **스킬 시스템** — SKILL.md 마크다운 기반 점진적 로딩
- **2계층 메모리** — MEMORY.md (장기) + HISTORY.md (이벤트 로그)
- **세션 관리** — SQLite 기반 대화 영속화
- **크론 스케줄러** — 예약 리마인더 및 반복 작업
- **하트비트** — 주기적 자율 점검 (기본 10분)
- **서브에이전트** — 백그라운드 병렬 작업 실행
- **MCP 지원** — stdio, SSE, streamableHttp 프로토콜
- **보안** — 워크스페이스 제한, SSRF 방어, 시크릿 필터링

---

## 요구사항

- Python 3.11 이상
- LLM API 키 (Anthropic, OpenAI, 또는 Gemini 중 하나 이상)

### 선택 사항

| 기능 | 필요 도구 |
|------|----------|
| 웹 검색 | [Brave Search API](https://brave.com/search/api/) 키 |
| 브라우저 자동화 | Node.js + `npx @playwright/mcp@latest` |
| Google Workspace | `npm install -g @googleworkspace/cli` |
| Obsidian 연동 | Obsidian vault 경로 |

---

## 설치 가이드

### 비개발자용 (사용자)

Python 3.11 이상이 설치되어 있어야 합니다. 터미널(맥: Terminal, 윈도우: PowerShell)에서 진행합니다.

```bash
# 1. 저장소 다운로드
git clone https://github.com/yonggill/companio-cc.git
cd companio-cc

# 2. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 3. 설치
pip install -e .

# 4. 초기 설정 (config.json + 워크스페이스 생성)
companiocc onboard

# 5. API 키 입력
#    ~/.companiocc/config.json을 열어 providers 섹션에 API 키를 입력합니다.
#    또는 onboard 과정에서 대화형으로 입력할 수 있습니다.

# 6. 테스트
companiocc agent -m "안녕하세요!"
```

#### Telegram 봇으로 사용하기

1. [@BotFather](https://t.me/BotFather)에서 봇 토큰을 발급받습니다.
2. `~/.companiocc/config.json`에서 Telegram을 설정합니다:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "123456:ABC-DEF...",
      "allowFrom": ["your_telegram_username"]
    }
  }
}
```

3. 게이트웨이를 시작합니다:

```bash
companiocc gateway
```

### 개발자용

```bash
# 1. 저장소 클론 및 개발 의존성 설치
git clone https://github.com/yonggill/companio-cc.git
cd companio-cc
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. 초기 설정
companiocc onboard

# 3. API 키 설정
#    ~/.companiocc/config.json 또는 환경 변수로 설정

# 4. 테스트 실행
pytest

# 5. 린팅 & 타입 체크
ruff check .
mypy companiocc
```

#### 프로젝트 구조

```
companio-cc/
├── companiocc/
│   ├── agent/              # ReAct 에이전트 루프, 컨텍스트, 메모리
│   │   └── tools/          # 내장 도구 (파일, 쉘, 웹, MCP 등)
│   ├── bus/                # 메시지 버스 (이벤트, 큐)
│   ├── channels/           # 채팅 채널 (Telegram 등)
│   ├── config/             # 설정 스키마, 로더
│   ├── cron/               # 크론 스케줄러
│   ├── heartbeat/          # 하트비트 서비스
│   ├── providers/          # LLM 프로바이더 (LiteLLM)
│   ├── session/            # SQLite 세션 관리
│   ├── skills/             # 내장 스킬 (SKILL.md)
│   ├── templates/          # 예제 설정, 워크스페이스 템플릿
│   └── cli/                # CLI 명령어
├── tests/                  # 테스트
└── pyproject.toml
```

---

## 빠른 시작

### 1. 초기 설정

```bash
companiocc onboard
```

`~/.companiocc/config.json`과 워크스페이스 디렉토리(`~/.companiocc/workspace`)가 생성됩니다.

### 2. API 키 설정

`~/.companiocc/config.json`을 열어 사용할 LLM 프로바이더의 API 키를 입력합니다:

```json
{
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    }
  }
}
```

또는 `.env` 파일을 사용할 수도 있습니다:

```bash
cp companiocc/templates/.env.example ~/.companiocc/.env
# 편집기로 API 키 입력
```

### 3. CLI 모드 테스트

```bash
# 단일 메시지
companiocc agent -m "안녕하세요!"

# 대화형 모드
companiocc agent
```

### 4. 게이트웨이 실행

게이트웨이는 Telegram 봇 + 크론 스케줄러 + 하트비트를 한꺼번에 시작합니다:

```bash
companiocc gateway
```

---

## 설정 파일

설정 파일 위치: `~/.companiocc/config.json`

샘플 설정은 `companiocc/templates/config.example.json`을 참고하세요.

### 설정 항목 레퍼런스

#### 에이전트 (`agents.defaults`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `workspace` | 워크스페이스 경로 | `~/.companiocc/workspace` |
| `model` | LLM 모델 | `anthropic/claude-opus-4-5` |
| `provider` | 프로바이더 선택 (`auto`이면 모델명에서 자동 감지) | `auto` |
| `maxTokens` | 최대 응답 토큰 수 | `8192` |
| `temperature` | 생성 온도 | `1.0` |
| `maxToolIterations` | 최대 도구 반복 횟수 | `40` |
| `memoryWindow` | 컨텍스트에 포함할 메시지 수 | `200` |
| `reasoningEffort` | 추론 수준 (`low` / `medium` / `high`) | `medium` |

#### 프로바이더 (`providers`)

| 항목 | 설명 |
|------|------|
| `providers.anthropic.apiKey` | Anthropic API 키 |
| `providers.openai.apiKey` | OpenAI API 키 |
| `providers.gemini.apiKey` | Gemini API 키 |
| `providers.*.apiBase` | 커스텀 API 엔드포인트 |
| `providers.*.extraHeaders` | 추가 HTTP 헤더 |

#### 채널 (`channels`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `sendProgress` | 진행 상황 스트리밍 | `true` |
| `sendToolHints` | 도구 호출 힌트 전송 | `false` |
| `telegram.enabled` | Telegram 활성화 | `false` |
| `telegram.token` | 봇 토큰 | — |
| `telegram.allowFrom` | 허용된 사용자 (username 또는 ID) | `[]` |
| `telegram.proxy` | SOCKS5 프록시 | — |
| `telegram.replyToMessage` | 메시지에 대한 답장 형태 | `false` |

#### 도구 (`tools`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `restrictToWorkspace` | 파일 도구를 워크스페이스 내로 제한 | `true` |
| `web.proxy` | HTTP/SOCKS5 프록시 | — |
| `web.search.apiKey` | Brave Search API 키 | — |
| `web.search.maxResults` | 웹 검색 최대 결과 수 | `5` |
| `exec.timeout` | 쉘 명령 타임아웃 (초) | `60` |
| `exec.pathAppend` | PATH에 추가할 디렉토리 | — |
| `obsidian.enabled` | Obsidian 도구 활성화 | `false` |
| `obsidian.vaultPath` | Obsidian vault 경로 | — |
| `mcpServers` | MCP 서버 연결 설정 | `{}` |

#### 게이트웨이 (`gateway`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `host` | 바인드 주소 | `0.0.0.0` |
| `port` | 게이트웨이 포트 | `18790` |
| `heartbeat.enabled` | 하트비트 활성화 | `true` |
| `heartbeat.intervalS` | 하트비트 주기 (초) | `600` |

### 환경 변수

`COMPANIO_` 접두사와 `__` 구분자로 모든 설정을 환경 변수로 덮어쓸 수 있습니다:

```bash
export COMPANIO_PROVIDERS__ANTHROPIC__API_KEY="sk-ant-..."
export COMPANIO_AGENTS__DEFAULTS__TEMPERATURE=0.5
```

---

## CLI 명령어

```
companiocc onboard          # 초기 설정 (config, workspace 생성)
companiocc agent -m "..."   # 단일 메시지 전송
companiocc agent            # 대화형 모드
companiocc gateway          # 게이트웨이 시작 (Telegram + 크론 + 하트비트)
companiocc channels status  # 채널 상태 확인
companiocc status           # 전체 상태 확인
companiocc --version        # 버전 확인
```

### 주요 옵션

```
companiocc agent --config /path/to/config.json   # 설정 파일 지정
companiocc agent --workspace /path/to/workspace  # 워크스페이스 지정
companiocc agent --no-markdown                   # 마크다운 렌더링 비활성화
companiocc agent --logs                          # 런타임 로그 출력
companiocc gateway --port 8080                   # 게이트웨이 포트 지정
companiocc gateway --verbose                     # 상세 로그 출력
```

### 채팅 내 특수 명령어

| 명령어 | 설명 |
|--------|------|
| `/new` | 새 세션 시작 (메모리 통합 후 초기화) |
| `/help` | 도움말 표시 |
| `/stop` | 실행 중인 서브에이전트 및 작업 취소 |

---

## 내장 도구

에이전트가 자율적으로 선택하여 사용하는 함수형 도구입니다.

### 기본 도구

항상 사용 가능한 도구입니다.

| 도구 | 이름 | 설명 |
|------|------|------|
| 📄 파일 읽기 | `read_file` | 파일 내용 읽기 (최대 128KB) |
| ✏️ 파일 쓰기 | `write_file` | 파일 생성 또는 덮어쓰기 |
| 🔧 파일 편집 | `edit_file` | 파일의 특정 라인 범위를 수정 |
| 📁 디렉토리 목록 | `list_dir` | 디렉토리 내용 나열 |
| 💻 쉘 실행 | `exec` | 쉘 명령어 실행 (시크릿 자동 마스킹) |
| 🔍 웹 검색 | `web_search` | Brave Search API로 웹 검색 |
| 🌐 웹 페치 | `web_fetch` | 웹페이지 내용 가져오기 (HTML → 텍스트 변환) |
| 💬 메시지 | `message` | 채팅 채널에 메시지 전송 (텍스트, 이미지, 파일) |
| 🤖 서브에이전트 | `spawn` | 백그라운드 작업용 서브에이전트 생성 |

### 조건부 도구

설정에 따라 활성화되는 도구입니다.

| 도구 | 이름 | 활성화 조건 | 설명 |
|------|------|-------------|------|
| ⏰ 크론 | `cron` | 크론 서비스 연결 시 | 리마인더 및 반복 작업 예약 |
| 📓 Obsidian | `obsidian` | `tools.obsidian.enabled: true` | Obsidian vault 노트 관리 (검색, 읽기, 생성, 목록) |

### MCP 도구

`tools.mcpServers`에 설정된 MCP 서버의 도구가 `mcp_{서버명}_{도구명}` 형태로 자동 등록됩니다.

#### 설정 예시

```json
{
  "tools": {
    "mcpServers": {
      "playwright": {
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
        "toolTimeout": 60
      },
      "my-api": {
        "url": "http://localhost:8080",
        "headers": { "Authorization": "Bearer token" }
      }
    }
  }
}
```

#### 지원 트랜스포트

| 트랜스포트 | 설정 방식 | 설명 |
|-----------|----------|------|
| **stdio** | `command` + `args` | 로컬 프로세스 실행 |
| **SSE** | `url` | Server-Sent Events |
| **streamableHttp** | `url` | Streamable HTTP |

---

## 스킬 시스템

스킬은 에이전트에게 특정 도구의 사용법을 가르치는 마크다운 파일(`SKILL.md`)입니다. 에이전트가 컨텍스트에서 스킬 목록을 확인하고, 필요할 때 전체 내용을 로드하여 참고합니다.

### 내장 스킬

| 스킬 | 설명 | 자동 로드 |
|------|------|-----------|
| **memory** | 2계층 메모리 시스템 (MEMORY.md + HISTORY.md) 관리법 | ✅ |
| **cron** | 리마인더와 반복 작업 스케줄링 | — |
| **browser** | Playwright MCP를 통한 브라우저 자동화 (네비게이션, 클릭, 폼 입력, 스크린샷 등) | — |
| **obsidian** | Obsidian vault 노트 검색, 읽기, 생성, 정리 | — |
| **google-workspace** | gws CLI를 통한 Google Workspace 연동 (Gmail, Drive, Calendar, Sheets 등) | — |
| **skill-creator** | 커스텀 스킬 생성 가이드 | — |

### 커스텀 스킬 만들기

워크스페이스의 `skills/` 디렉토리에 스킬 폴더를 만들면 자동으로 인식됩니다:

```
~/.companiocc/workspace/skills/
└── my-skill/
    └── SKILL.md
```

`SKILL.md` 프론트매터 형식:

```yaml
---
name: my-skill
description: 스킬에 대한 간단한 설명.
always: false
metadata:
  companiocc:
    requires:
      bins: ["some-cli"]
      env: ["SOME_API_KEY"]
---

# 스킬 내용 (마크다운)
에이전트가 참고할 도구 사용법, 예시, 주의사항 등을 작성합니다.
```

| 프론트매터 | 설명 |
|-----------|------|
| `name` | 스킬 고유 이름 |
| `description` | 스킬 목록에 표시되는 설명 |
| `always` | `true`이면 항상 컨텍스트에 포함 |
| `metadata.companiocc.requires.bins` | 필요한 CLI 바이너리 목록 |
| `metadata.companiocc.requires.env` | 필요한 환경 변수 목록 |

---

## 지원 LLM

[LiteLLM](https://docs.litellm.ai/)을 통해 다양한 모델을 지원합니다:

| 프로바이더 | 모델 예시 | 설정 키 |
|-----------|----------|---------|
| Anthropic | `anthropic/claude-opus-4-5`, `anthropic/claude-sonnet-4-20250514` | `providers.anthropic.apiKey` |
| OpenAI | `openai/gpt-4o`, `openai/o1` | `providers.openai.apiKey` |
| Gemini | `gemini/gemini-2.5-pro` | `providers.gemini.apiKey` |

`provider`를 `auto`로 설정하면 모델명에서 프로바이더를 자동 감지합니다.

---

## 아키텍처

### ReAct 에이전트 루프

```
사용자 메시지
    ↓
컨텍스트 구성 (시스템 프롬프트 + 메모리 + 스킬 + 히스토리)
    ↓
┌─→ LLM 호출 (도구 정의 포함)
│       ↓
│   도구 호출? ──Yes──→ 도구 실행 → 결과를 메시지에 추가 ─┐
│       │                                                  │
│      No                                                  │
│       ↓                                                  │
│   최종 응답 반환                              (최대 40회 반복)
│                                                          │
└──────────────────────────────────────────────────────────┘
```

- 세션별 잠금으로 동시 메시지 처리 시 안전성 보장
- 도구 실행 결과는 히스토리에 500자, 출력에 10,000자로 제한
- 에러 발생 시 자동 복구 힌트 제공

### 2계층 메모리

| 계층 | 파일 | 컨텍스트 포함 | 용도 |
|------|------|--------------|------|
| **장기 메모리** | `memory/MEMORY.md` | ✅ 항상 | 사용자 정보, 설정, 핵심 사실 |
| **이벤트 로그** | `memory/HISTORY.md` | ❌ | grep 검색 가능한 대화 요약 |

세션 메시지가 `memoryWindow`를 초과하면 자동으로 통합(consolidation)이 실행되어 오래된 메시지를 요약하고, MEMORY.md와 HISTORY.md에 기록합니다.

### 하트비트

주기적으로(기본 10분) `HEARTBEAT.md`를 읽고 LLM이 실행 여부를 판단합니다:

1. **판단 단계**: LLM이 HEARTBEAT.md를 읽고 skip/run 결정
2. **실행 단계**: run이면 전체 에이전트 루프로 작업 수행
3. **결과 전달**: 필요 시 채팅 채널로 결과 전송

### 크론 스케줄러

| 스케줄 방식 | 예시 | 설명 |
|-------------|------|------|
| `every_seconds` | `1200` | 20분마다 반복 |
| `cron_expr` | `"0 9 * * 1-5"` | 평일 오전 9시 |
| `at` | ISO 타임스탬프 | 특정 시각 1회 실행 |

작업 유형:
- **리마인더**: 메시지 직접 전달
- **태스크**: 에이전트가 작업 설명을 받아 자율 실행
- **1회성**: 실행 후 자동 삭제 (`delete_after_run: true`)

저장소: `~/.companiocc/workspace/cron/jobs.json`

### 서브에이전트

`spawn` 도구로 백그라운드에서 독립적인 에이전트를 실행합니다:

- 반복 제한: 15회 (메인 에이전트의 40회보다 적음)
- 제한된 도구: 파일, 웹, 쉘만 사용 가능 (메시지, spawn, cron 불가)
- 결과는 원래 세션으로 보고

### 세션 관리

- SQLite 기반 (`companiocc.db`), WAL 모드
- 세션별 원자적 쓰기 + 잠금
- 재시작해도 대화 이력 유지
- 메모리 통합 지점 추적

---

## 보안

- **워크스페이스 제한** — `restrictToWorkspace: true` (기본값)일 때, 모든 파일 도구는 워크스페이스 내부로만 접근 가능
- **SSRF 방어** — 웹 페치 도구가 내부 네트워크 주소(10.x, 172.16.x, 192.168.x, 127.x, ::1 등) 접근을 차단
- **시크릿 필터링** — 쉘 실행 결과에서 API 키, 토큰, 비밀번호 등 민감 정보를 자동 마스킹

---

## 개발

```bash
# 테스트 실행
pytest

# 린팅
ruff check .

# 타입 체크
mypy companiocc
```

---

## 라이선스

MIT

## Acknowledgments

이 프로젝트는 [nanobot](https://github.com/HKUDS/nanobot) (HKUDS)에서 영감을 받아 개발되었습니다.
