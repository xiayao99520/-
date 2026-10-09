"""Regression tests for the independent-prompt v3 trial workflow."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "v3"
sys.path.insert(0, str(ROOT / "scripts"))

from image_prompts import load_plan, render_prompts, write_prompts
from load_image_prompts import load_prompts
from make_package import video_prompt
from prepare_package import prepare


ROLES = ("建立场景", "关键对象", "动作关系", "结果冲突")


def lf(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


class LegacyImageV3Tests(unittest.TestCase):
    def fixture(self) -> dict:
        return load_plan(FIXTURES / "starch.json")

    def golden(self) -> list[str]:
        data = json.loads((FIXTURES / "golden_old_thread_01a11588.json").read_text(encoding="utf-8"))
        self.assertEqual(data["source_thread"], "01a11588-eadf-7280-abf1-3f0989ad7d35")
        self.assertEqual(data["prompt_count"], 4)
        return data["prompts"]

    def save_plan(self, project: Path, plan: dict) -> None:
        (project / "image-plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

    def test_old_thread_replay_is_exact_for_all_four_prompts(self):
        actual = [item["prompt"] for item in render_prompts(self.fixture())]
        expected = self.golden()
        self.assertEqual([lf(value) for value in actual], [lf(value) for value in expected])

    def test_v3_keeps_each_prompt_independent_and_repeated(self):
        plan = self.fixture()
        first = render_prompts(plan)
        self.assertEqual(first, render_prompts(plan))
        self.assertEqual([item["number"] for item in first], [1, 2, 3, 4])
        self.assertEqual([frame["role"] for frame in plan["frames"]], list(ROLES))
        self.assertEqual(len({item["prompt"] for item in first}), 4)

        changed = deepcopy(plan)
        changed["frames"][2]["prompt"] += " Additional independent frame detail."
        after = render_prompts(changed)
        self.assertEqual([i for i, (a, b) in enumerate(zip(first, after), 1) if a["prompt"] != b["prompt"]], [3])

    def test_v3_rejects_duplicate_or_shared_layout_prompt(self):
        plan = self.fixture()
        plan["frames"][1]["prompt"] = plan["frames"][0]["prompt"]
        with self.assertRaises(ValueError):
            render_prompts(plan)
        plan = self.fixture()
        plan["frames"][0]["prompt"] += " Keep the same board and no major relocation."
        with self.assertRaises(ValueError):
            render_prompts(plan)

    def test_saved_prompt_tampering_blocks_loader(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            plan = self.fixture()
            self.save_plan(project, plan)
            write_prompts(project, plan)
            path = project / "02-四张图片提示词" / "02-关键对象.txt"
            path.write_text(path.read_text(encoding="utf-8").replace("plain cream", "edited cream", 1), encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError):
                load_prompts(project)

    def test_prepare_writes_v3_package_and_keeps_video_function(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            input_path.write_text(json.dumps(self.fixture(), ensure_ascii=False), encoding="utf-8")
            project = prepare(input_path, root / "internal", "2026-10-07")
            saved = load_plan(project / "image-plan.json")
            self.assertEqual((saved["schema_version"], saved["template_version"]), (3, "3"))
            self.assertEqual([item["prompt"] for item in load_prompts(project)],
                             [item["prompt"] for item in render_prompts(saved)])
            expected_video = video_prompt(
                saved["speech"], scene=saved["scene"], objects=saved["objects"],
                action=saved["action"], result=saved["result"], palette=saved["palette"],
                duration=saved["duration_seconds"],
            ) + "\n"
            self.assertEqual(lf((project / "05-即梦视频提示词.txt").read_text(encoding="utf-8")), lf(expected_video))
            self.assertIn("template_version", json.loads((project / "visual-spec.json").read_text(encoding="utf-8")))

    def test_v3_requires_old_style_markers(self):
        plan = self.fixture()
        plan["frames"][0]["prompt"] = "独立中文提示词"
        with self.assertRaises(ValueError):
            render_prompts(plan)


if __name__ == "__main__":
    unittest.main()
