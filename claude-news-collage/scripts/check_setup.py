#!/usr/bin/env python3
"""Environment self-check for claude-news-collage.

Required: Python >= 3.9 and the original local switch (config/local-control.json
enabled). Optional: Pillow, only for the internal 四图预览.jpg. GEMINI_API_KEY,
ffmpeg and video APIs are never required.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SCRIPTS = Path(__file__).resolve().parent


def main() -> int:
    fail = False
    if sys.version_info >= (3, 9):
        print(f"PASS  Python {sys.version.split()[0]}")
    else:
        print("FAIL  需要 Python >= 3.9")
        fail = True

    done = subprocess.run([sys.executable, str(SCRIPTS / "access_control.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env={**__import__("os").environ, "PYTHONUTF8": "1"})
    if done.returncode == 0:
        print("PASS  " + done.stdout.strip())
    else:
        print("FAIL  " + (done.stdout.strip() or "本地控制检查失败") + "（运行 scripts/access_control.py --enable 启用）")
        fail = True

    try:
        import PIL  # noqa: F401
        print("PASS  Pillow 可用（内部四图预览）")
    except ImportError:
        print("WARN  缺少 Pillow：四图预览不可用，不影响图片与即梦提示词（python -m pip install pillow）")

    print("INFO  四张图由 Codex 内置 image_gen 生成；默认流程不需要 GEMINI_API_KEY、ffmpeg 或任何视频 API")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
