# Landed Review Contract

`landed_review.py` compares a baseline artifact manifest with an observed
implementation manifest after a Story completes.

## Rules

- The baseline anchor and baseline files are read-only.
- The result is a candidate revision or a blocking review; it is never user
  approval, `confirmed_active`, RC, or formal downstream release.
- Every result contains baseline/observed input hashes, classification, reasons,
  affected artifacts, evidence status and retest requirement.
- Any semantic requirement change is `requirements-review` and requires a new
  requirement anchor.
- Any implementation difference is `implementation-drift` and blocks release
  until repaired, re-anchored with approval, or explicitly risk-accepted with
  scope and expiry.
- Missing evidence, malformed manifests and secret-like values fail closed.
- Candidate revisions use `need-review` and retain `supersedes`; history is not
  deleted or overwritten.

## Input minimum

```json
{
  "anchorId": "REQ-...",
  "artifacts": [{"artifactId": "PRD-1", "version": "1.0.0", "contentHash": "..."}],
  "implementation": {"semanticRequirementChange": false},
  "evidence": [{"id": "E-1"}]
}
```

The observed manifest uses the same artifact keys. `implementation` may add
changed files and test references, but does not grant authority to alter the
anchor. Downstream systems must inspect `status` and `classification` before
consuming any candidate revision.
