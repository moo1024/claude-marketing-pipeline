# MCP Safety Rules

## Purpose

이 규칙은 Moduus Marketing Team 프로젝트에서 Notion, Gmail, Google Drive, youtube-transcript, context7 MCP를 안전하게 사용하기 위한 기준이다.

---

## Default Rule

모든 MCP는 사용자가 명시적으로 허락한 범위에서만 사용한다.

작업 전 항상 확인한다:

1. 어떤 MCP를 쓸 것인가
2. 어떤 DB/페이지/파일/메일을 볼 것인가
3. 읽기 작업인가, 쓰기 작업인가
4. 쓰기 작업이면 정확히 무엇을 바꿀 것인가
5. 사용자가 승인했는가

---

## Notion Rules

Notion MCP는 현재 핵심 MCP다.

**읽기 허용 대상 (settings.json allow — 확인 없이 사용 가능):**
- 사용자가 지목한 Notion 페이지
- 사용자가 지목한 Notion DB
- 블로그/아카이브 작업에 필요한 DB 스키마
- 사용자가 승인한 개별 행사 페이지
- **팩트 대조 목적의 행사 페이지 조회** — `content-editor-reviewer`가 블로그 초안의
  수치·기관명·날짜를 검증하기 위해 `notion-search` / `notion-fetch`로 해당 행사 페이지를
  읽는 것은 사전 승인된다. 이 에이전트는 **Notion 쓰기 도구를 보유하지 않는다.**

---

**Notion 쓰기 도구 3단계 처리 기준:**

### 1단계 — 사전 승인 (settings.json allow, 승인된 에이전트에 한정)

아래 도구는 `notion-archive-manager`, `marketing-content-writer` 에이전트가 아카이브·블로그 작업에 사용할 수 있도록 사전 승인되어 있다.
사용 전 반드시 어떤 페이지를 어떻게 바꾸는지 먼저 보고한다.

- `notion-update-page` — 행사 아카이브 페이지 본문·속성 업데이트
- `notion-create-pages` — 아카이브 초안 페이지 신규 생성

**⚠️ 쓰기 허용 DB 범위 제한:**
`notion-update-page`와 `notion-create-pages`는 `.claude/config/notion-targets.md`에 명시된 DB에 속한 페이지에만 실행 가능하다.
대상 페이지가 허용 DB 외부에 있으면 즉시 `[쓰기 거부]`를 출력하고 실행을 중단한다.
→ 상세 절차: `.claude/config/notion-targets.md` 참조

### 2단계 — 사용자 확인 필요 (defaultMode: ask)

아래 도구는 settings.json에 사전 승인되어 있지 않아 실행 시 사용자 확인을 받아야 한다.
Notion 구조를 바꾸는 작업이므로 의도를 명확히 설명한 뒤 승인 후 실행한다.

- `notion-create-database` — DB 신규 생성
- `notion-duplicate-page` — 페이지 복제
- `notion-move-pages` — 페이지 이동
- `notion-create-view` / `notion-update-view` — 뷰 생성·수정
- `notion-update-data-source` — 데이터 소스 수정
- `notion-create-comment` — 댓글 작성

### 3단계 — 절대 금지 (어떤 승인도 없이 실행 불가)

- 의미가 불확실한 속성 수정 (`포트폴리오 포함` 등)
- 여러 페이지 일괄 수정
- 페이지 삭제 또는 아카이브
- DB 스키마 구조 변경
- 사용자가 지목하지 않은 페이지 본문 수정

---

**⚠️ 설계 원칙: Notion 쓰기 도구를 settings.json `deny`에 넣지 않는다.**
deny는 settings.local.json으로도 복구할 수 없어 정당한 에이전트 작업까지 영구 차단된다.
쓰기 통제는 `allow`(사전 승인) + `defaultMode: ask`(확인 요구) 조합으로 한다.

---

## Gmail Rules

Gmail MCP는 기본 사용 금지다.

**사용 가능한 경우:**
- 사용자가 특정 행사/기관/담당자 관련 메일 확인을 명시한 경우
- 블로그/아카이브에 필요한 자료 출처를 확인해야 하는 경우

**금지:**
- 전체 메일함 탐색
- 개인 메일 내용 임의 조회
- 메일 발송
- 초안 생성
- 첨부파일 다운로드

---

## Google Drive Rules

Google Drive MCP는 기본 사용 금지다.

**사용 가능한 경우:**
- 사용자가 특정 폴더나 파일을 지목한 경우
- 행사 사진, 결과보고서, 첨부자료를 아카이브에 연결해야 하는 경우

**금지:**
- 전체 Drive 탐색
- 파일 삭제/이동
- 공유 권한 변경
- 대량 다운로드
- 승인 없는 Notion 업로드 연동

---

## Other MCP Rules

**youtube-transcript:**
- 영상 기반 콘텐츠가 필요할 때만 사용한다.

**context7:**
- 개발 문서나 라이브러리 확인이 필요할 때만 사용한다.
- 블로그/아카이브 일반 작업에는 사용하지 않는다.

---

## Sensitive Data

절대 출력하지 않는다:

- 토큰
- API 키
- 계정 정보
- 내부 페이지 ID
- 민감 URL
- 개인 연락처
- 불필요한 로컬 전체 경로

---

## Unclear Property Rule

Notion 속성 의미가 불확실하면 수정하지 않는다.

예:
- `포트폴리오 포함`
- `상태`
- `블로그 여부`
- `공개 여부`
- `우선순위`

먼저 사용자에게 의미를 확인한다.

---

## Output Rule

MCP를 쓰는 작업 전에는 아래 형식으로 먼저 보고한다:

1. 사용할 MCP
2. 읽을 대상
3. 수정 여부
4. 수정 예정 범위
5. 사용자 승인 필요 여부

**예외 — 사전 보고 생략 가능한 자동 파이프라인:**

아래 조건을 모두 충족하면 사전 보고 없이 즉시 실행한다.

- `/blog-review` 커맨드에서 총점 80점 이상 합격이 확정된 직후
- `notion-update-page`로 archive_draft 본문 반영 + `블로그 상태` → `초안` 변경에 한함
- 실행 후 결과를 반드시 출력한다 (사전 보고 대신 사후 보고)
