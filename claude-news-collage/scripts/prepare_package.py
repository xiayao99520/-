#!/usr/bin/env python3
"""Create a separate trial package with four independent, saved prompts."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from image_prompts import TEMPLATES, content_parameters, load_plan, render_prompts, write_prompts
from make_package import clean_name, require_local_access, video_prompt, write
from load_image_prompts import load_prompts


def prepare(plan_path: Path, output: Path, date_string: str | None = None) -> Path:
    plan = load_plan(plan_path)
    if plan["schema_version"] != 3:
        raise ValueError("新素材包只使用版本 3；版本 1/2 仅可读取或重渲染既有记录")
    # Validate the template before any package directory is created.
    render_prompts(plan)
    day = date_string or date.today().isoformat()
    date.fromisoformat(day)
    project = output.expanduser().resolve() / f"{day}-{clean_name(plan['title'])}"
    project.mkdir(parents=True, exist_ok=False)
    (project / "03-图片").mkdir()
    write(project / "image-plan.json", json.dumps(plan, ensure_ascii=False, indent=2))
    write_prompts(project, plan)
    content = content_parameters(plan)
    overview = [f"口播：{plan['speech']}", f"本组配色：{plan['palette']}"]
    overview.extend([
        f"核心场景：{content['scene']}", f"关键对象：{content['objects']}",
        f"动作关系：{content['action']}", f"最终结果：{content['result']}",
        "四张图片由模型分别设计完整提示词；只共用新闻画幅、半调纸拼贴风格和必要安全区规则。",
        "程序按编号保存每帧完整正文，不把其他图片的对象、坐标或结果复制进本图。",
    ])
    overview.append("内部方案已保存，继续同批生图，不要求用户确认。")
    write(project / "01-隐喻方案-待确认.txt", "\n".join(overview))
    write(project / "00-使用说明.txt", "内部先保存四张相互独立的完整生图提示词；四份正文全部通过一致性校验后同批生图。\n完成后从独立交付目录取四张图片和05-即梦视频提示词.txt。")
    write(project / "03-图片" / "README.txt", "按原请求索引保存01—04图片，保留实际格式与原始字节。")
    write(project / "05-即梦视频提示词.txt", video_prompt(
        plan["speech"], **content, duration=plan["duration_seconds"]
    ))
    write(project / "06-剪映使用说明.txt", f"画幅：9:16；建议时长：约 {plan['duration_seconds']:g} 秒。\n把即梦生成的视频放到对应口播下方；新闻标题放顶部，避免遮挡中部关键内容。")
    spec = {
        "speech": plan["speech"], "title": plan["title"], "duration_seconds": plan["duration_seconds"],
        "aspect_ratio": "9:16", "image_count": 4, "palette": plan["palette"],
        "style": "halftone-paper-collage", "top_title_safe_area": True,
        "status": "prompts-rendered", "template_version": plan["template_version"],
        "template_sha256": hashlib.sha256(TEMPLATES[plan["template_version"]].read_bytes()).hexdigest(),
    }
    write(project / "visual-spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
    load_prompts(project)
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description="创建逐图独立提示词的独立试用素材包")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date", help="YYYY-MM-DD")
    args = parser.parse_args()
    try:
        require_local_access()
        project = prepare(args.plan, args.output, args.date)
    except (OSError, ValueError, UnicodeError, PermissionError) as exc:
        parser.error(str(exc))
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
