"""Tests for runner: command detection and test-output parsing."""

import tempfile
import unittest
from pathlib import Path

from proofrun.runner import detect_command, parse_test_summary, run_command


class TestDetectCommand(unittest.TestCase):
    def test_package_json_test_script(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "package.json").write_text('{"scripts": {"test": "jest"}}')
            self.assertEqual(detect_command(d), "npm test")

    def test_package_json_without_test_script(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "package.json").write_text('{"scripts": {}}')
            self.assertIsNone(detect_command(d))

    def test_tests_dir(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "tests").mkdir()
            self.assertEqual(detect_command(d),
                             "python3 -m unittest discover -s tests -v")

    def test_no_tests_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "README.md").write_text("nothing here\n")
            self.assertIsNone(detect_command(d))


class TestParseSummary(unittest.TestCase):
    def test_pytest(self):
        out = "================ 12 passed, 2 failed, 1 error in 3.21s ================"
        s = parse_test_summary(out)
        self.assertEqual((s["passed"], s["failed"], s["errored"], s["total"]),
                         (12, 2, 1, 15))
        self.assertTrue(s["parseable"])

    def test_unittest_ok(self):
        out = "Ran 4 tests in 0.001s\n\nOK\n"
        s = parse_test_summary(out)
        self.assertEqual((s["passed"], s["failed"], s["total"]), (4, 0, 4))
        self.assertTrue(s["parseable"])

    def test_unittest_failed(self):
        out = "Ran 4 tests in 0.001s\n\nFAILED (failures=1, errors=1)\n"
        s = parse_test_summary(out)
        self.assertEqual((s["passed"], s["failed"], s["errored"], s["total"]),
                         (2, 1, 1, 4))

    def test_jest(self):
        out = "Tests:       1 failed, 5 passed, 6 total\n"
        s = parse_test_summary(out)
        self.assertEqual((s["passed"], s["failed"], s["total"]), (5, 1, 6))

    def test_generic_fallback(self):
        out = "some log\n7 passed\n3 failed\n"
        s = parse_test_summary(out)
        self.assertEqual((s["passed"], s["failed"], s["total"]), (7, 3, 10))

    def test_unparseable_returns_zeros(self):
        s = parse_test_summary("hello world, no numbers here\n")
        self.assertEqual((s["passed"], s["failed"], s["total"]), (0, 0, 0))
        self.assertFalse(s["parseable"])


class TestRunCommand(unittest.TestCase):
    def test_echo_command(self):
        r = run_command("echo hello", cwd=".", timeout=10)
        self.assertEqual(r["exit_code"], 0)
        self.assertIn("hello", r["stdout"])
        self.assertFalse(r["timed_out"])
        self.assertGreaterEqual(r["duration_ms"], 0)

    def test_failing_command(self):
        r = run_command("python3 -c 'import sys; sys.exit(3)'", cwd=".",
                        timeout=10)
        self.assertEqual(r["exit_code"], 3)


if __name__ == "__main__":
    unittest.main()
