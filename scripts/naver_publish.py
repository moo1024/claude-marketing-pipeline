#!/usr/bin/env python3
"""
Naver Blog Semi-Auto Publisher
Usage: python3 scripts/naver_publish.py .claude/artifacts/naver/[slug]-naver.md

발행 버튼은 사람이 직접 누른다.
"""

import sys
import re
import json
import asyncio
import os
from pathlib import Path

# WSL2/WSLg 환경에서 백그라운드 실행 시 DISPLAY가 없을 수 있어 강제 설정
if not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":0"
os.environ.setdefault("WAYLAND_DISPLAY", "wayland-0")

# ── 설정 (blogId 변경 시 scripts/naver_config.py만 수정) ─────────────
try:
    from naver_config import NAVER_BLOG_ID
except ImportError:
    NAVER_BLOG_ID = "muhyeok1024"

LOGIN_URL   = "https://nid.naver.com/nidlogin.login"
PROFILE_DIR = str(Path.home() / ".claude" / "config" / "naver-browser-profile")
# ─────────────────────────────────────────────────────────────────────


def parse_naver_md(filepath: str) -> tuple[str, str, list[str]]:
    content = Path(filepath).read_text(encoding="utf-8")

    title_m = re.search(r"## 제목 \(복붙용\)\n\n(.+?)(?:\n|$)", content)
    title = title_m.group(1).strip() if title_m else ""

    body_m = re.search(r"## 본문 \(복붙용\)\n\n(.*?)(?=\n---\n)", content, re.DOTALL)
    body = body_m.group(1).strip() if body_m else ""

    # 📷 마커 라인 제거 (에디터에 placeholder 텍스트가 노출되면 안 됨)
    body = re.sub(r'\n?📷 \[이미지 \d+\][^\n]*', '', body).strip()

    tags_m = re.search(r"## 태그.*?\n\n(.+?)(?:\n\n---|\Z)", content, re.DOTALL)
    tags_raw = tags_m.group(1).strip() if tags_m else ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    return title, body, tags


def markdown_to_html(text: str) -> str:
    # [인용구]...[/인용구] → <blockquote> (SmartEditor 인용구 블록으로 렌더링)
    def make_quote(m: re.Match) -> str:
        content = m.group(1).strip()
        content = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", content)
        # 인용구 내부 줄바꿈 유지 — 개행 문자는 HTML에서 공백으로 붕괴되므로 <br>로 변환
        content = content.replace("\n", "<br>")
        return f"\n\n<blockquote><p>{content}</p></blockquote>\n\n"

    # [표] 항목|수치 (줄바꿈 구분, 첫 줄 헤더) → <table> (SmartEditor 표 블록으로 렌더)
    def make_table(m: re.Match) -> str:
        lines = [ln.strip() for ln in m.group(1).strip().splitlines() if ln.strip()]
        rows_html = []
        for i, ln in enumerate(lines):
            cells = [c.strip() for c in ln.split("|")]
            tag = "th" if i == 0 else "td"
            tds = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
            rows_html.append(f"<tr>{tds}</tr>")
        return "\n\n<table><tbody>" + "".join(rows_html) + "</tbody></table>\n\n"

    text = re.sub(r"\[표\]\n?(.*?)\n?\[/표\]", make_table, text, flags=re.DOTALL)

    # [형광]...[/형광] → 형광펜(배경 하이라이트). 네이버가 인라인 style 유지 시 강조됨.
    text = re.sub(
        r"\[형광\](.+?)\[/형광\]",
        r'<span style="background-color:#fff59d;">\1</span>',
        text, flags=re.DOTALL)
    text = re.sub(
        r"\[인용구\]\n?(.*?)\n?\[/인용구\]",
        make_quote,
        text,
        flags=re.DOTALL,
    )
    # [구분선] → <hr>
    text = re.sub(r"\n*\[구분선\]\n*", "\n\n<hr>\n\n", text)
    # **볼드**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    paragraphs = re.split(r"\n\n+", text)
    parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # blockquote·hr·table은 div로 감싸지 않음 (SmartEditor 자체 블록 구조 유지)
        if p.startswith(("<blockquote", "<hr", "<table")):
            parts.append(p)
            parts.append("<div><br></div>")
        else:
            parts.append(f"<div>{p.replace(chr(10), '<br>')}</div>")
            parts.append("<div><br></div>")
    return "".join(parts)


# ══════════════════════════════════════════════════════════════════════
# Stage 2 (B) — 이미지 앵커 순수함수 (브라우저 무관, C단계 인터리브에서 사용 예정)
# 현재 main()의 본문 paste 경로는 이 함수들을 아직 호출하지 않는다(회귀 보호).
# ══════════════════════════════════════════════════════════════════════

