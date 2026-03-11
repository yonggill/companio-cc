# companiocc

Claude Code CLI 기반 개인 AI 어시스턴트.

Claude Code를 서브프로세스(`claude -p`)로 호출하여, Telegram 등 채팅 채널과 연동하는 경량 게이트웨이입니다.
도구 실행, 파일 접근, 웹 검색 등은 모두 Claude Code가 자체적으로 처리합니다.

---

## 주요 기능

- **Claude Code CLI 위임** — 모든 작업을 `claude -p` 서브프로세스에 위임 (도구, 파일, 웹 등 Claude Code가 처리)
- **세션 유지** — `--session-id` / `--resume`으로 대화 컨텍스트 유지, 토큰 비용 절감
- **Telegram 연동** — 봇을 통한 채팅 인터페이스
- **2계층 메모리** — MEMORY.md (장기) + HISTORY.md (이벤트 로그)
- **세션 관리** — SQLite 기반 대화 영속화 + 비용 추적
- **크론 스케줄러** — 예약 리마인더 및 반복 작업
- **하트비트** — 주기적 자율 점검 (기본 10분)
- **보안** — 환경변수 시크릿 필터링, Claude 내부 변수 격리

---

## 요구사항

- Python 3.11 이상
- [Claude Code CLI](https://claude.ai/code) 설치 및 인증 완료

### 선택 사항

| 기능 | 필요 도구 |
|------|----------|
| MCP 서버 (Playwright, GitHub 등) | Node.js (`npx`) |
| Google Workspace | `npm install -g @googleworkspace/cli` |

---

## 설치

```bash
git clone https://github.com/yonggill/companio-cc.git
cd companio-cc
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 초기 설정
companiocc onboard

# 테스트
companiocc agent -m "안녕하세요!"
```

### Telegram 봇

1. [@BotFather](https://t.me/BotFather)에서 봇 토큰 발급
2. `companiocc onboard`에서 Telegram 설정
3. `companiocc gateway` 실행

---

## 설정

설정 파일: `~/.companiocc/config.json`

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.companiocc/workspace",
      "memoryWindow": 200
    }
  },
  "claude": {
    "maxTurns": 50,
    "timeout": 300,
    "maxConcurrent": 5,
    "model": null
  },
  "channels": {
    "sendProgress": true,
    "telegram": {
      "enabled": false,
      "token": "",
      "allowFrom": [],
      "replyToMessage": false
    }
  },
  "gateway": {
    "heartbeat": { "enabled": true, "intervalS": 600 }
  }
}
```

### 설정 항목

#### Claude CLI (`claude`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `maxTurns` | Claude CLI 최대 agentic 턴 수 | `50` |
| `timeout` | 요청 타임아웃 (초) | `300` |
| `maxConcurrent` | 최대 동시 세션 수 | `5` |
| `model` | 모델 오버라이드 (`null` = CLI 기본값) | `null` |

#### 채널 (`channels`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `sendProgress` | "생각 중..." 진행 알림 전송 | `true` |
| `telegram.enabled` | Telegram 활성화 | `false` |
| `telegram.token` | 봇 토큰 | — |
| `telegram.allowFrom` | 허용된 사용자 (username 또는 ID) | `[]` |
| `telegram.proxy` | HTTP/SOCKS5 프록시 | — |
| `telegram.replyToMessage` | 메시지 답장 형태 | `false` |

#### 게이트웨이 (`gateway`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `heartbeat.enabled` | 하트비트 활성화 | `true` |
| `heartbeat.intervalS` | 하트비트 주기 (초) | `600` |

### 환경 변수

`COMPANIOCC_` 접두사와 `__` 구분자로 설정 오버라이드:

```bash
export COMPANIOCC_CLAUDE__TIMEOUT=600
export COMPANIOCC_CHANNELS__TELEGRAM__TOKEN="123456:ABC..."
```

---

## CLI 명령어

```
companiocc onboard          # 초기 설정
companiocc agent -m "..."   # 단일 메시지
companiocc agent            # 대화형 모드
companiocc gateway          # 게이트웨이 (Telegram + 크론 + 하트비트)
companiocc status           # 상태 확인
companiocc channels status  # 채널 상태
```

### 채팅 명령어

| 명령어 | 설명 |
|--------|------|
| `/new` | 새 세션 시작 (메모리 통합 후 초기화) |
| `/stop` | 진행 중인 작업 취소 |
| `/help` | 도움말 |

---

## 아키텍처

```
사용자 메시지 (Telegram / CLI)
    ↓
MessageBus (inbound)
    ↓
AgentLoop
    ├─ 세션 조회/생성 (SQLite)
    ├─ CLAUDE.md 생성 (시스템 프롬프트 + 메모리)
    ├─ claude -p 서브프로세스 호출
    │   ├─ 첫 호출: --session-id UUID
    │   └─ 이후: --resume SESSION_ID
    ├─ 응답 파싱 (JSON)
    └─ 세션 저장 + 비용 기록
    ↓
MessageBus (outbound)
    ↓
채널 (Telegram / CLI)
```

### Claude CLI 격리

- **프로젝트 디렉토리**: `~/.companiocc/project/` — Claude CLI의 cwd, CLAUDE.md 위치
- **`--add-dir ~/`**: 홈 디렉토리 전체 접근 허용
- **`--dangerously-skip-permissions`**: 자율 에이전트로 동작
- **환경변수 필터링**: API 키, 시크릿, Claude 내부 변수를 서브프로세스에서 제거

### 2계층 메모리

| 계층 | 파일 | 컨텍스트 포함 | 용도 |
|------|------|--------------|------|
| 장기 메모리 | `memory/MEMORY.md` | ✅ 항상 | 핵심 사실, 사용자 정보 |
| 이벤트 로그 | `memory/HISTORY.md` | ❌ | grep 검색 가능한 대화 요약 |

세션 메시지가 `memoryWindow`를 초과하면 자동 통합(consolidation) 실행.

### 프로젝트 구조

```
companio-cc/
├── companiocc/
│   ├── core/              # AgentLoop, ClaudeCLI, ContextBuilder, MemoryStore
│   ├── channels/          # 채팅 채널 (Telegram)
│   ├── config/            # 설정 스키마, 로더, 경로
│   ├── tools/             # companiocc 전용 도구 (message, cron)
│   ├── templates/         # 워크스페이스 템플릿 (SOUL.md, AGENTS.md 등)
│   ├── bus.py             # 메시지 버스
│   ├── cli.py             # CLI 명령어
│   ├── cron.py            # 크론 스케줄러
│   ├── heartbeat.py       # 하트비트 서비스
│   ├── session.py         # SQLite 세션 관리
│   └── helpers.py         # 유틸리티
├── tests/
└── pyproject.toml
```

---

## 개발

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy companiocc
```

---

## 라이선스

MIT

## Acknowledgments

이 프로젝트는 [nanobot](https://github.com/HKUDS/nanobot) (HKUDS)에서 영감을 받아 개발되었습니다.
