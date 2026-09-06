#!/usr/bin/env python3
"""네이버 SmartEditor '장소(지도)' 삽입 계측 probe.

목적(발행/저장 없이 관찰만): 장소 버튼 → 검색 패널 구조 → 검색 결과 → 삽입 버튼을 파악.
실행: python3 -u scripts/naver_place_probe.py
산출: unbuffered 로그 + /tmp/naver_place_*.png
⚠️ 저장/발행/예약 버튼은 클릭하지 않는다. (장소 '추가/확인'만 관찰)
"""
import asyncio
import os
import re
from pathlib import Path

try:
    from naver_config import NAVER_BLOG_ID
except ImportError:
    NAVER_BLOG_ID = "muhyeok1024"

LOGIN_URL = "https://nid.naver.com/nidlogin.login"
PROFILE_DIR = str(Path.home() / ".claude" / "config" / "naver-browser-profile")
WRITE_URL = f"https://blog.naver.com/{NAVER_BLOG_ID}/postwrite"
QUERY = "경북대학교 글로벌플라자"


def p(*a):
    print(*a, flush=True)


async def dump_ui(page, label):
    info = await page.evaluate(r"""() => {
        const btns = [...document.querySelectorAll('button')]
            .map(b => (b.getAttribute('aria-label') || b.textContent || '').trim())
            .filter(t => t && t.length <= 16);
        const inputs = [...document.querySelectorAll('input:not([type=hidden])')]
            .map(i => (i.getAttribute('placeholder') || i.className || i.type || '').slice(0,30));
        return { btns: [...new Set(btns)].slice(0,40), inputs: inputs.slice(0,10) };
    }""")
    p(f"\n[{label}] 버튼: {info['btns']}")
    p(f"[{label}] 입력창: {info['inputs']}")


async def main():
    p(f"장소 probe — query='{QUERY}', blogId={NAVER_BLOG_ID}")
    p("⚠️ 저장/발행 없이 관찰만.")
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, headless=False, locale="ko-KR",
            viewport={"width": 1280, "height": 900})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto(WRITE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        if "login" in page.url or "nidlogin" in page.url:
            p("로그인 필요 (최대 5분)")
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await page.wait_for_url(lambda u: "login" not in u, timeout=300000)
            await page.goto(WRITE_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
        # 임시저장 팝업 닫기
        try:
            await page.wait_for_selector(".se-popup-dim", state="visible", timeout=6000)
            await page.evaluate("""() => { const d=document.querySelector('.se-popup-dim');
                if(!d)return; const b=[...(d.parentElement||document).querySelectorAll('button')]
                .find(x=>['취소','닫기','아니오'].some(t=>x.textContent.includes(t))); if(b)b.click(); }""")
            await page.wait_for_timeout(1000)
        except Exception:
            pass

        await dump_ui(page, "에디터")

        # 장소 버튼 클릭
        p("\n장소 버튼 클릭 시도...")
        try:
            btn = page.get_by_role("button", name=re.compile("장소")).first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            await page.wait_for_timeout(2500)
            p("  ✓ 장소 버튼 클릭됨")
        except Exception as e:
            p(f"  ✗ 장소 버튼 실패: {e}")
            await page.screenshot(path="/tmp/naver_place_err.png")
            await ctx.close(); return
        await page.screenshot(path="/tmp/naver_place_panel.png")
        await dump_ui(page, "장소패널")

        # 검색어 입력
        p("\n검색어 입력 시도...")
        typed = False
        for sel in ["input[placeholder*='장소']", "input[placeholder*='검색']",
                    "input[placeholder*='찾']", "input[type=text]"]:
            try:
                inp = page.locator(sel).last
                await inp.wait_for(state="visible", timeout=2500)
                await inp.click()
                await inp.fill(QUERY)
                typed = True
                p(f"  ✓ 입력 성공 (sel={sel})")
                break
            except Exception:
                continue
        if not typed:
            p("  ✗ 검색 입력창 못 찾음")
        else:
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)
            await page.screenshot(path="/tmp/naver_place_results.png")
            # 결과 구조 덤프
            res = await page.evaluate(r"""() => {
                const items = [...document.querySelectorAll('li, .se-place-search-result-item, [class*=result] li, [class*=place] li')]
                    .map(e => (e.textContent||'').trim().slice(0,40)).filter(t=>t.length>3);
                const addBtns = [...document.querySelectorAll('button')]
                    .map(b=>(b.textContent||'').trim()).filter(t=>['추가','확인','삽입','완료','적용'].includes(t));
                return { results: [...new Set(items)].slice(0,8), addBtns:[...new Set(addBtns)] };
            }""")
            p(f"  검색 결과(상위): {res['results']}")
            p(f"  삽입류 버튼: {res['addBtns']}")

        p("\n관찰 종료. 스크린샷: /tmp/naver_place_{panel,results}.png")
        p("⚠️ 저장/발행 없이 종료.")
        await page.wait_for_timeout(1500)
        await ctx.close()
    p("종료.")


if __name__ == "__main__":
    asyncio.run(main())