# 앵커: [[IMG:파일]] 개별 / [[SLIDE:a,b,c]] 슬라이드 / [[COLLAGE:a,b]] 콜라주 / [[PLACE:검색어]] 지도
MEDIA_ANCHOR_RE = re.compile(r"\[\[(IMG|SLIDE|COLLAGE|PLACE):\s*([^\]|]+?)\s*(?:\|([^\]]*))?\]\]")
# strict 매치에 실패한 깨진 앵커 잔여물 탐지용
BROKEN_ANCHOR_RE = re.compile(r"\[\[(?:IMG|SLIDE|COLLAGE|PLACE):[^\]]*\]\]")
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB


def manual_note(filename: str, detail: str = "권장 위치") -> str:
    """이미지 실패 시 본문에 남길 사람용 안내 문구."""
    return f"[이미지 수동 삽입 필요: {filename} / {detail}]"


def _parse_anchor_meta(meta: str | None) -> dict:
    """'alt=설명|caption=캡션' → {'alt':..., 'caption':...}. 없으면 빈 문자열."""
    out = {"alt": "", "caption": ""}
    if not meta:
        return out
    for part in meta.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower()
            if k in out:
                out[k] = v.strip()
    return out


def _clean_broken_anchors(text: str) -> str:
    """strict 파싱을 통과 못한 깨진 [[IMG:...]] 잔여물을 수동 안내로 치환."""
    return BROKEN_ANCHOR_RE.sub(
        lambda m: manual_note("(파싱 실패 앵커)", "앵커 문법 오류"), text
    )


def split_body_by_anchor(body: str) -> list[dict]:
    """본문을 텍스트/이미지 세그먼트로 분할.

    반환 예:
      [{"type":"text","content":"..."},
       {"type":"image","file":"img-01.png","alt":"...","caption":"..."}, ...]

    - 앵커 순서 = 본문 등장 순서 = 업로드 순서.
    - 앵커가 하나도 없으면 [{"type":"text","content": body}] (원본 보존 = 회귀 보장).
    - 깨진 앵커는 텍스트 세그먼트 안에서 수동 안내로 치환된다(앵커 원문 미잔류).
    """
    segments: list[dict] = []
    last = 0
    for m in MEDIA_ANCHOR_RE.finditer(body):
        pre = body[last:m.start()]
        if pre.strip():
            segments.append({"type": "text", "content": _clean_broken_anchors(pre.strip())})
        k = m.group(1)
        kind = {"SLIDE": "slide", "COLLAGE": "collage", "PLACE": "place"}.get(k, "single")
        if k == "PLACE":
            files = [m.group(2).strip()]  # 검색어(콤마 분리 안 함)
        else:
            files = [f.strip() for f in m.group(2).split(",") if f.strip()]
        meta = _parse_anchor_meta(m.group(3))
        segments.append({
            "type": "media", "kind": kind, "files": files,
            "alt": meta["alt"], "caption": meta["caption"],
        })
        last = m.end()

    if not segments:
        # 유효 앵커 전무 → 단일 텍스트. 깨진 앵커만 정리(앵커가 아예 없으면 no-op = 회귀 보존).
        return [{"type": "text", "content": _clean_broken_anchors(body)}]

    tail = body[last:]
    if tail.strip():
        segments.append({"type": "text", "content": _clean_broken_anchors(tail.strip())})
    return segments


def resolve_image(slug: str, filename: str, images_root: str | None = None) -> dict:
    """이미지 경로 해석 + 크기 가드.

    반환: {"file","path","status","bytes","note"}
      status: "ok" | "missing" | "oversize"
      status != "ok" 이면 note = 본문에 남길 수동 삽입 안내.
    """
    root = images_root or f".claude/artifacts/naver/images/{slug}/"
    path = os.path.join(root, filename)
    if not os.path.isfile(path):
        return {"file": filename, "path": path, "status": "missing",
                "bytes": 0, "note": manual_note(filename, "파일 없음")}
    size = os.path.getsize(path)
    if size > MAX_IMAGE_BYTES:
        mb = round(size / 1024 / 1024, 1)
        return {"file": filename, "path": path, "status": "oversize",
                "bytes": size, "note": manual_note(filename, f"{mb}MB > 8MB 스킵")}
    return {"file": filename, "path": path, "status": "ok", "bytes": size, "note": ""}


