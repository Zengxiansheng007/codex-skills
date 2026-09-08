from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from phase_bridge import build_event, check_resume


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT.parent / "scholar-research-enhancement-20260829" / "baseline-v0.10.0-current"
FIXTURE = ROOT / "compatibility-adapter" / "fixtures" / "accepted-full-result.json"
LEDGER = ROOT / "compatibility-adapter" / "fixtures" / "accepted-full-ledger.json"
ENTRY = ROOT / "compatibility-adapter" / "run_baseline_ingest.py"


class PhaseBridgeTest(unittest.TestCase):
    def test_event_does_not_authorize_phase_mutation(self) -> None:
        event = build_event({"researchId": "r", "roundId": "round-2", "completionClaim": "complete", "evidenceLedgerRef": {"ledgerId": "l", "ledgerSha256": "a" * 64}}, story_id="ST-1", baseline_commit="c")
        self.assertEqual(event["phaseMutation"], "delegated-to-scholar-research_state-advance")
        self.assertEqual(event["stateMutationAuthority"], "scholar-research_state-only")

    def test_resume_requires_all_lineage_fields(self) -> None:
        checkpoint = {"storyId": "ST-1", "requirementAnchor": "A", "baselineCommit": "C", "ledgerSha256": "L"}
        self.assertTrue(check_resume(checkpoint, story_id="ST-1", requirement_anchor="A", baseline_commit="C", ledger_sha256="L")["resumeAllowed"])
        checkpoint["ledgerSha256"] = "other"
        self.assertFalse(check_resume(checkpoint, story_id="ST-1", requirement_anchor="A", baseline_commit="C", ledger_sha256="L")["resumeAllowed"])

    def test_entry_ingests_without_advancing_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            init = subprocess.run([sys.executable, str(BASELINE / "scripts" / "research_state.py"), "--state", str(state), "init", "--question", "fixture", "--archetype", "literature_review"], cwd=BASELINE, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            output = Path(tmp) / "entry.json"
            result = subprocess.run([sys.executable, str(ENTRY), "--result", str(FIXTURE), "--ledger", str(LEDGER), "--state", str(state), "--baseline-root", str(BASELINE), "--story-id", "DS-OPT-ST-005", "--output", str(output)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "ingested")
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(saved["phase"], 0)
            self.assertEqual(saved["queries"][0]["round"], 1)
            self.assertIn("doi:10.1000/oa-fixture", saved["papers"])


if __name__ == "__main__":
    unittest.main()
