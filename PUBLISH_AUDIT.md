# Codex Skills Publish Audit

Generated: 2026-07-27

## Scope

- Included: user-level skills under `C:\Users\lenovo\.codex\skills`.
- Excluded: `.system`, plugin cache, nested fixture skills under `analysis-skill/assets/fixtures/*-skill`.
- Requirements docs copied to `skills/_requirements-docs`.
- GitHub token is not stored in this package.

## Counts

- Skills: 22
- Requirement docs: 24
- Files total: 182

## Included Skills

- analysis-skill
- auto-testcase-generator
- create-agent-skill
- create-skill
- domain-modeling
- figma-rest-sync
- grill-system
- grill-with-docs
- rag-change-impact
- rag-downstream-handoff
- rag-governance
- rag-intake
- rag-query
- rag-schema
- rag-structure-fidelity
- rag-system
- research
- session-handoff
- skill-packager
- task-understanding-router
- ui-test
- write-requirements-prd

## Security Notes

- No literal GitHub PAT / ghp / AWS key / OpenAI-style credential was found after staging cleanup.
- Remaining scanner hits are environment-variable reads or ordinary skill names, not stored secret values.
- The user-provided token from chat must be revoked and must not be committed.
