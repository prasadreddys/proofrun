#!/bin/sh
# ProofRun v1: run the unit suite, then a demo end-to-end run.
# Usage: ./run_tests.sh   (run from the proofrun/ directory)
set -e
cd "$(dirname "$0")"

echo "=== unit tests ==="
python3 -m unittest discover -s tests -v

echo ""
echo "=== demo e2e: passing project, correct claim ==="
python3 -m proofrun run --repo examples/sample-project \
  --claim examples/sample-project/claim.json \
  --out /tmp/proofrun-demo/passing 2>/dev/null || true

echo ""
echo "=== demo e2e: passing project, over-claim (expect MISMATCH) ==="
python3 -m proofrun run --repo examples/sample-project \
  --claim examples/sample-project/claim-over.json \
  --out /tmp/proofrun-demo/overclaim 2>/dev/null || true

echo ""
echo "=== demo e2e: failing project (expect FAILED) ==="
python3 -m proofrun run --repo examples/sample-project-failing \
  --out /tmp/proofrun-demo/failing 2>/dev/null || true

echo ""
echo "=== demo verify ==="
python3 -m proofrun verify --pack /tmp/proofrun-demo/passing/proof-pack.json \
  --repo examples/sample-project
echo "demo done."
