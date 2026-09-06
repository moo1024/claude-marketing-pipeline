---
description: naver.md → Playwright로 네이버 블로그 에디터 자동 입력 (발행은 사람이 직접)
---

## 사전 확인 — Playwright 설치

Playwright가 없으면 먼저 실행해주세요 (최초 1회):
```
! pip install playwright
! playwright install chromium
```

---

## Step 1 — 경로 확인

`$ARGUMENTS`가 slug(`knu-idea-bridge-2026`)면 naver.md 경로로 변환한다:

```
.claude/artifacts/naver/[slug]-naver.md
```

파일 경로(`.md`로 끝남)면 그대로 사용한다.

파일이 없으면 출력하고 종료:
```
[중단] naver.md 없음: .claude/artifacts/naver/[slug]-naver.md
먼저 /channel-distribute .claude/artifacts/blog_drafts/[slug]-blog-draft.md 를 실행하세요.
```

---

## Step 2 — 스크립트 실행

```bash
python3 scripts/naver_publish.py [naver.md 경로]
```

스크립트가 하는 일:
1. naver.md에서 제목 / 본문 / 태그 파싱
2. Chromium 브라우저 실행 (화면 표시)
3. 네이버 로그인 확인 (미로그인이면 대기)
4. 블로그 글쓰기 페이지 이동
5. 제목 자동 입력
6. 본문 HTML 주입
7. 태그 자동 입력
8. 스크린샷 저장 → `/tmp/naver_preview.png`
9. 사람이 발행 버튼 클릭 후 엔터로 종료

---

## Step 3 — 완료 안내

스크립트 실행 후 남은 수동 작업을 안내한다:

```
남은 작업 (수동):
  1. 이미지 최소 3장 삽입 — naver.md 이미지 삽입 가이드 참조
  2. [확인 필요] 항목 직접 수정
  3. 발행 버튼 클릭 (자동 발행 금지 — CLAUDE.md 정책)
```

---

## 오류 시 대처

| 증상 | 확인 사항 |
|---|---|
| 제목/본문/태그 입력 실패 | `/tmp/naver_error_*.png` 스크린샷 확인. 에디터 업데이트 시 `scripts/naver_publish.py` 상단 셀렉터 수정 |
| 브라우저가 열리지 않음 | `playwright install chromium` 재실행 |
| 로그인 반복 요구 | 프로필 경로 `~/.claude/config/naver-browser-profile/` 확인 |
