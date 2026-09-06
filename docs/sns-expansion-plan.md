# SNS 확장 계획 — 인스타그램 · Threads (Phase 3)

- 작성일: 2026-07-09
- 상태: **계획 단계 — 사용자 승인 전 실행 금지**
- 근거: 딥리서치 워크플로(103 에이전트, 23개 클레임 3표 교차검증) + 보강 조사 4건(SaaS 비교 / 한국 레퍼런스 / 이미지 생성 / 업로드 방식) — 모두 2026-07-09 기준 라이브 확인

---

## 0. 한 줄 요약

블로그 파이프라인의 검수 통과본(blog_draft)을 **인스타 캐러셀(카드 8~10장 + 캡션)과 Threads(단발 + 타래)로 자동 변환**하고, 카드 이미지는 **HTML 템플릿 + Playwright 스크린샷**으로 자동 생성, 발행은 **Buffer 무료 API로 초안 큐 등록까지만 자동**(발행 버튼은 사람) — 기존 "자동 발행 금지" 원칙 그대로 유지.

---

## 1. 조사 결과 핵심 (설계 근거)

### 1-1. 공식 API 제약 (Meta 공식 문서, 2026-07-09 확인)

| 항목 | Instagram (Content Publishing API) | Threads API |
|---|---|---|
| 계정 요건 | 프로페셔널(비즈니스/크리에이터) 계정 필수 | Threads 프로필 + OAuth |
| 권한 | `instagram_content_publish` 등. 자기 계정은 Standard Access로 즉시, 제3자는 앱 심사 2~4주 | `threads_basic` + `threads_content_publish` |
| 발행 한도 | 100건/24h (문서 내 50 표기도 있어 실측 필요 — 우리 물량엔 무관) | 250건/24h |
| 캐러셀 | 최대 **10장**, 첫 이미지 기준 일괄 크롭(기본 1:1) | 2~20장 네이티브 지원 |
| 이미지 입력 | **공개 URL 필수** (바이트 업로드 불가, resumable은 영상 전용) | **공개 URL 필수** (동일) |
| 이미지 포맷 | **JPEG만** (PNG 불가), ≤8MB, 비율 4:5~1.91:1 | JPEG/PNG, ≤8MB, 비율 ≤10:1 |
| 텍스트 | 캡션 2,200자, 해시태그 30개(단, 앱 정책상 2025.12부터 5개 제한), @태그 20개 | 본문 500자. 2026.4 업데이트: 1만 자 장문 첨부 + 인스타 스토리 교차 공유 API 추가 |
| 링크 | 본문 링크 클릭 불가 | **본문 링크 허용** → 네이버 블로그 유입 도구 |

**설계 함의:** ① 카드 이미지는 **JPEG 통일**(두 채널 공용) ② 직접 API를 쓰려면 이미지 공개 호스팅(Cloudflare R2 무료 추천) + Meta 앱 생성이 선행 ③ Buffer 같은 중개 도구를 쓰면 둘 다 생략 가능.

### 1-2. 발행 도구 비교 결론

| 노선 | 도구 | 비용 | 장점 | 단점 |
|---|---|---|---|---|
| **A. SaaS 중개 (권장)** | **Buffer** | 무료(채널 3개·채널당 예약 10건) → Essentials $5/채널/월 | 무료 플랜에도 **공식 GraphQL API**(월 3,000요청). Meta 앱·토큰·이미지 호스팅 전부 대행. 초안 push → 사람이 앱에서 발행 = "자동 발행 금지" 원칙과 정합 | 예약 10건/채널 한도(우리 물량이면 커버), 외부 SaaS 의존 |
| B. 오픈소스 셀프호스트 | **Postiz** (AGPL-3.0, ~33k stars) | 무료(Docker) 또는 클라우드 $29/월 | REST API + **MCP 서버** + Claude용 Agent CLI 공식 제공. 승인 큐 UI 내장 | 자체 Meta 앱 생성·THREADS_APP_ID 설정·토큰 관리·서버 운영 직접 부담 |
| C. 직접 API | Meta Graph API + Threads API + R2 | 무료 | 의존성 최소, 완전 제어 | Meta 앱 생성·토큰 갱신·R2 호스팅·에러 처리 전부 직접 구현 |
| 탈락 | Later(API 없음) / Hootsuite($99/월) / Ayrshare($149/월) / Zapier(Threads 직발행 불가) | — | — | 소규모(월 10~30건) 물량에 부적합 |

