#!/usr/bin/env bash
# verify_pipeline_output.sh — 블로그 파이프라인 산출물 전체 검증
# Usage: bash scripts/verify_pipeline_output.sh <slug>
# Example: bash scripts/verify_pipeline_output.sh knu-idea-bridge-2026
#
# Exit codes:
#   0 — PASS (경고 있어도 통과)
#   1 — FAIL (필수 항목 1건 이상 실패)

SLUG="${1:-}"
STRICT=0

# 인자 파싱 — --strict 플래그 지원
for arg in "$@"; do
  if [[ "$arg" == "--strict" ]]; then
    STRICT=1
  fi
done

if [[ -z "$SLUG" ]]; then
  echo "Usage: bash scripts/verify_pipeline_output.sh <slug> [--strict]"
  echo "Example: bash scripts/verify_pipeline_output.sh knu-idea-bridge-2026 --strict"
  exit 1
fi

# ── 경로 정의 ──────────────────────────────────────────────
BASE=".claude/artifacts"
BLOG_DRAFT="$BASE/blog_drafts/${SLUG}-blog-draft.md"
BLOG_REVIEW="$BASE/blog_reviews/${SLUG}-review.md"
REVIEW_DIFF="$BASE/blog_reviews/${SLUG}-review-diff.md"
NAVER_MD="$BASE/naver/${SLUG}-naver.md"
ARCHIVE_DRAFT="$BASE/archive_drafts/${SLUG}-archive-draft.md"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

_pass() { echo "[PASS] $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
_fail() { echo "[FAIL] $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
_warn() { echo "[WARN] $1"; WARN_COUNT=$((WARN_COUNT + 1)); }

echo ""
echo "=== verify_pipeline_output: $SLUG ==="
echo ""

# ── 1. 필수 파일 존재 여부 ─────────────────────────────────
if [[ -f "$BLOG_DRAFT" ]]; then
  _pass "blog_draft.md 존재"
else
  _fail "blog_draft.md 없음 — $BLOG_DRAFT"
fi

if [[ -f "$BLOG_REVIEW" ]]; then
  _pass "blog_review.md 존재"
else
  _fail "blog_review.md 없음 — $BLOG_REVIEW"
fi

if [[ -f "$NAVER_MD" ]]; then
  _pass "naver.md 존재"
else
  _fail "naver.md 없음 — $NAVER_MD"
fi

# ── 2. 검수 총점 ≥ 80 ──────────────────────────────────────
if [[ -f "$BLOG_REVIEW" ]]; then
  SCORE=$(grep -oP '^총점: \K\d+' "$BLOG_REVIEW" | head -1)
  if [[ -z "$SCORE" ]]; then
    _fail "검수 총점 파싱 실패 (review.md에 '총점: XX/100' 형식 없음)"
  elif [[ "$SCORE" -ge 80 ]]; then
    _pass "검수 총점 ${SCORE}/100 (≥ 80)"
  else
    _fail "검수 총점 ${SCORE}/100 — 80점 미만 (합격 기준 미달)"
  fi
fi

# ── 3. review_diff.md 존재 (strict: FAIL / default: WARN) ─
if [[ -f "$REVIEW_DIFF" ]]; then
  _pass "review-diff.md 존재"
elif [[ "$STRICT" -eq 1 ]]; then
  _fail "review-diff.md 없음 — strict 모드에서는 발행 전 필수 산출물"
else
  _warn "review-diff.md 없음 (Phase A 미실행 — 권장 산출물)"
fi

# ── 4. blog_draft 분량 ≥ 2000자 (WARN) ───────────────────
if [[ -f "$BLOG_DRAFT" ]]; then
  CHAR_COUNT=$(wc -m < "$BLOG_DRAFT")
  if [[ "$CHAR_COUNT" -ge 2000 ]]; then
    _pass "blog_draft 분량 ${CHAR_COUNT}자 (≥ 2000)"
  else
    _warn "blog_draft 분량 ${CHAR_COUNT}자 — 강의자료 기준 2000자 미달"
  fi
fi

# ── 5. naver.md 민감정보 검사 ────────────────────────────
if [[ -f "$NAVER_MD" ]]; then
  # API key / token 패턴 (FAIL)
  SENSITIVE_PATTERN='(API[_-]?KEY\s*=|api_key\s*=|access_token\s*=|secret_key\s*=|Bearer\s+[A-Za-z0-9_\-]{16,}|password\s*=\s*['"'"'"])'
  if grep -qiP "$SENSITIVE_PATTERN" "$NAVER_MD" 2>/dev/null; then
    _fail "민감정보 패턴 검출 (API key / token)"
    grep -iP "$SENSITIVE_PATTERN" "$NAVER_MD" | head -3 | sed 's/^/    /'
  else
    _pass "민감정보 미검출 (API key / token)"
  fi

  # 전화번호 패턴 (WARN)
  PHONE_PATTERN='01[016789]-[0-9]{3,4}-[0-9]{4}'
  if grep -qP "$PHONE_PATTERN" "$NAVER_MD" 2>/dev/null; then
    _warn "전화번호 패턴 검출 — 의도된 노출인지 확인 필요"
    grep -P "$PHONE_PATTERN" "$NAVER_MD" | head -2 | sed 's/^/    /'
  else
    _pass "전화번호 미검출"
  fi
fi

# ── 6. 위험 발행 문자열 검사 ─────────────────────────────
if [[ -f "$NAVER_MD" ]]; then
  PUBLISH_DANGER_PATTERN='(auto.?publish|publish_click|\.click\(\)|발행\s*버튼\s*자동\s*클릭|자동\s*클릭\s*발행)'
  if grep -qiP "$PUBLISH_DANGER_PATTERN" "$NAVER_MD" 2>/dev/null; then
    _fail "위험 발행 문자열 검출"
    grep -iP "$PUBLISH_DANGER_PATTERN" "$NAVER_MD" | head -3 | sed 's/^/    /'
  else
    _pass "위험 발행 문자열 미검출"
  fi
fi

# ── 7. archive_draft 존재 (INFO) ──────────────────────────
if [[ -f "$ARCHIVE_DRAFT" ]]; then
  _pass "archive_draft.md 존재"
else
  _warn "archive_draft.md 없음 (Notion 아카이브 미연동)"
fi

# ── 최종 판정 ─────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────"
printf "PASS: %-3d  WARN: %-3d  FAIL: %d\n" "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"
echo ""

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo "결과: FAIL — ${FAIL_COUNT}건 오류 (naver_publish.py 실행 전 수정 필요)"
  exit 1
elif [[ "$WARN_COUNT" -gt 0 ]]; then
  echo "결과: PASS (경고 ${WARN_COUNT}건 — 확인 권장)"
  exit 0
else
  echo "결과: PASS"
  exit 0
fi
