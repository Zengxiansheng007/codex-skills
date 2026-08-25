# Runtime Contract

## Scope

Checkpoint Runtime v1 restores read-only UI state across sessions using stable assets organized by system, module, and function button. The supported chain is:

```text
CP1 login-state reference -> CP2 project/space context -> CP3 module entry -> CP4 read-only function button
```

It does not create credentials, bypass authentication, submit business forms, mutate private systems, or support R2/R3 checkpoints.

## Required Runtime Assets

```text
runtime-root/
  registry.index.json
  systems/{system_id}/
    system.manifest.json
    modules/{module_id}/
      module.manifest.json
      checkpoint.index.json
      auth/auth-ref.json
```

- `registry.index.json` locates systems through stable manifest references.
- `system.manifest.json` defines environments, modules, risk allowlists, and forbidden actions.
- `module.manifest.json` defines the public/read-only page contract, entry chain, assertions, and governed function buttons.
- `checkpoint.index.json` defines CP1-CP4 dependencies and R0/R1 classifications.
- `auth-ref.json` stores only an authentication mode, runtime environment-key names, and freshness/redaction metadata. It must not contain a state path, cookie, token, password, or `storageState` content.

## Execution Modes

### Dry Run

Use for normal planning and validation. It loads and validates assets, builds the recovery chain, applies risk and freshness policy, and writes a redacted report without opening a browser.

```powershell
python -B scripts/run_checkpoint_runtime.py --root <runtime-root> --system-id <system> --module-id <module> --button-id <button> --environment-alias <environment> --report <report.json>
```

### Live Public

Use only after approval for the exact public target and local dependencies. The runner creates a fresh browser context, never loads historical storage state, blocks `POST`, `PUT`, `PATCH`, and `DELETE`, captures evidence, and does not write state back.

```powershell
python -B scripts/run_checkpoint_runtime.py --mode live-public --root <runtime-root> --system-id <system> --module-id <module> --button-id <button> --environment-alias <environment> --node-path <node.exe> --playwright-module <playwright-module> --evidence-dir <evidence-dir> --report <report.json>
```

## Failure Governance

Reports use stable failure layers and types for missing or expired auth references, schema/registry problems, stale checkpoints, requirement ambiguity, assertion mismatch, network errors, and blocked write actions. Preserve the original failure and evidence; do not turn fallback success into an unexplained clean pass.

## Safety Boundary

- Only R0/R1 is allowed.
- Unknown or mutating actions fail closed.
- Reports exclude raw state paths, cookies, tokens, and authorization headers.
- Private URLs, accounts, and state files require separate execution approval.
- Promotion is advisory; installing assets into a real runtime root is a separate governed state change.