def _self_test() -> int:
    """브라우저 없이 순수함수 회귀·동작을 검증한다. 실패 시 비정상 종료코드."""
    import tempfile
    fails = []

    def check(name, cond):
        print(f"  {'✓' if cond else '✗'} {name}")
        if not cond:
            fails.append(name)

    # 1) 앵커 없는 본문 → 단일 텍스트, 원본 보존(회귀)
    plain = "첫 문단.\n\n둘째 문단."
    segs = split_body_by_anchor(plain)
    check("회귀: 앵커 없으면 1개 텍스트", len(segs) == 1 and segs[0]["type"] == "text")
    check("회귀: 본문 원본 보존", segs[0]["content"] == plain)

    # 2) 풀형 앵커 2개 → text,image,text,image 순서 + 메타 파싱
    body = ("도입 문단.\n\n"
            "[[IMG:img-poster-sns.jpg|alt=공식 포스터|caption=인스타 포스터]]\n\n"
            "가운데 문단.\n\n"
            "[[SLIDE:a.jpg, b.jpg, c.jpg|caption=현장 스케치]]\n\n"
            "마무리 문단.")
    segs = split_body_by_anchor(body)
    types = [s["type"] for s in segs]
    check("순서 text,media,text,media,text",
          types == ["text", "media", "text", "media", "text"])
    img1 = segs[1]
    check("단일 kind/파일", img1["kind"] == "single" and img1["files"] == ["img-poster-sns.jpg"])
    check("alt 파싱", img1["alt"] == "공식 포스터")
    check("caption 파싱", img1["caption"] == "인스타 포스터")
    sl = segs[3]
    check("슬라이드 kind/파일수",
          sl["kind"] == "slide" and sl["files"] == ["a.jpg", "b.jpg", "c.jpg"])
    check("앵커 원문 미잔류", all(
        "[[IMG" not in s["content"] and "[[SLIDE" not in s["content"]
        for s in segs if s["type"] == "text"))

    # 3) 깨진 앵커 → 수동 안내 치환, 원문 미잔류
    broken = "문단.\n\n[[IMG:]]\n\n끝."
    segs = split_body_by_anchor(broken)
    joined = " ".join(s["content"] for s in segs if s["type"] == "text")
    check("깨진 앵커: 원문 미잔류", "[[IMG:]]" not in joined)
    check("깨진 앵커: 수동 안내 존재", "이미지 수동 삽입 필요" in joined)

    # 4) resolve_image: missing / ok / oversize
    with tempfile.TemporaryDirectory() as td:
        r_missing = resolve_image("x", "nope.png", images_root=td + "/")
        check("resolve missing", r_missing["status"] == "missing"
              and "수동 삽입 필요" in r_missing["note"])

        small = os.path.join(td, "small.png")
        with open(small, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 1000)
        r_ok = resolve_image("x", "small.png", images_root=td + "/")
        check("resolve ok", r_ok["status"] == "ok" and r_ok["note"] == "")

        big = os.path.join(td, "big.png")
        with open(big, "wb") as f:
            f.seek(9 * 1024 * 1024)  # 9MB sparse
            f.write(b"\x00")
        r_big = resolve_image("x", "big.png", images_root=td + "/")
        check("resolve oversize(>8MB)", r_big["status"] == "oversize"
              and "8MB" in r_big["note"])

    # 5) manual_note 형식
    check("manual_note 형식",
          manual_note("a.png") == "[이미지 수동 삽입 필요: a.png / 권장 위치]")

    print("\n[self-test] " + ("PASS — 모든 순수함수 정상" if not fails
                              else f"FAIL — {len(fails)}건: {fails}"))
    return 1 if fails else 0


# ══════════════════════════════════════════════════════════════════════
# Stage 2 (C) — SmartEditor 인터리브 삽입 (텍스트 paste + 이미지 file_chooser 업로드)
# 앵커가 있을 때만 사용. 실패 시 전체 텍스트 폴백. 최종 발행 버튼은 절대 클릭하지 않는다.
# ══════════════════════════════════════════════════════════════════════

# 사진 버튼 라벨에 이 단어가 있으면 클릭하지 않는다(발행/저장류 오클릭 방지).
FORBIDDEN_CLICK_WORDS = ("발행", "저장", "예약", "확인", "완료", "게시")


def flatten_segments_to_text(segments) -> str:
    """세그먼트를 단일 텍스트로 평탄화. 미디어는 수동 안내로 치환(폴백/무앵커용)."""
    parts = []
    for s in segments:
        if s["type"] == "text":
            parts.append(s["content"])
        elif s.get("kind") == "place":
            parts.append(f"📍 {s['files'][0] if s['files'] else ''}")
        else:
            parts.append(manual_note(", ".join(s["files"]), "권장 위치"))
    return "\n\n".join(parts)


async def _find_editor_frame(page):
    """SmartEditor 본문 iframe 탐색(about:blank/editor 우선, 없으면 텍스트 최다 프레임)."""
    for frame in page.frames:
        if frame.url == "about:blank" or "editor" in frame.url:
            try:
                if await frame.locator("body").count() > 0:
                    return frame
            except Exception:
                continue
    best, best_len = None, 0
    for frame in page.frames:
        try:
            n = await frame.evaluate(
                "() => document.body ? document.body.innerText.length : 0")
            if n > best_len:
                best_len, best = n, frame
        except Exception:
            continue
    return best


