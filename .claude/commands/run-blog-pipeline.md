---
description: Moduus Marketing Team 전체 파이프라인 단일 진입점. marketing-orchestrator에 위임한다.
---

# /run-blog-pipeline

Moduus Studio 마케팅 파이프라인을 하나의 명령으로 실행한다.
직접 콘텐츠를 작성하거나 리뷰하지 않고, `marketing-orchestrator`에게 전달한다.

---

## 사용법

```
/run-blog-pipeline <input> [--stage <stage>] [--force] [--skip-archive] [--skip-blog] [--skip-review] [--skip-naver]
```

---

## 지원 입력 형식

| 형식 | 예시 |
|---|---|
| PDF 경로 | `/path/to/결과보고서.pdf` |
| 자료 폴더 경로 | `/path/to/행사자료/` |
| archive_draft 경로 | `.claude/artifacts/archive_drafts/mit-gsw-2026-archive-draft.md` |
| blog_draft 경로 | `.claude/artifacts/blog_drafts/mit-gsw-2026-blog-draft.md` |
| naver.md 경로 | `.claude/artifacts/naver/mit-gsw-2026-naver.md` |
| slug 문자열 | `mit-gsw-2026` |

---

## Stage 옵션

| 옵션 | 실행 범위 |
|---|---|
| `--stage archive` | archive_draft 생성까지 |
| `--stage notion` | archive_draft + Notion 페이지 반영까지 |
| `--stage blog` | blog_draft 생성까지 |
| `--stage review` | review 리포트 생성 + Fix 루프(최대 3회)까지 |
| `--stage naver` | naver.md 변환까지 |
| `--stage publish` | 네이버 브라우저 발행 직전 세팅까지 (명시 요청 시만) |
| `--stage full` | archive → naver 전체 (publish 제외, 기본값) |

**기본값:** stage 미지정 시 `full` (`archive → naver` 순서대로, publish 자동 포함 안 함)

---

## 추가 옵션

| 옵션 | 설명 |
|---|---|
| `--force` | 기존 산출물이 있어도 해당 stage를 재실행 |
| `--skip-archive` | archive stage 강제 스킵 |
| `--skip-blog` | blog stage 강제 스킵 |
| `--skip-review` | review stage 강제 스킵 (비권장) |
| `--skip-naver` | naver stage 강제 스킵 |

---

## 자연어 예시

아래처럼 자연어로도 실행할 수 있다. stage는 marketing-orchestrator가 자동으로 해석한다.

```
/run-blog-pipeline mit-gsw-2026 노션아카이빙까지만
/run-blog-pipeline .claude/artifacts/archive_drafts/knu-idea-bridge-2026-archive-draft.md 블로그 초안까지만
/run-blog-pipeline tech-patent-lecture-2026 검수만
/run-blog-pipeline knu-idea-bridge-2026 네이버 포맷까지만
/run-blog-pipeline mit-gsw-2026 발행 직전까지만 세팅
/run-blog-pipeline 결과보고서.pdf --stage full
```

---

## 안전 정책

> **⚠️ /run-blog-pipeline은 실제 네이버 최종 발행을 수행하지 않는다.**
>
> `--stage publish`는 네이버 에디터 화면에 제목·본문·태그를 입력하는 것까지만 허용한다.
> 발행 완료 버튼, 예약 발행 버튼, 최종 확인 버튼은 **반드시 사람이 직접 클릭**한다.

- `review` 점수 80점 미만이면 `naver` / `publish`로 자동 진행하지 않는다.
- `publish` stage는 사용자가 `--stage publish` 또는 자연어로 "발행 직전까지만"을 명시했을 때만 실행된다.
- Fix 루프는 최대 3회이며, 3회 후에도 80점 미만이면 `[수동 개입 필요]`로 중단한다.

---

## 실행 흐름

```
/run-blog-pipeline <input> [options]
          ↓
   marketing-orchestrator
          ↓
   slug 추출 + stage 결정
          ↓
   기존 산출물 확인
          ↓
   필요한 stage 순서대로 실행:
     archive  → notion-archive-manager (/archive-from-pdf)
     blog     → marketing-content-writer (/blog-from-archive)
     review   → content-editor-reviewer (/blog-review) [Fix 루프 max 3]
     naver    → channel-distributor (/channel-distribute)
     publish  → /naver-publish (명시 요청 시만)
          ↓
   Pipeline 실행 결과 출력
   .claude/artifacts/pipeline_runs/[slug]-run.md 저장
```

---

## 출력 형식

```
## Pipeline 실행 결과

- Slug: [slug]
- 요청 Stage: [stage]
- 실행된 Stages: [list]
- 스킵된 Stages: [list]
- 산출물:
  - [파일명] (생성/스킵/갱신)
- Review 점수: [점수] ([합격/불합격])
- 중단 사유: [있으면 기재]
- 다음 수동 작업: [안내]
```
