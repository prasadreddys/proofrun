"""Verify a proof pack: hash integrity + per-file SHA-256 re-check."""

from __future__ import annotations

from pathlib import Path

from .gitutil import sha256_file
from .pack import compute_pack_hash


def verify_pack(pack: dict, repo_path=None) -> dict:
    """Return {pack_hash_ok, expected_hash, actual_hash, files, overall_ok}.

    files entries: {path, status, expected, actual, detail} where status
    is MATCHED / MISSING / CHANGED. Deleted files are MATCHED when absent
    (deleted as recorded) and CHANGED when present again.
    """
    actual = pack.get("pack_hash")
    expected = compute_pack_hash(pack)
    hash_ok = (actual == expected)
    files: list[dict] = []
    if repo_path is not None:
        repo = Path(repo_path)
        for entry in pack.get("changed_files", []):
            rel = entry["path"]
            full = repo / rel
            expected_sha = entry.get("sha256")
            if entry.get("status") == "deleted":
                if not full.exists():
                    files.append({"path": rel, "status": "MATCHED",
                                  "expected": expected_sha, "actual": None,
                                  "detail": "deleted as recorded"})
                else:
                    files.append({"path": rel, "status": "CHANGED",
                                  "expected": expected_sha,
                                  "actual": sha256_file(full),
                                  "detail": "file present but recorded deleted"})
                continue
            if not full.is_file():
                files.append({"path": rel, "status": "MISSING",
                              "expected": expected_sha, "actual": None,
                              "detail": "file no longer present"})
                continue
            actual_sha = sha256_file(full)
            if actual_sha == expected_sha:
                files.append({"path": rel, "status": "MATCHED",
                              "expected": expected_sha, "actual": actual_sha,
                              "detail": "sha256 matches"})
            else:
                files.append({"path": rel, "status": "CHANGED",
                              "expected": expected_sha, "actual": actual_sha,
                              "detail": "sha256 differs from pack"})
    overall = hash_ok and all(f["status"] == "MATCHED" for f in files)
    return {"pack_hash_ok": hash_ok, "expected_hash": expected,
            "actual_hash": actual, "files": files, "overall_ok": overall}
