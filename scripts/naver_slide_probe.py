#!/usr/bin/env python3
"""네이버 SmartEditor 슬라이드 삽입 계측 probe (C단계 R&D).

목적(발행/저장 없이 관찰만):
  1) 여러 장 한 번에 업로드 → "사진 첨부 방식" 대화상자 뜨는지
  2) "슬라이드" 자동 클릭 가능한지
  3) 삽입 전/후 에디터 DOM 구조 덤프 → 슬라이드 컴포넌트 클래스 + 블록 순서 파악
     (단일 이미지가 왜 맨 끝에 박히는지 진단 포함)

실행: python3 -u scripts/naver_slide_probe.py
산출: 콘솔 로그(unbuffered) + /tmp/naver_slide_probe_*.png
⚠️ 저장/발행/예약/확인 버튼은 절대 클릭하지 않는다.
"""
import asyncio
import os
import re
import sys
from pathlib import Path

try:
    from naver_config import NAVER_BLOG_ID
except ImportError:
    NAVER_BLOG_ID = "muhyeok1024"

LOGIN_URL = "https://nid.naver.com/nidlogin.login"
PROFILE_DIR = str(Path.home() / ".claude" / "config" / "naver-browser-profile")
WRITE_URL = f"https://blog.naver.com/{NAVER_BLOG_ID}/postwrite"

IMG_DIR = ".claude/artifacts/naver/images/knu-idea-bridge-2026/_probe"
IMAGES = [os.path.abspath(os.path.join(IMG_DIR, f))
          for f in ("IMG_6068.jpg", "IMG_6069.jpg", "IMG_6079.jpg")]


def p(*a):
    print(*a, flush=True)


async def find_editor_frame(page):
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


async def dump_dom(frame, label):
    try:
        info = await frame.evaluate(r"""() => {
            const out = [];
            let comps = document.querySelectorAll('.se-component');
            if (comps.length === 0) {
                // fallback: contenteditable 직계 자식
                const ed = document.querySelector('[contenteditable=true]') || document.body;
                comps = ed.children;
            }
            [...comps].forEach((c, i) => {
                const cls = (c.className && c.className.toString ? c.className.toString() : '')
                    .split(' ').filter(x => x.startsWith('se-')).slice(0, 4).join(' ');
                const txt = (c.innerText || '').trim().slice(0, 24).replace(/\s+/g, ' ');
                const imgs = c.querySelectorAll('img').length;
                out.push(`${i}: <${c.tagName.toLowerCase()}> [${cls}] imgs=${imgs} "${txt}"`);
            });
            return { count: out.length, list: out };
        }""")
        p(f"\n--- DOM dump ({label}): {info['count']} blocks ---")
        for line in info["list"]:
            p("   " + line)
    except Exception as e:
        p(f"  [dump 오류 {label}] {e}")


async def dismiss_popup(page):
    try:
        await page.wait_for_selector(".se-popup-dim", state="visible", timeout=8000)
        r = await page.evaluate("""() => {
            const dim = document.querySelector('.se-popup-dim');
            if (!dim) return 'no_popup';
            const c = dim.parentElement || document.body;
            const b = [...c.querySelectorAll('button')].find(x =>
                ['취소','닫기','아니오'].some(t => x.textContent.includes(t)));
            if (b) { b.click(); return 'dismissed'; }
            return 'no_cancel';
        }""")
        p(f"  임시저장 팝업: {r}")
        await page.wait_for_timeout(1000)
    except Exception:
        p("  임시저장 팝업 없음")


