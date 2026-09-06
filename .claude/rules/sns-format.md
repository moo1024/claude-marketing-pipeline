# SNS Format Rules — 인스타그램 · Threads

## Purpose

검수 통과 블로그 초안(blog_draft)을 인스타그램 캐러셀·Threads 게시물로 변환할 때의 기준을 정의한다.
콘텐츠 공식·디자인 원칙은 `docs/sns-winning-patterns.md`, 금지 표현·팩트 기준은 `.claude/rules/blog-tone.md`를 승계한다.

---

## 1. 입력 조건 (Review Gate)

- 입력: `.claude/artifacts/blog_drafts/[slug]-blog-draft.md`
- **총점 80점 이상 검수 통과본만 변환 가능** (`.claude/artifacts/blog_reviews/[slug]-review.md` 확인)
- 미통과 시 즉시 중단: `[중단] 검수 미통과 초안입니다. /blog-review로 먼저 검수를 완료해주세요.`

## 2. 산출물과 저장 경로

| 산출물 | 경로 |
|---|---|
| 인스타 캐러셀 (문구+캡션+슬라이드 JSON) | `.claude/artifacts/sns/[slug]-instagram.md` |
| Threads (단발형+타래형) | `.claude/artifacts/sns/[slug]-threads.md` |
| 카드 이미지 (렌더링 결과) | `.claude/artifacts/sns/images/[slug]/slide-01.jpg ...` |
| 카드 manifest | `.claude/artifacts/sns/[slug]-carousel-manifest.json` |

slug 규칙은 `.claude/rules/artifact-storage.md` 정본을 따른다. `-final`, `-v2` 등 버전 접미사 금지, 재생성 시 같은 파일 덮어쓰기.

## 3. 인스타그램 변환 규칙

**캐러셀 (후기형 기본 8~10장, 모집형 6장):**
- 슬라이드 구성·순서는 `docs/sns-winning-patterns.md` §1 공식을 따른다.
- 카드 텍스트 분량: 표지 제목 **2줄(≈24자) 이내**, 텍스트 카드 본문 **90자 이내**, 카드당 메시지 1개.
- 수치는 **확인된 것만** 사용. `[확인 필요]`/`[자료 없음]`/`[추정]` 붙은 수치는 **카드·캡션에서 제외**한다 (블로그와 달리 표기를 유지하지 않는다 — 이미지 위 표기는 오히려 신뢰를 깎으므로 아예 싣지 않는다).
- 금지 표현은 blog-tone.md 목록 그대로 적용.

**캡션:**
- 첫 줄 후킹(숫자/문제의식) → 3~6줄 요약 → "자세한 운영기는 프로필 링크" → 해시태그.
- 길이 2,200자 이내(실제 목표 300~600자). **해시태그 5개 이하.**
- 본문에 URL 넣지 않는다(클릭 불가).

## 4. Threads 변환 규칙

- **단발형 1개 + 타래형 1개**를 항상 함께 생성한다 (게시 시 하나만 선택).
- 단발형: 300자 이내, 토픽 태그 1개, 이미지 1~2장 지정.
- 타래형: 루트 + 리플 2~4개 + 마지막 리플(블로그 링크). 각 게시물 500자 이내.
- 네이버 블로그 링크는 **발행된 실제 URL 확인 후 삽입** — 미발행이면 `[블로그 URL — 발행 후 삽입]` 플레이스홀더로 남긴다.
- 화자: 모드어스 운영 담당자 개인 톤 (기관 공지체 금지). 존댓말 유지하되 구어체 허용.

## 5. 슬라이드 JSON 블록 (기계가독 — carousel_render.py 계약)

