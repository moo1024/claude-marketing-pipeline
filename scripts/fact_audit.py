#!/usr/bin/env python3
"""수치 출처 대조기 (Fact Audit) — 블로그 초안의 모든 수치를 원자료와 1:1 대조한다.

배경: 기존 '팩트정확도' 채점은 `[확인 필요]` 태그 유무만 봤기 때문에, 헤징 없이
      확정 서술된 미출처 수치(예: "참여 243명")가 만점으로 통과했다.
      이 스크립트는 태그가 아니라 **값 자체**를 원자료와 대조한다.

사용:
    python3 scripts/fact_audit.py .claude/artifacts/blog_drafts/[slug]-blog-draft.md
    python3 scripts/fact_audit.py <draft> --source <원자료.md> [--source ...] [--json]
    python3 scripts/fact_audit.py <draft> --source <원본.md> --derived-source <파생본.md>

원자료 등급 (순환 검증 차단):
    이 팀의 실제 흐름은 `사용자 제공 원본(결과보고서·PDF) → archive_draft → 블로그`다.
    블로그는 archive_draft의 **파생본**이므로, 블로그를 archive_draft와만 대조하면
    "파생본을 원본으로 착각하는 순환 검증"이 된다(아카이브가 틀리면 블로그도 틀린 채 통과).

    PRIMARY (사용자 제공 원본 — 정량 수치의 유일한 기준)
        .claude/artifacts/fact_sources/[slug]*.md   ← 결과보고서 등 원본 발췌
        --source 로 직접 지정한 경로 (사람이 원본이라고 지목한 것으로 본다)
    DERIVED (파생본 — 구조·정성 서술의 근거로만 인정)
        .claude/artifacts/archive_drafts/[slug]-archive-draft.md
        --derived-source 로 직접 지정한 경로

    참여인원·%·건수·팀수 같은 **정량 성과 수치는 PRIMARY에만 근거할 수 있다.**
    존 개수·프로그램 수 같은 구조 서술과 날짜는 DERIVED로도 확인을 인정한다.

원자료 기본 탐색 (--source 미지정 시 자동):
    초안 경로에서 위로 올라가며 `.claude` 디렉토리를 가진 프로젝트 루트를 찾아 탐색한다.
    (cwd에 의존하지 않으므로 어느 위치에서 실행해도 같은 원자료를 찾는다.)

판정:
    SOURCED     — 숫자+단위가 해당 등급의 원자료에 그대로 존재 (출처 확인)
    HEDGED      — 같은 문장에 [확인 필요]/[자료 없음]/[추정] 표기 (단정하지 않음)
    DERIVED_ONLY— 정량 수치인데 근거가 파생본(archive_draft)에만 있음 → 대조 불가
    PARTIAL     — 숫자는 원자료에 있으나 단위/맥락이 다름 (확인으로 인정하지 않음)
    UNSOURCED   — 원자료에 근거 없음 + 헤징도 없음 (하드게이트 위반)

종료 코드:
    0 — 통과 (UNSOURCED·PARTIAL·DERIVED_ONLY 0건)
    1 — 하드게이트 실패 (미출처 수치 1건 이상) → 총점과 무관하게 재작성
    2 — 대조 불가 → 자동 합격 금지, 사용자 원본을 fact_sources에 확보한 뒤 재실행
        (원자료 파일 자체가 없음 / 정량 수치의 근거가 파생본에만 있음)
"""
import argparse
import glob
import json
import os
import re
import sys

# 헤징 표기는 `[확인 필요]` 뿐 아니라 `[확인 필요 — 사유]` 형태로도 쓰인다.
HEDGE_RE = re.compile(r"\[\s*(확인\s*필요|자료\s*없음|추정)[^\]]*\]")

# 대조 대상 단위 — 사실 주장 위험이 있는 수치만 검사한다.
# `일`·`년`·`월`은 날짜 표기와 구분이 어려워 제외하고, 날짜는 아래 DATE 검사로 따로 대조한다.
# (일수 단위 기간 주장은 이 스크립트가 잡지 않는다 — 사람이 확인한다.)
# `부`·`차`·`권`·`석`은 조사·합성어 오탐(`1부터`)이 잦아 제외한다.
UNITS = [
    "명분", "개월", "만원", "억원", "천원", "퍼센트",
    "명", "팀", "건", "개", "곳", "회", "배", "시간", "주",
    "점", "종", "장", "위", "원", "%",
]

