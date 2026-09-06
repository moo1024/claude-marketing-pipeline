---
description: 블로그 초안 → content-editor-reviewer → 4축 채점 + Fix 제안 + 리뷰 리포트 저장 → (80점 이상) Notion 자동 업데이트
---

$ARGUMENTS 경로의 블로그 초안을 content-editor-reviewer로 검수해줘.

`.claude/rules/review-quality.md` 기준으로 아래 세 가지를 수행해줘:

**⓪ 팩트 대조 (채점보다 먼저)** — 본문의 모든 수치·기관명·날짜를 원자료와 1:1 대조

- **원자료 등급** (블로그는 archive_draft의 파생본이다 — 파생본끼리 대조하면 순환 검증):
  - PRIMARY(원본): `.claude/artifacts/fact_sources/[slug]*.md` — **정량 수치(참여인원·%·건수·팀수)의 유일한 근거**
  - DERIVED(파생): `.claude/artifacts/archive_drafts/[slug]-archive-draft.md` — 구조·정성 서술과 날짜에만 인정
- PRIMARY가 없으면 사용자 제공 원본(결과보고서·PDF)에서 발췌하거나, Notion을 **읽기 전용**으로
  조회(`notion-search` → `notion-fetch`)해 수치·기관명·날짜 발췌를
  `.claude/artifacts/fact_sources/[slug]-source.md`에 저장한다. 원본에 없는 값은 적지 않는다.
- 기계 검증 필수 실행:
  ```bash
  python3 scripts/fact_audit.py $ARGUMENTS
  ```
- **하드게이트**: 미출처 수치가 1건이라도 있으면 총점과 무관하게 불합격(종료 코드 1).
  원자료를 전혀 확보하지 못했거나(`NO_SOURCE`), 정량 수치의 근거가 파생본에만 있으면
  (`NO_PRIMARY`, 종료 코드 2) `[대조 불가]`로 중단하고 합격 처리하지 않는다.
- 수치 대조표를 리뷰 리포트에 반드시 포함 (출처 열에 `fact_sources(원본)`/`archive_draft(파생)` 명시)

**① 4축 채점** (SEO/팩트정확도/브랜드톤/가독성) — 합격 여부 판정

**② 한국어 맞춤법 검사** — 블로그 초안 본문 전체를 읽고 맞춤법·띄어쓰기·문법 오류를 찾는다
- 오류 발견 시: 위치(섹션명 또는 문장 앞부분), 오류 내용, 수정 제안을 목록으로 출력
- 오류 없으면: `맞춤법 이상 없음` 한 줄 표기
- 결과는 리뷰 리포트의 `## 맞춤법 검사 결과` 섹션에 포함

리뷰 리포트 저장 경로: `.claude/artifacts/blog_reviews/`
파일명 형식: `[slug]-review.md`

저장 완료 후 총점, 합격 여부, channel-distributor 전달 가능 여부를 요약 출력해줘.

---

## Notion 자동 업데이트 (총점 80점 이상 **그리고 팩트 하드게이트 통과** 시)

검수 총점이 80점 이상이고 **팩트 하드게이트를 통과한 경우에만** 사용자 확인 없이 아래를 자동으로 실행한다.

**하드게이트 실패(`fact_audit.py` 종료 코드 1) 또는 대조 불가(종료 코드 2)이면 아래를 출력하고 중단한다.**
검수되지 않은 수치가 Notion 아카이브로 전파되는 것을 막기 위함이다.

```
[Notion 업데이트 차단] 팩트 하드게이트 미통과 — 미출처 수치 N건 / 대조 불가(사용자 원본 없음)
총점(XX점)과 무관하게 아카이브 반영을 보류합니다. 수치 확인 후 재검수해주세요.
```

### Step N-1. archive_draft 확인

`$ARGUMENTS` 파일명에서 slug를 추출한다.
- `[slug]-blog-draft.md` → slug = `[slug]`

`.claude/artifacts/archive_drafts/[slug]-archive-draft.md` 존재 여부를 확인한다.

파일 없으면:
```
[Notion 업데이트 스킵] archive_draft 없음: .claude/artifacts/archive_drafts/[slug]-archive-draft.md
Notion 업데이트는 archive_draft 생성 후 수동으로 진행해주세요.
```
출력하고 여기서 멈춘다. 파이프라인 전체는 계속 진행한다.

### Step N-2. notion-archive-manager에 위임

archive_draft 파일이 존재하면, notion-archive-manager에게 아래를 위임한다.

위임 내용:
- `.claude/artifacts/archive_drafts/[slug]-archive-draft.md`를 읽는다.
- archive_draft의 `행사명` 항목으로 Notion 워크스페이스에서 페이지를 검색한다.
- 검색 결과가 없으면:
  ```
  [Notion 업데이트 스킵] "[행사명]" 페이지를 Notion에서 찾을 수 없습니다.
  페이지를 직접 지목해주시면 업데이트할 수 있습니다.
  ```
- 검색 결과가 있으면 확인 없이 바로 실행한다:
  1. 해당 페이지 본문을 archive_draft 내용으로 업데이트한다.
  2. 아래 속성 12개를 archive_draft에서 추출해 업데이트한다.
     **값이 [확인 필요] / [자료 없음] / [추정]이면 해당 속성은 건너뛴다.**
     **의미가 불확실한 속성(`포트폴리오 포함` 등)은 건드리지 않는다.**

     | 속성 | archive_draft 출처 |
     |---|---|
     | 행사 날짜 | 행사 개요 > 기간 (시작일~종료일) |
     | 상태 | 결과보고서 기반 행사이면 `완료`, 아니면 건너뜀 |
     | 내 역할 | 내 역할 섹션 첫 문장 요약 |
     | 협력기관 | 행사 개요 > 주최·주관·협력기관 |
     | 대상 | 행사 개요 > 대상 |
     | 유형 | 행사 개요에서 추출 (특강/해커톤/교육과정/공모전/컨설팅/서포터즈/클래스/행사 중 택1) |
     | 연도 | 행사 개요 > 기간에서 연도 추출 |
     | 핵심 키워드 | SEO 키워드 섹션 > 메인·롱테일 키워드 쉼표 구분 |
     | 사용 도구·기술 | 확인된 경우에만 |
     | 참여 인원 | 운영규모 수치 (확정된 숫자만, 범위·추정이면 건너뜀) |
     | 블로그 상태 | `초안` (고정) |

  3. 완료 후 출력:
  ```
  [Notion 자동 업데이트 완료]
  - 페이지: [행사명]
  - 본문: archive_draft 반영
  - 업데이트 속성: [속성명 목록]
  - 스킵 속성: [속성명 + 이유]
  ```

---

## review_diff.md 생성

Fix 루프가 완료된 시점(합격 확정 또는 3회 종료)에 반드시 아래 경로에 review_diff를 생성한다.

```
.claude/artifacts/blog_reviews/[slug]-review-diff.md
```

- 80점 이상 합격 시 → 판정: `PASS`
- 3회 후 80점 미만 종료 시 → 판정: `NEEDS_MANUAL_REVIEW`
- 저장 실패 시 review 자체는 실패시키지 않고, 아래 문구만 출력한다:
  ```
  [review_diff 저장 실패 — 수동 작성 필요]
  ```

출력 형식은 `.claude/rules/review-quality.md`의 `## review_diff 출력 형식` 섹션을 따른다.
