# Moduus Marketing Team

## Project Context
Moduus Studio 행사·용역 아카이브 기반 마케팅 운영 시스템.
Notion DB와 결과보고서를 구조화된 아카이브로 만들고, 블로그·포트폴리오·제안서 문장을 뽑아내는 4인 에이전트 파이프라인을 구축한다.
단순 블로그 자동화가 아님 — 회사 지식 자산화가 목표다.

## Current Pipeline
1. **notion-archive-manager** — 자료/PDF/메모 → Notion 문서형 아카이브 초안 ✅
2. **marketing-content-writer** — 아카이브 → 블로그 본문 + 재사용 자산 ✅
3. **content-editor-reviewer** — 4축 검수 (SEO/팩트/브랜드톤/가독성, 80점 합격) ✅
4. **channel-distributor** — 검수 통과본 → 네이버 블로그 변환 ✅

## Standard Workflow
단일 진입점: `/run-blog-pipeline [input] [--stage stage]` → marketing-orchestrator가 전 파이프라인 조율

수동 단계별: `/archive-from-pdf [경로]` → `/blog-from-archive [경로]` → `/blog-review [경로]` → `/channel-distribute [경로]`

## Known Limitation
- MIT GSW 2026: `.claude/artifacts/archive_drafts/` 파일 없음 — blog_draft부터 시작됨, 파이프라인 1단계 소급 불가

## Directory Map
```
marketing-team/
├── CLAUDE.md, MEMORY.md
├── docs/db-schema.md
├── outputs/                  ← legacy, 삭제 금지
└── .claude/
    ├── agents/               ← 에이전트 JD (.md)
    ├── rules/                ← 세부 규칙
    ├── commands/             ← /archive-from-pdf, /blog-from-archive, /blog-review, /channel-distribute
    └── artifacts/            ← archive_drafts/ blog_drafts/ blog_reviews/ naver/ sns/ keywords/ pipeline_runs/
```

## Always Follow
- 큰 작업은 계획 먼저 → 사용자 승인 → 실행
- 불확실한 내용은 `[확인 필요]` 표시
- 세부 규칙은 아래 Rules Reference 참조

## Never Do
- Notion 삭제·이동·아카이브·DB 구조 변경 — 명시 승인 전 금지
- `notion-update-page` / `notion-create-pages` 이외 Notion 쓰기 — 명시 승인 전 금지 (해당 두 도구는 archive-manager·content-writer에 한해 사전 승인)
- Gmail, Google Drive, youtube-transcript, context7 — 명시 허락 전 금지
- 자동 발행 — 발행 버튼은 사람이 누른다
- `포트폴리오 포함` Notion 속성 임의 수정
- `outputs/` 폴더 삭제
- API 키, 토큰, 계정 정보, Notion 내부 ID 출력
- 확인되지 않은 수치·성과 단정

## Phase Order
- **Phase 0** ✅: `outputs/blog_drafts/` → `.claude/artifacts/blog_drafts/` 복사 완료
- **Phase 1** ✅: content-editor-reviewer + review-quality.md + commands 3개 완료
- **Phase 2** ✅: channel-distributor — 네이버 블로그 변환 완료
- **Later**: visual-director, Notion MCP 쓰기 연동

## Rules Reference
- 아카이브 구조: `.claude/rules/archive-structure.md`
- 산출물 저장: `.claude/rules/artifact-storage.md`
- 블로그 문체: `.claude/rules/blog-tone.md`
- MCP 안전: `.claude/rules/mcp-safety.md`
- 4축 검수: `.claude/rules/review-quality.md`
- 네이버 블로그 포맷: `.claude/rules/naver-blog-format.md`
- 실행 권한 정책: `.claude/settings.json` (공유) / `.claude/settings.local.json` (개인, gitignore)

## Default Response Format
답변은 짧고 실무적으로. 큰 작업 전 계획 먼저 제시. 불확실하면 질문한다.

## PPT가 필요하면 — 직접 만들지 말고 `ppt-ask`로 넘겨라

