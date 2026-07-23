# Grill Session Contract

Use this schema for the report JSON data block with id `grill-session`.

```json
{
  "sessionId": "grill-YYYYMMDD-HHMM",
  "scenario": "test-case-design",
  "status": "complete",
  "sourceInputs": [
    {"type": "prd", "pathOrLabel": "requirements.md", "freshness": "unknown"}
  ],
  "questions": [
    {
      "id": "Q-001",
      "question": "Which source should be treated as authoritative for current behavior?",
      "purpose": "Decide whether test cases should follow PRD, UI, code, or production behavior.",
      "evidence": ["E-001"],
      "recommendedAnswer": "Use running product behavior as current truth and mark PRD/Figma drift as requirement risk.",
      "blockingDecision": "test oracle source",
      "userResponse": "confirmed",
      "status": "confirmed",
      "severity": "P0"
    }
  ],
  "decisions": [
    {
      "id": "D-001",
      "title": "Use running product as the test oracle",
      "sourceQuestion": "Q-001",
      "decision": "confirmed",
      "consequence": "Generated cases must cite product evidence when PRD conflicts."
    }
  ],
  "evidenceIndex": [
    {"id": "E-001", "type": "code", "pathOrUrl": "src/module", "claim": "module is still routed"}
  ],
  "openItems": [
    {"id": "O-001", "severity": "P2", "owner": "product", "question": "Confirm final copy for empty state."}
  ],
  "nextActions": [
    {"type": "skill", "target": "to-spec", "reason": "Requirement decisions are ready for spec synthesis."}
  ]
}
```

## Status Values

- `draft`: grilling started but is not ready to use.
- `blocked`: a required decision or evidence source is unavailable.
- `complete`: P0 open items are zero and next action is clear.
- `risk-accepted`: P0 open items remain, but the user explicitly accepted the risk.

## Question Status Values

- `proposed`: agent asked and is waiting.
- `confirmed`: user accepted the answer.
- `changed`: user supplied a different answer.
- `rejected`: user rejected the premise.
- `needs-evidence`: fact lookup or research is required.

## Severity

- `P0`: blocks safe execution or materially changes scope.
- `P1`: likely changes design, coverage, or validation.
- `P2`: improves completeness or maintainability.
