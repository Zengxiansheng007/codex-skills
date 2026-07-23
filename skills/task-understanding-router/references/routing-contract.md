# Routing Contract

## Conversation state

Use these conceptual states only for behavior and test evidence: `new-task`, `ordinary-execution`, `clarification-pending`, `safety-approval-pending`, `full-grill-active`, and `target-change`.

- Confirmation, requested detail, or an answer to the current task stays in its active state.
- An answer to a grill-system question stays `full-grill-active`; do not route it again.
- An explicit stop-and-replace request enters `target-change`, then treats the replacement as `new-task`.

## Full-grill trigger

Route directly to grill-system if either condition holds:

1. The user contains the exact continuous phrase `帮我总结并完善需求` as an execution request.
2. The user simultaneously identifies a target Skill, expresses an execution intent (for example use, invoke, execute, or “按…流程处理”), and supplies an object to handle.

Merely quoting, explaining, discussing, or referencing the phrase or Skill does not trigger full grill.

## Ordinary mode selection

Apply the first matching rule.

1. `safety-gated`: external message, publish, install, delete/migrate, production or sensitive data, permissions, privacy, security, medical/legal/financial, or another irreversible/high-cost action. Follow the existing approval/safety policy.
2. `detailed-clarify`: two reasonable interpretations materially change the deliverable, external action, irreversibility, or safety result. Ask one highest-value question and wait.
3. `detailed-execute`: complex but clear work; two or more dependent steps; cross-file/system/Skill work; long-running work; behavior/config/API/data changes; hard rollback; or an explicit request for planning, review, analysis, verification, or detailed understanding.
4. `brief`: only when the task is clear, low-risk, reversible, and does not need a key assumption.

If classification is uncertain, use `detailed-execute`; uncertainty alone does not justify blocking with a question.

## Same-result ambiguity

Do not block merely because wording admits multiple interpretations. If every reasonable interpretation leads to the same low-risk deliverable and action, briefly state the adopted low-risk interpretation if useful and proceed.
