"""Regression checks for the trial's deterministic image prompt pipeline."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from image_prompts import load_plan, render_prompts, write_prompts
from load_image_prompts import load_prompts
from make_package import video_prompt


CASES = ("ticket", "wechat", "starch", "delivery")


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


class ImageTemplateTests(unittest.TestCase):
    def fixture(self, name: str = "ticket") -> dict:
        return load_plan(FIXTURES / f"{name}.json")

    def save_plan(self, project: Path, plan: dict) -> None:
        (project / "image-plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def assert_invalid(self, plan: dict) -> None:
        with self.assertRaises(ValueError):
            render_prompts(plan)

    def test_four_cases_render_repeatedly_without_mutating_parameters(self):
        for name in CASES:
            with self.subTest(case=name):
                plan = self.fixture(name)
                before = deepcopy(plan)
                first = render_prompts(plan)
                self.assertEqual(first, render_prompts(plan))
                self.assertEqual(plan, before)
                self.assertEqual([item["number"] for item in first], [1, 2, 3, 4])
                self.assertEqual(len({item["name"] for item in first}), 4)
                for item in first:
                    self.assertTrue(item["name"].endswith(".txt"))
                    self.assertTrue(item["prompt"].endswith("\n"))
                    self.assertFalse(item["prompt"].endswith("\n\n"))

    def test_changing_one_frame_affects_only_its_prompt(self):
        plan = self.fixture()
        before = render_prompts(plan)
        plan["frames"][2]["composition"] = "票券更靠中央，手和入口均保持清楚，动作仍是从左向右推送"
        after = render_prompts(plan)
        changed = [a["number"] for a, b in zip(before, after) if a["prompt"] != b["prompt"]]
        self.assertEqual(changed, [3])

    def test_saved_prompts_round_trip_for_all_four_cases(self):
        for name in CASES:
            with self.subTest(case=name), TemporaryDirectory() as directory:
                project = Path(directory)
                plan = self.fixture(name)
                self.save_plan(project, plan)
                write_prompts(project, plan)
                expected = render_prompts(plan)
                actual = load_prompts(project)
                self.assertEqual([x["number"] for x in actual], [1, 2, 3, 4])
                self.assertEqual([x["prompt"] for x in actual], [x["prompt"] for x in expected])
                self.assertEqual(len(list((project / "02-四张图片提示词").glob("*.txt"))), 4)
                for item in actual:
                    self.assertEqual(Path(item["path"]).read_bytes(), item["prompt"].encode("utf-8"))

    def test_tampering_with_saved_prompt_blocks_loading(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            plan = self.fixture()
            self.save_plan(project, plan)
            write_prompts(project, plan)
            item = render_prompts(plan)[1]
            path = project / "02-四张图片提示词" / item["name"]
            path.write_text(item["prompt"] + "额外自由改写的导演指令\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_prompts(project)

    def test_editing_plan_requires_rerender_before_loading(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            plan = self.fixture()
            self.save_plan(project, plan)
            write_prompts(project, plan)
            plan["frames"][1]["subjects"].append("小尺寸奶油白纸片")
            self.save_plan(project, plan)
            with self.assertRaises(ValueError):
                load_prompts(project)
            write_prompts(project, plan)
            self.assertEqual(len(load_prompts(project)), 4)

    def test_missing_saved_prompt_blocks_loading(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            plan = self.fixture()
            self.save_plan(project, plan)
            write_prompts(project, plan)
            name = render_prompts(plan)[3]["name"]
            (project / "02-四张图片提示词" / name).unlink()
            with self.assertRaises(ValueError):
                load_prompts(project)

    def test_missing_required_parameters_are_rejected(self):
        for key in ("speech", "palette", "video", "frames"):
            with self.subTest(root_key=key):
                plan = self.fixture()
                del plan[key]
                self.assert_invalid(plan)
        for key in ("focus", "subjects", "environment", "relation", "composition", "labels", "constraints"):
            with self.subTest(frame_key=key):
                plan = self.fixture()
                del plan["frames"][0][key]
                self.assert_invalid(plan)
        plan = self.fixture()
        del plan["video"]["action"]
        self.assert_invalid(plan)

    def test_empty_required_content_is_rejected(self):
        for key in ("focus", "environment", "relation", "composition"):
            with self.subTest(key=key):
                plan = self.fixture()
                plan["frames"][0][key] = "   "
                self.assert_invalid(plan)
        plan = self.fixture()
        plan["frames"][0]["subjects"] = []
        self.assert_invalid(plan)

    def test_frame_count_duplicate_number_and_wrong_order_are_rejected(self):
        plan = self.fixture()
        plan["frames"].pop()
        self.assert_invalid(plan)
        plan = self.fixture()
        plan["frames"][1]["number"] = 1
        self.assert_invalid(plan)
        plan = self.fixture()
        plan["frames"][0], plan["frames"][1] = plan["frames"][1], plan["frames"][0]
        self.assert_invalid(plan)

    def test_remaining_placeholders_are_rejected(self):
        for placeholder in ("{{主体}}", "${scene}", "<主体>", "TODO", "待填写"):
            with self.subTest(placeholder=placeholder):
                plan = self.fixture()
                plan["frames"][0]["subjects"] = [placeholder]
                self.assert_invalid(plan)

    def test_empty_labels_do_not_force_readable_text_or_cards(self):
        plan = self.fixture("wechat")
        self.assertEqual(plan["frames"][1]["labels"], [])
        plan["frames"][1]["constraints"] = []
        prompt = render_prompts(plan)[1]["prompt"]
        self.assertIn("不出现任何可读文字或数字", prompt)
        self.assertNotIn("清楚写出", prompt)
        self.assertNotIn("微信钱包", prompt)

    def test_labels_remain_attached_to_their_specified_carriers(self):
        for name in CASES:
            with self.subTest(case=name):
                plan = self.fixture(name)
                for frame, item in zip(plan["frames"], render_prompts(plan)):
                    for label in frame["labels"]:
                        self.assertIn(f"在【{label['carrier']}】上清楚写出「{label['text']}」", item["prompt"])

    def test_new_image_template_keeps_legacy_video_body_unchanged(self):
        for name in CASES:
            with self.subTest(case=name):
                plan = self.fixture(name)
                result = video_prompt(
                    plan["speech"], **plan["video"], palette=plan["palette"],
                    duration=plan["duration_seconds"],
                )
                expected = (FIXTURES / "expected-video" / f"{name}.txt").read_text(encoding="utf-8")
                self.assertEqual(normalize_newlines(result), normalize_newlines(expected))

    def test_six_second_duration_changes_only_video_duration_text(self):
        plan = self.fixture()
        five = video_prompt(plan["speech"], **plan["video"], palette=plan["palette"], duration=5)
        six = video_prompt(plan["speech"], **plan["video"], palette=plan["palette"], duration=6)
        self.assertEqual(six, five.replace("约 5 秒", "约 6 秒", 1))

    def test_trial_video_matches_installed_original_function(self):
        original_path = ROOT.parent / "gbro-jimeng-collage-broll-audited" / "scripts" / "make_package.py"
        if not original_path.is_file():
            self.skipTest("Original installed skill is unavailable; portable golden-body test still applies")
        spec = importlib.util.spec_from_file_location("original_make_package_for_trial_test", original_path)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        for name in CASES:
            with self.subTest(case=name):
                plan = self.fixture(name)
                arguments = {
                    "speech": plan["speech"], **plan["video"], "palette": plan["palette"],
                    "duration": plan["duration_seconds"],
                }
                self.assertEqual(video_prompt(**arguments), original.video_prompt(**arguments))


if __name__ == "__main__":
    unittest.main()
