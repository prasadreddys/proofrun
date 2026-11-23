"""Render report.md / report.html from a proof pack (no external assets)."""

from __future__ import annotations

import html


def _check_lines(pack: dict) -> str:
    lines = []
    for c in pack.get("checks", []):
        mark = "PASS" if c.get("passed") else "FAIL"
        lines.append(f"- [{mark}] **{c.get('name')}** — {c.get('detail')}")
    return "\n".join(lines) or "- (no checks)"


def _file_lines(pack: dict) -> str:
    lines = []
    for f in pack.get("changed_files", []):
        sha = (f.get("sha256") or "—")[:12]
        lines.append(f"- `{f.get('path')}` ({f.get('status')}, "
                     f"{f.get('bytes')} bytes, sha256 `{sha}…`)")
    return "\n".join(lines) or "- (no changed files)"


def render_markdown(pack: dict) -> str:
    s = pack.get("test_summary", {})
    git = pack.get("git", {})
    claim = pack.get("claim")
    return f"""# ProofRun Report

- **Verdict:** {pack.get('verdict')}
- **Generated (UTC):** {pack.get('generated_at_utc')}
- **Tool:** {pack.get('tool')}
- **Pack hash:** `{pack.get('pack_hash')}`
- **Repo:** `{pack.get('repo_path')}`
- **Git:** commit `{git.get('commit') or 'n/a'}`, branch `{git.get('branch') or 'n/a'}`, dirty: {git.get('dirty')}, git repo: {git.get('is_git')}

## Command

- Command: `{pack.get('command')}`
- Exit code: {pack.get('exit_code')}
- Duration: {pack.get('duration_ms')} ms
- Timed out: {pack.get('timed_out')}

## Tests

- Passed: {s.get('passed')}, Failed: {s.get('failed')}, Errored: {s.get('errored')}, Total: {s.get('total')}
- Summary parseable: {s.get('parseable')}

## Claim

{claim if claim is not None else '(no claim file given — verdict cannot be VERIFIED)'}

## Checks

{_check_lines(pack)}

## Changed files

{_file_lines(pack)}

## Stdout tail

```
{pack.get('stdout_tail') or ''}
```

## Stderr tail

```
{pack.get('stderr_tail') or ''}
```
"""


_CSS = ("body{font-family:system-ui,sans-serif;max-width:820px;margin:2em auto;"
        "padding:0 1em;color:#111}h1{font-size:1.6em}.badge{display:inline-block;"
        "padding:.2em .6em;border-radius:4px;background:#111;color:#fff;"
        "font-weight:700}table{border-collapse:collapse}td,th{border:1px solid #ccc;"
        "padding:.35em .6em;text-align:left}code{background:#f0f0f0;padding:.1em .3em}"
        ".pass{color:#067a2e}.fail{color:#b00020}pre{background:#f6f6f6;padding:1em;"
        "overflow:auto;white-space:pre-wrap}")


def render_html(pack: dict) -> str:
    s = pack.get("test_summary", {})
    git = pack.get("git", {})
    rows = "".join(
        f"<tr><td>{html.escape(str(c.get('name')))}</td>"
        f"<td class=\"{'pass' if c.get('passed') else 'fail'}\">"
        f"{'PASS' if c.get('passed') else 'FAIL'}</td>"
        f"<td>{html.escape(str(c.get('detail')))}</td></tr>"
        for c in pack.get("checks", []))
    files = "".join(
        f"<tr><td>{html.escape(str(f.get('path')))}</td>"
        f"<td>{html.escape(str(f.get('status')))}</td>"
        f"<td>{f.get('bytes')}</td>"
        f"<td><code>{html.escape(str(f.get('sha256') or '—'))}</code></td></tr>"
        for f in pack.get("changed_files", []))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>ProofRun Report — {html.escape(str(pack.get('verdict')))}</title>
<style>{_CSS}</style></head><body>
<h1>ProofRun Report</h1>
<p>Verdict: <span class="badge">{html.escape(str(pack.get('verdict')))}</span></p>
<p>Generated (UTC): {html.escape(str(pack.get('generated_at_utc')))}<br>
Tool: {html.escape(str(pack.get('tool')))}<br>
Pack hash: <code>{html.escape(str(pack.get('pack_hash')))}</code><br>
Repo: <code>{html.escape(str(pack.get('repo_path')))}</code></p>
<h2>Git</h2>
<p>Commit: <code>{html.escape(str(git.get('commit') or 'n/a'))}</code> —
Branch: {html.escape(str(git.get('branch') or 'n/a'))} —
Dirty: {git.get('dirty')} — Git repo: {git.get('is_git')}</p>
<h2>Command</h2>
<p><code>{html.escape(str(pack.get('command')))}</code> —
Exit: {pack.get('exit_code')} — Duration: {pack.get('duration_ms')} ms —
Timed out: {pack.get('timed_out')}</p>
<h2>Tests</h2>
<p>Passed: {s.get('passed')} — Failed: {s.get('failed')} —
Errored: {s.get('errored')} — Total: {s.get('total')} —
Parseable: {s.get('parseable')}</p>
<h2>Checks</h2>
<table><tr><th>Check</th><th>Result</th><th>Detail</th></tr>{rows}</table>
<h2>Changed files</h2>
<table><tr><th>Path</th><th>Status</th><th>Bytes</th><th>SHA-256</th></tr>{files}</table>
<h2>Stdout tail</h2><pre>{html.escape(str(pack.get('stdout_tail') or ''))}</pre>
<h2>Stderr tail</h2><pre>{html.escape(str(pack.get('stderr_tail') or ''))}</pre>
</body></html>
"""