PPT 덱(16:9 발표자료·제안서·공모전 장표 등)은 **ppt-master-v2 담당이 만든다.**
여기서 python-pptx를 직접 쓰거나 마크다운으로 흉내내지 말 것. 아래 한 줄이면 된다.

```bash
ppt-ask --slug <슬러그> "이 내용으로 12장 덱 만들어줘: <핵심 내용·대상·목적·톤>"
ppt-ask --slug <슬러그> -f 브리프.md "이 브리프대로. 공모전 심사용이라 헤드라인 크게."
ppt-ask --slug <슬러그> "p03 헤드라인 두 줄로 줄이고 다시 렌더해줘"   # 앞 대화 이어짐
cat 원고.md | ppt-ask --slug <슬러그> "이 원고로 덱"                   # 파이프도 됨
```

- ppt-master-v2 폴더에서 담당 세션이 뜨므로 테마 54종·도식 카탈로그·정렬 게이트가
  전부 적용된다. 담당의 보고 + **스크립트가 파일시스템을 실측해 붙인 `[ppt-ask 기계검증]`
  블록**(deck.pptx 경로·크기·시각, 썸네일 실제 개수와 전체 경로)이 stdout으로 돌아온다.
- **요청에 담아야 잘 나오는 것**: ① 발신 주체·수신자 ② 목적(심사/보고/영업) ③ 대략 장수
  ④ 스크린 발표용인지 인쇄·문서로 읽을 건지 ⑤ 원자료(수치·문구)는 파일로 붙일 것.
- **`--slug`를 항상 붙여라.** 그 슬러그 전용 세션이 이어져서, 수정 요청 때 앞 맥락을
  다시 설명할 필요가 없다. 처음부터 다시 하려면 `--fresh`.
- 담당은 되물을 수 없어서 애매하면 알아서 정하고 가정을 보고에 적는다. 원자료를 안 주면
  내용을 지어내지는 않지만 그만큼 빈약해진다.
- 기록은 `~/ppt-master-v2/.ppt-ask-log/` 에 남는다.

### 받은 덱은 "내가 시킨 게 맞나"로 검수하고 되던져라

**디자인 품질(겹침·정렬·여백·테마 문법)은 네 일이 아니다.** ppt-master-v2 안에서
`ppt-qa` 에이전트와 `check_align.py` 게이트가 이미 그걸 본다. 네가 또 보면 같은 검수를
두 번 하는 건데, 두 번째는 v2 디자인 규칙을 모르는 쪽이 하는 거라 의미가 없다.

**네가 유일하게 아는 건 "내가 뭘 시켰는지"다. 그걸 대조해라.**

1. **내용 누락·창작** — 의뢰한 항목이 다 들어갔나. 내가 준 적 없는 내용이 끼어 있나.
   회신의 "임의로 결정한 사항" 문단을 원자료와 한 줄씩 맞춰본다.
2. **수치·고유명사** — 금액·인원·날짜·기관명·사업명이 원자료와 정확히 같나.
   **담당은 원본을 모른다. 이건 너만 검증할 수 있다.**
3. **톤** — 대상·목적에 맞나. 심사용인데 내부보고 톤은 아닌가, 반대는 아닌가.
4. **장수·판형** — 요청한 대로인가.
5. 그 다음에야 **눈에 띄게 깨진 페이지만** 이차 확인. 회신 끝에 스크립트가 실측해 붙인
   `[ppt-ask 기계검증]` 블록의 썸네일 경로를 Read 로 열면 된다.
   (그 경로는 모델이 적은 게 아니라 실제 글롭 결과다. "썸네일 0장 — 눈검수 불가"가
   찍혀 있으면 렌더가 안 끝난 것이니 **그 상태로 사용자에게 넘기지 마라.**)

반려는 그대로 되던진다 — 앞 맥락이 이어져 있으니 짧게 써도 된다:

```
ppt-ask --slug foo "3장 예산이 4,200만원인데 원자료는 3,800만원이다. 수정.
                    그리고 협력기관에 없는 곳이 하나 들어갔다 — 원자료에 있는 것만."
```

한 줄 요약: **부서는 "내가 시킨 게 맞나", ppt-qa 는 "잘 만들어졌나".**
