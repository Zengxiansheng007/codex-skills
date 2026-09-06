---
name: write-requirements-prd
description: Turn business ideas, notes, rules, permissions, and source docs into a development-ready PRD with explicit scope, business rules, states, acceptance criteria, RTM, change governance, and grill-based ambiguity control. Use when creating, reviewing, or repairing a PRD from business sources.
---

# Write Requirements PRD

## Purpose

`write-requirements-prd` converts source notes into a complete, testable requirements document that development can use directly.

It is the only child skill that owns PRD-level truth. It must not spill into architecture, implementation planning, or test-plan detail beyond what is needed for traceability and acceptance.

## Operating Rules

- Default output format is Markdown.
- Use [the local shared-contract adapter](references/shared-contracts.md) for envelope, state, IDs, RTM, source baseline, reopen, and risk acceptance.
- For new PRDs, major semantic changes, or any P0/P1 ambiguity, enter `grill-system` using [the local Grill adapter](references/grill-system-requirements-adapter.md).
- Under an active Grill review, freeze the PRD body, envelope metadata, version, status, dates, RTM, and substitute versions. Record answers only in Grill's authoritative ledger; do not mistake one confirmed question, a rendered report, or a legacy result for whole-review closure.
- An active Grill caller may update its process ledger but may not use that permission to write the PRD. This Skill writes only inside the closure-backed, approved-scope centralized batch described by the V2 handoff.
- Ask only for decisions, priorities, and tradeoffs after facts are gathered.
- Never invent business facts. Unknowns must remain visible as assumptions or open questions.
- Keep the PRD as the source of truth for requirements. Do not write implementation details that belong in architecture or development planning.
- Preserve the user's terminology unless it is clarified by a direct decision.
- Treat a changed upstream source as a reason to mark the PRD stale or reopened, not as a reason to silently overwrite prior text.

## Workflow

1. Read the available source materials and extract:
   - goal;
   - users and roles;
   - scope and non-goals;
   - business rules;
   - pages, flows, states, and exceptions;
   - data objects and lifecycle rules;
   - integration points;
   - constraints;
   - open questions and assumptions.
2. Load the shared contract and determine the initial artifact state.
3. Run a coverage scan across:
   - user goals and success criteria;
   - roles and permissions;
   - domain entities;
   - lifecycle/state transitions;
   - edge cases and failure handling;
   - non-functional requirements;
   - acceptance criteria;
   - evidence and DoD signals;
   - terminology consistency.
4. If any P0/P1 ambiguity remains, route to `grill-system`. Resume formal PRD writing only after a closure-backed `review-ended` / `ready-for-writeback` result with a non-notes-only policy; otherwise preserve conclusions or recovery state without changing the PRD.
5. Draft the PRD in this order:
   - document control and source baseline;
   - background and problem statement;
   - goals and success measures;
   - scope and non-goals;
   - roles and permissions;
   - glossary and canonical terms;
   - business rules and constraints;
   - flows, states, and exceptions;
   - functional requirements;
   - non-functional requirements;
   - acceptance criteria;
   - RTM;
   - risks, dependencies, and change governance;
   - open questions and assumptions.
6. Number requirements and acceptance criteria with stable IDs from the shared contract.
7. Make every P0/P1 item testable:
   - observable behavior;
   - boundary cases;
   - negative cases where relevant;
   - permission failures;
   - evidence expectation.
8. Before finalizing, verify that:
   - the document is separated from downstream architecture, dev, and test material;
   - the RTM covers all P0/P1 items;
   - open questions and assumptions are explicit;
   - risk acceptance is traceable;
   - the lifecycle state matches the actual readiness.

## Decision Rules

- If the input is a brief idea and the user wants help shaping the PRD, produce a draft plus the smallest set of high-value questions.
- If the input is already a solid PRD, focus on repair, gaps, and traceability rather than rewriting the whole thing.
- If the input mixes requirements with architecture or implementation, keep the requirements artifact clean and move the extra detail out of scope.
- If the user explicitly wants only a short explanation, do not expand into a full PRD.
- At centralized writeback, recheck the source baseline and preserve external edits. Reopen only decisions affected by a semantic conflict; do not overwrite unrelated changes or turn a pause, block, repair-needed, partial failure, or legacy-read-only result into a write.
- Freeze effective decisions, approved scopes, and planned target hashes before centralized writing. A verified `no-op` means no PRD body, metadata, version, status, date, or RTM change; an `updated` receipt must cover each actual target hash. Neither outcome can be inferred from a report or outer command exit code.
- Obtain a batch plan through Grill's public `prepare-writeback-plan` command and register it as a process artifact. Do not recreate runtime decision or scope fingerprints in this Skill.

## References

- Read [the local shared-contract adapter](references/shared-contracts.md) for envelope, RTM, state, and change governance.
- Read [the local Grill adapter](references/grill-system-requirements-adapter.md) before every clarification round.
- Read [the local routing adapter](references/routing-and-prerequisites.md) when the request is mixed or stale.

## Validation

Before delivery, check that:

- the frontmatter is minimal and valid;
- the PRD has no hidden implementation plan;
- every P0/P1 requirement has at least one acceptance criterion;
- the RTM is complete enough for downstream use;
- no invented facts, credentials, or private URLs appear;
- any skipped grill, research, or external evidence gap is explained.

## Escalation

Ask before using private sources, external models, or writing to any global skill directory.
