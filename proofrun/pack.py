"""Proof-pack construction and hashing (canonical JSON, SHA-256)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FORMAT_VERSION = "1.0"
TOOL = "proofrun 1.0.0"


def canonical_json(obj) -> str:
    """Deterministic JSON: sorted keys, tight separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_pack_hash(pack: dict) -> str:
    """SHA-256 of canonical JSON of the pack WITHOUT its pack_hash field."""
    body = {k: v for k, v in pack.items() if k != "pack_hash"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def build_pack(*, generated_at_utc: str, repo_path: str, git: dict,
               changed_files: list, command: str, exit_code: int,
               duration_ms: int, timed_out: bool, test_summary: dict,
               claim, checks: list, verdict: str,
               stdout_tail: str, stderr_tail: str) -> dict:
    pack = {
        "format_version": FORMAT_VERSION,
        "generated_at_utc": generated_at_utc,
        "tool": TOOL,
        "repo_path": repo_path,
        "git": git,
        "changed_files": changed_files,
        "command": command,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "test_summary": test_summary,
        "claim": claim,
        "checks": checks,
        "verdict": verdict,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }
    pack["pack_hash"] = compute_pack_hash(pack)
    return pack


def save_pack(pack: dict, path) -> None:
    Path(path).write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")


def load_pack(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
