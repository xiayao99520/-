#!/usr/bin/env python3
"""Write 四图预览.jpg into the INTERNAL project from 03-图片/01–04.

Optional convenience only: it reads the four images, never changes them, and
is never copied to the delivery folder (export_delivery.py keeps its strict
four-images-plus-one-prompt whitelist).

Usage:
  python make_preview.py --project <内部项目目录>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

FONTS = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
         "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]


def make_preview(project: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    images = {}
    for path in (project / "03-图片").iterdir():
        m = re.match(r"^(0[1-4])", path.stem)
        if m and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            images[int(m.group(1))] = path
    if sorted(images) != [1, 2, 3, 4]:
        raise FileNotFoundError(f"03-图片 中缺少编号：{sorted(set(range(1, 5)) - set(images))}")
    font = next((ImageFont.truetype(f, 30) for f in FONTS if Path(f).exists()), ImageFont.load_default())
    tw, th, gap, head = 405, 720, 48, 80
    sheet = Image.new("RGB", (tw * 4 + gap * 5, th + head + gap), "#1E1E1E")
    draw = ImageDraw.Draw(sheet)
    for i in range(4):
        path = images[i + 1]
        with Image.open(path) as im:
            frame = im.convert("RGB").resize((tw, th))
        x = gap + i * (tw + gap)
        sheet.paste(frame, (x, head))
        draw.text((x, 22), path.stem, fill="#F4EBD8", font=font)
        if i < 3:
            ax, ay = x + tw + 10, head + th // 2
            draw.polygon([(ax, ay - 14), (ax + 28, ay), (ax, ay + 14)], fill="#E8B931")
    out = project / "四图预览.jpg"
    sheet.save(out, "JPEG", quality=90)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, type=Path)
    args = ap.parse_args()
    print(make_preview(args.project.expanduser().resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