`[slug]-instagram.md` 안에 반드시 **json 코드펜스 1개**로 슬라이드 정의를 포함한다.
`scripts/carousel_render.py`는 파일 내 첫 번째 ```json 블록을 파싱한다.

```
{
  "slug": "knu-idea-bridge-2026",
  "slides": [
    {"n": 1, "template": "cover",   "photo": "IMG_6068.jpg", "kicker": "행사 운영 사례", "title": "243명이 모인\n팀 빌딩 행사", "sub": "2026 KNU 아이디어브릿지"},
    {"n": 2, "template": "metrics", "kicker": "숫자로 보는 결과", "title": "목표 100명, 결과는", "metrics": [{"value": "243명", "label": "총 참여자"}], "footnote": ""},
    {"n": 3, "template": "photo",   "photo": "IMG_6100.jpg", "caption": "한 줄 캡션"},
    {"n": 4, "template": "info",    "title": "행사 개요", "rows": [{"icon": "📅", "label": "일시", "value": "2026.4.27 13-18시"}]},
    {"n": 5, "template": "text",    "kicker": "운영 설계 ①", "title": "소제목", "body": "본문 90자 이내", "bullets": ["불릿"]},
    {"n": 10, "template": "cta",    "title": "저장해두세요", "body": "CTA 문장", "team": "MODUUS STUDIO"}
  ]
}
```

**템플릿 6종과 필수 필드:**

| template | 용도 | 필수 필드 | 선택 필드 |
|---|---|---|---|
| `cover` | 표지 (사진배경+오버레이) | photo, title | kicker, sub |
| `metrics` | 수치 3개 카드 | metrics(1~3개) | kicker, title, footnote |
| `photo` | 사진+캡션바 | photo, caption | kicker |
| `info` | 정보 카드 | rows(icon/label/value) | title |
| `text` | 텍스트 카드 (설계 포인트·개선점·팀 소개) | title | kicker, body, bullets, photo(배경) |
| `cta` | 마지막 CTA | title | body, team |

- `photo` 값은 `.claude/artifacts/sns/images/[slug]/` 또는 `.claude/artifacts/naver/images/[slug]/`의 **실제 파일명** (렌더러가 두 폴더 순서로 탐색).
- `title`/`body`의 `\n`은 줄바꿈으로 렌더링된다.
- 이미지 규격: **1080×1350 (4:5) JPEG** 고정, 8MB 이하, 핵심 텍스트는 중앙 1:1 안전영역.

## 6. 사진 선택 규칙

1. **1순위**: `.claude/artifacts/naver/images/[slug]/`의 검증된 사진 재사용 (네이버 변환 때 수집본).
2. 없으면 Desktop 행사 폴더 탐색 (channel-distributor의 매핑 테이블 준용).
3. 표지: 현장 전경·대표 컷. 포스터는 표지보다 photo 카드에 배치 (텍스트 겹침 방지).
4. 동일·유사 컷 중복 사용 금지. 네이버 본문과 겹쳐도 무방 (채널이 다름).

## 7. 발행 체크리스트 (산출물에 필수 포함)

```
[ ] 슬라이드 1~3 트리플 훅 확인
[ ] 미확인 수치 카드/캡션 미포함 확인
[ ] 해시태그 5개 이하 (인스타) / 토픽 태그 1개 (Threads)
[ ] 카드 8~10장 JPEG 생성 완료 (scripts/carousel_render.py)
[ ] Threads 블로그 링크 실제 URL 확인
[ ] 사람이 최종 확인 후 발행 (Buffer 초안 큐 → 사람이 발행 버튼)
```

## 8. 금지

- **자동 발행 금지** — sns_publish.py는 초안 큐 등록까지만. 발행 버튼은 사람.
- API 키·토큰 출력 금지 (`.env` 관리).
- 미확인 수치·성과 단정 금지.
- 기존 네이버 파이프라인 파일 수정 금지.

## References

- `docs/sns-winning-patterns.md` — 콘텐츠 공식·디자인 원칙·레퍼런스
- `.claude/rules/blog-tone.md` — 금지 표현·Evidence Rule
- `.claude/rules/artifact-storage.md` — slug·저장 규칙
- `scripts/carousel_render.py` — 카드 렌더러 (JSON 계약 소비자)
- `scripts/sns_publish.py` — Buffer 초안 push (Phase 3-C)