async def _write_clipboard_html(frame, html) -> str:
    j = json.dumps(html)
    return await frame.evaluate(
        "async () => {"
        f"  try {{ const b=new Blob([{j}],{{type:'text/html'}});"
        "        await navigator.clipboard.write([new ClipboardItem({'text/html':b})]);"
        "        return 'ok'; }"
        "  catch(e){ return 'error:'+e.message; } }"
    )


async def _paste_html_segment(page, frame, html, iframe_rect) -> bool:
    """에디터에 포커스 → 문서 끝으로 이동 → HTML 클립보드 붙여넣기(append)."""
    click_y = int(iframe_rect['y']) + 200 if iframe_rect else 600
    await page.mouse.click(640, click_y)
    await page.wait_for_timeout(200)
    r = await _write_clipboard_html(frame, html)
    if r != "ok":
        return False
    await page.keyboard.press("Control+End")
    await page.keyboard.press("Control+v")
    await page.wait_for_timeout(600)
    return True


async def _count_editor_images(page) -> int:
    total = 0
    for frame in page.frames:
        try:
            n = await frame.evaluate(
                "() => document.querySelectorAll("
                "'.se-module-image, .se-image-resource, .se-image').length")
            total += int(n or 0)
        except Exception:
            continue
    return total


async def _cursor_to_end(frame) -> None:
    """에디터 편집영역 맨 끝으로 캐럿 이동(다음 미디어가 커서 위치에 삽입되도록)."""
    try:
        await frame.evaluate("""() => {
            const ed = document.querySelector('.se-content')
                || document.querySelector('[contenteditable=true]')
                || document.body;
            ed.focus();
            const r = document.createRange(); r.selectNodeContents(ed); r.collapse(false);
            const s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        }""")
    except Exception:
        pass


async def _upload_images_via_chooser(page, paths) -> bool:
    """probe로 검증된 경로: 사진 버튼 → file_chooser.set_files(리스트).
    실패 시 프레임 내 input[type=file] 직접 주입. 발행/저장 버튼은 클릭 안 함."""
    if isinstance(paths, str):
        paths = [paths]
    try:
        btn = page.get_by_role("button", name=re.compile("사진|이미지")).first
        await btn.wait_for(state="visible", timeout=5000)
        label = (await btn.get_attribute("aria-label")) or ""
        if any(w in label for w in FORBIDDEN_CLICK_WORDS):
            return False
        async with page.expect_file_chooser(timeout=8000) as fc:
            await btn.click()
        chooser = await fc.value
        await chooser.set_files(paths)
        return True
    except Exception:
        for frame in page.frames:
            try:
                inp = frame.locator("input[type=file]").first
                if await inp.count() > 0:
                    await inp.set_input_files(paths)
                    return True
            except Exception:
                continue
        return False


async def _select_photo_layout(page, label) -> None:
    """여러 장 업로드 시 뜨는 '사진 첨부 방식' 대화상자에서 레이아웃 선택.
    label: '슬라이드' 또는 '콜라주' (또는 '개별사진').
    확인·완료·발행 버튼은 클릭하지 않는다(probe 검증)."""
    await page.wait_for_timeout(2000)
    try:
        r = await page.evaluate(r"""(label) => {
            const all = [...document.querySelectorAll('button, span, div, a, p')];
            const el = all.find(e => (e.textContent||'').trim() === label);
            if (el) { el.click(); if (el.parentElement) el.parentElement.click();
                      return label; }
            return 'no-dialog';
        }""", label)
        print(f"  사진첨부방식: {r}")
        await page.wait_for_timeout(1500)
    except Exception as e:
        print(f"  레이아웃 선택 오류: {e}")


