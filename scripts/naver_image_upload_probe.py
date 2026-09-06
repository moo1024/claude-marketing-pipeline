#!/usr/bin/env python3
"""
Naver Blog 이미지 업로더 PROBE (단계 1 — 검증 전용)

목적: 네이버 SmartEditor 빈 글쓰기 화면에서
  (1) 사진 업로더(file chooser / hidden <input type=file>)를 찾을 수 있는지
  (2) 테스트용 소형 PNG 1장을 실제로 업로드할 수 있는지
만 검증한다. 본문 텍스트 입력·저장·발행·예약·확인 클릭은 절대 하지 않는다.

사용법:
    python3 scripts/naver_image_upload_probe.py

산출물:
    - stdout 로그(발견한 툴바 버튼/파일 input/업로드 성공 여부 — 단계 2 설계용)
    - /tmp/naver_probe_before.png, /tmp/naver_probe_after.png 스크린샷

⚠️ 이 스크립트는 글을 저장하거나 발행하지 않는다. 업로더 탐색 + 1장 업로드까지만.
"""

import asyncio
import os
import struct
import sys
import zlib
from pathlib import Path

# ── 설정 (기존 naver_publish.py와 동일 규약 재사용) ──────────────────
try:
    from naver_config import NAVER_BLOG_ID
except ImportError:
    NAVER_BLOG_ID = "muhyeok1024"

LOGIN_URL   = "https://nid.naver.com/nidlogin.login"
PROFILE_DIR = str(Path.home() / ".claude" / "config" / "naver-browser-profile")
WRITE_URL   = f"https://blog.naver.com/{NAVER_BLOG_ID}/postwrite"

TEST_IMG_PATH = "/tmp/naver_probe_test.png"

# 발행/저장류 텍스트 — probe는 이 단어가 붙은 버튼을 절대 클릭하지 않는다(안전 가드).
FORBIDDEN_CLICK_WORDS = ("발행", "저장", "예약", "확인", "완료", "게시")