# 정량 성과 수치 — 사용자 제공 원본(PRIMARY)에만 근거할 수 있는 단위.
# 참여인원·비율·건수·팀수·금액·점수처럼 "성과 주장"에 해당하는 값들이다.
# 나머지 단위(개·곳·회·시간·주·개월·종·장)와 날짜는 구조·정성 서술로 보고
# 파생본(archive_draft)의 근거도 확인으로 인정한다. (예: "6개 존 운영")
QUANT_UNITS = {
    "명", "명분", "팀", "건", "%", "퍼센트",
    "원", "만원", "억원", "천원", "점", "배", "위",
}
# 긴 단위를 먼저 시도해야 `18개월`이 `18개`로 잘리지 않는다.
UNIT_RE = "|".join(sorted(UNITS, key=len, reverse=True))
NUM = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?"

# 날짜 — 초안은 `2026년 1월 30일`, 원자료는 `2026. 1. 30.` 형태를 함께 쓴다.
# 파편(`30일`)이 아니라 날짜 전체를 하나의 주장으로 보고 대조한다.
DATE_FULL_RE = re.compile(r"(\d{4})\s*[.년]\s*(\d{1,2})\s*[.월]\s*(\d{1,2})\s*[.일]")
DATE_YM_RE = re.compile(r"(\d{4})\s*[.년]\s*(\d{1,2})\s*월")
DATE_MD_KR_RE = re.compile(r"(?<!\d)(\d{1,2})\s*월\s*(\d{1,2})\s*일")
# `~ 1. 29.(목)` 처럼 연도가 생략된 점 표기는 원자료 쪽에서만 인정한다.
DATE_MD_DOT_RE = re.compile(r"(?<![\d.])(\d{1,2})\s*\.\s*(\d{1,2})\s*\.(?!\d)")
# 단위 뒤에 조사가 붙는 게 한국어의 기본형이므로(`243명이`, `18개였습니다`)
# 뒤따르는 한글을 배제하면 안 된다. 배제하면 조작 수치가 통째로 미검출된다.
# 뒤에 숫자만 오지 않으면 된다.
CLAIM_RE = re.compile(rf"(?<![\w.])({NUM})\s*({UNIT_RE})(?!\d)")
BARE_NUM_RE = re.compile(rf"(?<![\w.])({NUM})(?![\w.])")

# 본문 구조·서식에서 오는 잡음 (섹션 번호, 이미지 앵커 등)은 대조 대상이 아니다.
NOISE_LINE_RE = re.compile(r"^\s*(\[\[IMG:|```|\|\s*-{2,})")

# 사실 주장이 아닌 메타 섹션 — 자체 채점표·태그 개수 등은 대조 대상에서 제외한다.
# (`재사용 자산`과 `확인 필요사항`은 사실 주장이 실리는 곳이므로 반드시 포함한다.)
META_SECTION_RE = re.compile(r"^##\s*(썸네일|SEO 키워드|태그|자체 퇴고|검수|맞춤법)")
TOP_HEADING_RE = re.compile(r"^##(?!#)\s*")

# 헤징은 줄 단위가 아니라 문장 단위로 적용한다. 한 줄에 수치가 8개 있는데
# 마지막 문장에만 `[확인 필요]`가 붙은 경우, 앞 문장의 수치까지 면죄되면 안 된다.
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\|")


def sentences(line: str):
    """(시작offset, 문장) 목록. 표 셀(|)과 문장부호를 경계로 쪼갠다."""
    out, pos = [], 0
    for part in SENT_SPLIT_RE.split(line):
        idx = line.find(part, pos)
        if idx < 0:
            idx = pos
        out.append((idx, part))
        pos = idx + len(part)
    return out


def norm_num(raw: str) -> str:
    """1,200 → 1200 / 98.30 → 98.3"""
    n = raw.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def extract_dates(text: str, allow_dot_md: bool = False) -> list:
    """(정규화된 날짜, 원문, 시작offset) 목록. YYYY-MM-DD / ????-MM-DD / YYYY-MM."""
    found = []
    for m in DATE_FULL_RE.finditer(text):
        y, mo, d = m.groups()
        found.append((f"{y}-{int(mo):02d}-{int(d):02d}", m.group(0), m.start(), m.end()))
    for m in DATE_MD_KR_RE.finditer(text):
        mo, d = m.groups()
        found.append((f"????-{int(mo):02d}-{int(d):02d}", m.group(0), m.start(), m.end()))
    if allow_dot_md:
        for m in DATE_MD_DOT_RE.finditer(text):
            mo, d = m.groups()
            if int(mo) <= 12 and int(d) <= 31:
                found.append((f"????-{int(mo):02d}-{int(d):02d}", m.group(0), m.start(), m.end()))
    for m in DATE_YM_RE.finditer(text):
        y, mo = m.groups()
        found.append((f"{y}-{int(mo):02d}", m.group(0), m.start(), m.end()))
    return found


