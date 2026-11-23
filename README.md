# ProofRun v1

Verifiable proof packs for AI coding agents. ProofRun re-runs tests, hashes
changed files, checks an agent's claims against reality, and emits a
tamper-evident proof pack. It does not trust what an agent *says* it did —
it proves what actually ran.

**Free / $0. No network. No paid APIs. Stdlib-only Python 3.12 — no
dependencies to install.**

## Quick start

```bash
cd proofrun
python3 -m unittest discover -s tests -v   # unit suite
./run_tests.sh                              # unit suite + demo e2e

# 1. An agent claims it finished a task — write the claim:
python3 -m proofrun init --dir ./my-claim
#    edit ./my-claim/claim.json

# 2. Run the tests and build the pack:
python3 -m proofrun run --repo /path/to/project \
  --claim ./my-claim/claim.json --out ./proofrun-output

# 3. Verify it later (or on another machine):
python3 -m proofrun verify --pack ./proofrun-output/proof-pack.json \
  --repo /path/to/project

# 4. Regenerate the reports from a pack:
python3 -m proofrun report --pack ./proofrun-output/proof-pack.json
```

## Claim format (`claim.json`)

```json
{
  "agent": "example-agent",
  "task": "Add a function and its tests",
  "claimed_files": ["calc.py", "tests/test_calc.py"],
  "claimed_tests_passed": 4,
  "claimed_success": true
}
```

- `claimed_files` — files the agent says it changed.
- `claimed_tests_passed` — how many tests the agent says passed.
- `claimed_success` — whether the agent claims the task succeeded.

## Claim checks

1. `claimed_files_subset` — every claimed file is in the changed files.
2. `claimed_tests_count` — `claimed_tests_passed <=` actual tests passed.
3. `claimed_success` — if success is claimed, exit code must be 0 and
   failed/errored must be 0.
4. `pack_integrity` — `pack_hash` recomputes from the pack contents.

## Verdict meanings

| Verdict | Meaning |
|---|---|
| `VERIFIED` | A claim was given, all checks pass, exit code 0. |
| `FAILED` | The command failed, or tests failed/errored (no claim mismatch). |
| `MISMATCH` | A claim check failed. Takes precedence over `FAILED` when a claim is present, because the claim itself is wrong. |
| `UNVERIFIED` | No claim file was given, but the command passed. Tests ran; nothing was claimed, so nothing is verified. |

If no test command can be auto-detected, `run` fails honestly (exit 2,
clear error) — it never fakes a pass.

## Auto-detection (in order)

1. `package.json` with `scripts.test` → `npm test`
2. `tests/` directory or `test_*.py` files → `python3 -m unittest discover -s tests -v`
3. Otherwise: error. Pass `--command` explicitly to override.

## Outputs (`--out`, default `./proofrun-output`)

- `proof-pack.json` — the pack: git state, changed files with SHA-256,
  command, exit code, duration, parsed test summary, claim, checks,
  verdict, stdout/stderr tails (last 2000 chars), and `pack_hash`.
- `report.md` / `report.html` — human-readable reports (HTML is
  self-contained, inline CSS only, no external assets).
- `raw.log` — full stdout, then stderr after a `--- stderr ---` marker.

`pack_hash` is the SHA-256 of the canonical JSON (sorted keys, tight
separators) of the pack *without* `pack_hash`. Changing any field — or
one byte of a recorded file — makes verification fail.

## `verify` output

- `pack_hash: OK / MISMATCH`
- Per file: `MATCHED` / `MISSING` / `CHANGED` (deleted files are
  `MATCHED` when absent, as recorded).
- Exit 0 only if the hash matches and every present file matches.

## Test-summary parsing

Handles pytest (`N passed, N failed, N error`), unittest
(`Ran N tests` + `OK` / `FAILED (failures=N, errors=N)`), Jest
(`Tests: N passed, N failed, N total`), and a generic
`N passed` / `N failed` fallback. If nothing parses, counts are 0
and `parseable` is `false` — numbers are never invented.

## Non-git repos

If the repo is not a git repo, ProofRun still works: it hashes every
file under the repo (except `.git`, `__pycache__`, `node_modules`,
`proofrun-output`, etc.) with status `present`, and the pack notes
`is_git: false`.

## Limitations (honest)

- Test counts come from parsing test-runner output; an exotic runner
  whose output matches none of the four formats yields `parseable:
  false` and 0 counts — the raw log still holds the truth.
- `verify --repo` checks files recorded in the pack; files added
  after the run are not in the pack and are not checked.
- ProofRun proves what ran on *this* machine at *this* time. It does
  not prove the code is correct, secure, or complete — only that the
  claimed tests ran and passed, and the files match their hashes.
- Timeout default is 600s (`--timeout`); a timed-out run exits 124
  in the pack and verdict `FAILED`.

## Layout

```
proofrun/
  proofrun/   __init__.py __main__.py cli.py gitutil.py runner.py pack.py verify.py report.py
  tests/      stdlib unittest only
  examples/   sample-project (passing) / sample-project-failing (1 failing test)
  run_tests.sh
```