def make_test_png(path: str, w: int = 240, h: int = 160,
                  rgb: tuple[int, int, int] = (80, 120, 200)) -> None:
    """의존성(Pillow) 없이 stdlib만으로 소형 유효 PNG를 생성한다.
    원본 행사 이미지를 쓰지 않기 위한 테스트용 이미지."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8bit truecolor RGB
    row = b"\x00" + bytes(rgb) * w                        # filter 0 + 픽셀
    raw = row * h
    idat = zlib.compress(raw, 9)
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


async def count_images(page) -> int:
    """모든 프레임에서 에디터 이미지 요소 수 합산(업로드 전후 비교용)."""
    total = 0
    for frame in page.frames:
        try:
            n = await frame.evaluate(
                "() => document.querySelectorAll("
                "'img, .se-image-resource, .se-module-image, .se-image').length"
            )
            total += int(n or 0)
        except Exception:
            continue
    return total


async def log_uploader_candidates(page) -> None:
    """단계 2 설계를 돕기 위해 툴바 버튼/파일 input 후보를 로그로 남긴다."""
    print("\n[probe] 툴바 버튼 후보 (main page):")
    try:
        names = await page.evaluate(r"""
            () => Array.from(document.querySelectorAll('button'))
                .map(b => (b.getAttribute('aria-label') || b.textContent || '').trim())
                .filter(t => t && t.length <= 20)
                .slice(0, 60)
        """)
        photo_like = [n for n in names if ("사진" in n or "이미지" in n)]
        print(f"    총 {len(names)}개 중 사진/이미지 관련: {photo_like or '없음'}")
    except Exception as e:
        print(f"    버튼 탐색 오류: {e}")

    print("[probe] input[type=file] 후보 (전 프레임):")
    for frame in page.frames:
        try:
            cnt = await frame.evaluate(
                "() => document.querySelectorAll('input[type=file]').length"
            )
            if cnt:
                print(f"    frame={frame.url[:50]!r} → input[type=file] {cnt}개")
        except Exception:
            continue


async def dismiss_draft_popup(page) -> None:
    """'작성 중인 글' 팝업이 뜨면 취소 버튼으로 닫는다(기존 naver_publish.py 로직 재사용)."""
    try:
        await page.wait_for_selector(".se-popup-dim", state="visible", timeout=8000)
        clicked = await page.evaluate("""
            () => {
                const dim = document.querySelector('.se-popup-dim');
                if (!dim) return 'no_popup';
                const container = dim.parentElement || document.body;
                const btns = Array.from(container.querySelectorAll('button'));
                const cancel = btns.find(b =>
                    ['취소', '닫기', '아니오'].some(t => b.textContent.trim().includes(t))
                    || b.getAttribute('aria-label') === '닫기');
                if (cancel) { cancel.click(); return 'dismissed'; }
                return 'no_cancel_btn';
            }
        """)
        if clicked == "dismissed":
            await page.wait_for_selector(".se-popup-dim", state="hidden", timeout=3000)
            print("  ✓ 임시저장 팝업 닫음 (취소)")
            await page.wait_for_timeout(1000)
        elif clicked == "no_cancel_btn":
            print("  ! 팝업 있으나 취소 버튼 못 찾음 — 계속 진행(클릭 안 함)")
    except Exception:
        print("  팝업 없음 — 계속 진행")


async def try_upload(page) -> str:
    """사진 업로더로 테스트 이미지 1장 업로드 시도.
    primary: file_chooser / fallback: hidden input[type=file] 직접 주입.
    저장·발행 버튼은 절대 클릭하지 않는다."""

    # ── primary: 사진 툴바 버튼 클릭 → file chooser ──────────────────
    try:
        import re
        photo_btn = page.get_by_role(
            "button", name=re.compile("사진|이미지")
        ).first
        await photo_btn.wait_for(state="visible", timeout=5000)
        label = (await photo_btn.get_attribute("aria-label")) or "(사진)"
        # 안전 가드: 발행/저장류 버튼이면 클릭하지 않는다
        if any(w in (label or "") for w in FORBIDDEN_CLICK_WORDS):
            return "aborted: 사진 버튼 라벨에 발행/저장류 단어 포함 — 클릭 안 함"
        async with page.expect_file_chooser(timeout=8000) as fc_info:
            await photo_btn.click()
        chooser = await fc_info.value
        await chooser.set_files(TEST_IMG_PATH)
        return f"ok(file_chooser via '{label}')"
    except Exception as e:
        print(f"  [primary 실패] file_chooser 경로: {e}")

    # ── fallback: 전 프레임에서 input[type=file] 직접 set_input_files ──
    for frame in page.frames:
        try:
            inp = frame.locator("input[type=file]").first
            if await inp.count() > 0:
                await inp.set_input_files(TEST_IMG_PATH)
                return f"ok(input[type=file] via frame {frame.url[:40]!r})"
        except Exception as e:
            print(f"  [fallback] frame={frame.url[:30]!r} 오류: {e}")
            continue

    return "failed: 업로더를 찾지 못함(툴바 버튼·file input 모두 실패)"


async def main() -> None:
    make_test_png(TEST_IMG_PATH)
    size_kb = round(Path(TEST_IMG_PATH).stat().st_size / 1024, 1)
    print(f"[probe] 테스트 이미지 생성: {TEST_IMG_PATH} ({size_kb} KB)")
    print(f"[probe] blogId={NAVER_BLOG_ID}  write_url={WRITE_URL}")
    print("[probe] ⚠️ 이 스크립트는 저장/발행/예약/확인을 절대 클릭하지 않습니다.\n")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # ── 로그인 확인 ──────────────────────────────────────────────
        print("로그인 상태 확인 중...")
        await page.goto(WRITE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        if "login" in page.url or "nidlogin" in page.url:
            print("로그인 필요 — 브라우저에서 로그인해주세요. (최대 5분 대기)")
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await page.wait_for_url(
                lambda url: "nidlogin" not in url and "login" not in url,
                timeout=300000,
            )
            await page.goto(WRITE_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
        print(f"  ✓ 에디터 URL: {page.url}")

        await dismiss_draft_popup(page)
        await page.wait_for_timeout(1500)

        # ── 업로드 전 상태 기록 ─────────────────────────────────────
        await page.screenshot(path="/tmp/naver_probe_before.png")
        before = await count_images(page)
        print(f"\n[probe] 업로드 전 이미지 요소 수: {before}")
        await log_uploader_candidates(page)

        # ── 업로드 시도 ─────────────────────────────────────────────
        print("\n[probe] 테스트 이미지 업로드 시도...")
        result = await try_upload(page)
        print(f"[probe] 업로드 결과: {result}")

        # 업로드 반영 대기(모달/미리보기 렌더링)
        await page.wait_for_timeout(4000)
        after = await count_images(page)
        await page.screenshot(path="/tmp/naver_probe_after.png")

        # ── 판정 ────────────────────────────────────────────────────
        print("\n" + "=" * 55)
        print(f"[probe] 업로드 전 이미지 수: {before} → 후: {after}")
        if result.startswith("ok") and after > before:
            print("✅ PROBE 성공: 업로더로 이미지 1장 삽입 확인됨.")
        elif result.startswith("ok"):
            print("△ PROBE 부분 성공: 업로더는 열렸으나 이미지 요소 증가 미확인.")
            print("   (모달에서 '넣기' 확인 단계가 필요할 수 있음 — 단계 2에서 처리)")
        else:
            print("❌ PROBE 실패: 업로더 경로를 찾지 못함. 로그의 버튼/ input 후보 참고.")
        print("스크린샷: /tmp/naver_probe_before.png, /tmp/naver_probe_after.png")
        print("⚠️ 저장/발행 없이 종료합니다.")
        print("=" * 55)

        await page.wait_for_timeout(1500)
        await context.close()
    print("종료.")


if __name__ == "__main__":
    asyncio.run(main())
