#!/usr/bin/env python3
"""Rerender four image prompts using the package's explicitly recorded version."""

from __future__ import annotations

import argparse
from pathlib import Path

from image_prompts import load_plan, write_prompts
from load_image_prompts import load_prompts
from make_package import require_local_access


def main() -> int:
    parser = argparse.ArgumentParser(description="根据内部 image-plan.json 重写四份版本化生图提示词")
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()
    try:
        require_local_access()
        project = args.project.expanduser().resolve()
        plan = load_plan(project / "image-plan.json")
        write_prompts(project, plan)
        load_prompts(project)
    except (OSError, ValueError, UnicodeError, PermissionError) as exc:
        parser.error(str(exc))
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
