# midscene-ui-poc Deployment And Usage

## What this folder is

This is a portable copy of the local Midscene POC project, staged as a separate folder under the Codex skills repository.

## Deploy on another machine

1. Copy the entire `projects/midscene-ui-poc` folder to the target machine.
2. Install Node.js or use the bundled Codex runtime environment.
3. From this folder, run:

```powershell
pnpm install
node .\node_modules\playwright\cli.js install chromium
```

4. Create a local `.env` from `.env.example` and fill in only machine-local test credentials.
5. Run the helper scripts in `scripts/` as needed.

## Use

- `scripts/run-connectivity.ps1` for connectivity checks.
- `scripts/run-yaml-all.ps1` for Midscene YAML execution.
- `scripts/run-playwright.ps1` for Playwright execution.
- `scripts/run-redact.ps1` to redact generated reports before sharing.

## Safety notes

- Do not commit `.env`.
- Do not place real passwords, tokens, cookies, or production data into this package.
- `node_modules`, `test-results`, and `midscene_run` are intentionally excluded from the portable copy.

