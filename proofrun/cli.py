"""ProofRun CLI: run / verify / report / init (stdlib only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .gitutil import collect_repo_state
from .pack import build_pack, compute_pack_hash, load_pack, save_pack
from .report import render_html, render_markdown
from .runner import DEFAULT_TIMEOUT, detect_command, parse_test_summary, run_command
from .verify import verify_pack

CLAIM_TEMPLATE = {
    "agent": "example-agent",
    "task": "Add a function and its tests",
    "claimed_files": ["calc.py", "tests/test_calc.py"],
    "claimed_tests_passed": 4,
    "claimed_success": True,
}


def check_claim(claim, changed_files, test_summary, exit_code) -> list[dict]:
    """Claim checks (1)-(3); (4) pack integrity is added by the caller
    after the pack hash exists. Returns a list of check dicts."""
    checks: list[dict] = []
    changed_paths = {f["path"] for f in changed_files}
    claimed_files = claim.get("claimed_files") or []
    missing = [f for f in claimed_files if f not in changed_paths]
    checks.append({
        "name": "claimed_files_subset",
        "passed": not missing,
        "detail": ("all claimed files are in changed files"
                   if not missing else
                   f"claimed files not in changed files: {missing}"),
    })
    claimed_passed = claim.get("claimed_tests_passed")
    if claimed_passed is None:
        checks.append({"name": "claimed_tests_count", "passed": True,
                       "detail": "no claimed test count given"})
    else:
        actual = test_summary.get("passed", 0)
        checks.append({
            "name": "claimed_tests_count",
            "passed": claimed_passed <= actual,
            "detail": (f"claimed {claimed_passed} passed, actual {actual}"
                       if claimed_passed <= actual else
                       f"claimed {claimed_passed} passed but only {actual} passed"),
        })
    if claim.get("claimed_success"):
        ok = exit_code == 0 and test_summary.get("failed", 0) == 0 \
            and test_summary.get("errored", 0) == 0
        checks.append({
            "name": "claimed_success",
            "passed": ok,
            "detail": ("claimed success matches: exit 0, no failures"
                       if ok else
                       f"claimed success but exit={exit_code}, "
                       f"failed={test_summary.get('failed')}, "
                       f"errored={test_summary.get('errored')}"),
        })
    else:
        checks.append({"name": "claimed_success", "passed": True,
                       "detail": "no success claimed"})
    return checks


def decide_verdict(checks, exit_code, test_summary, has_claim) -> str:
    """Precedence: MISMATCH (claim check fails) > FAILED (command/tests
    failed) > VERIFIED (claim, all pass, exit 0) > UNVERIFIED (no claim,
    command passed)."""
    if has_claim and any(not c["passed"] for c in checks):
        return "MISMATCH"
    if exit_code != 0 or test_summary.get("failed", 0) or test_summary.get("errored", 0):
        return "FAILED"
    if has_claim:
        return "VERIFIED"
    return "UNVERIFIED"


def _cmd_run(args) -> int:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"error: repo path does not exist: {repo}", file=sys.stderr)
        return 2
    command = args.command or detect_command(repo)
    if not command:
        print("error: could not auto-detect a test command for "
              f"{repo} (no package.json scripts.test, no tests/ or test_*.py); "
              "pass --command explicitly", file=sys.stderr)
        return 2
    claim = None
    if args.claim:
        try:
            claim = json.loads(Path(args.claim).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"error: cannot read claim JSON: {e}", file=sys.stderr)
            return 2
    state = collect_repo_state(repo)
    result = run_command(command, cwd=repo, timeout=args.timeout)
    combined = (result["stdout"] or "") + "\n" + (result["stderr"] or "")
    summary = parse_test_summary(combined)
    checks = check_claim(claim, state["changed_files"], summary,
                         result["exit_code"]) if claim is not None else []
    # Pack integrity check: build the pack, hash it, then verify the hash
    # recomputes — the check is only added once the hash exists.
    verdict_probe = decide_verdict(checks, result["exit_code"], summary,
                                   claim is not None)
    pack = build_pack(
        generated_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        repo_path=str(repo), git=state["git"],
        changed_files=state["changed_files"], command=command,
        exit_code=result["exit_code"], duration_ms=result["duration_ms"],
        timed_out=result["timed_out"], test_summary=summary, claim=claim,
        checks=checks, verdict=verdict_probe,
        stdout_tail=(result["stdout"] or "")[-2000:],
        stderr_tail=(result["stderr"] or "")[-2000:])
    integrity_ok = compute_pack_hash(pack) == pack["pack_hash"]
    pack["checks"] = checks + [{
        "name": "pack_integrity",
        "passed": integrity_ok,
        "detail": "pack_hash recomputes from pack contents" if integrity_ok
                  else "pack_hash does NOT recompute — pack is corrupt",
    }]
    # Re-hash, because the checks list changed.
    pack["pack_hash"] = compute_pack_hash(pack)
    pack["verdict"] = decide_verdict(pack["checks"], result["exit_code"],
                                     summary, claim is not None)
    outdir = Path(args.out).resolve() if args.out else (Path.cwd() / "proofrun-output")
    outdir.mkdir(parents=True, exist_ok=True)
    save_pack(pack, outdir / "proof-pack.json")
    (outdir / "report.md").write_text(render_markdown(pack), encoding="utf-8")
    (outdir / "report.html").write_text(render_html(pack), encoding="utf-8")
    (outdir / "raw.log").write_text(
        result["stdout"] or "", encoding="utf-8", errors="replace")
    # Append stderr to raw.log after a marker so nothing is lost.
    with open(outdir / "raw.log", "a", encoding="utf-8", errors="replace") as f:
        if result["stderr"]:
            f.write("\n--- stderr ---\n" + result["stderr"])
    print(f"verdict: {pack['verdict']}")
    print(f"command: {command} (exit {result['exit_code']}, "
          f"{result['duration_ms']} ms)")
    print(f"tests: {summary['passed']} passed, {summary['failed']} failed, "
          f"{summary['errored']} errored, total {summary['total']} "
          f"(parseable={summary['parseable']})")
    print(f"pack: {outdir / 'proof-pack.json'}")
    return 0


def _cmd_verify(args) -> int:
    try:
        pack = load_pack(args.pack)
    except (OSError, ValueError) as e:
        print(f"error: cannot read pack: {e}", file=sys.stderr)
        return 2
    result = verify_pack(pack, repo_path=args.repo)
    print(f"pack_hash: {'OK' if result['pack_hash_ok'] else 'MISMATCH'}")
    print(f"  expected: {result['expected_hash']}")
    print(f"  actual:   {result['actual_hash']}")
    if args.repo:
        for f in result["files"]:
            print(f"  {f['status']}: {f['path']} — {f['detail']}")
        if not result["files"]:
            print("  (no changed files recorded)")
    print(f"overall: {'OK' if result['overall_ok'] else 'FAILED'}")
    return 0 if result["overall_ok"] else 1


def _cmd_report(args) -> int:
    try:
        pack = load_pack(args.pack)
    except (OSError, ValueError) as e:
        print(f"error: cannot read pack: {e}", file=sys.stderr)
        return 2
    pack_path = Path(args.pack).resolve()
    if args.out:
        out = Path(args.out)
        if str(out).endswith(".html"):
            md_out = out.with_suffix(".md")
            out.write_text(render_html(pack), encoding="utf-8")
            md_out.write_text(render_markdown(pack), encoding="utf-8")
            print(f"wrote {out} and {md_out}")
        else:
            html_out = out.with_suffix(".html")
            out.write_text(render_markdown(pack), encoding="utf-8")
            html_out.write_text(render_html(pack), encoding="utf-8")
            print(f"wrote {out} and {html_out}")
    else:
        md_out = pack_path.parent / "report.md"
        html_out = pack_path.parent / "report.html"
        md_out.write_text(render_markdown(pack), encoding="utf-8")
        html_out.write_text(render_html(pack), encoding="utf-8")
        print(f"wrote {md_out} and {html_out}")
    return 0


def _cmd_init(args) -> int:
    target = Path(args.dir)
    target.mkdir(parents=True, exist_ok=True)
    dest = target / "claim.json"
    dest.write_text(json.dumps(CLAIM_TEMPLATE, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {dest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="proofrun",
                                description="Verifiable proof packs for AI coding agents.")
    p.add_argument("--version", action="version", version=f"proofrun {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run tests and emit a proof pack")
    r.add_argument("--repo", required=True)
    r.add_argument("--command")
    r.add_argument("--claim")
    r.add_argument("--out")
    r.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    r.set_defaults(func=_cmd_run)

    v = sub.add_parser("verify", help="verify a proof pack")
    v.add_argument("--pack", required=True)
    v.add_argument("--repo")
    v.set_defaults(func=_cmd_verify)

    rep = sub.add_parser("report", help="regenerate report(s) from a pack")
    rep.add_argument("--pack", required=True)
    rep.add_argument("--out")
    rep.set_defaults(func=_cmd_report)

    i = sub.add_parser("init", help="write a sample claim.json template")
    i.add_argument("--dir", required=True)
    i.set_defaults(func=_cmd_init)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
