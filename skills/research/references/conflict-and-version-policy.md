# Conflict And Version Policy

Always preserve material conflicts.

Version handling:

- Pin code evidence to commit, tag, package version, or release.
- Mark floating links such as `main` or `latest` as unstable.
- Record access date for web pages.
- Prefer docs matching the user's stated version.
- If no version is stated, ask or state the assumption.

Conflict handling:

| Conflict | Handling |
|---|---|
| Official docs vs source behavior | Prefer observed/version-pinned behavior; flag docs mismatch |
| Old tutorial vs current docs | Prefer current docs; keep tutorial only as historical context |
| Vendor marketing vs independent benchmark | Separate vendor claims from verified facts |
| Standard draft vs final standard | Prefer final standard; cite draft only for upcoming change |
| Multiple community answers | Treat as weak evidence unless backed by docs or reproduction |

Each disputed claim should include `conflictSummary` and `recommendedAction`.
