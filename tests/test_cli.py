"""CLI end-to-end tests (subprocess, real packs, real test runs)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def _run_cli(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "-m", "proofrun", *args],
                          cwd=str(cwd), capture_output=True, text=True,
                          timeout=120)


def _load(outdir):
    return json.loads((Path(outdir) / "proof-pack.json").read_text())


class TestCliE2E(unittest.TestCase):
    def test_passing_project_verified_with_correct_claim(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            r = _run_cli("run", "--repo", str(EXAMPLES / "sample-project"),
                         "--claim", str(EXAMPLES / "sample-project" / "claim.json"),
                         "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            pack = _load(out)
            self.assertEqual(pack["verdict"], "VERIFIED")
            self.assertEqual(pack["test_summary"]["passed"], 4)
            self.assertEqual(pack["exit_code"], 0)
            self.assertTrue((out / "report.md").exists())
            self.assertTrue((out / "report.html").exists())
            self.assertTrue((out / "raw.log").exists())
            self.assertEqual(pack["pack_hash"],
                             __import__("proofrun.pack", fromlist=["compute_pack_hash"])
                             .compute_pack_hash(pack))

    def test_passing_project_mismatch_with_over_claim(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            r = _run_cli("run", "--repo", str(EXAMPLES / "sample-project"),
                         "--claim", str(EXAMPLES / "sample-project" / "claim-over.json"),
                         "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(_load(out)["verdict"], "MISMATCH")

    def test_failing_project_failed(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            r = _run_cli("run", "--repo",
                         str(EXAMPLES / "sample-project-failing"),
                         "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            pack = _load(out)
            self.assertEqual(pack["verdict"], "FAILED")
            self.assertEqual(pack["test_summary"]["failed"], 1)
            self.assertEqual(pack["test_summary"]["passed"], 3)

    def test_passing_project_without_claim_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            _run_cli("run", "--repo", str(EXAMPLES / "sample-project"),
                     "--out", str(out))
            self.assertEqual(_load(out)["verdict"], "UNVERIFIED")

    def test_no_detectable_command_fails_honestly(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "README.md").write_text("no tests\n")
            r = _run_cli("run", "--repo", d, "--out", str(Path(d) / "out"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("could not auto-detect", r.stderr)

    def test_verify_cli_pass_then_changed(self):
        with tempfile.TemporaryDirectory() as d:
            # Copy the passing project so we can mutate it after the run.
            import shutil
            proj = Path(d) / "proj"
            shutil.copytree(EXAMPLES / "sample-project", proj)
            out = Path(d) / "out"
            _run_cli("run", "--repo", str(proj), "--out", str(out))
            pack_path = out / "proof-pack.json"
            r = _run_cli("verify", "--pack", str(pack_path), "--repo", str(proj))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("overall: OK", r.stdout)
            (proj / "calc.py").write_text("# tampered\n")
            r2 = _run_cli("verify", "--pack", str(pack_path), "--repo", str(proj))
            self.assertEqual(r2.returncode, 1)
            self.assertIn("CHANGED: calc.py", r2.stdout)

    def test_report_regenerates_from_pack(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            _run_cli("run", "--repo", str(EXAMPLES / "sample-project"),
                     "--out", str(out))
            (out / "report.md").unlink()
            r = _run_cli("report", "--pack", str(out / "proof-pack.json"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((out / "report.md").exists())
            self.assertIn("VERIFIED", (out / "report.md").read_text())

    def test_init_writes_claim_template(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "claims"
            r = _run_cli("init", "--dir", str(target))
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((target / "claim.json").read_text())
            self.assertIn("claimed_files", data)
            self.assertIn("claimed_success", data)


if __name__ == "__main__":
    unittest.main()
