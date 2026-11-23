"""Tests for verify: hash integrity and per-file MATCHED/CHANGED/MISSING."""

import copy
import tempfile
import unittest
from pathlib import Path

from proofrun.pack import build_pack
from proofrun.verify import verify_pack


def _make_pack(repo: Path):
    (repo / "a.py").write_text("x = 1\n")
    from proofrun.gitutil import sha256_file
    changed = [{"path": "a.py", "sha256": sha256_file(repo / "a.py"),
                "bytes": 6, "status": "present"}]
    return build_pack(
        generated_at_utc="2026-11-24T00:00:00Z", repo_path=str(repo),
        git={"is_git": False, "commit": None, "branch": None, "dirty": False,
             "status": []},
        changed_files=changed, command="echo hi", exit_code=0,
        duration_ms=1, timed_out=False,
        test_summary={"passed": 1, "failed": 0, "errored": 0, "total": 1,
                      "parseable": True},
        claim=None, checks=[], verdict="UNVERIFIED",
        stdout_tail="", stderr_tail="")


class TestVerify(unittest.TestCase):
    def test_verify_passes_on_real_pack(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            pack = _make_pack(repo)
            result = verify_pack(pack, repo_path=repo)
            self.assertTrue(result["pack_hash_ok"])
            self.assertTrue(result["overall_ok"])
            self.assertEqual(result["files"][0]["status"], "MATCHED")

    def test_tampered_pack_hash_fails(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            pack = _make_pack(repo)
            tampered = copy.deepcopy(pack)
            tampered["exit_code"] = 1
            result = verify_pack(tampered, repo_path=repo)
            self.assertFalse(result["pack_hash_ok"])
            self.assertFalse(result["overall_ok"])

    def test_modified_file_reports_changed(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            pack = _make_pack(repo)
            (repo / "a.py").write_text("x = 999\n")
            result = verify_pack(pack, repo_path=repo)
            self.assertTrue(result["pack_hash_ok"])  # pack itself is intact
            self.assertEqual(result["files"][0]["status"], "CHANGED")
            self.assertFalse(result["overall_ok"])

    def test_deleted_file_reports_missing(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            pack = _make_pack(repo)
            (repo / "a.py").unlink()
            result = verify_pack(pack, repo_path=repo)
            self.assertEqual(result["files"][0]["status"], "MISSING")
            self.assertFalse(result["overall_ok"])

    def test_verify_without_repo_checks_hash_only(self):
        with tempfile.TemporaryDirectory() as d:
            pack = _make_pack(Path(d))
            result = verify_pack(pack)
            self.assertTrue(result["overall_ok"])
            self.assertEqual(result["files"], [])


if __name__ == "__main__":
    unittest.main()
