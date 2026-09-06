# Routing And Prerequisites Adapter

The canonical mixed-request and stale-source rules are maintained by `write-prd` at `../../write-prd/references/routing-and-prerequisites.md`. Apply them when selecting an artifact path or reopening a stale artifact.

During active Grill, a source conflict preserves external edits and reopens only the decisions affected by semantic drift. It does not allow an immediate PRD rewrite.
