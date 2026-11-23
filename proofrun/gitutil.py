"""Git state capture and file hashing (stdlib only, no network)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
                 "proofrun-output", "out", ".proofrun-output"}


def sha256_file(path) -> str:
    """Return the SHA-256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo: Path, *args: str) -> str | None:
    """Run a git command in repo; return stdout stripped, or None on failure."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    # rstrip only: `git status --porcelain` lines start with a significant
    # space (e.g. " M a.py"), and stripping the whole output would shift
    # the first line's columns by one.
    return r.stdout.rstrip("\n").rstrip()


def _status_entry(line: str, repo: Path) -> dict | None:
    """Parse one `git status --porcelain` line into a changed-file record."""
    if len(line) < 4:
        return None
    code = line[:2].strip()
    path_str = line[3:].strip()
    # Renames look like "old -> new"; the new path is what exists now.
    if " -> " in path_str:
        path_str = path_str.split(" -> ", 1)[1]
    path_str = path_str.strip('"')
    status_map = {"M": "modified", "A": "added", "D": "deleted",
                  "?": "untracked", "??": "untracked", "R": "renamed",
                  "C": "copied"}
    status = status_map.get(code, "modified" if code else "unknown")
    full = repo / path_str
    if status == "deleted" or not full.is_file():
        return {"path": path_str, "sha256": None, "bytes": 0, "status": status}
    try:
        size = full.stat().st_size
        digest = sha256_file(full)
    except OSError:
        return {"path": path_str, "sha256": None, "bytes": 0, "status": status}
    return {"path": path_str, "sha256": digest, "bytes": size, "status": status}


def _walk_all_files(repo: Path) -> list[dict]:
    """Hash every file under repo, skipping excluded dirs (non-git mode)."""
    out: list[dict] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(files):
            full = Path(root) / name
            rel = str(full.relative_to(repo))
            try:
                out.append({"path": rel, "sha256": sha256_file(full),
                            "bytes": full.stat().st_size, "status": "present"})
            except OSError:
                continue
    return out


def collect_repo_state(repo_path) -> dict:
    """Capture git state and changed-file hashes for repo_path.

    Returns {"git": {...}, "changed_files": [...]}. If repo_path is not a
    git repo, git fields are None/False and changed_files lists every
    file under the repo (status "present").
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        raise FileNotFoundError(f"repo path does not exist: {repo}")
    is_git = (repo / ".git").exists() or _git(repo, "rev-parse", "--git-dir") is not None
    if not is_git:
        return {
            "git": {"is_git": False, "commit": None, "branch": None,
                    "dirty": False, "status": []},
            "changed_files": _walk_all_files(repo),
        }
    commit = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    status_raw = _git(repo, "status", "--porcelain")
    status_lines = [ln for ln in (status_raw or "").splitlines() if ln.strip()]
    diff_stat = _git(repo, "diff", "--stat") or ""
    changed = []
    for line in status_lines:
        entry = _status_entry(line, repo)
        if entry is not None:
            changed.append(entry)
    return {
        "git": {"is_git": True, "commit": commit, "branch": branch,
                "dirty": bool(status_lines), "status": status_lines,
                "diff_stat": diff_stat},
        "changed_files": changed,
    }
