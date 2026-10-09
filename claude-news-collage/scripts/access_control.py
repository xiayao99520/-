#!/usr/bin/env python3
"""Manage the transparent local on/off switch for this Skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "local-control.json"


class ControlError(ValueError):
    """Raised when the local control file is missing or invalid."""


def read_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ControlError(f"本地控制文件不存在：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ControlError(f"本地控制文件无法读取：{path}") from exc
    if not isinstance(data, dict) or type(data.get("enabled")) is not bool:
        raise ControlError('本地控制文件必须包含布尔字段 "enabled"')
    return data


def is_enabled(path: Path = DEFAULT_CONFIG) -> bool:
    return bool(read_config(path)["enabled"])


def set_enabled(path: Path, enabled: bool) -> None:
    data: dict[str, Any]
    if path.exists():
        data = read_config(path)
    else:
        data = {}
    data["enabled"] = enabled
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查或切换 Skill 的本地启用状态")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查当前状态（默认操作）")
    mode.add_argument("--enable", action="store_true", help="启用 Skill")
    mode.add_argument("--disable", action="store_true", help="停用 Skill")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="本地控制文件路径")
    args = parser.parse_args(argv)
    try:
        if args.enable or args.disable:
            set_enabled(args.config, args.enable)
            print("已启用" if args.enable else "已停用")
            return 0
        enabled = is_enabled(args.config)
    except ControlError as exc:
        print(str(exc))
        return 2
    if enabled:
        print("本地控制：已启用")
        return 0
    print("本地控制：已停用")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
