# Reporting And Promotion

Read this reference when creating reports, reviewing run quality, or deciding whether to generate stable regression assets.

## Business Test Report

Use a Chinese HTML filename and include:

- scope, environment, role, and safety boundary;
- requirement/test-point coverage;
- normal, abnormal, boundary, permission, and downstream results;
- expected versus actual results;
- final route/state and strongest business evidence;
- defects, reproduction steps, severity suggestion, and evidence links;
- exclusions and unverified claims.

Do not include passwords, tokens, cookies, full private payloads, or unnecessary personal data.

## Agent Execution Quality Report

Use a separate Chinese HTML filename and include:

- Midscene attempted/verified pass ratio;
- model calls, latency, timeouts, retries, and repeated failures;
- false positives and false negatives;
- Playwright fallback count and reason;
- evidence completeness and redaction result;
- issue classification;
- repairs applied and re-run outcome;
- remaining risks and recommended upstream changes.

## Promotion Gates

Promote to Playwright/Hybrid regression only when all are true:

1. the requirement and expected result are stable enough to automate;
2. deterministic verification passes on repeated runs;
3. no unresolved business, requirement, access, or environment issue remains;
4. test data can be prepared and cleaned safely;
5. locators use stable contracts or a documented semantic fallback;
6. evidence is complete and reproducible;
7. the flow has bounded runtime and retry behavior;
8. maintenance ownership is known.

Choose:

- **Playwright** for stable, critical, high-frequency paths.
- **Hybrid** for changing UI with stable business checkpoints.
- **Midscene exploration only** for volatile or poorly specified flows.
- **Do not promote** when success depends on one shared environment run or unverifiable model judgment.

## Repair Gate

| Change | Gate |
|---|---|
| wait condition, locator scope, evidence index, report formatting | automatic |
| exploration wording or low-risk assertion clarification | automatic with re-run |
| test-data creation, update, cleanup, or business action | explicit confirmation |
| deletion, publishing, payment, permission change, production mutation | forbidden unless narrowly and explicitly authorized |
| weakening/removing an assertion to obtain green status | forbidden |

