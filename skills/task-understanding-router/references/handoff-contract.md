# Handoff Contract

Full-grill handoff is a conversation-level instruction, not an RPC call. Preserve only facts that grill-system needs; grill-system owns its own question pack and report schema.

Use this conceptual record in the active conversation or test evidence:

```json
{
  "handoffId": "HR-unique",
  "target": "grill-system",
  "reason": "exact-trigger | explicit-execution-intent",
  "originalTask": "verbatim user request",
  "knownFactsAndConstraints": ["known fact or explicitly marked assumption"],
  "sourceReferences": ["user-provided path or label"],
  "routerDisposition": "delegated-no-question-pack",
  "nextState": "full-grill-active"
}
```

After handoff, do not display router framing, ask router questions, or trigger a second grill sequence. A response to the active grill question belongs to grill-system. Only an explicit stop-and-replace target returns to router classification.