**권장: A(Buffer)로 시작 → 물량·요구 증가 시 B(Postiz)로 이전.** Mixpost Pro($299 일회성)는 B의 대안. n8n(무료 셀프호스트 + 커뮤니티 meta-publisher 노드)도 B 변형으로 가능.

### 1-3. 카드 이미지 자동 생성 결론

**HTML/CSS 템플릿 + Playwright 스크린샷** 확정 (경쟁 없음):
- 비용 0원, naver_publish.py로 이미 운용 중인 Playwright 재사용 (WSL2 검증 완료 환경)
- 한글 타이포 최상: `word-break: keep-all`, Pretendard/Noto Sans KR `@font-face` 로컬 지정
- 행사 사진 배경 + 어두운 오버레이 + 흰 텍스트 = CSS 몇 줄 (사진은 base64 임베드)
- 렌더링: viewport **1080×1350 (4:5 세로형)** — 2025 인스타 그리드 개편 기준 권장. 핵심 텍스트는 중앙 1:1 안전영역
- 출력: **JPEG** (Instagram PNG 불가 제약 대응)
- 선례: open-carrusel(Claude Code용 캐러셀 빌더, GitHub)
- 탈락: Pillow(한글 줄바꿈 수동 구현), satori(CJK 줄바꿈 버그), Bannerbear $49/월·Canva API Enterprise 전용 ~$600/월(과투자), AI 이미지 생성(한글 오탈자)

### 1-4. 콘텐츠 공식 (한국 레퍼런스 조사 기반)

**인스타 캐러셀 — 후기형 (B2B 발주처 타깃, 4:5 세로 8~10장):**

| 슬라이드 | 역할 |
|---|---|
| 1 | 숫자 후킹 표지 (12단어 이내) — "243명이 참여한 ○○, 성패는 전날 결정됐다" |
| 2 | 핵심 성과 수치 3개 카드 (트리플 훅 — 슬라이드 1~3 각각 독립 미끼) |
| 3 | 현장 베스트 컷 + 한 줄 |
| 4 | 행사 개요 정보 카드 (📅📍👥🤝) |
| 5~6 | 운영 **설계** 포인트 ①② ("진행"이 아닌 "설계" 강조 + 현장 사진) |
| 7 | 성과·피드백 (확인 수치만, 미확인 표기 유지) |
| 8 | 개선점 1스푼 (신뢰 장치 — 블로그 §9와 동일 철학) |
| 9 | "이 행사를 운영한 팀" — 모드어스 스튜디오 |
| 10 | CTA + 저장 유도 ("다음 행사 기획 때 꺼내보세요") |

캡션: 첫 줄 후킹 + 검색 키워드, **해시태그 5개 이하**(2025.12 정책). 모집형은 6장 압축 변형(혜택→대상→내용→일정→혜택상세→신청 CTA).

**Threads 공식:**
- 단발형: 1줄 후킹(숫자/고백형) + 2~3줄 운영 인사이트 + 질문 or 블로그 링크. 300자 이내, **토픽 태그 1개만**, 이미지 1~2장(4:5)
- 타래형: 루트(후킹+사진) → 리플 2~4개(운영 디테일·실패담·비하인드) → 마지막 리플(성과 요약 + 네이버 블로그 링크)
- 톤: 기관 공지체 금지, **'모드어스 운영 담당자 개인' 화자** (스픽·잡코리아 사례 패턴). 게시 골든타임 8~9시 / 23시~1시
- 참고: 캐러셀이 릴스 대비 참여율·저장률 우위(저장률 2배), 릴스는 비팔로워 도달 3~5배 — 후기형은 캐러셀 중심, 릴스는 후순위 옵션

