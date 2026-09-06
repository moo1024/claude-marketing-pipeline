---
description: PDF 또는 메모 → notion-archive-manager → 아카이브 초안 생성
---

## Step 0 — 환경 확인 (PDF 입력 시)

`$ARGUMENTS`가 `.pdf`로 끝나면 먼저 아래를 실행한다.

```bash
which pdftotext
```

- 있으면 → Step 1으로 진행
- 없으면 → 아래를 출력하고 즉시 중단:

```
[중단] pdftotext가 설치되어 있지 않습니다.
터미널에서 아래 명령을 실행 후 다시 시도하세요:
! sudo apt-get install -y poppler-utils
```

---

## Step 1 — 원자료 포획 (아카이브보다 먼저)

`$ARGUMENTS` 경로의 원본에서 **수치·날짜·기관명 구간만 출처와 함께 발췌**해
`.claude/artifacts/fact_sources/[slug]-source.md`로 저장한다.

이 단계를 건너뛰면 안 된다. 블로그는 아카이브의 파생본이므로, 원본을 잡아두지 않으면
나중 팩트체크가 파생본끼리 대조하는 순환 검증이 된다(아카이브가 틀리면 블로그도 통과).
사용자 원본이 손에 있는 지금이 유일한 포획 시점이다.

- 발췌 규칙·형식: `.claude/artifacts/fact_sources/README.md`,
  notion-archive-manager의 `원자료 포획` 절차
- 원본에 인쇄된 값 그대로 옮긴다. **원본에 없는 값을 적지 않는다.**
- 같은 지표가 원본 안에서 다른 값으로 나오면 모두 남기고 채택값·근거를 명시한다.

## Step 2 — 아카이브 초안 생성

`$ARGUMENTS` 경로의 자료를 읽어 notion-archive-manager로 Notion 문서형 아카이브 초안을 생성해줘.

저장 경로: `.claude/artifacts/archive_drafts/`
파일명 형식: `[slug]-archive-draft.md` (예: `mit-gsw-2026-archive-draft.md`)

초안의 수치는 Step 1에서 저장한 fact_sources 발췌값과 일치해야 한다.

완료 후 저장 경로(archive_draft + fact_sources), 확인 필요사항,
Notion 반영 전 승인 필요사항을 출력해줘.
