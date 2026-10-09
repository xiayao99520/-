#!/usr/bin/env python3
"""Copy four generated images and the final Jimeng prompt without changing bytes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil


PROMPT_NAME = "05-即梦视频提示词.txt"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def delivery_sources(project: Path) -> list[Path]:
    """Check the file whitelist; workflow completion remains the Skill's responsibility."""
    if not project.is_dir():
        raise ValueError(f"内部项目目录不存在：{project}")
    image_dir = project / "03-图片"
    if not image_dir.is_dir():
        raise ValueError(f"图片目录不存在：{image_dir}")
    numbered: dict[str, list[Path]] = {f"{i:02d}": [] for i in range(1, 5)}
    for path in image_dir.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            match = re.match(r"^(0[1-4])(?:\D|$)", path.stem)
            if match:
                numbered[match.group(1)].append(path)
    sources = []
    for number, candidates in numbered.items():
        if len(candidates) != 1:
            raise ValueError(f"编号 {number} 必须恰好有一张最终图片，实际找到 {len(candidates)} 张")
        if candidates[0].stat().st_size == 0:
            raise ValueError(f"图片文件为空：{candidates[0].name}")
        sources.append(candidates[0])
    prompt = project / PROMPT_NAME
    if not prompt.is_file() or not prompt.read_text(encoding="utf-8-sig").strip():
        raise ValueError(f"最终即梦提示词不存在或为空：{prompt}")
    sources.append(prompt)
    return sources


def new_delivery_dir(requested: Path) -> Path:
    requested.parent.mkdir(parents=True, exist_ok=True)
    version = 1
    while True:
        candidate = requested if version == 1 else requested.with_name(f"{requested.name}_{version:02d}")
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            version += 1


def export_delivery(project: Path, output: Path | None = None) -> Path:
    project = project.expanduser().resolve()
    requested = (output.expanduser().resolve() if output else project.parent / "交付" / project.name)
    if requested == project or project in requested.parents:
        raise ValueError("交付目录必须独立于内部项目目录")
    # Validate every input before creating any delivery folder.
    sources = delivery_sources(project)
    expected = {source.name: digest(source) for source in sources}
    destination = new_delivery_dir(requested)
    try:
        for source in sources:
            target = destination / source.name
            shutil.copyfile(source, target)
            if digest(target) != expected[source.name] or digest(source) != expected[source.name]:
                raise ValueError(f"复制校验失败：{source.name}")
        if {p.name for p in destination.iterdir()} != set(expected):
            raise ValueError("交付目录必须严格只有四张图片和一个提示词文件")
    except Exception:
        # Only remove this invocation's known copies; never remove an old version.
        for name in expected:
            target = destination / name
            if target.is_file():
                target.unlink()
        if not any(destination.iterdir()):
            destination.rmdir()
        raise
    return destination


def require_local_access() -> None:
    from access_control import ControlError, is_enabled

    try:
        enabled = is_enabled()
    except ControlError as exc:
        raise PermissionError(str(exc)) from exc
    if not enabled:
        raise PermissionError("本地控制已停用，未导出交付目录")


def main() -> int:
    parser = argparse.ArgumentParser(description="原样导出四张图片与最终即梦提示词")
    parser.add_argument("--project", type=Path, required=True, help="已完成内部生成和文件完整性核对的项目目录")
    parser.add_argument("--output", type=Path, help="交付目录；默认：项目父目录/交付/项目名")
    args = parser.parse_args()
    try:
        require_local_access()
        destination = export_delivery(args.project, args.output)
    except (OSError, PermissionError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