async def _insert_place(page, query) -> bool:
    """장소(지도) 카드 삽입: 장소 버튼 → 검색 → 첫 결과 → 확인. (probe 검증 흐름)
    발행 버튼은 건드리지 않는다('확인'은 장소 패널 내부 삽입 버튼)."""
    try:
        btn = page.get_by_role("button", name=re.compile("장소")).first
        await btn.wait_for(state="visible", timeout=5000)
        await btn.click()
        await page.wait_for_timeout(2000)
        inp = page.locator("input[placeholder*='장소']").last
        await inp.wait_for(state="visible", timeout=4000)
        await inp.click()
        await inp.fill(query)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2800)
        clicked = await page.evaluate(r"""(q) => {
            const first = q.split(' ')[0];
            const cand = [...document.querySelectorAll('li, a, [class*=item], [class*=result] div')]
              .filter(e => { const t=(e.textContent||'').trim();
                 return t.length>4 && t.length<80 &&
                   (t.includes(first) || /대구|서울|경기|부산|대전|광주|인천|울산|경북|경남|강원|충|전|제주/.test(t)); });
            if(!cand.length) return 'no-result';
            cand[0].click(); return 'clicked';
        }""", query)
        await page.wait_for_timeout(1500)
        ok = await page.evaluate(r"""() => {
            const b=[...document.querySelectorAll('button')].find(x=>{
               const t=(x.textContent||'').trim();
               return t==='확인' && !t.includes('발행'); });
            if(b){ b.click(); return 'ok'; } return 'no-confirm';
        }""")
        await page.wait_for_timeout(2000)
        # 검색 패널이 안 닫히면 downstream(태그·발행)을 막으므로 Esc로 강제 정리
        try:
            if await page.locator("input[placeholder*='장소']").count() > 0:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(800)
        except Exception:
            pass
        return clicked == "clicked" and ok == "ok"
    except Exception as e:
        print(f"  장소 삽입 예외: {e}")
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def _insert_body_interleaved(page, segments, images_root, iframe_rect) -> bool:
    """텍스트 세그먼트 paste와 이미지 업로드를 등장 순서대로 append.
    반환 True=성공(부분 실패는 수동 안내로 흡수) / False=첫 텍스트 실패(→전체 폴백)."""
    frame = await _find_editor_frame(page)
    if not frame:
        return False
    first_ok = False
    for seg in segments:
        if seg["type"] == "text":
            ok = await _paste_html_segment(page, frame, markdown_to_html(seg["content"]), iframe_rect)
            if not ok and not first_ok:
                return False
            first_ok = first_ok or ok
            frame = await _find_editor_frame(page) or frame
            continue

        # ── 장소(지도) ──────────────────────────────────────────────
        if seg["kind"] == "place":
            q = seg["files"][0] if seg["files"] else ""
            await _cursor_to_end(frame)
            ok = await _insert_place(page, q)
            if ok:
                print(f"  ✓ 장소(지도) 삽입: {q}")
            else:
                await _paste_html_segment(page, frame, markdown_to_html(f"📍 {q}"), iframe_rect)
                print(f"  ! 장소 삽입 실패 → 텍스트 안내: {q}")
            await page.wait_for_timeout(1000)
            frame = await _find_editor_frame(page) or frame
            continue

        # ── media (개별 single / 슬라이드 slide / 콜라주 collage) ─────
        paths, notes = [], []
        for fn in seg["files"]:
            info = resolve_image("", fn, images_root=images_root)
            if info["status"] == "ok":
                paths.append(info["path"])
            else:
                notes.append(info["note"])
                print(f"  ! 이미지 {fn}: {info['status']} (스킵)")
        if not paths:
            fallback = " / ".join(notes) or manual_note(", ".join(seg["files"]))
            await _paste_html_segment(page, frame, markdown_to_html(fallback), iframe_rect)
            print(f"  ! {seg['kind']} {seg['files']}: 유효 이미지 없음 → 수동 안내")
            frame = await _find_editor_frame(page) or frame
            continue

        is_multi = seg["kind"] in ("slide", "collage") or len(paths) > 1
        layout_label = "콜라주" if seg["kind"] == "collage" else "슬라이드"
        before = await _count_editor_images(page)
        await _cursor_to_end(frame)
        uploaded = await _upload_images_via_chooser(page, paths)
        if uploaded and is_multi and len(paths) > 1:
            await _select_photo_layout(page, layout_label)   # '사진 첨부 방식'
        inserted = False
        if uploaded:
            for _ in range(25):
                await page.wait_for_timeout(1000)
                if await _count_editor_images(page) > before:
                    inserted = True
                    break
            if inserted:
                await page.wait_for_timeout(1800)  # 삽입 DOM 안정화 후 다음 세그먼트
        frame = await _find_editor_frame(page) or frame
        if inserted:
            kind_ko = {"slide": "슬라이드", "collage": "콜라주"}.get(seg["kind"], "이미지")
            label = f"{kind_ko} {len(paths)}장" if len(paths) > 1 else "이미지"
            print(f"  ✓ {label} 삽입: {[os.path.basename(x) for x in paths]}")
            if notes:  # 일부만 유효했던 경우 나머지는 수동 안내
                await _paste_html_segment(page, frame, markdown_to_html(" / ".join(notes)), iframe_rect)
                frame = await _find_editor_frame(page) or frame
            # caption은 본문 텍스트로 삽입하지 않는다 — 에디터에서 이미지 클릭 후 직접 입력
        else:
            note = manual_note(", ".join(seg["files"]), "업로드 확인 실패 — 수동 삽입")
            await _paste_html_segment(page, frame, markdown_to_html(note), iframe_rect)
            print(f"  ! {seg['kind']} {seg['files']}: 업로드/증가 미확인 → 수동 안내")
    return first_ok