def mask_spans(text: str, spans: list) -> str:
    """날짜로 소비된 구간을 공백으로 덮어, 숫자+단위 스캔이 파편을 줍지 않게 한다."""
    chars = list(text)
    for start, end in spans:
        for i in range(start, min(end, len(chars))):
            chars[i] = " "
    return "".join(chars)


def date_sourced(norm: str, src_dates: set) -> bool:
    """연도 미상(????)이면 월-일만 일치해도 인정. 연-월이면 해당 월의 날짜가 있으면 인정."""
    if norm in src_dates:
        return True
    if norm.startswith("????-"):
        md = norm[5:]
        return any(s.endswith(f"-{md}") and not s.startswith("????") for s in src_dates)
    if len(norm) == 7:  # YYYY-MM
        return any(s.startswith(norm + "-") for s in src_dates)
    # YYYY-MM-DD → 원자료가 연도를 생략한 경우도 인정
    return f"????-{norm[5:]}" in src_dates


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def slug_of(draft_path: str) -> str:
    base = os.path.basename(draft_path)
    return re.sub(r"-blog-draft\.md$|\.md$", "", base)


def project_root(draft_path: str) -> str:
    """초안 경로에서 위로 올라가며 `.claude` 디렉토리를 가진 프로젝트 루트를 찾는다.

    cwd 기준으로 원자료를 찾으면 프로젝트 루트가 아닌 곳에서 실행했을 때
    원자료를 놓치고 `대조 불가`로 떨어진다(안전 실패이지만 취약하다).
    초안 파일의 위치는 실행 위치와 무관하므로 여기서 루트를 확정한다.
    """
    d = os.path.dirname(os.path.abspath(draft_path))
    while True:
        if os.path.isdir(os.path.join(d, ".claude", "artifacts")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.getcwd()  # 프로젝트 밖의 초안 — cwd로 폴백(대개 원자료 없음 → EXIT 2)
        d = parent


def default_sources(draft_path: str) -> tuple:
    """(primary, derived) 경로 목록. 등급 구분은 순환 검증 차단의 핵심이다."""
    slug = slug_of(draft_path)
    root = project_root(draft_path)
    primary = sorted(glob.glob(
        os.path.join(root, ".claude", "artifacts", "fact_sources", f"{slug}*.md")))
    derived = []
    arch = os.path.join(root, ".claude", "artifacts", "archive_drafts",
                        f"{slug}-archive-draft.md")
    if os.path.isfile(arch):
        derived.append(arch)
    return primary, derived


def collect_source_index(paths: list) -> dict:
    """원자료에서 (숫자+단위) 집합과 (숫자만) 집합, 날짜 집합을 뽑는다."""
    pairs, bares, dates = set(), set(), set()
    for p in paths:
        text = read(p)
        found = extract_dates(text, allow_dot_md=True)
        dates.update(d[0] for d in found)
        text = mask_spans(text, [(d[2], d[3]) for d in found])
        for m in CLAIM_RE.finditer(text):
            pairs.add((norm_num(m.group(1)), m.group(2)))
        for m in BARE_NUM_RE.finditer(text):
            bares.add(norm_num(m.group(1)))
    return {"pairs": pairs, "bares": bares, "dates": dates}


def merge_index(*idxs: dict) -> dict:
    return {k: set().union(*(i[k] for i in idxs)) for k in ("pairs", "bares", "dates")}


def extract_claims(draft_text: str) -> list:
    claims = []
    in_fence = False
    in_meta = False
    for i, line in enumerate(draft_text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if TOP_HEADING_RE.match(line):
            in_meta = bool(META_SECTION_RE.match(line))
            continue
        if in_fence or in_meta or NOISE_LINE_RE.match(line):
            continue
        for start, sent in sentences(line):
            hedged = bool(HEDGE_RE.search(sent))
            found = extract_dates(sent)
            for norm, raw, s0, _e0 in found:
                claims.append({
                    "line": i, "token": raw.strip(), "num": norm, "unit": "날짜",
                    "hedged": hedged, "context": sent.strip()[:110] or line.strip()[:110],
                    "col": start + s0, "kind": "date",
                })
            sent = mask_spans(sent, [(d[2], d[3]) for d in found])
            for m in CLAIM_RE.finditer(sent):
                claims.append({
                    "line": i,
                    "token": f"{m.group(1)}{m.group(2)}",
                    "num": norm_num(m.group(1)),
                    "unit": m.group(2),
                    "hedged": hedged,
                    "context": sent.strip()[:110] or line.strip()[:110],
                    "col": start + m.start(),
                    "kind": "quantity",
                })
    return claims


def judge(claims: list, primary: dict, derived: dict) -> list:
    """정량 수치는 PRIMARY(사용자 원본)로만 확인을 인정한다.

    파생본(archive_draft)에만 근거가 있는 정량 수치는 SOURCED가 아니라 DERIVED_ONLY다.
    아카이브가 원본을 잘못 옮겨 적었을 때 블로그가 같은 오류를 안고 통과하는
    순환 검증을 여기서 끊는다.
    """
    both = merge_index(primary, derived)
    out = []
    for c in claims:
        quant = c.get("kind") == "quantity" and c["unit"] in QUANT_UNITS
        idx = primary if quant else both

        if c.get("kind") == "date":
            # 날짜는 구조 서술로 보고 파생본 근거도 인정한다.
            if date_sourced(c["num"], both["dates"]):
                verdict = "SOURCED"
            elif c["hedged"]:
                verdict = "HEDGED"
            else:
                verdict = "UNSOURCED"
            out.append({**c, "verdict": verdict, "tier": "any"})
            continue

        key = (c["num"], c["unit"])
        if key in idx["pairs"]:
            verdict = "SOURCED"
        elif c["hedged"]:
            verdict = "HEDGED"
        elif quant and key in derived["pairs"]:
            verdict = "DERIVED_ONLY"
        elif c["num"] in idx["bares"] or (quant and c["num"] in derived["bares"]):
            verdict = "PARTIAL"
        else:
            verdict = "UNSOURCED"
        out.append({**c, "verdict": verdict, "tier": "primary" if quant else "any"})
    return out


def dedupe(results: list) -> list:
    """같은 토큰이 여러 번 나오면 최초 등장 1건으로 묶되 등장 횟수를 남긴다."""
    seen = {}
    for r in results:
        k = (r["token"], r["verdict"])
        if k in seen:
            seen[k]["count"] += 1
        else:
            seen[k] = {**r, "count": 1}
    return list(seen.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="블로그 초안 수치 ↔ 원자료 1:1 대조")
    ap.add_argument("draft", help="블로그 초안 경로")
    ap.add_argument("--source", action="append", default=[],
                    help="사용자 제공 원본 경로 (PRIMARY, 반복 지정 가능)")
    ap.add_argument("--derived-source", action="append", default=[], dest="derived_source",
                    help="파생본 경로 (archive_draft 등 — 구조·정성 근거로만 인정)")
    ap.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = ap.parse_args()

    if not os.path.isfile(args.draft):
        print(f"[오류] 초안 파일 없음: {args.draft}", file=sys.stderr)
        return 2

    if args.source or args.derived_source:
        # 사람이 직접 지목한 경로는 지목한 등급 그대로 쓴다.
        primary_paths, derived_paths = list(args.source), list(args.derived_source)
    else:
        primary_paths, derived_paths = default_sources(args.draft)
    sources = primary_paths + derived_paths

    missing = [p for p in sources if not os.path.isfile(p)]
    if missing:
        print(f"[오류] 원자료 파일 없음: {', '.join(missing)}", file=sys.stderr)
        return 2

    slug = slug_of(args.draft)

    def emit_no_source(status: str, msg: str, results=None) -> int:
        if args.json:
            print(json.dumps({"slug": slug, "status": status,
                              "sources": sources, "primary_sources": primary_paths,
                              "derived_sources": derived_paths,
                              "claims": results or []}, ensure_ascii=False, indent=2))
        else:
            print(msg)
        return 2

    if not sources:
        return emit_no_source("NO_SOURCE", (
            f"[대조 불가] {slug} 원자료 없음.\n"
            f"  - .claude/artifacts/fact_sources/{slug}*.md 없음 (사용자 제공 원본 — 필수)\n"
            f"  - .claude/artifacts/archive_drafts/{slug}-archive-draft.md 없음 (파생본)\n"
            "→ 결과보고서·PDF 등 사용자 제공 원본의 수치 구간을 발췌해 "
            f".claude/artifacts/fact_sources/{slug}-source.md 로 저장한 뒤 재실행하세요.\n"
            "→ 원자료 없이 팩트정확도 자동 합격은 금지된다."))

    primary = collect_source_index(primary_paths)
    derived = collect_source_index(derived_paths)
    results = dedupe(judge(extract_claims(read(args.draft)), primary, derived))

    quant = [r for r in results if r.get("tier") == "primary" and r["verdict"] != "HEDGED"]
    if quant and not primary_paths:
        # 파생본만으로 정량 수치를 통과시키면 아카이브의 오류가 그대로 발행된다.
        listing = "\n".join(f"  L{r['line']}  {r['token']}  | {r['context']}"
                            for r in sorted(quant, key=lambda x: x["line"])[:20])
        return emit_no_source("NO_PRIMARY", (
            f"[대조 불가] {slug} 사용자 제공 원본(fact_sources) 없음 — "
            f"정량 수치 {len(quant)}건을 파생본만으로 통과시킬 수 없다.\n"
            f"파생본: {', '.join(derived_paths) or '없음'}\n"
            f"{listing}\n"
            "→ 결과보고서·PDF 등 원본의 수치 구간을 발췌해 "
            f".claude/artifacts/fact_sources/{slug}-source.md 로 저장한 뒤 재실행하세요."), results)

    buckets = {v: [r for r in results if r["verdict"] == v]
               for v in ("SOURCED", "HEDGED", "PARTIAL", "UNSOURCED", "DERIVED_ONLY")}
    failed = buckets["UNSOURCED"] + buckets["PARTIAL"]
    blocked = buckets["DERIVED_ONLY"]
    status = "FAIL" if failed else ("NO_PRIMARY" if blocked else "PASS")

    if args.json:
        print(json.dumps({"slug": slug, "status": status, "sources": sources,
                          "primary_sources": primary_paths, "derived_sources": derived_paths,
                          "summary": {k: len(v) for k, v in buckets.items()},
                          "claims": results}, ensure_ascii=False, indent=2))
    else:
        print(f"# 수치 출처 대조 — {slug}")
        print(f"원본(PRIMARY): {', '.join(primary_paths) or '없음'}")
        print(f"파생본(DERIVED): {', '.join(derived_paths) or '없음'}")
        print(f"검사 수치: {len(results)}건 (출처확인 {len(buckets['SOURCED'])} / "
              f"헤징 {len(buckets['HEDGED'])} / 단위불일치 {len(buckets['PARTIAL'])} / "
              f"미출처 {len(buckets['UNSOURCED'])} / 파생본만 {len(blocked)})\n")
        for label, key in (("미출처 (하드게이트 위반)", "UNSOURCED"),
                           ("단위·맥락 불일치 (확인 불인정)", "PARTIAL"),
                           ("파생본에만 근거 있음 (정량 수치 — 원본 확인 필요)", "DERIVED_ONLY")):
            if buckets[key]:
                print(f"## {label}")
                for r in sorted(buckets[key], key=lambda x: x["line"]):
                    print(f"  L{r['line']}  {r['token']}  (본문 {r['count']}회)  | {r['context']}")
                print()
        if status == "FAIL":
            print(f"[하드게이트 실패] 미출처 수치 {len(failed)}건 — "
                  "총점과 무관하게 자동 탈락(재작성). 원자료 확인 또는 헤징 표기 필요.")
        elif status == "NO_PRIMARY":
            print(f"[대조 불가] 정량 수치 {len(blocked)}건의 근거가 파생본(archive_draft)에만 있다. "
                  f"사용자 제공 원본 발췌를 .claude/artifacts/fact_sources/{slug}-source.md 에 "
                  "확보한 뒤 재실행하세요 — 파생본 단독 통과는 금지된다.")
        else:
            print("[하드게이트 통과] 정량 수치는 사용자 제공 원본으로 확인되었거나 헤징 표기됨.")

    return {"FAIL": 1, "NO_PRIMARY": 2}.get(status, 0)


if __name__ == "__main__":
    sys.exit(main())
