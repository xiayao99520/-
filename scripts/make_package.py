#!/usr/bin/env python3
"""Create a Jimeng-ready collage B-roll package from a prepared visual plan."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
from datetime import date


STYLE = (
    "高级 editorial 半调纸拼贴，黑白 halftone 摄影剪贴，彩色卡纸点缀，"
    "清晰裁切边，暖奶油色描边，细腻纸张颗粒，低透明度柔和纸张阴影，"
    "二维定格动画质感，非写实 3D。"
)
COMMON = (
    "竖屏 9:16，画面整体铺满，不要四周大面积空白；主要主体和关键关系位于画面中部核心区域。"
    "顶部是新闻标题安全区，可以有背景、纸张和不重要的装饰，但不要把唯一的关键对象、关键文字或冲突结果放在顶部。"
    "只使用中文必要标签，文字清晰可读。不要英文乱码、无关文字、logo、水印、UI、字幕段落。"
)


def clean_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\r\n]+", " ", value).strip()
    value = re.sub(r"\s+", " ", value)
    return (value or "未命名项目")[:48]


def write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def image_prompt(role: str, scene: str, objects: str, action: str, result: str, palette: str) -> str:
    role_lines = {
        "建立场景": f"这是第 1 张参考图，建立场景：{scene}。画面重点是让观众一眼看懂场景代表什么。",
        "关键对象": f"这是第 2 张参考图，突出关键对象：{objects}。对象要大而清楚，放在画面中部。",
        "动作关系": f"这是第 3 张参考图，表现动作关系：{action}。明确对象和场景之间正在发生什么。",
        "结果冲突": f"这是第 4 张参考图，表现最终结果和冲突：{result}。让结果在画面中部清楚可见。",
    }
    return (
        f"请生成一张用于即梦图生视频参考的成品静帧。{role_lines[role]}\n"
        f"场景与语义：{scene}；关键对象：{objects}；动作：{action}；结果：{result}。\n"
        f"色彩：{palette}。风格：{STYLE}\n{COMMON}\n"
        "构图要有层次，边缘可以出现次要纸片和装饰来铺满画面，但不要抢走中部主体。"
        "不要把画面做成四格分镜，不要把提示词写进画面。"
    )


def video_prompt(speech: str, scene: str, objects: str, action: str, result: str, palette: str, duration: float = 5) -> str:
    return (
        f"请使用我上传的 4 张参考图，严格按 1→2→3→4 的顺序，把它们做成一条约 {duration:g} 秒的竖屏半调纸拼贴组装动画。\n\n"
        f"对应口播：{speech}\n"
        f"视觉隐喻：{scene}；关键对象：{objects}；动作关系：{action}；最终结果：{result}。\n\n"
        "动画顺序：先以第 1 张图的场景为基础，从平坦纸面开始；再让第 2 张图中的关键对象从画外滑入并卡位；"
        "随后按照第 3 张图的关系让对象进入、连接、塞入、推动或挤压场景；最后完成第 4 张图的冲突结果，"
        "例如出现纸质叉号、封条、阻挡或拒绝动作，并在最后停留片刻。动作要有清晰的逐件组装感，"
        "不要整张图淡入，不要慢速缩放。\n\n"
        f"视觉保持：{STYLE} 色彩使用{palette}。保持 9:16 竖屏，画面整体铺满，主要动作集中在中部核心区域；"
        "顶部新闻标题安全区可以有次要装饰，但不能放唯一关键文字或结果。\n"
        "限制：固定视角，二维纸片定格动画，元素从画外进入并精准卡位；不要切镜，不要 3D 化，不要写实环境，"
        "不要新增人物或物件，不要改变四张参考图中的中文标签，不要英文乱码，不要 logo、水印、UI、字幕段落、对白和配乐。"
    )


def make(args: argparse.Namespace) -> Path:
    root = Path(args.output).expanduser().resolve()
    project = root / f"{args.date or date.today().isoformat()}-{clean_name(args.title or args.speech[:20])}"
    if args.video_only:
        if not project.is_dir():
            raise FileNotFoundError(f"Existing package directory required: {project}")
        write(project / "05-即梦视频提示词.txt", video_prompt(args.speech, args.scene, args.objects, args.action, args.result, args.palette, args.duration))
        return project

    prompts = project / "02-四张图片提示词"
    images = project / "03-图片"
    prompts.mkdir(parents=True, exist_ok=False)
    images.mkdir()

    roles = [("01-建立场景", "建立场景"), ("02-关键对象", "关键对象"),
             ("03-动作关系", "动作关系"), ("04-结果冲突", "结果冲突")]
    for filename, role in roles:
        write(prompts / f"{filename}.txt", image_prompt(role, args.scene, args.objects, args.action, args.result, args.palette))
    write(images / "README.txt", "Codex 生图会把四张最终 PNG/JPG 保存到这里；生成完成后按 01、02、03、04 编号，再拖入即梦参考图区域。")

    write(project / "00-使用说明.txt", "\n".join([
        "1. 内部方案写入 01-隐喻方案-待确认.txt；随后先写完四份实际生图提示词，再同批生成四张图。历史文件名中的“待确认”不要求用户回复确认。",
        "2. 四张 Codex 图片按 1→2→3→4 保存到内部 03-图片；最终从独立交付目录取图，无需逐张目视验图。",
        f"3. 从独立交付目录复制 05-即梦视频提示词.txt 到即梦，生成约 {args.duration:g} 秒、9:16 的组装动画。",
        "4. 把视频放到剪映对应口播下方；顶部标题可覆盖安全区，关键对象和结果已安排在中部。",
    ]))
    write(project / "01-隐喻方案-待确认.txt", "\n".join([
        f"口播：{args.speech}", f"核心场景：{args.scene}", f"关键对象：{args.objects}",
        f"动作关系：{args.action}", f"结果冲突：{args.result}", f"色彩建议：{args.palette}",
        "组装顺序：建立场景 → 关键对象 → 动作关系 → 结果冲突。",
        "内部方案记录完成后，直接写完四张图片提示词并进入生图，不等待用户确认。",
    ]))
    write(project / "05-即梦视频提示词.txt", video_prompt(args.speech, args.scene, args.objects, args.action, args.result, args.palette, args.duration))
    write(project / "06-剪映使用说明.txt", "\n".join([
        f"画幅：9:16；建议时长：约 {args.duration:g} 秒；用途：垫在对应口播下方。",
        "把即梦生成的视频放在这句口播对应的时间线上。视频默认不承担旁白和字幕。",
        "新闻标题可以覆盖画面顶部安全区；不要遮挡画面中部的关键对象、动作和结果。",
    ]))
    spec = {
        "speech": args.speech, "title": args.title or clean_name(args.speech[:20]),
        "aspect_ratio": "9:16", "duration_seconds": args.duration, "language": "zh-CN",
        "style": "halftone-paper-collage", "top_title_safe_area": True,
        "composition": "full_frame_with_center_core", "image_count": 4,
        "roles": [r for _, r in roles], "palette": args.palette,
        "status": "plan-created",
    }
    (project / "visual-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return project


def require_local_access() -> None:
    from access_control import ControlError, is_enabled

    try:
        enabled = is_enabled()
    except ControlError as exc:
        raise PermissionError(str(exc)) from exc
    if not enabled:
        raise PermissionError("本地控制已停用，未建立素材包")


def main() -> int:
    p = argparse.ArgumentParser(description="Create a Jimeng-ready collage B-roll package")
    p.add_argument("--speech", required=True, help="one Chinese voiceover line")
    p.add_argument("--title", help="project title")
    p.add_argument("--scene", required=True, help="establishing scene")
    p.add_argument("--objects", required=True, help="key objects")
    p.add_argument("--action", required=True, help="action relationship")
    p.add_argument("--result", required=True, help="conflict/result")
    p.add_argument("--palette", default="根据语义选择一组强烈平面色场，搭配奶油白、黑白和一到两种彩色纸片")
    p.add_argument("--output", default="~/hyperframes-projects/collage-broll")
    p.add_argument("--date", help="override date, YYYY-MM-DD")
    p.add_argument("--duration", type=float, default=5, help="video duration in seconds (default: 5)")
    p.add_argument("--video-only", action="store_true", help="update only the video prompt in an existing package")
    args = p.parse_args()
    if not math.isfinite(args.duration) or args.duration <= 0:
        p.error("--duration must be a positive finite number")
    try:
        require_local_access()
        project = make(args)
    except (FileNotFoundError, PermissionError) as exc:
        p.error(str(exc))
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
