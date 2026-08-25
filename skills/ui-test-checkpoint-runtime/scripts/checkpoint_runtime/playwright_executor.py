from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .io_utils import resolve_ref, write_json
from .models import RuntimePlan


class PlaywrightExecutionError(RuntimeError):
    pass


class PlaywrightExecutor:
    def __init__(self, runner_path: Path, node_path: Path, playwright_module: Path | None = None, timeout_seconds: int = 90):
        self.runner_path = runner_path
        self.node_path = node_path
        self.playwright_module = playwright_module
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        *,
        root: Path,
        plan: RuntimePlan,
        module_manifest: dict[str, Any],
        auth_ref: dict[str, Any],
        out_dir: Path,
        proxy_server: str | None = None,
    ) -> dict[str, Any]:
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        input_path = out_dir / "playwright-input.json"
        output_path = out_dir / "playwright-output.json"
        trace_path = out_dir / "trace.zip"
        before_screenshot = out_dir / "01-module-entry.png"
        after_screenshot = out_dir / "02-after-button.png"
        payload = {
            "run_id": plan.run_id,
            "correlation_id": plan.correlation_id,
            "target": {
                "system_id": plan.target.system_id,
                "module_id": plan.target.module_id,
                "function_button_id": plan.target.function_button_id,
                "environment_alias": plan.target.environment_alias,
            },
            "base_url_ref": "CHECKPOINT_RUNTIME_BASE_URL",
            "module_assertions": module_manifest["module_assertions"],
            "button": self._find_button(module_manifest, plan.target.function_button_id),
            "proxy_server": proxy_server,
            "forbidden_methods": ["POST", "PUT", "PATCH", "DELETE"],
            "readonly_post_signatures": module_manifest.get("readonly_post_signatures", []),
            "trace_path": trace_path.name,
            "before_screenshot": before_screenshot.name,
            "after_screenshot": after_screenshot.name,
            "output_path": output_path.name,
        }
        write_json(input_path, payload)

        argv = [str(self.node_path), str(self.runner_path), str(input_path)]
        env = os.environ.copy()
        env["CHECKPOINT_RUNTIME_BASE_URL"] = module_manifest["base_url"]
        if self.playwright_module:
            env["CHECKPOINT_RUNTIME_PLAYWRIGHT_MODULE"] = str(self.playwright_module)
        completed = subprocess.run(
            argv,
            cwd=str(out_dir),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
            env=env,
        )
        if not output_path.exists():
            raise PlaywrightExecutionError(
                f"Playwright runner did not write output; exit={completed.returncode}; stdout={completed.stdout}; stderr={completed.stderr}"
            )
        output = json.loads(output_path.read_text(encoding="utf-8"))
        output["node_exit_code"] = completed.returncode
        output["stdout"] = completed.stdout
        output["stderr"] = completed.stderr
        return output

    @staticmethod
    def _find_button(module_manifest: dict[str, Any], button_id: str | None) -> dict[str, Any] | None:
        if not button_id:
            return None
        for button in module_manifest.get("function_buttons", []):
            if button.get("button_id") == button_id:
                return button
        return None
