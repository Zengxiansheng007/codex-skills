# UI-Test Experience Governance

Use this contract when a UI-Test run should learn from execution or consume a previously approved experience.

## Scope identity

Every experience and every lookup must carry independent, non-empty fields:

`project_group`, `product`, `system`, `module`, `function`, `checkpoint`, `environment`, `risk_level`.

`project_group` and `product` must never be inferred from one combined label. Environment does not inherit across environments. A checkpoint-specific record has higher precedence than a function, module, system, or product record; scope precedence does not allow a record to cross project group, product, or environment boundaries.

Project and product boundaries are supplied by the versioned project configuration and active writeback policy. The generic Skill must not embed a project group, product name, knowledge-space ID, or target root. A policy mismatch fails closed; other project groups and business platforms are excluded unless a separate project configuration authorizes them.

## Lifecycle and consumption

Use these states: `observed`, `candidate`, `validated`, `promotable`, `active`, `stale`, `retired`, `rejected`.

- `observed` and `candidate` are evidence and recommendations. They must not silently change a test run.
- `validated` and `promotable` may be shown as recommendations after deterministic verification and review.
- Only `active` may be consumed as an automatic strategy, and only inside the exact scope and environment.
- `active`, shared projections, and formal RC require the applicable owner approvals. The execution agent cannot grant them.
- Failure history, retry history, fallback history, required fix points, checkpoint IDs, and evidence IDs are retained in the safe projection.
- A conflicting, stale, incomplete, or sensitive record is quarantined and excluded from the default retrieval projection.

## Run-end capture

At the end of every run, construct an observed/candidate packet containing the scope, category, trigger, strategy, source run/step/checkpoint IDs, evidence references, outcome attempts, failure attribution, and consumption feedback. Store only logical evidence references and redacted summaries. Never store passwords, tokens, cookies, storage state, raw URL values, private payloads, or screenshots in the experience packet.

Writeback is append-only and must pass, in order:

1. packet and scope validation;
2. sensitive and production-data scan;
3. exact knowledge-space and target-root check;
4. active, time-bounded preauthorization check;
5. idempotency/conflict check;
6. atomic candidate write and redacted audit write.

An expired, missing, mismatched, or auto-renewing policy fails closed. A failed writeback is recorded locally as a redacted failure and does not make the UI test fail unless the requirement explicitly makes learning mandatory.

## Semantic read-only POST

The default network policy still blocks all login-time and post-login `POST`, `PUT`, `PATCH`, and `DELETE` requests. A semantic read-only POST exception is valid only when all of these match a reviewed signature:

- method is `POST`;
- path is represented by a path-only SHA-256 fingerprint, never a raw URL;
- query-key set, body-key set, and content type match exactly;
- no request values are persisted;
- per-session count is bounded;
- the endpoint is explicitly classified as query/pagination/authentication, not submit or mutation;
- every other write request remains blocked.

The signature is evidence for policy evaluation, not a substitute for visible UI assertions. A read-only POST does not authorize a business write.

## Retention

Governance objects and decisions are retained through product retirement plus one year. Event and evidence indexes are retained for one year. Ordinary raw evidence is retained for 180 days. Failure, security, and R2/R3 evidence is retained for one year. Sensitive payload deletion retains only a redacted tombstone and audit record.

## Operational directory contract

The dedicated space selected by project configuration is governed as:

```text
${KNOWLEDGE_SPACE_ROOT}\\
  manifest.json
  INDEX.md
  governance\\
    audit\\
      events.jsonl
      experience-writeback\\
    bootstrap-evidence.json
    structure-map.json
  project\\
    candidates\\
    validated\\
    promotable\\
    active\\
    conflicts\\
    quarantine\\
  reference\\
  deprecated\\
  skill\\
```

`project_group`, `product`, `system`, `module`, `function`, and `checkpoint` are fields in records and lookup keys; they are not merged into a free-form path label. The path is a knowledge-space boundary, not an authorization by itself.
