# Grill phase-boundary runtime contract

The V2 runtime is local workflow enforcement and evidence detection. It does not install an ACL, intercept unrelated tools, infer external-file semantics, or merge formal documents.

`grill_session_runtime.py init` creates one non-overwriting canonical ledger. `record-answer`, `close`, `pause`, `resume`, and `reopen` preserve phase, decision, recovery, and reopen-history evidence. Every mutating command loads the same ledger path and performs semantic and process-artifact collision checks itself.

`checkpoint` hashes the observable protected set. `create-exception`, `consume-exception`, and `finish-exception` create one bounded user-authorized lease, reserve it for one target, then require actual postcondition hashes and a new baseline before the review freeze is restored. `begin-writeback` only starts a downstream batch after it independently checks closure, default authorization, phase, P0/risk acceptance, checkpoint equality, and scopes. `verify-writeback` validates actual local target hashes and the full protected-set delta against an existing batch. It marks `completed` only after those checks; it records per-item partial failure without rollback or a success claim. A matching frozen target with no protected delta is labeled `no-op`, with `contentChanged=false` and `mergePerformed=false`.

The only automatic external-drift result is an observable hash/path difference. Its semantic impact is `unknown` until a user or reviewer supplies evidence; the runtime preserves the external content and blocks the affected batch. Pausing and resuming preserve a recovery point but do not mint new closure or writeback authorization.

## Public ledger operations

Use `propose-question --session <ledger.json> --question-json <question.json>` to append the next question without hand-editing the ledger. The JSON input is one object with `id`, `question`, `purpose`, `recommendedAnswer`, `blockingDecision`, and `severity` (`P0`, `P1`, or `P2`); it may include `evidence` as an array. The runtime rejects duplicate IDs, more than one question mark, and a second `proposed` question. A P0 proposal automatically receives an `openItems` entry linked by `sourceQuestion`; a later `record-answer` clears that linked item on a terminal answer.

After `close` produces `review-ended` and `ready-for-writeback`, use `prepare-writeback-plan --session <ledger.json> --items <items.json> --output <plan.json>`. Add `<plan.json>` first to the ledger's `processArtifacts` as `{ "kind": "writeback-plan", "path": "<absolute path>" }`; the output is refused otherwise and protected assets remain untouched. `items.json` is `{ "items": [{"id":"I-001","path":"formal/requirements.md","expectedSha256":"<64 lowercase hex chars>"}] }`. The generated plan includes the canonical full-effective-decision fingerprint and scope fingerprint, so it can be passed directly to `begin-writeback --plan <plan.json>` without callers reproducing private serialization.

## Input and validation precision

Use lowercase SHA-256 hex digests, such as the output of hashlib.sha256(...).hexdigest(), for expectedSha256. The current implementation compares digest strings exactly; it does not normalize uppercase digest inputs. The public validate command inspects a ledger with read, close, or write intent; successful legacy inspection is not write authorization. Schema checks and runtime semantic/path checks have separate responsibilities.
