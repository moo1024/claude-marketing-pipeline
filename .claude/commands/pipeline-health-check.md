---
description: 마케팅 파이프라인 전체 구조의 건강 상태를 read-only로 점검한다. 수정·삭제·실행은 절대 하지 않는다.
---

아래 항목을 순서대로 점검하고 보고서를 출력해줘.
**절대 수정·삭제·파일 생성·Notion 쓰기·브라우저 실행을 하지 말 것.**

---

## 점검 항목

### 1. Git 상태
- `git status`로 untracked / modified / staged 파일 목록 확인
- `git log --oneline -5`로 최근 5개 commit 확인
- `git diff --stat`으로 미커밋 변경 범위 확인
- working tree clean 여부 판단

### 2. 핵심 파일 존재 여부
아래 파일이 각각 존재하는지 확인한다. 없으면 ❌, 있으면 ✅ 표기.

| 파일 | 역할 |
|---|---|
| `.claude/agents/marketing-orchestrator.md` | 오케스트레이터 에이전트 |
| `.claude/commands/run-blog-pipeline.md` | 단일 진입점 커맨드 |
| `.claude/agents/notion-archive-manager.md` | 아카이브 에이전트 |
| `.claude/agents/marketing-content-writer.md` | 블로그 초안 에이전트 |
| `.claude/agents/content-editor-reviewer.md` | 검수 에이전트 |
| `.claude/agents/channel-distributor.md` | 네이버 변환 에이전트 |
| `.claude/commands/archive-from-pdf.md` | PDF → 아카이브 커맨드 |
| `.claude/commands/blog-from-archive.md` | 아카이브 → 블로그 커맨드 |
| `.claude/commands/blog-review.md` | 검수 커맨드 |
| `.claude/commands/channel-distribute.md` | 네이버 변환 커맨드 |
| `.claude/commands/naver-publish.md` | 발행 직전 세팅 커맨드 |
| `.claude/settings.json` | 공유 권한 정책 |
| `.claude/artifacts/pipeline_runs/` | 실행 로그 폴더 |
| `scripts/naver_publish.py` | Playwright 발행 스크립트 |

### 3. settings.json 무결성
- `.claude/settings.json`을 읽어서 아래를 확인한다.
  - `deny` 목록에 `rm`, `sudo`, `chmod`, `curl`, `wget` 포함 여부
  - `defaultMode` 값
  - `allow`에 `notion-update-page`, `notion-create-pages` 포함 여부
- 파일 내용 전체는 출력하지 않는다. 위 3개 항목만 요약 보고.

### 4. 오케스트레이터 안전장치 확인
`.claude/agents/marketing-orchestrator.md`를 읽어서 아래 문구가 존재하는지 확인한다.

| 항목 | 확인 기준 |
|---|---|
| publish 클릭 금지 | "발행.*금지" 또는 "클릭.*금지" 문구 존재 |
| review 80점 gate | "80" 또는 "≥ 80" 문구 존재 |
| Fix loop max 3 | "최대 3회" 또는 "max 3" 문구 존재 |
| pipeline_runs 저장 | "pipeline_runs" 문구 존재 |

### 5. 민감정보 tracking 의심 여부
`git ls-files`로 추적 중인 파일 중 아래 패턴이 있는지 확인한다.
- `.env`, `*.token`, `cookie*`, `secret*`, `credential*`, `settings.local.json`
- 발견되면 ⚠️ 경고, 없으면 ✅ 정상

---

## 출력 형식

```
# Pipeline Health Check Report
실행 시각: [현재 시각]

## Git 상태
- working tree: [clean / dirty]
- 최근 commit: [hash] [message]
- untracked: [목록 또는 없음]
- modified: [목록 또는 없음]

## 핵심 파일 존재
| 파일 | 결과 |
|---|---|
...

## settings.json 무결성
- deny 포함 여부: ...
- defaultMode: ...
- allow Notion write: ...

## 오케스트레이터 안전장치
| 항목 | 결과 |
|---|---|
...

## 민감정보 Tracking
- 결과: [✅ 정상 / ⚠️ 경고: 파일명]

## 종합 판정
[✅ 정상 운영 가능 / ⚠️ 주의 항목 있음 — 목록]
```

$ARGUMENTS가 있으면 해당 항목만 집중 점검한다. 없으면 전체 항목을 점검한다.
