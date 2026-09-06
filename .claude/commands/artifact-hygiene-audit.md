---
description: .claude/artifacts/ 산출물 위생 상태를 read-only로 점검한다. 수정·삭제·이동은 절대 하지 않는다.
---

아래 항목을 순서대로 점검하고 보고서를 출력해줘.
**절대 파일 수정·삭제·이동·Notion 쓰기를 하지 말 것. 보고서 출력만 한다.**

---

## 점검 항목

### 1. Slug 규칙 위반 검사
`.claude/artifacts/` 하위 전체를 재귀 탐색해서 아래를 확인한다.

**위반 패턴:**
- 파일명에 `-final`, `-v2`, `-v3`, `-수정`, `-수정본`, 날짜(`-20`, `-26`) 접미사 포함
- 파일명에 한글 포함
- 파일명에 공백 포함
- 같은 slug에 리뷰 파일이 2개 이상 존재 (`[slug]-review.md`가 아닌 변형본)

위반 파일 발견 시 경로와 위반 사유를 목록으로 출력한다.

### 2. 폴더별 파일 현황
각 폴더의 파일 목록과 개수를 출력한다.

| 폴더 | 파일 수 | 파일 목록 |
|---|---|---|
| `archive_drafts/` | | |
| `blog_drafts/` | | |
| `blog_reviews/` | | |
| `naver/` (md 파일만) | | |
| `naver/images/` | | |
| `keywords/` | | |
| `sns/` | | |
| `pipeline_runs/` | | |

### 3. slug별 파이프라인 완성도
현재 존재하는 slug 목록을 추출한 뒤, 각 slug의 단계별 산출물 존재 여부를 표로 출력한다.

| slug | archive_draft | blog_draft | review | naver.md | 비고 |
|---|---|---|---|---|---|

Known Limitation은 아래와 같이 표기한다:
- `mit-gsw-2026` archive_draft 없음: `[Known Limitation — blog_draft부터 시작]`

### 4. naver.md 마커 상태
`.claude/artifacts/naver/` 안의 각 `.md` 파일에 대해 아래를 확인한다.

| 파일 | `[인용구]` 마커 | `[구분선]` 마커 | 포맷 상태 |
|---|---|---|---|

- 마커 있으면: 개수와 위치 섹션명 요약
- 마커 없으면: `구형 포맷 (수동 적용 필요)`

### 5. naver/images 이미지 현황
`.claude/artifacts/naver/images/` 하위 폴더별로 이미지 파일 목록과 개수를 확인한다.

- 각 폴더의 이미지 총 수
- 파일 확장자 분포 (jpg/png/gif 등)
- 권장 최소 7장 대비 현황

### 6. blog_reviews 리뷰 점수 요약
각 `[slug]-review.md` 파일에서 `총점:` 줄을 찾아 점수를 추출한다.

| slug | 총점 | 합격 여부 |
|---|---|---|

점수 줄을 찾지 못하면 `[파싱 불가]`로 표기한다.

### 7. outputs/ 레거시 폴더 상태
`outputs/` 폴더가 존재하는지 확인하고, 내부 파일 목록을 출력한다.
이 폴더는 삭제 금지 대상이므로 현황 파악만 한다.

---

## 출력 형식

```
# Artifact Hygiene Audit Report
실행 시각: [현재 시각]

## Slug 규칙 위반
[위반 없음 / 위반 목록]

## 폴더별 파일 현황
| 폴더 | 파일 수 | 파일 목록 |
...

## slug별 파이프라인 완성도
| slug | archive | blog | review | naver | 비고 |
...

## naver.md 마커 상태
| 파일 | [인용구] | [구분선] | 상태 |
...

## naver/images 이미지 현황
...

## 리뷰 점수 요약
| slug | 총점 | 합격 여부 |
...

## outputs/ 레거시 폴더
...

## 종합 요약
- 정상: [목록]
- 주의: [목록]
- 수동 조치 필요: [목록]
```

$ARGUMENTS가 있으면 해당 항목만 집중 점검한다. (예: `slug` → slug 규칙만, `naver` → naver 관련 3,4,5번만)
없으면 전체 항목을 점검한다.
