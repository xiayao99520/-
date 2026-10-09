"""Tests for the transparent local enable/disable switch."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "access_control.py"
SPEC = importlib.util.spec_from_file_location("access_control", SCRIPT)
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="local-control-")
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "local-control.json"

    def test_enabled_config_allows_workflow(self):
        self.config.write_text('{"enabled": true}\n', encoding="utf-8")
        self.assertTrue(CONTROL.is_enabled(self.config))
        self.assertEqual(CONTROL.main(["--check", "--config", str(self.config)]), 0)

    def test_disable_blocks_workflow_until_reenabled(self):
        CONTROL.set_enabled(self.config, False)
        self.assertFalse(CONTROL.is_enabled(self.config))
        self.assertEqual(CONTROL.main(["--check", "--config", str(self.config)]), 3)
        CONTROL.set_enabled(self.config, True)
        self.assertTrue(CONTROL.is_enabled(self.config))
        self.assertEqual(CONTROL.main(["--check", "--config", str(self.config)]), 0)

    def test_missing_config_fails_closed(self):
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.is_enabled(self.config)
        self.assertEqual(CONTROL.main(["--check", "--config", str(self.config)]), 2)

    def test_invalid_config_fails_closed(self):
        self.config.write_text('{"enabled": "yes"}\n', encoding="utf-8")
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.is_enabled(self.config)
        self.assertEqual(CONTROL.main(["--check", "--config", str(self.config)]), 2)


if __name__ == "__main__":
    unittest.main()
