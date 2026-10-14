# Issue tracker: GitHub

Repository: **Zengxiansheng007/codex-skills**.

- Tracker: https://github.com/Zengxiansheng007/codex-skills/issues
- Host: github.com; API: https://api.github.com
- Specs and work items are GitHub Issues. Publish against this repository explicitly; do not infer a different target from the local workspace remote.
- Prefer the authenticated GitHub connector. When using gh, always pass `--repo Zengxiansheng007/codex-skills`; multiline bodies use `--body-file`.
- Read the actual Issue/body/labels and check for an existing matching item before creating or updating it. After writes, read back the result. If the outcome is unknown, reconcile before retrying.
- `to-spec` uses `ready-for-agent`; full label roles are in [triage-labels.md](triage-labels.md).

## Authentication

Reuse the execution host's authenticated GitHub connection. A repository-specific local credential reference may be used when the connector lacks a required capability; the location and secret remain in the user's private configuration, outside this repository. Never put tokens in project docs, Issues, command arguments, remote URLs or logs.

Read access and actual write qualification are separate. Create only the real, authorized Issue or content change; do not create test Issues to check authentication. Repository settings and labels do not authorize implementation, JMeter execution, installation, unrelated publication or automatic replay.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## JMeter work

Begin with [JMeter index](../../jmeter/README.md). The joint-spec Issue is one specification item; its JP work packages are a development dependency plan, not separately created Issues or a second execution ledger. Native Issue dependencies/sub-issues are introduced only when the project explicitly enters ticket decomposition.
