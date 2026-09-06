#!/usr/bin/env bash
# pre-publish-check.sh — naver_publish.py 실행 전 파이프라인 검증 hook
#
# Claude Code PreToolUse hook으로 동작.
# stdin으로 tool input JSON을 수신하고, naver_publish.py 호출일 때만 개입.
#
# Exit codes:
#   0 — 허용 (PASS 또는 non-target 명령)
#   2 — 차단 (FAIL — Claude Code가 tool call을 막음)

INPUT=$(cat)

# ── 대상 명령 확인 ──────────────────────────────────────────
COMMAND=$(echo "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" \
  2>/dev/null || echo "")

# naver_publish.py 호출이 아니면 무조건 통과
if [[ "$COMMAND" != *"naver_publish.py"* ]]; then
  exit 0
fi

# ── 예외 조건 ───────────────────────────────────────────────
# --skip-verify 플래그: 경고 후 통과
if [[ "$COMMAND" == *"--skip-verify"* ]]; then
  echo "[pre-publish-check] --skip-verify 감지 — 검증 스킵 후 실행 허용" >&2
  exit 0
fi

# verify 스크립트 없으면 경고 후 통과 (Phase B 미설치 환경 보호)
if [[ ! -f "scripts/verify_pipeline_output.sh" ]]; then
  echo "[pre-publish-check] 경고: verify_pipeline_output.sh 없음 — 검증 스킵" >&2
  exit 0
fi

# ── slug 추출 ────────────────────────────────────────────────
# 패턴: .claude/artifacts/naver/[slug]-naver.md
SLUG=$(echo "$COMMAND" | grep -oP '[a-z0-9][a-z0-9\-]+(?=-naver\.md)' | head -1)

if [[ -z "$SLUG" ]]; then
  echo "[pre-publish-check] 경고: slug 추출 실패 — 검증 스킵 후 실행 허용" >&2
  exit 0
fi

# ── 검증 실행 ────────────────────────────────────────────────
echo "" >&2
echo "[pre-publish-check] naver_publish.py 실행 전 파이프라인 검증" >&2
echo "[pre-publish-check] Slug: $SLUG" >&2

bash scripts/verify_pipeline_output.sh "$SLUG" --strict >&2
VERIFY_EXIT=$?

if [[ "$VERIFY_EXIT" -ne 0 ]]; then
  echo "" >&2
  echo "[pre-publish-check] FAIL — naver_publish.py 실행 차단" >&2
  echo "[pre-publish-check] 위 FAIL 항목을 수정한 뒤 다시 실행하세요." >&2
  echo "[pre-publish-check] 긴급 실행이 필요하면 명령에 --skip-verify를 추가하세요." >&2
  exit 2
fi

# ── 본문 내 미확정 표기 차단 ([확인 필요]/[자료 없음]/[추정]) ────
MARKER_COUNT=$(python3 -c "
import re
try:
    c = open('.claude/artifacts/naver/${SLUG}-naver.md', encoding='utf-8').read()
    m = re.search(r'## 본문 \(복붙용\)\n\n(.*?)(?=\n---\n)', c, re.DOTALL)
    print(len(re.findall(r'\[(확인 필요|자료 없음|추정)\]', m.group(1))) if m else print(0))
except Exception:
    print(0)
" 2>/dev/null || echo 0)

if [[ "$MARKER_COUNT" -gt 0 ]]; then
  echo "" >&2
  echo "[pre-publish-check] FAIL — 본문(복붙용)에 [확인 필요]/[자료 없음]/[추정] 표기 ${MARKER_COUNT}건" >&2
  echo "[pre-publish-check] 발행 본문에 미확정 표기가 노출되면 안 됩니다. 문장을 재작성하거나 제외하세요." >&2
  echo "[pre-publish-check] 긴급 실행이 필요하면 명령에 --skip-verify를 추가하세요." >&2
  exit 2
fi

# ── 품질 점수 게이트 (blog_score 90점+, naver-blog-format.md §10) ──
if [[ -f "scripts/blog_score.py" ]]; then
  echo "" >&2
  python3 scripts/blog_score.py ".claude/artifacts/naver/${SLUG}-naver.md" >&2
  SCORE_EXIT=$?
  if [[ "$SCORE_EXIT" -ne 0 ]]; then
    echo "" >&2
    echo "[pre-publish-check] FAIL — blog_score 90점 미만, naver_publish.py 실행 차단" >&2
    echo "[pre-publish-check] 위 '개선 여지' 항목을 보완한 뒤 다시 실행하세요." >&2
    echo "[pre-publish-check] 긴급 실행이 필요하면 명령에 --skip-verify를 추가하세요." >&2
    exit 2
  fi
fi

echo "" >&2
echo "[pre-publish-check] PASS — naver_publish.py 실행 허용" >&2
exit 0
