# Artifact Storage Rules

## Purpose

Moduus Marketing Team에서 생성되는 모든 산출물의 저장 위치를 통일한다.

---

## Standard Folders

- `.claude/artifacts/archive_drafts/`
  - notion-archive-manager가 만든 문서형 아카이브 초안
  - 예: `mit-gsw-2026-archive-draft.md`

- `.claude/artifacts/blog_drafts/`
  - marketing-content-writer가 만든 블로그 초안 Markdown
  - 예: `mit-gsw-2026-blog-draft.md`

- `.claude/artifacts/blog_reviews/`
  - 블로그 검수표, Pass/Fix 결과, 수정 제안
  - 예: `mit-gsw-2026-review.md`

- `.claude/artifacts/fact_sources/`
  - **사용자 제공 원본 발췌 (PRIMARY — 정량 수치의 기준)**
  - 결과보고서·PDF·Notion에서 수치·기관명·날짜만 출처와 함께 발췌
  - **아카이브 단계에서 archive_draft와 함께 생성한다** (`archive-structure.md` §4 원자료 포획)
  - `scripts/fact_audit.py`가 자동 탐색하며, `archive_drafts/`(파생본)와 등급을 구분한다
  - 예: `mit-gsw-2026-source.md`

- `.claude/artifacts/naver/`
  - 네이버 블로그 최적화 본문, 태그 목록, 이미지 가이드, 발행 체크리스트
  - 예: `knu-idea-bridge-2026-naver.md`

- `.claude/artifacts/sns/`
  - 인스타그램 캐러셀 문구, Threads/X, LinkedIn 변환 문구 (Phase 3 이후)
  - 예: `mit-gsw-2026-linkedin.md`

- `.claude/artifacts/keywords/`
  - SEO 키워드, 태그, 검색 의도 JSON
  - 예: `mit-gsw-2026-keywords.json`

- `output/design/`
  - PNG, JPG 등 이미지 산출물
  - 예: `mit-gsw-2026-thumbnail.png`

---

## Naming Rule

- 파일명은 lowercase kebab-case 사용
- 공백, 한글 파일명, 특수문자 지양
- 예: `mit-gsw-2026-blog-draft.md`

---

## Slug 규칙 (정본)

슬러그는 모든 에이전트의 공통 기준이다. 각 에이전트의 File Save Rule은 이 정본을 따른다.

**형식:** `[행사키워드]-[연도]`

예시:
- `knu-idea-bridge-2026`
- `mit-gsw-2026`
- `google-ai-hackathon-2026`

**파일별 접미사:**

| 산출물 | 파일명 형식 |
|---|---|
| 아카이브 초안 | `[slug]-archive-draft.md` |
| 블로그 초안 | `[slug]-blog-draft.md` |
| 리뷰 리포트 | `[slug]-review.md` |
| 네이버 변환본 | `[slug]-naver.md` |

**금지:**
- `-final`, `-v2`, 날짜, 숫자 버전 접미사 사용 금지
- 한 slug당 리뷰 파일은 반드시 1개 (`[slug]-review.md`)
- 재검수 후에도 같은 파일을 덮어쓴다 — 버전 파일 신규 생성 금지

---

## Output Rule

- 블로그/아카이브/검수/SNS 텍스트 산출물은 Markdown 또는 JSON으로 저장
- 디자인 이미지만 `output/design/`에 저장
- 자동 발행 금지
- 발행용 최종본이라도 사람 검수 전에는 draft로 표시

---

## Legacy Rule

- 기존 `outputs/` 폴더는 읽을 수 있지만, 새 산출물의 기본 저장 위치로 쓰지 않는다.
- 기존 `outputs/` 안의 유효한 결과물은 필요 시 `.claude/artifacts/` 아래로 복사한다.
- 삭제는 사용자 명시 승인 전 금지.
