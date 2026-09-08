# Guided handoff

Read the sibling research-guided/SKILL.md and its entry-compatibility reference. Preserve its existing workflows, source ledgers and validators. Explicitly selecting Codex is an approved entry exception, not an assertion that Claude failed.

The router emits kind=research-guided-handoff with taskId, generation, executor, pending objectives and existing sources. The host must actually run the selected guided workflow; the router does not spawn external models itself.

After the host's original workflow validation, accept-guided consumes a receipt with taskId, generation, executor, actualRetrieval=true, hostValidationPassed=true, non-empty toolEvidence and sources. Each source has url, title, content, objective and readDepth. The host is responsible for attaching true tool execution evidence and for retaining the original detailed packet. Do not manufacture hostValidationPassed or provider/MCP fields to pass a check.

The receipt must match current task, generation and executor. A result from before resume or from another provider is rejected. Accepted evidence still requires the router's coverage review; it is not automatically marked complete.

Claude unavailable: record guided-failure; applicable prior Codex authorization allows the selected fallback. Without it, pause. A failed Codex execution pauses without bouncing back to AnySearch. Existing user no-fallback constraints win.