**전략적 발견:** 한국 행사 대행사들의 인스타 후기형 콘텐츠는 미성숙 → 차별화 여지 큼. 기관 계정도 팔로워보다 **"계정 = 운영 실적 진열장"**(B2B 증빙) 가치가 실질적. 네이버 §9 플레이북(핵심요약+수치 3개+개선점 1스푼)이 그대로 이식 가능.

레퍼런스 계정: 창업진흥원 @smartkised, 서울창업허브 @seoul_startup_hub, 인프콘 @inflearn__official(UGC 유도 설계), FEConf @feconf [확인 필요: 내부 포맷은 2차 자료 기준]

---

## 2. 아키텍처 설계

```
blog_draft (검수 80+ 통과)
   │
   ├── /channel-distribute ──→ naver/ (기존, 변경 없음)
   │
   └── /sns-distribute (신규)
          │  sns-distributor 에이전트 (신규)
          ├→ .claude/artifacts/sns/[slug]-instagram.md   ← 캐러셀 카드별 문구 + 캡션 + 해시태그
          ├→ .claude/artifacts/sns/[slug]-threads.md     ← 단발형 + 타래형
          │
          ├→ scripts/carousel_render.py (신규)           ← HTML 템플릿 + Playwright → JPEG 1080×1350
          │     templates/carousel/*.html                ← 슬라이드 유형별 템플릿 (표지/수치/사진/정보카드/CTA)
          │     출력: .claude/artifacts/sns/images/[slug]/slide-01.jpg ...
          │
          └→ scripts/sns_publish.py (신규, Phase 3-C)    ← Buffer API로 초안 큐 push
                발행 버튼 = 사람 (Buffer 앱/웹에서 확인 후 클릭)
```

**기존 자산 재사용:** 이미지 앵커/manifest 패턴(channel-distributor), Review Gate 80+(blog-review), 행사 사진 폴더 규약, blog_draft의 재사용 자산 섹션(캐러셀 문구 원천).

**제약 준수:** 기존 에이전트 4개·커맨드 파일 수정 금지 → 전부 신규 추가. orchestrator의 stage 테이블에 `sns` 추가는 orchestrator 파일 수정이 필요하므로 **사용자 승인 항목**(§5). 승인 전엔 `/sns-distribute` 단독 커맨드로 동작.

---

## 3. 단계별 실행 계획

### Phase 3-A — 콘텐츠 변환 (코드 없음, 즉시 가능)
1. `docs/sns-winning-patterns.md` — §1-4 공식 + 레퍼런스를 플레이북으로 문서화
2. `.claude/rules/sns-format.md` — 변환 규칙 (카드 구성, 글자수, 해시태그 5개, 토픽태그 1개, 톤, 금지어는 blog-tone.md 승계)
3. `.claude/agents/sns-distributor.md` — 신규 에이전트 JD (입력: 검수 통과 blog_draft / 출력: instagram.md + threads.md)
4. `.claude/commands/sns-distribute.md` — Review Gate 80+ 확인 → 에이전트 위임
5. 기존 발행 대기 4건(knu-idea-bridge 등) 중 1건으로 파일럿 → 산출물 품질 확인
- **완료 기준:** 파일럿 slug의 instagram.md/threads.md가 공식 준수 + 사람 검토 통과
- **비용/선행조건: 없음**

### Phase 3-B — 카드 이미지 자동 생성
1. `templates/carousel/` — 슬라이드 유형별 HTML 템플릿 5종(표지/수치/사진배경/정보카드/CTA), Pretendard, 브랜드 컬러 CSS 변수화
2. `scripts/carousel_render.py` — instagram.md 파싱 → 템플릿 렌더 → Playwright 스크린샷 → JPEG(≤8MB, 1080×1350) + manifest
3. `fonts-noto-cjk`/Pretendard 폰트 확인 (WSL2)
4. sns-distributor 출력에 카드-템플릿 매핑 필드 추가
- **완료 기준:** 파일럿 slug 카드 8~10장 JPEG 생성, 한글 렌더링·안전영역 확인
- **비용: 0원** (Playwright 기존 자산)

