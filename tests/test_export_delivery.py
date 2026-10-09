"""Regression checks for byte-preserving, five-file delivery exports."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_delivery.py"
SPEC = importlib.util.spec_from_file_location("export_delivery", SCRIPT)
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="delivery-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "内部" / "2026-10-06-主题"
        self.images = self.project / "03-图片"
        self.images.mkdir(parents=True)
        self.names = ["01-建立场景.PNG", "02-关键对象.jpg", "03-动作关系.jpeg", "04-结果冲突.png"]
        for i, name in enumerate(self.names):
            (self.images / name).write_bytes(bytes([i, 255, 0, 13, 10]))
        (self.project / EXPORT.PROMPT_NAME).write_bytes("中文提示词\r\n保留换行\r\n".encode("utf-8"))
        (self.images / "README.txt").write_text("内部说明", encoding="utf-8")
        (self.images / "contact-sheet.png").write_bytes(b"internal preview")
        (self.project / "visual-spec.json").write_text('{"status":"gate1-package-created"}', encoding="utf-8")
        self.output = self.root / "交付" / self.project.name

    def snapshot(self):
        return {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}

    def test_only_five_original_files_are_copied(self):
        before = self.snapshot()
        destination = EXPORT.export_delivery(self.project, self.output)
        self.assertEqual(destination, self.output)
        self.assertEqual({p.name for p in destination.iterdir()}, set(self.names + [EXPORT.PROMPT_NAME]))
        for name in self.names:
            self.assertEqual((destination / name).read_bytes(), (self.images / name).read_bytes())
        self.assertEqual((destination / EXPORT.PROMPT_NAME).read_bytes(), (self.project / EXPORT.PROMPT_NAME).read_bytes())
        self.assertEqual(self.snapshot(), before)

    def test_existing_delivery_gets_a_new_number(self):
        first = EXPORT.export_delivery(self.project, self.output)
        first_bytes = {p.name: p.read_bytes() for p in first.iterdir()}
        (self.images / self.names[0]).write_bytes(b"updated original")
        second = EXPORT.export_delivery(self.project, self.output)
        self.assertEqual(second.name, self.output.name + "_02")
        self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()}, first_bytes)
        self.assertEqual((second / self.names[0]).read_bytes(), b"updated original")

    def test_default_destination(self):
        destination = EXPORT.export_delivery(self.project)
        self.assertEqual(destination, self.project.parent / "交付" / self.project.name)

    def test_missing_image_prevents_export(self):
        (self.images / self.names[0]).unlink()
        with self.assertRaisesRegex(ValueError, "01"):
            EXPORT.export_delivery(self.project, self.output)
        self.assertFalse(self.output.parent.exists())

    def test_duplicate_number_prevents_export(self):
        (self.images / "01-另一个候选.jpg").write_bytes(b"duplicate")
        with self.assertRaisesRegex(ValueError, "01"):
            EXPORT.export_delivery(self.project, self.output)
        self.assertFalse(self.output.parent.exists())

    def test_empty_or_missing_prompt_prevents_export(self):
        prompt = self.project / EXPORT.PROMPT_NAME
        for content in (b"", b" \r\n\t", b"\xef\xbb\xbf\r\n", None):
            with self.subTest(content=content):
                if content is None:
                    prompt.unlink()
                else:
                    prompt.write_bytes(content)
                with self.assertRaises(ValueError):
                    EXPORT.export_delivery(self.project, self.output)
                self.assertFalse(self.output.parent.exists())

    def test_delivery_cannot_be_inside_internal_project(self):
        before = self.snapshot()
        for output in (self.project, self.project / "交付"):
            with self.assertRaises(ValueError):
                EXPORT.export_delivery(self.project, output)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
