---
description: 검수 통과 블로그 초안 → 네이버 블로그 최적화 변환
---

아래 단계를 반드시 순서대로 실행한다.  
**Step 0을 완료하기 전에 channel-distributor에 절대 위임하지 않는다.**

---

## Step 0 — Review Gate (Hard Check)

### 0-1. 슬러그 추출

입력 경로 `$ARGUMENTS`의 파일명에서 슬러그를 추출한다.  
파일명 형식: `[slug]-blog-draft.md` → slug = `[slug]`

예시:
- `.../knu-idea-bridge-2026-blog-draft.md` → slug = `knu-idea-bridge-2026`
- `.../google-ai-hackathon-2026-blog-draft.md` → slug = `google-ai-hackathon-2026`

### 0-2. Review 파일 탐색

아래 두 경로를 순서대로 탐색한다.

1. `.claude/artifacts/blog_reviews/[slug]-review.md`
2. `.claude/artifacts/blog_reviews/[slug]-review-final.md`

```bash
find ".claude/artifacts/blog_reviews" \( -name "[slug]-review.md" -o -name "[slug]-review-final.md" \) 2>/dev/null
```

**탐색 결과가 없으면 즉시 아래를 출력하고 종료한다:**
```
[중단] 검수 리포트가 없습니다.
먼저 다음 명령을 실행하세요: /blog-review $ARGUMENTS
```

### 0-3. 총점 확인

탐색된 review 파일에서 총점 줄을 읽는다.

```bash
grep "총점:" "[탐색된 review 파일 경로]"
```

총점 표기 형식: `총점: XX/100`

| 조건 | 출력 후 동작 |
|---|---|
| grep 결과 없음 (형식 불일치 또는 빈 결과) | `[중단] review 파일에서 총점을 읽을 수 없습니다. 파일 형식을 확인하세요.` → 종료 |
| 총점 < 80 | `[중단] 총점 XX점 — 합격 기준(80점) 미달입니다. Fix 후 /blog-review를 재실행하세요.` → 종료 |
| 총점 ≥ 80 | `[통과] 총점 XX점 — Review Gate 통과. 네이버 블로그 변환을 시작합니다.` → Step 0-4로 진행 |

### 0-4. 맞춤법 검사 결과 확인

review 파일에서 맞춤법 검사 섹션을 읽는다.

```bash
grep -A 3 "맞춤법 검사 결과" "[탐색된 review 파일 경로]"
```

결과에 따라 아래 변수를 설정한다:

| 조건 | 체크리스트 반영 |
|---|---|
| "맞춤법 이상 없음" 포함 | `[x] 맞춤법 검사 완료 (blog-review 자동 완료)` |
| 오류 목록 있음 | `[ ] 맞춤법 검사 완료 — 오류 발견됨 (아래 목록 확인 후 수정)` + 오류 목록 출력 |
| 섹션 없음 (구버전 review) | `[ ] 맞춤법 검사 완료 — 수동 진행 필요 (/blog-review 재실행 권장)` |

---

## Step 1 — channel-distributor에 위임

Review Gate 통과 후에만 실행한다.

`$ARGUMENTS` 경로의 블로그 초안을 channel-distributor로 네이버 블로그 발행 형식으로 변환해줘.

`.claude/rules/naver-blog-format.md` 기준을 따른다.

저장 경로: `.claude/artifacts/naver/`
파일명 형식: `[slug]-naver.md` (예: `knu-idea-bridge-2026-naver.md`)

맞춤법 검사 체크리스트 항목은 Step 0-4에서 확인한 결과로 채워줘.

저장 완료 후 아래를 출력해줘:
1. 저장 파일 경로
2. 최적화 제목
3. 태그 수
4. 발행 체크리스트 (미완료 항목 강조)
