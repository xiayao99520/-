#!/usr/bin/env python3
"""Design-time check of a schema-3 image plan for this Skill's extra rules.

It only READS the plan. It never changes image-plan.json, the four prompts,
or anything used by video_prompt(); the original validators in
image_prompts.py still decide whether a plan is valid.

Extra rules checked:
1. Voiceover order: every frames[n].prompt names the voiceover words it
   illustrates as  voiceover words 「…」 ; the four pieces are verbatim
   parts of `speech` (punctuation ignored) and appear in spoken order.
2. Key label: every frames[n].prompt asks for at least one Simplified
   Chinese label written in “…” quotes.

Usage:
  python check_plan_rules.py --plan <image-plan.json>
Exit 0 = ok, 1 = rule violated (fix the plan before prepare_package.py).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SEGMENT = re.compile(r"voiceover words\s*「([^」]+)」", re.IGNORECASE)
LABEL = re.compile(r"“([^”]*[一-鿿][^”]*)”")


def compact(text: str) -> str:
    return "".join(re.findall(r"[一-鿿0-9A-Za-z%.]", text))


def check(plan: dict) -> list[str]:
    errors = []
    speech = compact(plan.get("speech", ""))
    cursor = 0
    covered = 0
    for frame in plan.get("frames", []):
        n = frame.get("number")
        prompt = frame.get("prompt", "")
        found = SEGMENT.findall(prompt)
        if len(found) != 1:
            errors.append(f"第 {n} 张：需要且只需要一处 voiceover words 「…」 指明本图对应的口播原文")
        else:
            seg = compact(found[0])
            pos = speech.find(seg, cursor) if seg else -1
            if pos == -1:
                where = "不是口播原文" if seg not in speech else "顺序与口播不一致"
                errors.append(f"第 {n} 张：「{found[0]}」{where}")
            else:
                cursor = pos + len(seg)
                covered += len(seg)
        if not LABEL.search(prompt):
            errors.append(f"第 {n} 张：至少需要一个用 “…” 写明的简体中文关键标签")
    if speech and covered and covered < len(speech) * 0.8:
        errors.append(f"四段口播只覆盖了 {covered}/{len(speech)} 字，四段连起来应覆盖整段口播")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True, type=Path)
    args = ap.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    errors = check(plan)
    for e in errors:
        print(f"FAIL  {e}")
    if not errors:
        print("PASS  四张图按口播顺序对应，且每张都有中文关键标签")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