async def _insert_body_fulltext(page, body_html, body_plain, iframe_rect) -> None:
    """전체 본문 단일 HTML clipboard paste(기존 검증 경로) → innerHTML/plain 폴백."""
    print("본문 입력 중...")
    try:
        editor_frame = await _find_editor_frame(page)
        if not editor_frame:
            raise Exception("iframe not found")
        body_click_y = int(iframe_rect['y']) + 200 if iframe_rect else 600
        await page.mouse.click(640, body_click_y)
        await page.wait_for_timeout(400)
        clip = await _write_clipboard_html(editor_frame, body_html)
        print(f"  clipboard write 결과: {clip}")
        if clip != "ok":
            raise Exception(clip)
        await page.keyboard.press("Control+v")
        await page.wait_for_timeout(800)
        await page.screenshot(path="/tmp/naver_after_body.png")
        print("  ✓ 본문 완료 (HTML clipboard paste)")
        return
    except Exception:
        pass
    try:
        editor_frame = await _find_editor_frame(page)
        if editor_frame:
            await editor_frame.evaluate(
                "(html) => { document.body.innerHTML = html; "
                "document.body.dispatchEvent(new Event('input', {bubbles:true})); }",
                body_html)
            print("  ✓ 본문 완료 (innerHTML fallback)")
        else:
            await page.evaluate(f"() => navigator.clipboard.writeText({json.dumps(body_plain)})")
            body_area = page.locator("div[contenteditable]").nth(1)
            await body_area.click()
            await page.keyboard.press("Control+v")
            print("  ✓ 본문 완료 (plain text clipboard fallback)")
    except Exception as e2:
        await page.screenshot(path="/tmp/naver_error_body.png")
        print(f"  ✗ 본문 실패: {e2}")


