"""Version 2 must reproduce the shared historical five-line image prompts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
V2 = FIXTURES / "v2"
sys.path.insert(0, str(ROOT / "scripts"))

from image_prompts import load_plan, render_prompts, validate_plan, write_prompts
from load_image_prompts import load_prompts
from make_package import image_prompt, video_prompt
from prepare_package import prepare


CASES = ("ticket", "wechat", "starch", "delivery")
ROLES = ("建立场景", "关键对象", "动作关系", "结果冲突")
PARAMETERS = ("scene", "objects", "action", "result", "palette")
V2_KEYS = {
    "schema_version", "template_version", "speech", "title", "duration_seconds",
    *PARAMETERS,
}


def lf(value: str) -> str:
    """Only normalize Windows and Unix line endings; preserve all other text."""
    return value.replace("\r\n", "\n")


class LegacyImageV2Tests(unittest.TestCase):
    def fixture(self, case: str = "ticket") -> dict:
        return load_plan(V2 / f"{case}.json")

    def save_plan(self, project: Path, plan: dict) -> None:
        (project / "image-plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            newline="\n",
        )

    def assert_invalid(self, plan: dict) -> None:
        with self.assertRaises(ValueError):
            render_prompts(plan)

    def video(self, plan: dict, duration: float | None = None) -> str:
        return video_prompt(
            plan["speech"], **{key: plan[key] for key in PARAMETERS},
            duration=plan["duration_seconds"] if duration is None else duration,
        )

    def test_fifteen_ordinary_and_wechat_common_prompt_goldens_match(self):
        compared = 0
        for case in CASES:
            for item in render_prompts(self.fixture(case)):
                with self.subTest(case=case, number=item["number"]):
                    path = V2 / "expected-images" / case / item["name"]
                    expected = path.read_bytes().decode("utf-8")
                    self.assertEqual(lf(item["prompt"]), lf(expected))
                    compared += 1
        self.assertEqual(compared, 16)

    def test_wechat_currency_appendix_is_evidence_not_shared_template(self):
        prompt = render_prompts(self.fixture("wechat"))[2]["prompt"]
        original = (V2 / "historical-exceptions" /
                    "wechat-03-original-with-currency-restriction.txt").read_text(encoding="utf-8")
        self.assertTrue(lf(original).startswith(prompt))
        self.assertIn("货币表现限制：", original)
        self.assertNotIn("货币表现限制", prompt)
        self.assertNotIn("真实人民币", prompt)

    def test_renderer_calls_the_original_role_function_and_keeps_five_lines(self):
        plan = self.fixture()
        original = deepcopy(plan)
        items = render_prompts(plan)
        self.assertEqual(plan, original)
        self.assertEqual([item["number"] for item in items], [1, 2, 3, 4])
        self.assertEqual(len({item["name"] for item in items}), 4)
        for index, (role, item) in enumerate(zip(ROLES, items), 1):
            with self.subTest(number=index):
                expected = image_prompt(role, **{key: plan[key] for key in PARAMETERS}) + "\n"
                self.assertEqual(item["prompt"], expected)
                self.assertEqual(item["name"], f"{index:02d}-{role}.txt")
                self.assertTrue(item["prompt"].startswith(
                    f"请生成一张用于即梦图生视频参考的成品静帧。这是第 {index} 张参考图，"
                ))
                self.assertEqual(len(item["prompt"].splitlines()), 5)
                self.assertNotIn("\n\n", item["prompt"])
                self.assertTrue(item["prompt"].endswith("\n"))
                self.assertFalse(item["prompt"].endswith("\n\n"))

    def test_repeated_rendering_is_identical(self):
        for case in CASES:
            with self.subTest(case=case):
                plan = self.fixture(case)
                self.assertEqual(render_prompts(plan), render_prompts(plan))

    def test_changing_shared_parameter_changes_only_its_slot(self):
        for key in PARAMETERS:
            with self.subTest(parameter=key):
                plan = self.fixture()
                before = render_prompts(plan)
                previous = plan[key]
                plan[key] = previous + "；参数回归测试改动"
                after = render_prompts(plan)
                for index, (old, new) in enumerate(zip(before, after)):
                    self.assertEqual(new["prompt"], old["prompt"].replace(previous, plan[key]))
                    old_lines, new_lines = old["prompt"].splitlines(), new["prompt"].splitlines()
                    changed_lines = {i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b}
                    expected_lines = {2} if key == "palette" else {1}
                    if key in PARAMETERS[:4] and index == PARAMETERS.index(key):
                        expected_lines.add(0)
                    self.assertEqual(changed_lines, expected_lines)

    def test_version_tags_default_to_two_when_both_are_omitted(self):
        plan = self.fixture()
        del plan["schema_version"]
        del plan["template_version"]
        with TemporaryDirectory() as directory:
            project = Path(directory)
            self.save_plan(project, plan)
            result = load_plan(project / "image-plan.json")
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["template_version"], "2")
        self.assertEqual(set(result), V2_KEYS)
        self.assertEqual(render_prompts(plan), render_prompts(result))
        self.assertEqual(validate_plan(plan)["schema_version"], 2)

    def test_missing_empty_unknown_and_per_image_fields_are_rejected(self):
        for key in ("speech", "title", "duration_seconds", *PARAMETERS):
            with self.subTest(missing=key):
                plan = self.fixture()
                del plan[key]
                self.assert_invalid(plan)
        for key in ("speech", "title", *PARAMETERS):
            with self.subTest(empty=key):
                plan = self.fixture()
                plan[key] = "   "
                self.assert_invalid(plan)
        for key, value in (("frames", []), ("video", {}), ("composition", "新增构图"),
                           ("constraints", ["新增限制"])):
            with self.subTest(unknown=key):
                plan = self.fixture()
                plan[key] = value
                self.assert_invalid(plan)

    def test_shared_parameters_cannot_inject_newlines_or_placeholders(self):
        for key in PARAMETERS:
            for suffix in ("\n新增段落", "\r新增段落", "\r\n新增段落", "\u2028新增段落",
                           "\u2029新增段落", "\u0085新增段落", "\v新增段落", "\f新增段落",
                           "\x1c新增段落", "\x1d新增段落", "\x1e新增段落", " {{待填}}", " ${scene}"):
                with self.subTest(parameter=key, suffix=repr(suffix)):
                    plan = self.fixture()
                    plan[key] += suffix
                    self.assert_invalid(plan)

    def test_version_mismatch_and_invalid_duration_are_rejected(self):
        for schema, template in ((2, "1"), (1, "2"), (True, "2"), (2, 2), (3, "3")):
            with self.subTest(schema=schema, template=template):
                plan = self.fixture()
                plan["schema_version"], plan["template_version"] = schema, template
                self.assert_invalid(plan)
        for duration in (0, -1, True, "5", float("inf"), float("nan")):
            with self.subTest(duration=duration):
                plan = self.fixture()
                plan["duration_seconds"] = duration
                self.assert_invalid(plan)

    def test_saved_prompts_round_trip_and_tampering_blocks_loading(self):
        for case in CASES:
            with self.subTest(case=case), TemporaryDirectory() as directory:
                project = Path(directory)
                plan = self.fixture(case)
                self.save_plan(project, plan)
                write_prompts(project, plan)
                expected = render_prompts(plan)
                loaded = load_prompts(project)
                self.assertEqual([x["number"] for x in loaded], [1, 2, 3, 4])
                self.assertEqual([x["prompt"] for x in loaded], [x["prompt"] for x in expected])
                path = Path(loaded[1]["path"])
                path.write_text(loaded[1]["prompt"].replace("成品静帧", "自行修改静帧", 1),
                                encoding="utf-8", newline="\n")
                with self.assertRaises(ValueError):
                    load_prompts(project)

    def test_missing_prompt_or_changed_parameters_block_loading(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            plan = self.fixture()
            self.save_plan(project, plan)
            write_prompts(project, plan)
            expected = render_prompts(plan)
            missing = project / "02-四张图片提示词" / expected[3]["name"]
            missing.unlink()
            with self.assertRaises(ValueError):
                load_prompts(project)
            write_prompts(project, plan)
            plan["scene"] += "；调整场景"
            self.save_plan(project, plan)
            with self.assertRaises(ValueError):
                load_prompts(project)
            write_prompts(project, plan)
            self.assertEqual(len(load_prompts(project)), 4)

    def test_prepare_rejects_v2_for_new_packages(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.fixture()
            input_path = root / "input.json"
            input_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            before_input = input_path.read_bytes()
            with self.assertRaises(ValueError):
                prepare(input_path, root / "internal", "2026-10-07")
            self.assertEqual(input_path.read_bytes(), before_input)
            self.assertFalse((root / "internal").exists())

    def test_video_function_still_matches_historical_six_parameter_output(self):
        for case in CASES:
            with self.subTest(case=case):
                plan = self.fixture(case)
                expected = (V2 / "expected-video" / f"{case}.txt").read_bytes().decode("utf-8")
                self.assertEqual(lf(self.video(plan) + "\n"), lf(expected))
                self.assertEqual(self.video(plan, 6), self.video(plan, 5).replace("约 5 秒", "约 6 秒", 1))

    def test_version_one_remains_readable_and_render_hashes_are_unchanged(self):
        expected = json.loads((V2 / "v1-render-sha256.json").read_text(encoding="utf-8"))
        for case in CASES:
            with self.subTest(case=case):
                path = FIXTURES / f"{case}.json"
                before = path.read_bytes()
                plan = load_plan(path)
                self.assertEqual((plan["schema_version"], plan["template_version"]), (1, "1"))
                self.assertIn("frames", plan)
                actual = {x["name"]: hashlib.sha256(x["prompt"].encode("utf-8")).hexdigest()
                          for x in render_prompts(plan)}
                self.assertEqual(actual, expected[case])
                self.assertEqual(path.read_bytes(), before)
                with TemporaryDirectory() as directory:
                    # Simulate a pre-existing v1 record; reading and rerendering it
                    # must preserve its version and the prior prompt bytes.
                    project = Path(directory)
                    self.save_plan(project, plan)
                    write_prompts(project, plan)
                    saved_before = (project / "image-plan.json").read_bytes()
                    saved = load_plan(project / "image-plan.json")
                    self.assertEqual((saved["schema_version"], saved["template_version"]), (1, "1"))
                    loaded = load_prompts(project)
                    hashes = {Path(item["path"]).name: hashlib.sha256(item["prompt"].encode("utf-8")).hexdigest()
                              for item in loaded}
                    self.assertEqual(hashes, expected[case])
                    write_prompts(project, saved)
                    self.assertEqual((project / "image-plan.json").read_bytes(), saved_before)
                    self.assertEqual([x["prompt"] for x in load_prompts(project)],
                                     [x["prompt"] for x in loaded])

    def test_prepare_rejects_new_version_one_package_before_creating_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "new-internal"
            before = (FIXTURES / "ticket.json").read_bytes()
            with self.assertRaises(ValueError):
                prepare(FIXTURES / "ticket.json", output, "2026-10-07")
            self.assertFalse(output.exists())
            self.assertEqual((FIXTURES / "ticket.json").read_bytes(), before)

    def test_optional_original_source_files_match_recorded_read_only_hashes(self):
        manifest = json.loads((V2 / "legacy-source-manifest.json").read_text(encoding="utf-8"))
        if not all(Path(value["source_directory"]).is_dir() for value in manifest.values()):
            self.skipTest("Historical source packages are not installed; portable copied goldens still apply")
        for case, value in manifest.items():
            for name, expected in value["files"].items():
                with self.subTest(case=case, file=name):
                    path = Path(value["source_directory"]) / name
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
