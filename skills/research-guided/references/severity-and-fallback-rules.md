# Severity and Fallback Rules

## Packet Severity Rules

### P0 - Critical

- P0 = missing required feedback packet fields.
- P0 = missing evidence for a critical claim.
- P0 = sensitive content exported without confirmation.
- Action: direct failure. The feedback packet is invalid and the loop stops immediately.

### P1 - Important

- P1 = coverage gap in requirements, development plan, or test plan.
- P1 = source conflict or stale evidence.
- P1 = weak source coverage for a critical design decision.
- P1 = schema concern or ambiguous packet field.
- Action: require user confirmation before proceeding. Do not auto-resolve.
### P2 - Format

- P2 = format inconsistency in the feedback packet.
- P2 = minor wording or link issue.
- P2 = optional field missing.
- Action: Codex may repair and log the fix without blocking.

### Live Adapter Cleanliness

- Raw Claude output must be schema-valid or explicitly marked `repair-needed`.
- A flat workspace layout is a repair condition because it hides the true artifact structure.
- A malformed feedback packet is P1 direct failure; do not treat it as a successful live run.
- Action: preserve raw artifacts, repair the workspace copy, rerun validation, and do not request global deployment until the repaired artifacts pass.

### Research Repair Failure Classes (FR-RR-006)

The following stable failure classes are defined in `schemas/failure-classification.json` and propagate through all contracts:

| Failure Class | Severity | Propagation | Trigger |
|---|---|---|---|
| `plan-mode-blocked` | P0 | `repair-needed` | Live research attempted with permission mode plan |
| `unregistered-tool-requested` | P0 | `blocked-user-decision` | Claude requested an MCP tool outside the approved registry |
| `mcp-schema-absent` | P0 | `blocked-external-dependency` | MCP tool schema was not visible in the session |
| `tool-count-zero` | P0 | `blocked-external-dependency` | No MCP tools were visible in the session |
| `stale-session` | P0 | `repair-needed` | Session freshness was not proven |
| `canary-missing` | P0 | `repair-needed` | Canary evidence was missing |
| `canary-failed` | P0 | `repair-needed` | Canary evidence was present but failed |
| `permission-denials-nonzero` | P0 | `blocked-user-decision` | Permission denials were nonzero |
| `output-not-json` | P0 | `repair-needed` | Research output was not pure UTF-8 JSON |
| `source-mappings-invalid` | P0 | `repair-needed` | Source mappings in research output were invalid |
| `unverified-sources-claimed-complete` | P0 | `repair-needed` | Unverified sources were claimed as complete evidence |
| `format-retry-limit-exceeded` | P1 | `repair-needed` | Format repair retries exceeded the maximum of 3 |
| `reinforcement-limit-exceeded` | P1 | `repair-needed` | Content reinforcement rounds exceeded the maximum of 1 |
| `claude-unavailable` | P1 | `blocked-external-dependency` | Claude was unavailable |
| `timeout` | P1 | `blocked-external-dependency` | Research session timed out |
| `internal-error` | P1 | `repair-needed` | Internal adapter error |

### Adapter-Validated Failure Classes (FR-ADP-008)

The two-stage adapter-validated compatibility profile adds failure classes that
propagate through all contracts. None may map a result to `completed`.

| Failure Class | Severity | Propagation | Trigger |
|---|---|---|---|
| `structured-output-empty` | P0 | `blocked-external-dependency` | Gateway returned no output under `--json-schema`; native Schema enforcement unavailable |
| `silent-native-downgrade` | P0 | `repair-needed` | Adapter-validated mode activated silently after a native failure instead of by an explicit profile |
| `evidence-ledger-missing` | P0 | `repair-needed` | Serialization produced output without a frozen retrieval evidence ledger |
| `evidence-hash-unstable` | P0 | `repair-needed` | The evidence hash changed between format attempts |
| `unsupported-fact-introduced` | P0 | `repair-needed` | Serialization introduced a source, URL, claim, or mapping absent from the frozen ledger |
| `serialization-tool-access` | P0 | `repair-needed` | The serialization phase requested or used a retrieval/shell/browser/write/network tool |
| `adapter-validation-failed` | P0 | `repair-needed` | Local Schema or semantic validation failed for a result that claimed complete |
| `format-attempt-exhaustion` | P1 | `repair-needed` | Three format attempts were exhausted without a valid output |

## Fallback Rules

### Claude Public Research Auto-Approval

1. For standard and deep public research, Codex self-approves the Claude retrieval call.
2. Codex also self-approves Claude use of these MCP tools:
   - `mcp__exa__web_search_exa`
   - `mcp__exa__web_fetch_exa`
   - `mcp__firecrawl__firecrawl_search`
   - `mcp__firecrawl__firecrawl_scrape`
3. This approval covers public search, public fetch, public scrape, and structured evidence return only.
4. If Claude requests any other MCP, shell, browser, account, write, delete, install, login-gated, paid, private, internal, or restricted action, classify it as a scope mismatch and block or request a new approval.
5. Every accepted Claude packet must still pass source coverage, schema, sensitive-boundary, and final Codex review gates.

### Claude Unavailable

1. Default to blocked.
2. Ask the user before using Codex fallback retrieval unless a separate active requirement anchor explicitly preauthorizes that fallback.
3. If the user confirms Codex fallback:
   - record the user confirmation;
   - use Codex reference materials for retrieval;
   - mark the result as fallback in the research report.
4. If the user does not confirm:
   - remain blocked;
   - record the blocked status and reason.
### Reinforcement Round

1. If Codex finds P0/P1 gaps after round one, initiate at most one reinforcement round.
2. Produce a targeted gap list with specific items for Claude to address.
3. After the reinforcement round, re-evaluate gaps.
4. If P0/P1 gaps remain after the second round:
   - output partial, blocked, or rerun;
   - record design defects in the defect matrix;
   - do not initiate a third round.

### Missing Validation Tool

1. If a validation script is missing, add it inside the workspace copy.
2. Rerun validation with the new script.
3. If the script cannot be created, return repair-needed or blocked.

### Adapter-Validated Profile Selection (FR-ADP-001, FR-ADP-007)

1. When the gateway returns `structured-output-empty` under `--json-schema`, the
   explicit `adapter-validated` profile is the preferred repair; it keeps the
   gateway and model unchanged.
2. The profile is selected only by an explicit profile selection, never as a
   silent downgrade after a provider-native failure. A silent downgrade is a
   P0 `silent-native-downgrade`.
3. The run must record `schemaEnforcementMode=adapter-validated` and
   `providerNativeSchema=false` honestly; it must never claim provider-native
   Schema enforcement.
4. Provider-native behavior remains available and unchanged for capable
   gateways; native-mode regression tests must pass.
5. The two-stage adapter is a candidate-workspace component. A localhost proxy
   is a separate unapproved fallback and must not be created without a new risk
   review.
