#!/usr/bin/env python3
"""Fast path: the whole workflow in two calls, using the ORIGINAL functions.

  start   access check + plan checks (all errors at once) + prepare_package.prepare()
          (which also runs load_image_prompts) -> prints the four prompts as JSON
  finish  copy the four image_gen files into 03-图片 -> make_package.make(--video-only)
          with the plan's own parameters -> export_delivery() -> prints the folder

Nothing here builds or edits prompt text. 05-即梦视频提示词.txt is written only by
the original make_package.make()/write() from content_parameters(plan), exactly as
`make_package.py --video-only` would, and copied by the original export_delivery().

Usage:
  python run.py start  --plan <image-plan.json> --output <内部父目录> [--date YYYY-MM-DD]
  python run.py finish --project <内部项目目录> --images <图1> <图2> <图3> <图4> [--preview]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_plan_rules import check as check_rules  # noqa: E402
from export_delivery import IMAGE_EXTENSIONS, export_delivery  # noqa: E402
from image_prompts import NAMES, content_parameters, load_plan, validate_plan  # noqa: E402
from load_image_prompts import load_prompts  # noqa: E402
import make_package  # noqa: E402
from prepare_package import prepare  # noqa: E402


def plan_errors(plan_path: Path) -> list[str]:
    """Collect every problem before anything is written, so one fix pass is enough."""
    try:
        raw = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return [f"image-plan.json 不是合法 JSON：第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}"]
    errors = []
    try:
        validate_plan(raw)  # original validator: fields, markers, placeholders
    except ValueError as exc:
        errors.append(f"原项目校验：{exc}")
    if isinstance(raw, dict):
        errors += check_rules(raw)
    return errors


def start(plan_path: Path, output: Path, date: str | None) -> dict:
    make_package.require_local_access()
    errors = plan_errors(plan_path)
    if errors:
        raise ValueError("方案未通过，未建立任何目录：\n- " + "\n- ".join(errors))
    project = prepare(plan_path, output, date)
    return {"project": str(project), "prompts": load_prompts(project)}


def finish(project: Path, images: list[Path], preview: bool = False) -> Path:
    make_package.require_local_access()
    project = project.expanduser().resolve()
    plan = load_plan(project / "image-plan.json")
    sources = []
    for name, src in zip(NAMES, images):
        if not src.is_file() or src.stat().st_size == 0:
            raise ValueError(f"{name[:2]} 号图片不存在或为空：{src}")
        if src.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"{name[:2]} 号图片格式 {src.suffix} 不受原导出脚本支持（png/jpg/jpeg）")
        sources.append((src, project / "03-图片" / (Path(name).stem + src.suffix.lower())))
    keep = {src.resolve() for src, _ in sources}
    for _, target in sources:  # one final image per number, as export_delivery requires
        for stale in target.parent.glob(target.stem + ".*"):
            if stale.suffix.lower() in IMAGE_EXTENSIONS and stale.resolve() not in keep:
                stale.unlink()
    for src, target in sources:
        if src.resolve() != target.resolve():
            shutil.copyfile(src, target)

    # Same Namespace that `make_package.py --video-only ...` builds from its CLI.
    content = content_parameters(plan)
    args = argparse.Namespace(
        speech=plan["speech"], title=plan["title"], **content,
        output=str(project.parent), date=project.name[:10],
        duration=float(plan["duration_seconds"]), video_only=True,
    )
    if make_package.make(args) != project:
        raise ValueError("项目目录与 title/date 不对应，无法定位原素材包")
    delivery = export_delivery(project)
    if preview:
        from make_preview import make_preview
        make_preview(project)
    return delivery


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--plan", type=Path, required=True)
    s.add_argument("--output", type=Path, required=True)
    s.add_argument("--date")
    f = sub.add_parser("finish")
    f.add_argument("--project", type=Path, required=True)
    f.add_argument("--images", type=Path, nargs=4, required=True, metavar="IMG")
    f.add_argument("--preview", action="store_true", help="另在内部项目写 四图预览.jpg")
    args = ap.parse_args()
    try:
        if args.cmd == "start":
            print(json.dumps(start(args.plan, args.output, args.date), ensure_ascii=False))
        else:
            print(finish(args.project, args.images, args.preview))
    except (OSError, ValueError, UnicodeError, PermissionError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
