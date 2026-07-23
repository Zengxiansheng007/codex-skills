# Evidence Policy

Use evidence markers so the next agent can tell what is reliable.

| Marker | Meaning | Use When | Required Detail |
|---|---|---|---|
| `[V]` | Verified in the current session | A command, test, screenshot, report, file read, or user confirmation supports the claim | Include command summary, file path, report path, or confirmation source |
| `[R]` | Referenced from an existing artifact | A PRD, plan, report, issue, commit, diff, or existing document contains the detail | Include the path or URL and a one-line reason to read it |
| `[?]` | Unverified, inferred, or remembered | The claim is useful for continuation but not independently verified | State what must be checked first |

## Rules

- Do not convert `[?]` items into facts.
- Do not repeat settled artifact content. Cite the artifact and explain how the next agent should use it.
- Put the highest-risk or most time-sensitive evidence first.
- If two sources conflict, keep both and mark the conflict in the risk section.
- If validation could not run, say so explicitly and list the missing validation.

## Recommended Evidence Order

1. User-confirmed decisions.
2. Files generated or changed in this session.
3. Test results and validation commands.
4. Reports and screenshots.
5. External references.
6. Unverified memory.

## Minimum Evidence For A Usable Handoff

- One current objective.
- One current status.
- At least one next action.
- At least one file, report, or reason why no artifact exists.
- Explicit sensitive-data handling.
- A recovery prompt.
