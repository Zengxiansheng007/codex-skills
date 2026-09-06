---
name: domain-modeling
description: Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decision, or when another skill needs to maintain the domain model.
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline — challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `CONTEXT.md` for vocabulary is not this skill — that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

## Grill Invocation Boundary

When `domain-modeling` is called from an active Grill review, return proposed canonical terms, glossary entries, and ADR candidates to the Grill ledger instead of writing `CONTEXT.md` or ADR files. The caller keeps every formal artifact frozen until explicit whole-review closure makes centralized writeback eligible. A question-level confirmation, report, callee return, or legacy session is insufficient.

The caller's permission to append proposals to the Grill ledger does not authorize `CONTEXT.md` or ADR mutation. Domain-file permission remains with the owning post-closure writer and its approved batch scope.

This suppression is scoped only to the active Grill invocation. Standalone `domain-modeling` retains the immediate-update behavior below. After eligible post-closure writeback, the owning writer applies approved domain changes against a fresh baseline, preserves external edits, and reopens only affected questions on semantic conflict.

## Validation

For an active Grill invocation, verify that the returned proposal is recorded in the canonical Grill ledger and that no `CONTEXT.md` or ADR changed before a closure-backed eligible writeback. For standalone use, verify that each resolved term follows [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md) and each ADR follows [ADR-FORMAT.md](./ADR-FORMAT.md).

## Escalation

Ask before writing outside the requested project, changing global Skills, using private sources or external models, or making domain-file changes when the caller has not established whether an active Grill boundary applies. If that boundary is active, return proposals to the Grill ledger and wait for the owning writer's eligible post-closure batch.

## File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up — capture them as they happen. Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

`CONTEXT.md` should be totally devoid of implementation details. Do not treat `CONTEXT.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).
