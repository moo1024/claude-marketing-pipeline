---
description: 검수 통과 블로그 초안 → 인스타그램 캐러셀 + Threads 변환 (카드 이미지 렌더링 포함)
---

아래 단계를 반드시 순서대로 실행한다.
**Step 0을 완료하기 전에 sns-distributor에 절대 위임하지 않는다.**

---

## Step 0 — Review Gate (Hard Check)

### 0-1. 슬러그 추출

입력 경로 `$ARGUMENTS`의 파일명에서 슬러그를 추출한다.
파일명 형식: `[slug]-blog-draft.md` → slug = `[slug]`

### 0-2. Review 파일 탐색

```bash
find ".claude/artifacts/blog_reviews" \( -name "[slug]-review.md" -o -name "[slug]-review-final.md" \) 2>/dev/null
```

**탐색 결과가 없으면 즉시 아래를 출력하고 종료한다:**
```
[중단] 검수 리포트가 없습니다.
먼저 다음 명령을 실행하세요: /blog-review $ARGUMENTS
```

### 0-3. 총점 확인

```bash
grep "총점:" "[탐색된 review 파일 경로]"
```

| 조건 | 출력 후 동작 |
|---|---|
| grep 결과 없음 | `[중단] review 파일에서 총점을 읽을 수 없습니다.` → 종료 |
| 총점 < 80 | `[중단] 총점 XX점 — 합격 기준(80점) 미달입니다. Fix 후 /blog-review를 재실행하세요.` → 종료 |
| 총점 ≥ 80 | `[통과] 총점 XX점 — Review Gate 통과. SNS 변환을 시작합니다.` → Step 1 진행 |

---

## Step 1 — sns-distributor에 위임

Review Gate 통과 후에만 실행한다.

`$ARGUMENTS` 경로의 블로그 초안을 sns-distributor로 인스타그램 캐러셀 + Threads 형식으로 변환해줘.

`.claude/rules/sns-format.md`와 `docs/sns-winning-patterns.md` 기준을 따른다.

저장 경로: `.claude/artifacts/sns/`
파일명: `[slug]-instagram.md`, `[slug]-threads.md`
카드 이미지: `scripts/carousel_render.py` 실행 → `.claude/artifacts/sns/images/[slug]/`

저장 완료 후 아래를 출력해줘:
1. 저장 파일 경로 2개
2. 카드 생성 결과 (N장, manifest 경로)
3. 캡션 첫 줄 + 해시태그 수
4. 발행 체크리스트 (미완료 항목 강조)

---

## Step 2 — 발행 안내 (자동 발행 금지)

- Buffer 초안 큐 등록이 필요하면: `python3 scripts/sns_publish.py [slug]` (기본 --dry-run, Phase 3-C)
- **발행 버튼은 항상 사람이 누른다.**
