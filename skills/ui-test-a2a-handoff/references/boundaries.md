# Boundaries

## In scope

- packet-to-packet transformation
- history preservation
- stable reference extraction
- safe downgrade on malformed input
- compatibility with later checkpoint/review/memory consumption

## Out of scope

- remote A2A transport
- browser execution
- checkpoint runtime
- modifying business pages
- collecting fresh screenshots or traces
- embedding large prompt prose into refs

## Safety rules

- read-only by default
- source packets with `safety.read_only != true` are invalid
- source packets with empty or missing `safety.forbidden_actions` are invalid
- no credentials, cookies, tokens, or passwords in outputs
- no `Bearer` authorization values in `artifact_refs`
- no write actions on the business system
- preserve the source packet lineage