async def main():
    for f in IMAGES:
        if not os.path.isfile(f):
            p(f"[오류] 이미지 없음: {f}")
            return
    p(f"슬라이드 probe — {len(IMAGES)}장 업로드 예정, blogId={NAVER_BLOG_ID}")
    p("⚠️ 저장/발행 없이 관찰만 합니다.")

    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False, locale="ko-KR",
            viewport={"width": 1280, "height": 900})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        p("\n로그인/에디터 로드...")
        await page.goto(WRITE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        if "login" in page.url or "nidlogin" in page.url:
            p("로그인 필요 — 브라우저에서 로그인 (최대 5분)")
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await page.wait_for_url(
                lambda u: "nidlogin" not in u and "login" not in u, timeout=300000)
            await page.goto(WRITE_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
        p(f"  에디터 URL: {page.url}")
        await dismiss_popup(page)
        await page.wait_for_timeout(1500)

        frame = await find_editor_frame(page)
        await dump_dom(frame, "업로드 전")

        # 본문 포커스
        await page.mouse.click(640, 500)
        await page.wait_for_timeout(400)

        # 여러 장 한 번에 업로드
        p(f"\n사진 버튼 → 파일 {len(IMAGES)}장 set_files...")
        try:
            btn = page.get_by_role("button", name=re.compile("사진")).first
            await btn.wait_for(state="visible", timeout=5000)
            async with page.expect_file_chooser(timeout=8000) as fc:
                await btn.click()
            chooser = await fc.value
            await chooser.set_files(IMAGES)
            p("  set_files 완료")
        except Exception as e:
            p(f"  ✗ 업로드 트리거 실패: {e}")
            await page.screenshot(path="/tmp/naver_slide_probe_err.png")
            await ctx.close()
            return

        # "사진 첨부 방식" 대화상자 → 슬라이드
        await page.wait_for_timeout(2500)
        await page.screenshot(path="/tmp/naver_slide_probe_dialog.png")
        dlg = await page.evaluate(r"""() => {
            const all = [...document.querySelectorAll('button, span, div, a, p')];
            const labels = all.map(e => (e.textContent||'').trim())
                .filter(t => ['개별사진','콜라주','슬라이드'].includes(t));
            const uniq = [...new Set(labels)];
            const slide = all.find(e => (e.textContent||'').trim() === '슬라이드');
            let clicked = 'no-slide';
            if (slide) {
                slide.click();
                if (slide.parentElement) slide.parentElement.click();
                clicked = 'slide-clicked';
            }
            return { dialogLabels: uniq, clicked };
        }""")
        p(f"  대화상자 라벨: {dlg['dialogLabels']}  → {dlg['clicked']}")

        # 삽입 대기 (CDN 업로드)
        p("\n삽입 대기(최대 25초)...")
        inserted = 0
        for i in range(25):
            await page.wait_for_timeout(1000)
            cnt = 0
            for fr in page.frames:
                try:
                    cnt += int(await fr.evaluate(
                        "() => document.querySelectorAll('img').length") or 0)
                except Exception:
                    pass
            if cnt > 0:
                inserted = cnt
                p(f"  {i+1}s: img 요소 {cnt}개 감지")
                if i >= 3:
                    break
        await page.wait_for_timeout(2000)

        frame = await find_editor_frame(page)
        await dump_dom(frame, "슬라이드 삽입 후")

        # 슬라이드/이미지 컴포넌트 클래스 상세
        detail = await frame.evaluate(r"""() => {
            const pick = sel => [...document.querySelectorAll(sel)]
                .map(e => (e.className||'').toString().split(' ').slice(0,6).join(' '));
            return {
                slideshow: pick('[class*="slideshow"], [class*="Slide"], [class*="strip"]').slice(0,4),
                image: pick('.se-image, .se-module-image').slice(0,4),
            };
        }""")
        p(f"\n슬라이드류 클래스: {detail['slideshow']}")
        p(f"이미지 클래스: {detail['image']}")

        await page.screenshot(path="/tmp/naver_slide_probe_after.png")
        p("\n" + "=" * 55)
        p(f"결과: img 요소 {inserted}개. 스크린샷 /tmp/naver_slide_probe_{{dialog,after}}.png")
        p("⚠️ 저장/발행 없이 종료.")
        p("=" * 55)
        await page.wait_for_timeout(1500)
        await ctx.close()
    p("종료.")


if __name__ == "__main__":
    asyncio.run(main())
