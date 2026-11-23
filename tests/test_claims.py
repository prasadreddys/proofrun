"""Tests for claim checks and verdict logic."""

import unittest

from proofrun.cli import check_claim, decide_verdict

CHANGED = [{"path": "calc.py", "sha256": "a", "bytes": 10, "status": "present"},
           {"path": "tests/test_calc.py", "sha256": "b", "bytes": 20,
            "status": "present"}]
SUMMARY_OK = {"passed": 4, "failed": 0, "errored": 0, "total": 4,
              "parseable": True}


def _claim(**over):
    c = {"agent": "a", "task": "t", "claimed_files": ["calc.py"],
         "claimed_tests_passed": 4, "claimed_success": True}
    c.update(over)
    return c


def _by_name(checks):
    return {c["name"]: c for c in checks}


class TestClaimChecks(unittest.TestCase):
    def test_correct_claim_all_pass(self):
        checks = _by_name(check_claim(_claim(), CHANGED, SUMMARY_OK, 0))
        self.assertTrue(all(c["passed"] for c in checks.values()))

    def test_claimed_file_not_changed_fails(self):
        checks = _by_name(check_claim(_claim(claimed_files=["nope.py"]),
                                      CHANGED, SUMMARY_OK, 0))
        self.assertFalse(checks["claimed_files_subset"]["passed"])
        self.assertIn("nope.py", checks["claimed_files_subset"]["detail"])

    def test_over_claimed_test_count_fails(self):
        checks = _by_name(check_claim(_claim(claimed_tests_passed=99),
                                      CHANGED, SUMMARY_OK, 0))
        self.assertFalse(checks["claimed_tests_count"]["passed"])

    def test_claimed_success_with_failing_tests_fails(self):
        bad = dict(SUMMARY_OK, failed=1, passed=3)
        checks = _by_name(check_claim(_claim(), CHANGED, bad, 1))
        self.assertFalse(checks["claimed_success"]["passed"])

    def test_no_success_claimed_passes_even_on_failure(self):
        bad = dict(SUMMARY_OK, failed=1, passed=3)
        checks = _by_name(check_claim(_claim(claimed_success=False),
                                      CHANGED, bad, 1))
        self.assertTrue(checks["claimed_success"]["passed"])


class TestVerdict(unittest.TestCase):
    def test_verified(self):
        self.assertEqual(decide_verdict(
            [{"name": "x", "passed": True, "detail": ""}], 0, SUMMARY_OK, True),
            "VERIFIED")

    def test_mismatch_beats_failed(self):
        bad = dict(SUMMARY_OK, failed=1)
        self.assertEqual(decide_verdict(
            [{"name": "x", "passed": False, "detail": ""}], 1, bad, True),
            "MISMATCH")

    def test_failed_without_claim(self):
        bad = dict(SUMMARY_OK, failed=1)
        self.assertEqual(decide_verdict([], 1, bad, False), "FAILED")

    def test_unverified_without_claim_and_passing(self):
        self.assertEqual(decide_verdict([], 0, SUMMARY_OK, False),
                         "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
