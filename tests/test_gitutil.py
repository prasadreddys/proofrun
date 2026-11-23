"""Tests for gitutil: hashing and changed-file detection."""

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from proofrun.gitutil import collect_repo_state, sha256_file


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def _config_git(repo):
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.t"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                   check=True, capture_output=True)


class TestHashing(unittest.TestCase):
    def test_sha256_file_matches_hashlib(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.txt"
            p.write_bytes(b"hello proofrun\n")
            self.assertEqual(sha256_file(p),
                             hashlib.sha256(b"hello proofrun\n").hexdigest())

    def test_sha256_file_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty.txt"
            p.write_bytes(b"")
            self.assertEqual(sha256_file(p), hashlib.sha256(b"").hexdigest())


class TestGitRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        subprocess.run(["git", "init", str(self.repo)], check=True,
                       capture_output=True)
        _config_git(self.repo)
        (self.repo / "a.py").write_text("x = 1\n")
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-m", "init")

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_repo_no_changed_files(self):
        state = collect_repo_state(self.repo)
        self.assertTrue(state["git"]["is_git"])
        self.assertIsNotNone(state["git"]["commit"])
        self.assertIn(state["git"]["branch"], ("master", "main"))
        self.assertFalse(state["git"]["dirty"])
        self.assertEqual(state["changed_files"], [])

    def test_modified_file_detected_with_hash(self):
        (self.repo / "a.py").write_text("x = 2\n")
        state = collect_repo_state(self.repo)
        self.assertTrue(state["git"]["dirty"])
        self.assertEqual(len(state["changed_files"]), 1)
        entry = state["changed_files"][0]
        self.assertEqual(entry["path"], "a.py")
        self.assertEqual(entry["status"], "modified")
        self.assertEqual(entry["sha256"], sha256_file(self.repo / "a.py"))
        self.assertEqual(entry["bytes"], 6)

    def test_untracked_file_detected(self):
        (self.repo / "new.py").write_text("y = 1\n")
        state = collect_repo_state(self.repo)
        paths = {e["path"]: e for e in state["changed_files"]}
        self.assertIn("new.py", paths)
        self.assertEqual(paths["new.py"]["status"], "untracked")
        self.assertIsNotNone(paths["new.py"]["sha256"])

    def test_non_git_repo_hashes_all_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "x.py").write_text("a = 1\n")
            (root / "sub").mkdir()
            (root / "sub" / "y.py").write_text("b = 2\n")
            state = collect_repo_state(root)
            self.assertFalse(state["git"]["is_git"])
            self.assertIsNone(state["git"]["commit"])
            paths = {e["path"] for e in state["changed_files"]}
            self.assertEqual(paths, {"x.py", "sub/y.py"})
            for e in state["changed_files"]:
                self.assertEqual(e["status"], "present")


if __name__ == "__main__":
    unittest.main()