### Phase 3-C — 반자동 발행 (Buffer 노선)
1. 선행: 인스타그램 **프로페셔널 계정 전환** + Threads 프로필 → Buffer 무료 가입 → 두 채널 연결 (사람이 직접, ~30분)
2. `scripts/sns_publish.py` — Buffer GraphQL API로 캐러셀+캡션/Threads 초안 큐 push (API 키는 `.env`, 출력 금지)
3. 발행 체크리스트를 sns 산출물에 포함 (naver 패턴 승계)
4. **발행 버튼은 사람이 Buffer에서 클릭** — 자동 발행 금지 원칙 유지
- **완료 기준:** 파일럿 1건이 Buffer 초안 큐에 올라가고 사람이 발행 완료
- **비용: 0원** (무료 티어) — 채널당 예약 10건 초과 시 Essentials $5/채널/월
- **리스크:** Buffer API의 캐러셀 초안 세부 지원은 [확인 필요] — 구현 첫 단계에서 실측, 미지원 시 Postiz 셀프호스트(B노선)로 전환

### Phase 3-D — 선택 (추후 판단)
- orchestrator `sns` stage 통합 (`/run-blog-pipeline --stage sns`)
- Postiz 셀프호스트 이전 (MCP 서버로 Claude Code 직결) 또는 직접 Meta API + Cloudflare R2
- 릴스(60초 하이라이트) 확장, Threads→인스타 스토리 교차 공유(2026.4 API)
- `scripts/sns_score.py` 품질 게이트 (blog_score 패턴)
- CLAUDE.md·repo MEMORY.md 현행화 (채널 정책 "네이버 단독" → "네이버+인스타+Threads", commands 8개 표기)

---

## 4. 신규 파일 요약

| 파일 | Phase |
|---|---|
| `docs/sns-winning-patterns.md` | 3-A |
| `.claude/rules/sns-format.md` | 3-A |
| `.claude/agents/sns-distributor.md` | 3-A |
| `.claude/commands/sns-distribute.md` | 3-A |
| `templates/carousel/*.html` | 3-B |
| `scripts/carousel_render.py` | 3-B |
| `scripts/sns_publish.py` | 3-C |

기존 파일 수정: 없음 (3-D에서 orchestrator·CLAUDE.md만, 승인 후)

---

## 5. 사용자 결정 필요 사항

1. **발행 노선**: A. Buffer(권장, 무료+API 대행) / B. Postiz 셀프호스트(무료, MCP 직결, Meta 앱 직접) / C. 직접 API — 계획은 A 기준
2. **착수 범위**: 3-A만 먼저 vs 3-A~C 연속 진행
3. **orchestrator 수정 승인 여부** (sns stage 통합 — 3-D)
4. **인스타 계정 상태**: 모드어스 인스타가 이미 프로페셔널 계정인지, Threads 프로필 개설 여부 [확인 필요]
5. **콘텐츠 타입 우선순위**: 후기형(운영 실적, 발주처 타깃) 우선으로 설계함 — 모집형(행사 홍보 대행)도 3-A에 포함할지

## 6. 리스크

- Buffer 무료 티어 캐러셀 API 세부 미확인 → 3-C 첫 단계에서 실측 (대안 준비됨)
- Meta 정책·rate limit·가격은 수시 변동 (조사값 전부 2026-07-09 기준)
- Threads API로 임의 스토리 발행은 불가 (기존 Threads 게시물 파생만 가능)
- 인스타 캐러셀은 첫 이미지 기준 일괄 크롭 → 전 카드 동일 비율(4:5) 강제 생성으로 대응
