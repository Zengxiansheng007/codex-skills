# codex-skills

Portable Codex skill packages staged from the local Codex environment.

## Layout

- `skills/<skill-name>/`: user-level Codex skills.
- `skills/<skill-name>/DEPLOYMENT_AND_USAGE.md`: per-skill deployment and usage guide for another machine.
- `skills/_requirements-docs/`: related PRD, research, development plan, test plan, and review documents.
- `PUBLISH_AUDIT.md`: packaging scope and safety notes.

## Safety Notes

- No GitHub token or credential is stored in this repository.
- System/bundled skills under `.system` are excluded.
- Nested fixture skills used only for parser/security tests are excluded from the publish package.
- Candidate RAG materials, production data, cookies, API keys, and account data are not included.
