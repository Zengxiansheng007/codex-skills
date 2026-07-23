# Execution Adapters

This skill keeps R0 static analysis separate from higher-risk follow-up actions.

## GitHub Snapshot

- Use `scripts/fetch_github_snapshot.py` only after approving the public repo, ref, and local output directory.
- The script resolves the requested ref to a commit SHA, downloads the GitHub zipball, safely extracts it, and writes HTML/JSON metadata.
- It does not install dependencies or execute target files.

## Third-Party Checks

- Use `scripts/run_third_party_checks.py` as supplementary evidence.
- Cisco `cisco-ai-skill-scanner==2.0.12` is the pinned local scanner adapter when installed in the project virtual environment.
- `skill-validator` and `skills-ref` are optional adapters and must be reported as `unverified` when the pinned binary or runtime is unavailable.
- A scanner timeout, crash, or empty result is not a pass.

## R3 Sandbox Runner

- Use `scripts/sandbox_runner.py --dry-run` to generate an execution plan. On Windows, prefer `--command-file` over inline JSON because PowerShell can strip nested quotes from JSON array arguments.
- Actual R3 requires `--allow-r3`, an installed sandbox provider, approved command, input mount, network policy, timeout, and cleanup rule.
- The current Docker adapter uses read-only source mount, writable output mount, no network, read-only container filesystem, dropped capabilities, and `no-new-privileges`.
- Do not fall back to executing an unknown Skill directly on the host.

## External LLM Review

- Use `scripts/llm_review.py --dry-run` to show the payload boundary.
- Actual review requires `--allow-external-llm`, approved endpoint, model, API key in `ANALYSIS_LLM_API_KEY`, and source data scope.
- Only redacted `SKILL.md` text and optional redacted R0 summary may be sent by default.
