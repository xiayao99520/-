"""run.py fast path: same bytes as the original pipeline, fewer steps, early errors."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from image_prompts import load_plan  # noqa: E402
from run import finish, plan_errors, start  # noqa: E402
from test_migration import EXAMPLE, expected_file_bytes  # noqa: E402


def fake_images(folder: Path, ext: str = ".png") -> list[Path]:
    paths = []
    for n in range(1, 5):
        p = folder / f"imagegen_{n}{ext}"
        p.write_bytes(b"\x89PNG generated " + bytes([n]))
        paths.append(p)
    return paths


class RunFastPathTests(unittest.TestCase):
    def test_start_finish_matches_original_prompt_bytes(self):
        # The original golden fixture predates this Skill's voiceover rule, so the
        # fast path is checked on the example; test_migration covers the fixture.
        for plan_path in [EXAMPLE]:
            with self.subTest(plan=plan_path.name), TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                result = start(plan_path, tmp / "internal", "2026-10-09")
                self.assertEqual([p["number"] for p in result["prompts"]], [1, 2, 3, 4])
                delivery = finish(Path(result["project"]), fake_images(tmp))
                self.assertEqual((delivery / "05-即梦视频提示词.txt").read_bytes(),
                                 expected_file_bytes(load_plan(plan_path)))
                self.assertEqual(sorted(p.name for p in delivery.iterdir()), [
                    "01-建立场景.png", "02-关键对象.png", "03-动作关系.png", "04-结果冲突.png",
                    "05-即梦视频提示词.txt"])
                self.assertEqual((delivery / "02-关键对象.png").read_bytes(), b"\x89PNG generated \x02")

    def test_all_plan_problems_reported_at_once_and_nothing_created(self):
        plan = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        plan["frames"][0]["prompt"] = plan["frames"][0]["prompt"].replace("middle core", "centre")
        plan["frames"][1]["prompt"], plan["frames"][2]["prompt"] = plan["frames"][2]["prompt"], plan["frames"][1]["prompt"]
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bad = tmp / "plan.json"
            bad.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            errors = plan_errors(bad)
            self.assertTrue(any("middle core" in e for e in errors))
            self.assertTrue(any("顺序与口播不一致" in e for e in errors))
            with self.assertRaises(ValueError):
                start(bad, tmp / "internal", "2026-10-09")
            self.assertFalse((tmp / "internal").exists())

    def test_json_comma_error_points_to_line(self):
        with TemporaryDirectory() as tmp:
            bad = Path(tmp) / "plan.json"
            bad.write_text('{\n  "speech": "x",\n  "title": "y",\n}\n', encoding="utf-8")
            errors = plan_errors(bad)
            self.assertEqual(len(errors), 1)
            self.assertIn("第 3 行", errors[0])

    def test_finish_refuses_missing_or_unsupported_images(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project = Path(start(EXAMPLE, tmp / "internal", "2026-10-09")["project"])
            images = fake_images(tmp)
            with self.assertRaises(ValueError):
                finish(project, images[:3] + [tmp / "missing.png"])
            with self.assertRaises(ValueError):
                finish(project, fake_images(tmp, ".webp"))
            self.assertFalse((tmp / "internal" / "交付").exists())

    def test_finish_twice_makes_new_delivery_and_replaces_image(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project = Path(start(EXAMPLE, tmp / "internal", "2026-10-09")["project"])
            first = finish(project, fake_images(tmp))
            redo = tmp / "redo3.jpg"
            redo.write_bytes(b"jpeg redo")
            images = fake_images(tmp)
            images[2] = redo
            second = finish(project, images)
            self.assertNotEqual(first, second)
            self.assertEqual((second / "03-动作关系.jpg").read_bytes(), b"jpeg redo")
            self.assertFalse((project / "03-图片" / "03-动作关系.png").exists())

    def test_example_does_not_ask_for_a_blank_top(self):
        for frame in json.loads(EXAMPLE.read_text(encoding="utf-8"))["frames"]:
            text = frame["prompt"].lower()
            self.assertNotIn("only secondary texture", text)
            self.assertIn("do not leave it as an empty band", text)
            self.assertIn("news headline", text)
            self.assertIn("middle core", text)


if __name__ == "__main__":
    unittest.main()
