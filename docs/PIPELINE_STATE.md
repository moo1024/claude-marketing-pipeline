# Pipeline State — 세션 인계 문서

> 최종 업데이트: 2026-07-09
> git HEAD: 5455e53

---

## 현재 파이프라인 판정

**강의자료 Part 6 기준: PASS**
**4개 슬러그 전체 blog_score 90+ 달성 — 품질 게이트 hook 연동 완료**

---

## 이번 세션에서 완료한 작업 (2026-07-09)

| 커밋 | 내용 |
|---|---|
| a2e3464 | pre-publish hook에 blog_score 90점 게이트 연결 + naver_publish 대기 중복 제거 + WSL2 DISPLAY 수정 |
| 5455e53 | 3개 슬러그 naver.md §9 플레이북 재변환 (64/56/39점 → 100/92/90점) |

---

## 발행 대기 중인 콘텐츠

| slug | 제목 | 이미지 실파일 | verify --strict | blog_score | 상태 |
|---|---|---|---|---|---|
| `knu-idea-bridge-2026` | KNU 아이디어브릿지 후기 \| 243명 창업 네트워킹 | 39장 ✅ | PASS 10/10 | **100** | 발행 가능 — naver_publish.py 재실행 필요 (이전 모달 세션 종료됨) |
| `mit-gsw-2026` | 학생 서포터즈 50명으로 신청자 1,211명 만든 운영 설계 | 13장 ✅ | PASS 9/10 | **100** | 발행 가능 |
| `google-ai-hackathon-2026` | 노코드로 150분 만에 AI 서비스를 만든 해커톤 운영기 | 1장(포스터만) ⚠️ | PASS 9/10 | **92** | 발행 가능 — 현장 사진 3장+ 추가 시 97~100점 |
| `tech-patent-lecture-2026` | 기술특허 특강 (§9 재변환본) | 0장 ❌ | PASS 10/10 | **90** | 발행 가능 — 현장 사진 8장+ 확보 시 100점 |

> blog_score 90+ = hook 통과 = 발행 가능. 발행 버튼은 항상 사람이 클릭.

---

## 품질 게이트 구조 (2026-07-09 이후)

`naver_publish.py` 실행 시 PreToolUse hook(`pre-publish-check.sh`)이 3단계 검증:
1. `verify_pipeline_output.sh [slug] --strict` — 산출물 구조 검증 (FAIL 시 차단)
2. 본문(복붙용) 내 `[확인 필요]/[자료 없음]/[추정]` 표기 — 1건이라도 있으면 차단 (독자 노출 방지)
3. `blog_score.py [slug]-naver.md` — 90점 미만 시 차단

긴급 우회: 명령에 `--skip-verify` 추가 (경고 후 통과).

## 사람 대상 품질 개선 (2026-07-09, 자가진단 후속)

- 발행 본문 내 미확정 마커 16건 전량 해소 (mit-gsw 2 · google-ai 6 · tech-patent 8) — 미확정 수치는 본문에서 제외/재서술, 원본 마커는 blog_draft에 보존
- knu 마무리 콜라주 교체: IMG_6112(행사 전 빈 행사장)·6114 → IMG_9344(아이디어 보드·참가 열기)·9280(참여 인파) — 사진 내용 직접 대조 완료
- knu 사용 사진 8장 + mit-gsw 2장 내용 대조 완료. IMG_6116은 케이블 사진 — 사용 금지
- 캡션 자동입력 없음 → naver.md에 '이미지 캡션 (복붙용)' 섹션 추가(knu 6개·mit-gsw 5개) + 체크리스트 항목 추가
- 에디터 화면의 이모지 ⊠ 깨짐은 WSL Chrome 이모지 폰트 부재(로컬 렌더 문제) — 발행 후 모바일 1회 확인 권장
- 미검증 잔여: SmartEditor의 [인용구]→인용구 블록 / [표]→표 블록 변환 시각 확인 (첫 발행 시 확인)

---

## 버그 수정 이력

- **발행 대기 중복 (a2e3464)**: `wait_for_url` 10분 타임아웃 후 `asyncio.sleep(600)`이 추가로 돌아 최대 20분 대기하던 문제 — 잔여 시간만 채우도록 수정 (총 10분 유지).
- **캡션 텍스트 오배치 (c0976b3)**: `[[IMG:...|caption=text]]` 앵커의 caption이 본문 텍스트 문단으로 삽입되던 문제 제거. 캡션은 에디터에서 이미지 클릭 후 직접 입력.

---

## 미해결 환경 이슈

- **WSLg 브라우저 가시성**: Claude Code 백그라운드 태스크에서 naver_publish.py를 실행하면 Chrome 창이 사용자 화면에 안 보임 (Chrome이 X11 소켓에 연결하지 않음). **우회: 사용자가 터미널에서 직접 실행** — `! python3 scripts/naver_publish.py .claude/artifacts/naver/[slug]-naver.md`

---

## 현재 스크립트 구조

```
scripts/
├── naver_publish.py          — Playwright SmartEditor 자동 입력 (발행 클릭은 사람)
├── blog_score.py             — naver.md 100점 품질 게이트 (90+ = 발행 권장)
├── verify_pipeline_output.sh — 파이프라인 산출물 검증 (--strict 지원)
├── pre-publish-check.sh      — PreToolUse hook (verify --strict + blog_score 90+ 이중 게이트)
├── heic_to_jpg.py            — HEIC → JPG 변환
└── naver_*.py                — 업로드·슬라이드·위치 probe 스크립트
```

---

## 다음 작업 후보

1. **knu 발행** — `python3 scripts/naver_publish.py .claude/artifacts/naver/knu-idea-bridge-2026-naver.md` (터미널 직접 실행 권장)
2. **mit-gsw 발행** — 동일 방식, 100점 상태
3. **google-ai-hackathon 현장 사진 보강** — `.claude/artifacts/naver/images/google-ai-hackathon-2026/`에 강연/실습/시상 사진 3장+ 추가 → 앵커 배치 → 발행
4. **tech-patent-lecture 현장 사진 확보** — 8장+ 확보 → 앵커 배치 → 발행
5. **MIT GSW 2026 아카이브** — archive_draft 없음, 자료 확보 후 `/blog-from-archive`

---

## 낮은 우선순위 잔여 항목

| 항목 | 상태 |
|---|---|
| review_diff.md 전체 슬러그 | ✅ 완료 (4개 모두) |
| verify_pipeline_output.sh --strict | ✅ 완료 |
| hook 기반 안전장치 (verify + blog_score 이중 게이트) | ✅ 완료 |
| CLAUDE.md 디렉토리맵 현행화 (commands 8개, sns/·keywords/ 미생성 표기) | 미착수 (사소) |
| keywords.json 독립 출력 | 미착수 |
| SNS 3종 (인스타·X·LinkedIn) | Phase 3 예약 |
| visual-director (이미지 생성) | Later 예약 |
