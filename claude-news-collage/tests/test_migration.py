"""Migration checks for claude-news-collage.

Proves that the Jimeng prompt chain is the original xy-to-make code, unchanged:
vendored files are byte-identical to the source commit, the delivered
05-即梦视频提示词.txt equals the original video_prompt() return value (plus the
original write() final LF), and nothing else in the Skill produces a video prompt.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_plan_rules import check as check_rules  # noqa: E402
from export_delivery import export_delivery  # noqa: E402
from image_prompts import content_parameters, load_plan  # noqa: E402
from make_package import video_prompt  # noqa: E402
from prepare_package import prepare  # noqa: E402

EXAMPLE = ROOT / "examples" / "票务平台退票" / "image-plan.json"
PLANS = [EXAMPLE, ROOT / "tests" / "fixtures" / "v3" / "starch.json"]
VENDORED = json.loads((ROOT / "VENDORED.json").read_text(encoding="utf-8"))
OWN_SCRIPTS = {"check_setup.py", "check_plan_rules.py", "make_preview.py", "run.py"}


def expected_text(plan: dict) -> str:
    """Original video_prompt() return value as written by the original write()."""
    text = video_prompt(plan["speech"], **content_parameters(plan), duration=plan["duration_seconds"])
    return text.rstrip() + "\n"


def expected_file_bytes(plan: dict) -> bytes:
    # The original write() uses Path.write_text in text mode, so the platform
    # line ending (CRLF on Windows) is part of the original behaviour.
    return expected_text(plan).replace("\n", os.linesep).encode("utf-8")


class VendoredCodeTests(unittest.TestCase):
    def test_vendored_files_are_byte_identical_to_source_commit(self):
        self.assertEqual(VENDORED["commit"], "52351a79796fe1b34ff46001210f2198ec61ab1b")
        for rel, digest in VENDORED["files"].items():
            with self.subTest(file=rel):
                self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest)

    def test_core_files_are_in_manifest(self):
        for rel in ["scripts/make_package.py", "scripts/image_prompts.py", "scripts/prepare_package.py",
                    "scripts/export_delivery.py", "scripts/load_image_prompts.py",
                    "scripts/render_image_prompts.py", "references/image-plan.md"]:
            self.assertIn(rel, VENDORED["files"])

    def test_no_other_script_builds_a_video_prompt(self):
        for path in (ROOT / "scripts").glob("*.py"):
            if path.name in OWN_SCRIPTS:
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("def video_prompt", source, path.name)
                self.assertNotRegex(source, r"import[^\n]*video_prompt", path.name)
            else:
                self.assertIn(f"scripts/{path.name}", VENDORED["files"], f"{path.name} 不在原项目清单中")


class EndToEndTests(unittest.TestCase):
    def run_pipeline(self, plan_path: Path, root: Path) -> tuple[Path, Path]:
        project = prepare(plan_path, root / "internal", "2026-10-09")
        for n, name in enumerate(["01-建立场景", "02-关键对象", "03-动作关系", "04-结果冲突"], 1):
            (project / "03-图片" / f"{name}.png").write_bytes(b"\x89PNG fake image " + bytes([n]))
        delivery = export_delivery(project)
        return project, delivery

    def test_delivered_prompt_equals_original_video_prompt(self):
        for plan_path in PLANS:
            with self.subTest(plan=plan_path.name), TemporaryDirectory() as tmp:
                plan = load_plan(plan_path)
                project, delivery = self.run_pipeline(plan_path, Path(tmp))
                expected = expected_file_bytes(plan)
                self.assertEqual((project / "05-即梦视频提示词.txt").read_bytes(), expected)
                self.assertEqual((delivery / "05-即梦视频提示词.txt").read_bytes(), expected)
                self.assertEqual(sorted(p.name for p in delivery.iterdir()), [
                    "01-建立场景.png", "02-关键对象.png", "03-动作关系.png", "04-结果冲突.png",
                    "05-即梦视频提示词.txt"])
                self.assertFalse(list(delivery.rglob("*.zip")))

    def test_example_prompt_text_snapshot(self):
        plan = load_plan(EXAMPLE)
        text = expected_text(plan)
        self.assertTrue(text.startswith("请使用我上传的 4 张参考图，严格按 1→2→3→4 的顺序，把它们做成一条约 6 秒的竖屏半调纸拼贴组装动画。\n\n对应口播：票务平台也不能再随便拿票品属于特殊商品当借口拒绝退票。\n"))
        self.assertIn("视觉隐喻：票务平台的纸片大楼和售票窗口，观众排队办理退票；关键对象：", text)
        self.assertTrue(text.endswith("不要 logo、水印、UI、字幕段落、对白和配乐。\n"))


class PlanRuleTests(unittest.TestCase):
    def test_example_follows_voiceover_order_and_labels(self):
        self.assertEqual(check_rules(json.loads(EXAMPLE.read_text(encoding="utf-8"))), [])

    def test_swapped_voiceover_order_is_reported(self):
        plan = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        a, b = plan["frames"][1]["prompt"], plan["frames"][2]["prompt"]
        plan["frames"][1]["prompt"], plan["frames"][2]["prompt"] = b, a
        self.assertTrue(any("顺序与口播不一致" in e for e in check_rules(plan)))

    def test_missing_label_is_reported(self):
        plan = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        plan["frames"][0]["prompt"] = plan["frames"][0]["prompt"].replace("“票务平台”", "the platform name")
        self.assertTrue(any("关键标签" in e for e in check_rules(plan)))

    def test_rule_check_never_changes_video_inputs(self):
        plan = load_plan(EXAMPLE)
        before = deepcopy(plan)
        check_rules(plan)
        self.assertEqual(plan, before)


if __name__ == "__main__":
    unittest.main()