async def main():
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/naver_publish.py .claude/artifacts/naver/[slug]-naver.md")
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"[오류] 파일 없음: {filepath}")
        sys.exit(1)

    title, body, tags = parse_naver_md(filepath)
    body_html = markdown_to_html(body)
    # 이미지 앵커 분할: 있으면 인터리브, 없으면 전체 텍스트. 폴백용 body_html은 앵커를 수동안내로 평탄화.
    _segments = split_body_by_anchor(body)
    _image_segs = [s for s in _segments if s["type"] == "media"]
    if _image_segs:
        body_html = markdown_to_html(flatten_segments_to_text(_segments))
    _slug = re.sub(r"-naver\.md$", "", os.path.basename(filepath))
    _images_root = f".claude/artifacts/naver/images/{_slug}/"
    write_url = f"https://blog.naver.com/{NAVER_BLOG_ID}/postwrite"

    print(f"제목 ({len(title)}자): {title}")
    print(f"본문: {len(body)}자  태그: {len(tags)}개  blogId: {NAVER_BLOG_ID}")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
            env=dict(os.environ),  # DISPLAY/WAYLAND_DISPLAY 등 화면 변수 명시 전달
        )
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.pages[0] if context.pages else await context.new_page()

        # ── 로그인 확인 ──────────────────────────────────────────────
        print("\n로그인 상태 확인 중...")
        await page.goto(write_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        if "login" in page.url or "nidlogin" in page.url:
            print("로그인 필요 — 브라우저에서 로그인해주세요. (최대 5분 대기)")
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await page.wait_for_url(
                lambda url: "nidlogin" not in url and "login" not in url,
                timeout=300000,
            )
            await page.goto(write_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

        print(f"  ✓ 에디터 URL: {page.url}")
        await page.wait_for_timeout(2000)

        # ── "작성 중인 글" 팝업 처리 ────────────────────────────────
        # wait_for_selector로 팝업 등장 대기 (최대 8초)
        # 취소/닫기/아니오 텍스트 버튼을 탐색해서 클릭 — 무작정 첫 버튼 클릭 안 함
        try:
            await page.wait_for_selector(".se-popup-dim", state="visible", timeout=8000)
            clicked = await page.evaluate("""
                () => {
                    const dimEl = document.querySelector('.se-popup-dim');
                    if (!dimEl) return 'no_popup';
                    // 버튼은 dim 자체가 아닌 부모 컨테이너 안에 있음
                    const container = dimEl.parentElement || document.body;
                    const btns = Array.from(container.querySelectorAll('button'));
                    const cancel = btns.find(b =>
                        ['취소', '닫기', '아니오'].some(t => b.textContent.trim().includes(t))
                        || b.getAttribute('aria-label') === '닫기'
                    );
                    if (cancel) { cancel.click(); return 'dismissed'; }
                    return 'no_cancel_btn';
                }
            """)
            if clicked == "dismissed":
                await page.wait_for_selector(".se-popup-dim", state="hidden", timeout=3000)
                print("  ✓ 임시저장 팝업 닫음 (취소 버튼)")
                await page.wait_for_timeout(1000)
            elif clicked == "no_cancel_btn":
                await page.screenshot(path="/tmp/naver_error_popup.png")
                print("  ✗ 팝업 있으나 취소 버튼 없음 → 중단. 스크린샷: /tmp/naver_error_popup.png")
                await context.close()
                return
        except Exception:
            print("  팝업 없음 — 계속 진행")

        # ── 제목 입력 (모든 iframe probe → 좌표 fallback) ───────────
        # SmartEditor 전체가 iframe 안에 있으므로 main page가 아닌 각 frame에서 탐색
        # contenteditable + input + textarea 모두 탐색, 높이 필터 없음
        iframe_rect = None   # body paste / image 삽입 섹션에서 공유
        print("\n제목 입력 중...")
        title_done = False
        try:
            title_json = json.dumps(title)
            for frame in page.frames:
                try:
                    result = await frame.evaluate(f"""
                        () => {{
                            const TITLE = {title_json};
                            // contenteditable div + input[type!=hidden] + textarea 모두 탐색
                            const selectors = [
                                '[contenteditable]:not(body)',
                                'input:not([type=hidden]):not([type=submit]):not([type=button])',
                                'textarea'
                            ];
                            const all = selectors.flatMap(s => [...document.querySelectorAll(s)]);
                            const candidates = all.filter(e => {{
                                // 검색창 제외 (클래스명에 search 포함)
                                if ((e.className||'').toLowerCase().includes('search')) return false;
                                if (e.type === 'search') return false;
                                const r = e.getBoundingClientRect();
                                return r.height > 0 && r.width > 100;
                            }});
                            const probe = candidates.map(e =>
                                e.tagName + '|' + (e.className||'').split(' ')[0] + '|' + (e.type||'') +
                                '|h=' + Math.round(e.getBoundingClientRect().height) +
                                '|y=' + Math.round(e.getBoundingClientRect().y)
                            );
                            if (candidates.length === 0) return JSON.stringify({{status: 'not_found', probe}});
                            // "제목" 관련 placeholder 요소 우선, 없으면 y좌표 최상단
                            const titleEl = candidates.find(e => {{
                                const ph = (e.getAttribute('placeholder') || e.getAttribute('data-placeholder') || '').toLowerCase();
                                const cls = (e.className||'').toLowerCase();
                                return ph.includes('제목') || cls.includes('title') || cls.includes('documenttitle');
                            }});
                            const el = titleEl || candidates.sort((a, b) =>
                                a.getBoundingClientRect().y - b.getBoundingClientRect().y
                            )[0];
                            el.focus();
                            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {{
                                el.value = TITLE;
                                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                                const actual = el.value.trim();
                                const status = actual === TITLE.trim() ? 'ok' : 'mismatch:' + actual.slice(0, 30);
                                return JSON.stringify({{status, probe}});
                            }} else {{
                                document.execCommand('selectAll');
                                document.execCommand('insertText', false, TITLE);
                                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                                const actual = el.innerText.trim();
                                const status = actual === TITLE.trim() ? 'ok' : 'mismatch:' + actual.slice(0, 30);
                                return JSON.stringify({{status, probe}});
                            }}
                        }}
                    """)
                    parsed = json.loads(result)
                    if parsed.get('status') == 'ok':
                        print("  ✓ 제목 완료 (iframe probe)")
                        title_done = True
                        break
                except Exception as fe:
                    print(f"  [{frame.url[:40]}] 평가 오류: {fe}")
                    continue

            if not title_done:
                # body iframe의 실제 위치를 구해 그 위(제목 영역)를 클릭
                iframe_rect = await page.evaluate("""
                    () => {
                        const iframes = [...document.querySelectorAll('iframe')];
                        // about:blank iframe 또는 가장 큰 iframe을 body editor로 판정
                        let target = iframes.find(f => {
                            try { return f.contentDocument && f.contentDocument.location.href === 'about:blank'; }
                            catch { return false; }
                        });
                        if (!target) {
                            target = iframes.reduce((a, b) => {
                                const ra = a ? a.getBoundingClientRect() : {width:0, height:0};
                                const rb = b.getBoundingClientRect();
                                return ra.width * ra.height >= rb.width * rb.height ? a : b;
                            }, null);
                        }
                        if (!target) return null;
                        const r = target.getBoundingClientRect();
                        return {x: r.x, y: r.y, w: r.width};
                    }
                """)
                if iframe_rect:
                    title_x = int(iframe_rect['x'] + iframe_rect['w'] // 2)
                    # 제목 영역은 iframe 상단보다 한참 위 — 오프셋 120px
                    title_y = max(int(iframe_rect['y']) - 120, 100)
                    print(f"  iframe 상단 y={int(iframe_rect['y'])} → 제목 클릭 y={title_y}")
                else:
                    title_x, title_y = 640, 250
                    print(f"  iframe 위치 불명 → 고정 좌표 ({title_x}, {title_y})")
                await page.mouse.click(title_x, title_y)
                await page.wait_for_timeout(300)
                await page.keyboard.press("Control+a")
                await page.keyboard.type(title, delay=15)
                await page.screenshot(path="/tmp/naver_after_title.png")
                print("  ✓ 제목 입력 (iframe 기준 좌표 — 수동 확인 권장)")
        except Exception as e:
            print(f"  ✗ 제목 실패: {e}")

        await page.wait_for_timeout(500)

        # ── 본문 입력 — 앵커 있으면 인터리브(텍스트+이미지), 없으면 전체 텍스트 ──
        _body_done = False
        if _image_segs:
            print(f"본문 입력 (인터리브: 텍스트 + 이미지 {len(_image_segs)}장)...")
            try:
                _body_done = await _insert_body_interleaved(
                    page, _segments, _images_root, iframe_rect)
            except Exception as _ie:
                print(f"  ! 인터리브 예외 → 전체 텍스트 폴백: {_ie}")
                _body_done = False
            if _body_done:
                await page.screenshot(path="/tmp/naver_after_body.png")
                print("  ✓ 본문 완료 (인터리브 삽입)")
        if not _body_done:
            await _insert_body_fulltext(page, body_html, body, iframe_rect)

        await page.wait_for_timeout(500)

        # 잔여 패널(장소 검색 등)이 발행 버튼을 가릴 수 있어 Esc로 정리 + 본문 클릭
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            await page.mouse.click(640, 500)
            await page.wait_for_timeout(500)
        except Exception:
            pass

        # ── 발행 버튼 클릭 → 태그 모달 열기 ───────────────────────
        # 발행 버튼은 태그 모달을 열기 위해서만 사용.
        # 모달 내 최종 발행 확인/완료 버튼은 절대 클릭하지 않는다.
        print("발행 버튼 클릭 (태그 모달 열기)...")
        try:
            publish_btn = page.get_by_role("button", name=re.compile("발행")).first
            await publish_btn.wait_for(state="visible", timeout=5000)
            await publish_btn.click(timeout=8000)
            await page.wait_for_timeout(2000)
            print("  ✓ 발행 모달 열림")

            # 태그 입력란 — 셀렉터 fallback 순서대로 시도
            print(f"태그 입력 중 ({len(tags)}개)...")
            tag_input = None
            for sel in ["input[placeholder*='태그']", "input.se-tag-input", "input[class*='tag']"]:
                candidate = page.locator(sel).first
                try:
                    await candidate.wait_for(state="visible", timeout=3000)
                    tag_input = candidate
                    break
                except Exception:
                    continue

            if tag_input is None:
                print("  ✗ 태그 입력란 없음 — 수동 입력 필요")
                print(f"  수동 입력: {', '.join(tags)}")
            else:
                for tag in tags:
                    await tag_input.click()
                    await tag_input.type(tag, delay=20)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(300)
                print(f"  ✓ 태그 {len(tags)}개 입력 완료")
        except Exception as e:
            print(f"  ✗ 태그/발행 모달 실패: {e}")
            print(f"  수동 입력: {', '.join(tags)}")

        # ── 완료 안내 ────────────────────────────────────────────────
        await page.screenshot(path="/tmp/naver_preview.png")
        print("\n" + "=" * 55)
        print("자동 입력 완료. 발행 모달이 열려 있습니다.")
        print("남은 작업 (수동):")
        print("  1. [확인 필요] 항목 확인")
        print("  2. 발행 모달에서 최종 확인 후 발행 클릭")
        print("스크린샷: /tmp/naver_preview.png")
        print("=" * 55)

        print("\n발행 대기 중... 브라우저에서 발행 버튼을 클릭해주세요. (최대 10분)")
        wait_started = asyncio.get_running_loop().time()
        try:
            await page.wait_for_url(
                lambda url: re.search(r"blog\.naver\.com/[^/]+/\d+$", url) is not None,
                timeout=600000,
            )
            print("\n발행 완료 감지됨.")
        except Exception as _wait_err:
            # wait_for_url이 페이지 상태 이상으로 조기 종료된 경우에만
            # asyncio.sleep으로 잔여 시간을 채운다 (총 대기 10분 유지, 중복 대기 방지)
            remaining = 600 - (asyncio.get_running_loop().time() - wait_started)
            if remaining > 1:
                print(f"  [debug] wait_for_url 예외: {type(_wait_err).__name__} — 잔여 {int(remaining)}초 대기")
                await asyncio.sleep(remaining)

        await context.close()
    print("종료.")


if __name__ == "__main__":
    # 브라우저 없이 순수함수만 검증: python3 scripts/naver_publish.py --self-test
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    asyncio.run(main())
