---
name: ui-test-checkpoint-runtime
description: Plan, validate, and execute R0/R1 read-only cross-session UI checkpoint recovery by system, module, and function button. Use when Codex needs to load a checkpoint registry, validate auth-reference freshness without exposing state, plan fresh current-session login/module/page/button recovery, produce a dry-run report, or perform explicitly approved public-site Playwright verification. Do not use for R2/R3 writes, private-site execution without approval, credential creation, or historical browser-state reuse.
---

# UI-Test Checkpoint Runtime

## Operating Rules

- Support only R0/R1 read-only recovery. Reject create, submit, save, update, delete, approve, publish, pay, deploy, and other write semantics.
- Default to `dry-run`. Treat `live-public` as approval-gated browser execution for the exact public URLs, runtime root, Node executable, Playwright module, proxy, and evidence directory.
- Do not access a private system or send page content to an external model without explicit approval for that execution. A private R1 adapter must use a fresh current-session Page and credentials supplied only to that process in memory.
- Keep real credentials, cookies, tokens, and `storageState` content outside the Skill, reports, RAG, handoff packets, and version control. Runtime assets may contain only governed references and redacted metadata.
- Do not write to `D:\midscene\checkpoint-runtime` or another real runtime root unless the user explicitly approves that exact destination.
- Preserve `run_id`, `correlation_id`, failure attribution, evidence references, and blocked reasons in the generated report.
- Use independent `project_group`, `product`, `system`, `module_path`, `function`, `checkpoint`, `environment`, and `risk_level` identity fields. Legacy single `module` identity is migration-only.
- A ModuleReadyContext requires verified host, current authenticated session, route and two independent UI features, and is valid only for its exact session/run until expiry.
- Checkpoint direct routes optimize Midscene exploration only. Formal Python pytest-playwright regression always executes the complete precondition Flow.

## Workflow

1. Read [the runtime contract](references/runtime-contract.md) before planning a recovery or interpreting runtime assets.
2. Resolve the exact runtime root, `system_id`, `module_id`, optional `button_id`, and `environment_alias`.
3. Confirm the registry, system manifest, module manifest, checkpoint index, and auth reference exist and pass schema validation.
4. Run `scripts/run_checkpoint_runtime.py` in `dry-run` mode unless the user approved `live-public` execution.
5. Inspect the report for `result`, `blocked`, `executed_chain`, `failure_attribution`, redaction status, and evidence references.
6. If blocked or stale, report the root cause and required upstream change. Do not silently reauthenticate, rewrite locators, expand risk scope, or downgrade assertions.
7. For an approved public run, supply explicit Node and Playwright paths and verify that no write request was permitted.

## Decision Rules

- Use dry-run for registry validation, recovery-chain planning, stale detection, and safety review.
- Use `live-public` only for public, non-sensitive UI verification after approval.
- Stop on R2/R3 risk, a write-classified button, expired/missing auth metadata, schema incompatibility, an unknown target, or unresolved requirement ambiguity.
- A single successful session recommends `validated`; only a two-independent-session aggregator may recommend `eligible`. Promotion to `active` and writes to the real runtime root remain separately governed.
- Keep runtime assets organized by stable `system_id/module_id/function_button_id`; never infer ownership by scanning arbitrary directories.

## Validation

- Static validation: verify frontmatter, referenced files, Python syntax, fixture schema, and absence of embedded secrets.
- Behavioral validation is available at `tests/run_tests.py`; executing target Skill tests remains an explicit action.
- A valid dry-run report must exclude raw state paths and secret values, preserve correlation identifiers, and block write actions deterministically.

## Escalation

Ask before private-site browser execution, real login-state reuse or creation, dependency installation, global Skill updates, writes to a real runtime root, or any action outside R0/R1.
