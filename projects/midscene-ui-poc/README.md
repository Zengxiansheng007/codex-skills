# Codex + Midscene.js UI Testing POC

This workspace is for validating a Codex-orchestrated Midscene.js workflow.

## Main path

1. Pull Midscene repositories into `vendor/`.
2. Install local dependencies.
3. Configure `.env` with a rotated model key.
4. Run connectivity YAML.
5. Let Codex generate test points, steps, YAML, reports, and Playwright assets.

## Security

- Never commit `.env`.
- Never put API keys, cookies, tokens, or real passwords into YAML, reports, or chat.
- Use `${TEST_ACCOUNT_USER}` and `${TEST_ACCOUNT_PASSWORD}` placeholders.
- Run `npm run redact:reports` before sharing generated reports.

## Commands

```powershell
pnpm install
node .\node_modules\playwright\cli.js install chromium
.\scripts\run-connectivity.ps1
.\scripts\run-yaml-all.ps1
.\scripts\run-playwright.ps1
.\scripts\run-redact.ps1
```

If `node` is not available in PATH, use the PowerShell helper scripts. They add the bundled Codex Node runtime to PATH before running local binaries.
