"""Tests for pack hashing: determinism and tamper detection."""

import copy
import tempfile
import unittest
from pathlib import Path

from proofrun.pack import build_pack, compute_pack_hash, load_pack, save_pack


def _pack(**overrides):
    base = dict(generated_at_utc="2026-11-24T00:00:00Z", repo_path="/tmp/x",
                git={"is_git": False, "commit": None, "branch": None,
                     "dirty": False, "status": []},
                changed_files=[{"path": "a.py", "sha256": "abc", "bytes": 3,
                                "status": "present"}],
                command="python3 -m unittest discover -s tests -v",
                exit_code=0, duration_ms=12, timed_out=False,
                test_summary={"passed": 4, "failed": 0, "errored": 0,
                              "total": 4, "parseable": True},
                claim=None, checks=[], verdict="UNVERIFIED",
                stdout_tail="ok", stderr_tail="")
    base.update(overrides)
    return build_pack(**base)


class TestPackHash(unittest.TestCase):
    def test_hash_deterministic(self):
        self.assertEqual(_pack()["pack_hash"], _pack()["pack_hash"])

    def test_flip_one_field_changes_hash(self):
        p1 = _pack()
        p2 = _pack(exit_code=1)
        self.assertNotEqual(p1["pack_hash"], p2["pack_hash"])

    def test_flip_one_byte_of_hash_fails_recompute(self):
        p = _pack()
        tampered = copy.deepcopy(p)
        tampered["test_summary"]["passed"] = 99
        self.assertNotEqual(compute_pack_hash(tampered), tampered["pack_hash"])

    def test_save_load_roundtrip_preserves_hash(self):
        p = _pack()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "proof-pack.json"
            save_pack(p, path)
            loaded = load_pack(path)
        self.assertEqual(loaded["pack_hash"], p["pack_hash"])
        self.assertEqual(compute_pack_hash(loaded), p["pack_hash"])


if __name__ == "__main__":
    unittest.main()
