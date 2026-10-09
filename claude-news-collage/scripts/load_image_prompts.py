#!/usr/bin/env python3
"""Return a four-request batch only when saved prompts equal the plan verbatim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from image_prompts import NAMES, load_plan, render_prompts
from make_package import require_local_access


def load_prompts(project: Path) -> list[dict]:
    project = Path(project).expanduser().resolve()
    expected = render_prompts(load_plan(project / "image-plan.json"))
    items = []
    for item in expected:
        path = project / "02-四张图片提示词" / item["name"]
        if not path.is_file():
            raise ValueError(f"缺少第 {item['number']} 张的生图提示词：{path}")
        # Compare bytes, including UTF-8 encoding and the renderer's single final LF.
        if path.read_bytes() != item["prompt"].encode("utf-8"):
            raise ValueError(f"第 {item['number']} 张提示词不等于模板与参数输出，请重新渲染，禁止自由改写")
        items.append({"number": item["number"], "path": str(path), "prompt": item["prompt"]})
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 image-plan 中四份独立 Prompt 与文件完全一致")
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()
    try:
        require_local_access()
        items = load_prompts(args.project)
    except (OSError, ValueError, UnicodeError, PermissionError) as exc:
        parser.error(str(exc))
    print(json.dumps(items, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
