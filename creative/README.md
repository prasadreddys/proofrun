# ProofRun — Creative Pipeline

Free-only, $0. No paid stock, no paid video tools. Assets are generated
locally with Muse's media tools and reused across README, launch post,
and demo video.

## Assets (verified by eye, 24 Nov 2026)

- `media-generation-proofrun-logo-0-7bb473cb-a73c-4681-943e-d5d3bc52f225.webp`
  — App icon: green shield + checkmark + receipt document on green.
  Clean, readable at small sizes.
- `media-generation-proofrun-hero-0-5a95bff1-7608-40a1-9442-8a54cbc2d131.webp`
  — Hero: dark terminal checklist with green VERIFIED stamp, sealed
  receipt with green wax seal. On-brand, no invented claims in image.

## Demo video — 45-second script (not yet rendered)

Format: screen-record the real CLI demo + voiceover. No AI video
generation needed; the proof is the terminal output.

| Time | Visual | Voiceover |
|---|---|---|
| 0–6s | Hero image, title "ProofRun" | "Your AI agent says it's done. Prove it." |
| 6–16s | Terminal: agent claims 99 tests passed | "Agents over-claim. They say finished when they aren't." |
| 16–28s | `proofrun run --claim claim-over.json` → MISMATCH, 4 passed | "ProofRun re-runs the tests, hashes every changed file, and checks the claim." |
| 28–38s | `proofrun run --claim claim.json` → VERIFIED, then `verify` → all MATCHED | "Correct claim? VERIFIED. Tamper with a file and verify catches it." |
| 38–45s | report.html open, logo | "ProofRun. Don't trust the claim. Check the receipt." |

Storyboard shots are the real demo outputs in `/tmp/proofrun-demo/`
(passing / overclaim / failing) plus `report.html` from the demo run.

## Launch copy (draft, not published)

- One-liner: "ProofRun — verifiable proof packs for AI coding agents. Re-run the tests, hash the diff, check the claim."
- Post: "Your coding agent says 99 tests passed. ProofRun ran them: 4 passed. Don't trust the claim. Check the receipt. Free, open, stdlib-only Python."
- No fake users, sales, or reviews. Only the measured numbers:
  44 tests, 1.4s, demo 4 passed / 1 failed.

## Pipeline rules

- Every visual must show real output (real terminal, real verdicts).
- Regenerate an asset only if it misrepresents the product.
- Per the image-collection verification skill: distinct assets are
  checked by eye, not by file hash alone — logo and hero are
  visually distinct (icon vs wide scene) and share only the
  green shield/check motif.
