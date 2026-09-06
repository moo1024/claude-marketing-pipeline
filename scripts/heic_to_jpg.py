#!/usr/bin/env python3
"""HEIC/HEIF → JPG 변환 (EXIF 회전 보정 + 리사이즈 + 압축).

원본은 절대 수정/삭제하지 않는다. 출력은 지정 폴더에만 저장한다.
목표: 긴 변 ~1800px, 장당 8MB 이하 (네이버 업로드 안전).

사용:
  python3 scripts/heic_to_jpg.py <출력폴더> <파일1.heic> [파일2 ...]
  python3 scripts/heic_to_jpg.py <출력폴더> --dir "<소스폴더>" [--max N] [--start N]
"""
import os
import sys

from pillow_heif import register_heif_opener  # noqa: E402
register_heif_opener()
from PIL import Image, ImageOps  # noqa: E402

LONG_EDGE = 1800
QUALITY = 85
MAX_BYTES = 8 * 1024 * 1024
EXTS = (".heic", ".heif", ".jpg", ".jpeg", ".png")


def convert_one(src: str, out_dir: str) -> tuple[str, int] | None:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(out_dir, base + ".jpg")
    try:
        im = Image.open(src)
        im = ImageOps.exif_transpose(im).convert("RGB")
    except Exception as e:
        print(f"  [SKIP] {os.path.basename(src)}: {e}")
        return None
    w, h = im.size
    scale = LONG_EDGE / max(w, h)
    if scale < 1:
        im = im.resize((int(w * scale), int(h * scale)))
    q = QUALITY
    im.save(out, "JPEG", quality=q)
    while os.path.getsize(out) > MAX_BYTES and q > 40:
        q -= 10
        im.save(out, "JPEG", quality=q)
    size = os.path.getsize(out)
    print(f"  [OK] {os.path.basename(src)} → {os.path.basename(out)} "
          f"({round(size/1024/1024, 2)}MB, q={q})")
    return out, size


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    out_dir = sys.argv[1]
    rest = sys.argv[2:]

    files = []
    if rest and rest[0] == "--dir":
        src_dir = rest[1]
        mx, start = None, 0
        if "--max" in rest:
            mx = int(rest[rest.index("--max") + 1])
        if "--start" in rest:
            start = int(rest[rest.index("--start") + 1])
        allf = sorted(
            os.path.join(src_dir, f) for f in os.listdir(src_dir)
            if f.lower().endswith(EXTS))
        files = allf[start: (start + mx) if mx else None]
    else:
        files = rest

    ok = 0
    for f in files:
        if convert_one(f, out_dir):
            ok += 1
    print(f"\n변환 완료: {ok}/{len(files)}장 → {out_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
