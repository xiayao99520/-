#!/usr/bin/env python3
"""Validate versioned image plans and render the exact prompts they contain."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from string import Template
from typing import Any

from make_package import image_prompt


NAMES = (
    "01-建立场景.txt", "02-关键对象.txt", "03-动作关系.txt", "04-结果冲突.txt"
)
ROLES = ("建立场景", "关键对象", "动作关系", "结果冲突")

# Version 1 and 2 remain readable. New plans use v3, where every image keeps
# its own complete prompt instead of receiving the same five content fields.
DEFAULT_SCHEMA_VERSION = 3
DEFAULT_TEMPLATE_VERSION = "3"
TEMPLATES = {
    "1": Path(__file__).resolve().parents[1] / "templates" / "image-v1.txt",
    "2": Path(__file__).resolve().with_name("make_package.py"),
    "3": Path(__file__).resolve().parents[1] / "templates" / "image-v3.txt",
}
ROOT_KEYS_V1 = {
    "schema_version", "template_version", "speech", "title", "duration_seconds",
    "palette", "video", "frames",
}
CONTENT_KEYS = ("scene", "objects", "action", "result", "palette")
ROOT_KEYS_V2 = {
    "schema_version", "template_version", "speech", "title", "duration_seconds",
    *CONTENT_KEYS,
}
ROOT_KEYS_V3 = {
    "schema_version", "template_version", "speech", "title", "duration_seconds",
    *CONTENT_KEYS, "frames",
}
FRAME_KEYS_V1 = {
    "number", "focus", "subjects", "environment", "relation", "composition",
    "labels", "constraints",
}
FRAME_KEYS_V3 = {"number", "role", "prompt"}
PLACEHOLDER = re.compile(
    r"\b(?:TODO|TBD)\b|待填写|待填入|待补充|占位符|<[^<>\n]+>|"
    r"\{\{[^\n]+?\}\}|\$\{[^\n]+?\}", re.IGNORECASE
)
V3_STYLE_MARKERS = (
    "use case:", "9:16", "premium editorial halftone paper collage",
    "middle core", "news headline", "no english", "no logo", "no watermark",
    "no ui", "no subtitles", "no 3d",
)
V3_LOCKED_LAYOUT = (
    "same board", "fixed composition for all four", "no major relocation",
    "same composition for all four",
)


def _keys(value: Any, expected: set[str], location: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        actual = set(value) if isinstance(value, dict) else set()
        raise ValueError(
            f"{location} 字段不匹配；缺少 {sorted(expected - actual)}；"
            f"多出 {sorted(actual - expected)}"
        )
    return value


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} 必须是非空文字")
    if PLACEHOLDER.search(value):
        raise ValueError(f"{location} 残留占位符，请先填写实际内容")
    if "\x00" in value:
        raise ValueError(f"{location} 不能包含 NUL 字符")
    return value


def _texts(value: Any, location: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{location} 必须是文字列表")
    for i, item in enumerate(value):
        _text(item, f"{location}[{i}]")
    return value


def _infer_schema(plan: dict) -> int:
    """Infer only untagged historical shapes; tagged plans are authoritative."""
    if "schema_version" in plan:
        return plan["schema_version"]
    if "video" in plan and "frames" in plan:
        return 1
    if "frames" in plan and all(key in plan for key in ("scene", "objects", "action", "result")):
        return 3
    return 2


def _validate_v1(plan: dict) -> None:
    _keys(plan["video"], {"scene", "objects", "action", "result"}, "video")
    for key, value in plan["video"].items():
        _text(value, f"video.{key}")
    frames = plan["frames"]
    if not isinstance(frames, list) or len(frames) != 4:
        raise ValueError("frames 必须恰好包含四张图片参数")
    for index, frame in enumerate(frames, 1):
        location = f"frames[{index}]"
        _keys(frame, FRAME_KEYS_V1, location)
        if type(frame["number"]) is not int or frame["number"] != index:
            raise ValueError("图片编号必须依次为 1、2、3、4，不能重复或错序")
        for key in ["focus", "environment", "relation", "composition"]:
            _text(frame[key], f"{location}.{key}")
        _texts(frame["subjects"], f"{location}.subjects")
        _texts(frame["constraints"], f"{location}.constraints", allow_empty=True)
        if not isinstance(frame["labels"], list):
            raise ValueError(f"{location}.labels 必须是列表，可以为空")
        for label in frame["labels"]:
            _keys(label, {"carrier", "text"}, f"{location}.label")
            _text(label["carrier"], f"{location}.label.carrier")
            _text(label["text"], f"{location}.label.text")


def _validate_v3(plan: dict) -> None:
    for key in CONTENT_KEYS:
        _text(plan[key], key)
    frames = plan["frames"]
    if not isinstance(frames, list) or len(frames) != 4:
        raise ValueError("v3 frames 必须恰好包含四张完整图片提示词")
    prompts: list[str] = []
    for index, frame in enumerate(frames, 1):
        location = f"frames[{index}]"
        _keys(frame, FRAME_KEYS_V3, location)
        if type(frame["number"]) is not int or frame["number"] != index:
            raise ValueError("v3 图片编号必须依次为 1、2、3、4，不能重复或错序")
        if frame["role"] != ROLES[index - 1]:
            raise ValueError(f"{location}.role 必须对应 {ROLES[index - 1]}")
        prompt = _text(frame["prompt"], f"{location}.prompt").strip()
        lowered = prompt.lower()
        missing = [marker for marker in V3_STYLE_MARKERS if marker not in lowered]
        if missing:
            raise ValueError(f"{location}.prompt 缺少旧流程固定风格/安全区/负面标记：{missing}")
        locked = [phrase for phrase in V3_LOCKED_LAYOUT if phrase in lowered]
        if locked:
            raise ValueError(f"{location}.prompt 含跨图锁死构图指令：{locked}")
        prompts.append(prompt)
    if len(set(prompts)) != 4:
        raise ValueError("v3 四张图片提示词必须各自独立，不能重复同一正文")


def validate_plan(plan: Any) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("image-plan 必须是参数对象")
    plan = dict(plan)
    schema = _infer_schema(plan)
    if type(schema) is not int or schema not in (1, 2, 3):
        raise ValueError("schema_version 必须为整数 1、2 或 3")
    plan.setdefault("schema_version", schema)
    plan.setdefault("template_version", str(schema))
    expected = {1: ROOT_KEYS_V1, 2: ROOT_KEYS_V2, 3: ROOT_KEYS_V3}[schema]
    _keys(plan, expected, "image-plan")
    if plan["template_version"] != str(schema):
        raise ValueError("schema_version 和 template_version 必须对应，不能自动转换旧数据")
    for key in ["speech", "title"]:
        _text(plan[key], key)
    duration = plan["duration_seconds"]
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration_seconds 必须是有限正数")
    if schema == 1:
        _text(plan["palette"], "palette")
        _validate_v1(plan)
    elif schema == 2:
        for key in CONTENT_KEYS:
            _text(plan[key], key)
            if plan[key].splitlines() != [plan[key]]:
                raise ValueError(f"{key} 只能填写单行内容，不能插入新增段落")
    else:
        _validate_v3(plan)
    return plan


def load_plan(path: Path) -> dict:
    return validate_plan(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def content_parameters(plan: dict) -> dict[str, str]:
    """Return the five video content inputs without changing video_prompt()."""
    plan = validate_plan(plan)
    if plan["schema_version"] == 1:
        return {**plan["video"], "palette": plan["palette"]}
    return {key: plan[key] for key in CONTENT_KEYS}


def _render_v1(plan: dict) -> list[dict]:
    template = Template(TEMPLATES["1"].read_text(encoding="utf-8"))
    items = []
    for frame, name in zip(plan["frames"], NAMES):
        if frame["labels"]:
            labels = "；".join(
                f"在【{item['carrier']}】上清楚写出「{item['text']}」" for item in frame["labels"]
            ) + "。本图仅允许以上文字与数字，不另加标签、日期或段落。"
        else:
            labels = "本图不出现任何可读文字或数字，不加标签卡片或字幕。"
        values = {
            "focus": frame["focus"], "subjects": "；".join(frame["subjects"]),
            "environment": frame["environment"], "relation": frame["relation"],
            "composition": frame["composition"], "palette": plan["palette"],
            "labels": labels,
            "constraints": "；".join(frame["constraints"]) if frame["constraints"] else "无需额外内容限制。",
        }
        prompt = template.substitute(values).rstrip() + "\n"
        if PLACEHOLDER.search(prompt):
            raise ValueError("渲染结果残留占位符")
        items.append({"number": frame["number"], "name": name, "prompt": prompt})
    return items


def render_prompts(plan: dict) -> list[dict]:
    plan = validate_plan(plan)
    schema = plan["schema_version"]
    if schema == 3:
        # v3 deliberately preserves each complete prompt verbatim. The model
        # designs each frame independently; the program only adds one final LF.
        return [
            {"number": frame["number"], "name": name,
             "prompt": frame["prompt"].rstrip() + "\n"}
            for frame, name in zip(plan["frames"], NAMES)
        ]
    if schema == 2:
        content = content_parameters(plan)
        return [
            {"number": number, "name": name,
             "prompt": image_prompt(role, **content).rstrip() + "\n"}
            for number, (role, name) in enumerate(zip(ROLES, NAMES), 1)
        ]
    return _render_v1(plan)


def write_prompts(project: Path, plan: dict) -> None:
    """Render all four prompts before writing any prompt file."""
    items = render_prompts(plan)
    directory = Path(project) / "02-四张图片提示词"
    directory.mkdir(parents=True, exist_ok=True)
    for item in items:
        (directory / item["name"]).write_text(item["prompt"], encoding="utf-8", newline="\n")
