# ProofRun launch post — DRAFT, not published

Status: draft for the user's approval. Nothing posted yet.

## X / Threads version

Your coding agent says 99 tests passed.

ProofRun ran them: 4 passed.

Don't trust the claim. Check the receipt.

ProofRun — verifiable proof packs for AI coding agents. Free, open source (MIT), stdlib-only Python, no sign-up, no paid API.

https://github.com/prasadreddys/proofrun

## Longer version (README / Product Hunt style)

AI coding agents say "done" when they aren't — they skip tests, or loop, or
over-claim. ProofRun is the receipt: it re-runs the tests, SHA-256 hashes
every changed file, checks the agent's claim against what actually ran, and
emits a tamper-evident proof pack (proof-pack.json + report + raw log).

- Correct claim: VERIFIED (4 passed)
- Over-claim (claimed 99, actual 4): MISMATCH
- Failing project: FAILED (3 passed, 1 failed)
- Verify later: pack hash OK, all files MATCHED

Measured, not estimated: 44 unit tests, all passing in ~1.4s. Demo video
(45s, real terminal output) in creative/proofrun-demo-45s.mp4.

## Rules for posting

- Post only the measured numbers above. No users, sales, reviews, or
  revenue claims — none exist yet.
- Link the repo and the demo video, not a screenshot of a faked run.
- The video is slides typeset from real logs, not a live screen recording —
  say "demo" if asked, don't call it a screen recording.
