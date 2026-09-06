#!/usr/bin/env python3
"""네이버 블로그(naver.md) 품질 스코어러 v2 — docs/blog-winning-patterns.md 루브릭.

용도: 용역사(Moduus) 홍보 + 아카이빙에 적합한 '잘 읽히고 정보 충분하며 홍보력 있는' 글인지
      100점으로 객관 검증. 90점+ = 발행 권장.
사용: python3 scripts/blog_score.py .claude/artifacts/naver/[slug]-naver.md
"""
import re
import sys

FORBIDDEN = ["뜻깊", "성황리", "많은 분들", "좋은 반응", "최선을 다",
             "체계적으로", "전문적으로 진행"]
EMOJI_HEADERS = ["📌", "🗂", "🙋", "📈", "🏛", "💡", "✅", "🎯", "🔑", "📝", "🧩", "🚀", "🎙", "🤝"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def section(md, name):
    m = re.search(rf"## {re.escape(name)}[^\n]*\n\n(.*?)(?=\n---\n|\n## )", md, re.DOTALL)
    return m.group(1).strip() if m else ""


def score(path):
    md = load(path)
    title = section(md, "제목 (복붙용)")
    body = section(md, "본문 (복붙용)")
    plain = re.sub(r"\[\[[^\]]+\]\]", "", body)
    plain = re.sub(r"\[/?(인용구|형광|구분선)\]", "", plain)
    body_len = len(re.sub(r"\s", "", plain))
    rows = []

    def add(name, got, mx, note=""):
        rows.append((name, round(min(got, mx), 1), mx, note))

    # 1. 제목 (8)
    t = (4 if title and len(title) <= 32 else 0) + (2 if re.search(r"\d", title) else 0) + \
        (2 if title[:8].strip() else 0)
    add("제목(키워드앞·숫자·32자)", t, 8, f"{len(title)}자")
    # 2. 후킹 (6)
    first = plain.strip().split("\n")[0][:60] if plain.strip() else ""
    add("후킹 첫문장", 6 if re.search(r'["“]|\d|없|왜|어떻게|처음', first) else 2, 6)
    # 3. 핵심요약+정보카드 (8)
    quotes = len(re.findall(r"\[인용구\]", body))
    card = bool(re.search(r"📅|📍|👥|🤝", body))
    add("핵심요약·정보카드", min(quotes, 2) * 2 + (4 if card else 0), 8)
    # 4. 이모지 소제목 (8): 5+
    # 특정 이모지 whitelist가 아니라 "줄 첫머리 이모지 + 굵은 소제목" 형태를 센다.
    # (whitelist 방식은 글마다 같은 이모지 세트를 쓰도록 강제해 템플릿 티를 유발했다)
    eh = len(re.findall(
        r"(?m)^[\U0001F300-\U0001FAFF☀-➿️]+\s*\*\*.+?\*\*", body))
    add("이모지 소제목", min(eh, 5) * 1.6, 8, f"{eh}개")
    # 5. 문단짧게·불릿 (8)
    bullets = body.count("•") + len(re.findall(r"(?m)^✔", body))
    paras = [p for p in re.split(r"\n\n+", plain) if len(p.strip()) > 15]
    avg = sum(len(p) for p in paras) / len(paras) if paras else 999
    add("문단짧게·불릿", (4 if bullets >= 4 else bullets) + (4 if avg <= 180 else 1), 8,
        f"불릿{bullets}·평균{int(avg)}자")
    # 6. 형광펜 (6)
    add("형광펜 강조", min(body.count("[형광]"), 6), 6, f"{body.count('[형광]')}곳")
    # 7. 이미지 혼합·다량 (12)
    single = len(re.findall(r"\[\[IMG:", body))
    collage = len(re.findall(r"\[\[COLLAGE:", body))
    slide = len(re.findall(r"\[\[SLIDE:", body))
    total_imgs = single
    for m in re.findall(r"\[\[(?:SLIDE|COLLAGE):([^\]|]+)", body):
        total_imgs += len([x for x in m.split(",") if x.strip()])
    mix = sum(1 for x in (single, collage, slide) if x > 0)
    add("이미지 혼합·다량", mix * 2.5 + (4.5 if total_imgs >= 8 else 1.5), 12,
        f"개별{single}/콜라주{collage}/슬라이드{slide}·총{total_imgs}장")
    # 8. 본문 분량 (8): 1800~3500
    bl = 8 if 1800 <= body_len <= 3600 else (round(body_len / 225) if body_len < 1800 else 6)
    add("본문 분량", bl, 8, f"{body_len}자")
    # 9. 금지어 (6)
    hits = [w for w in FORBIDDEN if w in body]
    add("금지어 회피", 6 - 3 * len(hits), 6, str(hits) if hits else "")
    # 10. 개선점 (5) — 자연스러운 반성 표현도 인정
    add("솔직한 개선점",
        5 if re.search(r"아쉬|개선|다음엔|다음에는|보완|한계|잘 안 [된됐]|못 (채|한|했)|반성", body) else 0, 5)
    # 11. 기관 효용 (6)
    add("기관·발주처 효용", 6 if re.search(r"기관|산학|발주|참고할 수 있는|모델|효용|자산", body) else 2, 6)
    # 12. 참가자/현장 직접 인용 (6) — NEW
    pq = len(re.findall(r'[""].{4,40}[""]', body))
    add("참가자/현장 인용", 6 if pq >= 2 else (3 if pq == 1 else 0), 6, f"인용 {pq}개")
    # 13. 용역사 CTA·회사 역량 (7) — NEW (홍보)
    moduus = bool(re.search(r"모드어스|Moduus|모두스", body))
    cta = bool(re.search(r"문의|의뢰|연락|운영이 필요|대행|함께", body))
    add("용역사 CTA·회사명", (4 if moduus else 0) + (3 if cta else 0), 7,
        "" if moduus and cta else "회사명(모드어스)+운영문의 CTA 권장")
    # 14. 재사용 자산·아카이빙 (6)
    # 키워드뿐 아니라 "다음에 그대로 쓴다"는 자연 표현도 인정 (내용이 있으면 잡는다)
    reuse = bool(re.search(
        r"재사용|포트폴리오|제안서|회사소개|이식|활용할 수 있|"
        r"그대로 (쓰|가져|옮|꺼내)|운영 자산|다음(에|엔).{0,12}(쓰|옮|가져|적용)", body))
    add("재사용 자산(아카이빙)", 6 if reuse else 0, 6, "" if reuse else "포트폴리오/제안서 재사용 문장 권장")

    total = round(sum(r[1] for r in rows))

    # ── 문체 감점 (획일성·AI 티) — blog-tone.md '문장 기술' 반영 ──────────
    # 채점기가 개수만 세면 4편이 같은 틀로 찍혀 나와도 만점이 된다.
    # 아래는 '사람 글'에서 멀어질수록 깎는다. (감점만, 가점 없음)
    penalties = []
    clean = re.sub(r"\[/?[^\]]+\]|\[\[.*?\]\]|<[^>]+>|\*\*", "", body)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if len(s.strip()) > 10]
    if sents:
        # (a) 어미 단조: 최빈 종결어미 비율이 높으면 감점
        ends = {}
        for s in sents:
            e = s.rstrip(".").strip()[-4:]
            ends[e] = ends.get(e, 0) + 1
        top_ratio = max(ends.values()) / len(sents)
        if top_ratio > 0.30:
            penalties.append(("어미 단조 (한 어미 30%↑)", -4, f"최빈 {top_ratio*100:.0f}%"))
        elif top_ratio > 0.22:
            penalties.append(("어미 단조 (한 어미 22%↑)", -2, f"최빈 {top_ratio*100:.0f}%"))
        # (b) 문장 길이: 평균이 길면 감점 (짧게 끊는 글이 잘 읽힌다)
        avg = sum(len(s) for s in sents) / len(sents)
        if avg > 60:
            penalties.append(("문장 과다 장문 (평균 60자↑)", -3, f"평균 {avg:.0f}자"))
        elif avg > 50:
            penalties.append(("문장 다소 장문 (평균 50자↑)", -1, f"평균 {avg:.0f}자"))
    # (c) 번역투·이중피동
    trans = len(re.findall(r"되어지|불려지|보여지|만들어지|를? 통해|에 대[한해]|에 있어", body))
    if trans:
        penalties.append(("번역투·이중피동", -min(trans, 4), f"{trans}건"))
    # (d) 템플릿 티: 같은 폴더 다른 글과 소제목 이모지가 겹치면 감점
    import glob, os
    my_emoji = set(re.findall(r"(?m)^([\U0001F300-\U0001FAFF☀-➿️]+)\s*\*\*", body))
    if my_emoji:
        others = set()
        for f in glob.glob(os.path.join(os.path.dirname(path) or ".", "*-naver.md")):
            if os.path.abspath(f) == os.path.abspath(path):
                continue
            ob = section(load(f), "본문 (복붙용)")
            others |= set(re.findall(r"(?m)^([\U0001F300-\U0001FAFF☀-➿️]+)\s*\*\*", ob))
        shared = my_emoji & others
        if len(shared) >= 5:
            penalties.append(("소제목 이모지 템플릿 중복", -5, f"{len(shared)}개 겹침"))
        elif len(shared) >= 3:
            penalties.append(("소제목 이모지 일부 중복", -2, f"{len(shared)}개 겹침"))

    total = max(0, total + sum(p[1] for p in penalties))
    print("=" * 66)
    print(f"블로그 품질 채점 v2 — {path.split('/')[-1]}")
    print("=" * 66)
    for name, got, mx, note in rows:
        b = round(got / mx * 8) if mx else 0
        print(f"  {'●'*b}{'○'*(8-b)} {got:>4.1f}/{mx:<3} {name}" + (f"  — {note}" if note else ""))
    if penalties:
        print("-" * 66)
        print("  문체 감점 (획일성·AI 티):")
        for name, pen, note in penalties:
            print(f"  {pen:>5.0f}   {name}" + (f"  — {note}" if note else ""))
    print("-" * 66)
    v = "발행 권장 ✅" if total >= 90 else ("보완 필요 ⚠️" if total >= 75 else "재작성 ❌")
    print(f"  총점: {total}/100   → {v}")
    gaps = [f"{n}(+{mx-g:.0f})" for n, g, mx, _ in rows if g < mx - 0.5]
    if gaps:
        print("  개선 여지:", ", ".join(gaps))
    return total


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: blog_score.py <naver.md>")
        sys.exit(2)
    sys.exit(0 if score(sys.argv[1]) >= 90 else 1)
