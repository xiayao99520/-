"""Verify that every trial CLI checks local access before any workflow write."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import export_delivery
import load_image_prompts
import make_package
import prepare_package
import render_image_prompts


class TrialEntrypointTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="trial-entrypoints-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.internal = self.root / "internal"
        self.project = self.internal / "2026-10-07-test"
        self.project.mkdir(parents=True)
        (self.project / "image-plan.json").write_text("existing plan\n", encoding="utf-8")
        (self.project / "05-即梦视频提示词.txt").write_text("existing video\n", encoding="utf-8")

    def snapshot(self):
        return sorted(
            (str(path.relative_to(self.root)), path.is_dir(),
             None if path.is_dir() else path.read_bytes())
            for path in self.root.rglob("*")
        )

    def assert_disabled_before_writes(self, entrypoint, arguments):
        before = self.snapshot()
        output = io.StringIO()
        with patch("access_control.is_enabled", return_value=False), \
                patch.object(sys, "argv", [entrypoint.__module__ + ".py", *arguments]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit) as raised:
                entrypoint()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("本地控制已停用", output.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_disabled_prepare_does_not_create_package(self):
        self.assert_disabled_before_writes(prepare_package.main, [
            "--plan", str(ROOT / "tests" / "fixtures" / "ticket.json"),
            "--output", str(self.root / "new-package"),
        ])

    def test_disabled_render_does_not_write_prompts(self):
        self.assert_disabled_before_writes(render_image_prompts.main, [
            "--project", str(self.project),
        ])

    def test_disabled_loader_stops_before_plan_read(self):
        self.assert_disabled_before_writes(load_image_prompts.main, [
            "--project", str(self.project),
        ])

    def test_disabled_video_only_preserves_existing_video(self):
        self.assert_disabled_before_writes(make_package.main, [
            "--speech", "政策出现新变化", "--title", "test",
            "--scene", "政府大楼", "--objects", "政策文件",
            "--action", "文件替换", "--result", "新政策生效",
            "--output", str(self.internal), "--date", "2026-10-07",
            "--video-only",
        ])

    def test_disabled_export_does_not_create_delivery(self):
        self.assert_disabled_before_writes(export_delivery.main, [
            "--project", str(self.project), "--output", str(self.root / "delivery"),
        ])


if __name__ == "__main__":
    unittest.main()
