# Document Manifest Contract

The manifest binds a document ID, semantic classification, SemVer, source
commit, content digest, local RAG path, GitHub path and online path. The digest
must be recomputed from the supplied UTF-8 content; a supplied digest is not
trusted. JSON Schema validates shape, while the runtime validates computed
invariants and state transitions.

## Publish states

`draft -> preflight-passed -> github-published -> gitbook-sync-pending ->
gitbook-verified`.

`failed` and `rolled-back` are terminal records for the current attempt. A
rollback never deletes history and should normally be followed by a new patch
version. `gitbook-verified` requires explicit content-check evidence; GitHub
success alone is never full publication.

## Idempotency

The idempotency key is `docId:version:sourceCommit`. Repeating the same key
returns the existing registry record and does not create a duplicate publish
attempt. Concurrency control is outside this offline runtime and belongs to the
fixed publishing script.
