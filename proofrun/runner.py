"""Test-command detection, subprocess execution, test-output parsing."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

DEFAULT_TIMEOUT = 600


def detect_command(repo_path) -> str | None:
    """Auto-detect a test command, in the specified order.

    package.json scripts.test -> `npm test`; else if tests/ or test_*.py
    present -> `python3 -m unittest discover -s tests -v`; else None.
    """
    repo = Path(repo_path)
    pkg = repo / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("scripts"), dict) \
                    and data["scripts"].get("test"):
                return "npm test"
        except (ValueError, OSError):
            pass
    if (repo / "tests").is_dir():
        return "python3 -m unittest discover -s tests -v"
    if list(repo.glob("test_*.py")) or list((repo / "tests").glob("test_*.py")) \
            or list(repo.rglob("test_*.py")):
        return "python3 -m unittest discover -s tests -v"
    return None


def run_command(command: str, cwd, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run command via the shell, capturing stdout/stderr, exit, duration."""
    start = time.monotonic()
    try:
        r = subprocess.run(command, shell=True, cwd=str(cwd),
                           capture_output=True, text=True, timeout=timeout)
        duration_ms = int((time.monotonic() - start) * 1000)
        return {"stdout": r.stdout, "stderr": r.stderr,
                "exit_code": r.returncode, "duration_ms": duration_ms,
                "timed_out": False}
    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return {"stdout": out, "stderr": err, "exit_code": 124,
                "duration_ms": duration_ms, "timed_out": True}


def parse_test_summary(output: str) -> dict:
    """Parse passed/failed/errored/total from test output.

    Handles unittest, pytest, Jest/npm, and a generic
    `N passed` / `N failed` fallback. Returns ints; 0s and
    parseable=False when nothing could be parsed. Never invents numbers.
    """
    text = output or ""
    passed = failed = errored = total = 0
    parseable = False

    # --- unittest: "Ran N tests" + "OK" / "FAILED (failures=N, errors=N)"
    m_ran = re.search(r"Ran (\d+) test", text)
    if m_ran:
        total = int(m_ran.group(1))
        parseable = True
        m_fail = re.search(r"FAILED \(([^)]*)\)", text)
        if m_fail:
            inner = m_fail.group(1)
            fm = re.search(r"failures=(\d+)", inner)
            em = re.search(r"errors=(\d+)", inner)
            failed = int(fm.group(1)) if fm else 0
            errored = int(em.group(1)) if em else 0
            # Bare "FAILED" with no counts and a total: treat as 1 failure
            # only if no counts at all were found.
            if fm is None and em is None and total:
                failed = total
        elif re.search(r"^OK$", text, re.MULTILINE):
            failed = errored = 0
        passed = max(total - failed - errored, 0)
        return {"passed": passed, "failed": failed, "errored": errored,
                "total": total, "parseable": parseable}

    # --- Jest / npm: "Tests: N passed, N failed, N total"
    m_jest = re.search(r"Tests:\s*([^\n]+)", text)
    if m_jest:
        seg = m_jest.group(1)
        pm = re.search(r"(\d+)\s+passed", seg)
        fm = re.search(r"(\d+)\s+failed", seg)
        tm = re.search(r"(\d+)\s+total", seg)
        if pm or fm or tm:
            passed = int(pm.group(1)) if pm else 0
            failed = int(fm.group(1)) if fm else 0
            total = int(tm.group(1)) if tm else passed + failed
            return {"passed": passed, "failed": failed, "errored": 0,
                    "total": total, "parseable": True}

    # --- pytest / generic: "N passed", "N failed", "N error"
    pm = re.search(r"(\d+)\s+passed", text)
    fm = re.search(r"(\d+)\s+failed", text)
    em = re.search(r"(\d+)\s+error", text)
    if pm or fm or em:
        passed = int(pm.group(1)) if pm else 0
        failed = int(fm.group(1)) if fm else 0
        errored = int(em.group(1)) if em else 0
        total = passed + failed + errored
        return {"passed": passed, "failed": failed, "errored": errored,
                "total": total, "parseable": True}

    return {"passed": 0, "failed": 0, "errored": 0, "total": 0,
            "parseable": False}
