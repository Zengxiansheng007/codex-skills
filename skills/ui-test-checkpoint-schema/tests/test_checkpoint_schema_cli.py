import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "checkpoint_schema.py"
FIXTURE = ROOT / "fixtures" / "checkpoint_samples_valid.json"


class CheckpointSchemaCliTests(unittest.TestCase):
    def test_validate_cli_accepts_valid_fixtures(self):
        cmd = [sys.executable, str(SCRIPT), "validate", "--input", str(FIXTURE)]
        subprocess.run(cmd, check=True)

    def test_bundle_cli_writes_output(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bundle.json"
            cmd = [sys.executable, str(SCRIPT), "bundle", "--input", str(FIXTURE), "--output", str(out)]
            subprocess.run(cmd, check=True)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list)
            self.assertEqual(len(payload), 7)
            self.assertIn("handoff_packet", payload[0])
            self.assertIn("ui_test_packet", payload[0])


if __name__ == "__main__":
    unittest.main()
