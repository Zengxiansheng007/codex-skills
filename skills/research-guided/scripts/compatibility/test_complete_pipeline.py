from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from complete_pipeline import main


ROOT = Path(__file__).resolve().parent
BASELINE = ROOT.parent.parent / "scholar-research-enhancement-20260829" / "baseline-v0.10.0-current"
FULL_FIXTURE = ROOT / "fixtures" / "accepted-full-result.json"
PIPELINE_PLAN = ROOT / "fixtures" / "full-pipeline-plan.json"
LEDGER = ROOT / "fixtures" / "accepted-full-ledger.json"
WEB_RESULT = Path("C:/Users/lenovo/Documents/ChatGPT/ui-test/work/handoffs/claude-glm52-adapter-repair-handoff-20260827/candidate-workspace/real-runtime-acceptance-20260829/reinforcement-round-2-final/research-result.json")
WEB_LEDGER = WEB_RESULT.parent / "evidence-ledger.json"


class CompletePipelineTest(unittest.TestCase):
    def test_full_pipeline_reaches_report_export_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence.json"
            rc = main([
                "--result", str(FULL_FIXTURE),
                "--baseline-root", str(BASELINE),
                "--state", str(root / "research_state.json"),
                "--report", str(root / "report.md"),
                "--export", str(root / "refs.bib"),
                "--question", "fixture compatibility research",
                "--story-id", "CC-004",
                "--pipeline-plan", str(PIPELINE_PLAN),
                "--ledger", str(LEDGER),
                "--evidence-output", str(evidence),
            ])
            self.assertEqual(rc, 0)
            output = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(output["status"], "test-completed")
            self.assertEqual(output["phase"], 7)
            self.assertTrue(output["reportLint"]["ok"])
            self.assertTrue((root / "refs.bib").stat().st_size > 0)
            self.assertEqual(output["findings"], [])
            self.assertTrue(output["formalCompletionEvaluation"]["passed"])
            self.assertEqual(output["formalCompletionEvaluation"]["state"], "completed")
            self.assertTrue(output["ledgerVerification"]["checks"]["ledgerHashSelfConsistent"])
            self.assertTrue(output["planVerification"]["checks"]["sourceStateHashMatches"])

    def test_web_only_real_result_blocks_without_state_mutation(self) -> None:
        if not WEB_RESULT.exists():
            self.skipTest("preserved real-runtime evidence is unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "research_state.json"
            rc = main([
                "--result", str(WEB_RESULT),
                "--baseline-root", str(BASELINE),
                "--state", str(state),
                "--report", str(root / "report.md"),
                "--export", str(root / "refs.bib"),
                "--question", "web evidence must remain evidence-only",
                "--story-id", "CC-004",
                "--ledger", str(WEB_LEDGER),
            ])
            self.assertEqual(rc, 4)
            self.assertFalse(state.exists())

    def test_ready_result_without_phase_plan_blocks_without_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc = main([
                "--result", str(FULL_FIXTURE),
                "--baseline-root", str(BASELINE),
                "--state", str(root / "research_state.json"),
                "--report", str(root / "report.md"),
                "--export", str(root / "refs.bib"),
                "--question", "plan required",
                "--story-id", "CC-004",
                "--ledger", str(LEDGER),
            ])
            self.assertEqual(rc, 4)
            self.assertFalse((root / "research_state.json").exists())

    def test_ledger_mismatch_blocks_without_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger.json"
            ledger.write_text(json.dumps({"ledgerSha256": "d" * 64}), encoding="utf-8")
            rc = main([
                "--result", str(FULL_FIXTURE),
                "--ledger", str(ledger),
                "--baseline-root", str(BASELINE),
                "--state", str(root / "research_state.json"),
                "--report", str(root / "report.md"),
                "--export", str(root / "refs.bib"),
                "--question", "ledger mismatch",
                "--story-id", "CC-005",
            ])
            self.assertEqual(rc, 4)
            self.assertFalse((root / "research_state.json").exists())

    def test_live_plan_without_real_evidence_refs_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = json.loads(PIPELINE_PLAN.read_text(encoding="utf-8"))
            plan["planType"] = "live-scholarly"
            live_plan = root / "live-plan.json"
            live_plan.write_text(json.dumps(plan), encoding="utf-8")
            rc = main([
                "--result", str(FULL_FIXTURE),
                "--ledger", str(LEDGER),
                "--pipeline-plan", str(live_plan),
                "--baseline-root", str(BASELINE),
                "--state", str(root / "research_state.json"),
                "--report", str(root / "report.md"),
                "--export", str(root / "refs.bib"),
                "--question", "live boundary",
                "--story-id", "CC-006",
            ])
            self.assertEqual(rc, 4)
            self.assertFalse((root / "research_state.json").exists())

    def test_baseline_idempotency_key_does_not_duplicate_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "research_state.json"
            payload = root / "payload.json"
            payload.write_text(json.dumps({
                "source": "openalex",
                "query": "idempotency fixture",
                "round": 1,
                "papers": [{"doi": "10.1000/idempotent", "title": "Idempotent fixture"}],
            }), encoding="utf-8")
            env = dict()
            env["SCHOLAR_CACHE_DIR"] = str(root / "cache")
            init = subprocess.run([sys.executable, str(BASELINE / "scripts" / "research_state.py"), "--state", str(state), "init", "--question", "idempotency", "--archetype", "literature_review"], cwd=BASELINE, capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            command = [sys.executable, str(BASELINE / "scripts" / "research_state.py"), "--state", str(state), "ingest", "--input", str(payload), "--idempotency-key", "same-key"]
            first = subprocess.run(command, cwd=BASELINE, capture_output=True, text=True, encoding="utf-8", env=env)
            second = subprocess.run(command, cwd=BASELINE, capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["queries"]), 1)
            self.assertEqual(len(saved["papers"]), 1)


if __name__ == "__main__":
    unittest.main()
