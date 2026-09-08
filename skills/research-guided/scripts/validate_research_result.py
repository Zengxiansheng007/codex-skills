#!/usr/bin/env python3
"""Validate research output against the strict result schema (FR-RR-004).

Checks:
1. Output is pure UTF-8 JSON (no BOM, no non-UTF-8, no prose wrapper).
2. Schema validation against Draft 2020-12 research-result.schema.json.
3. Semantic evidence gates:
   - sessionFresh is true.
   - evidenceComplete is true only when all sources are verified.
   - toolRegistryMatch is true.
   - permissionDenials is 0.
   - mode is not plan.
   - toolCount > 0.
   - mcpSchemaVisible is true.
   - canary evidence passed.
   - source mappings are valid (each claim's sourceUrl exists in sources).
   - formatRetries <= 3.
   - reinforcementRounds <= 1.
   - unverified sources are not claimed complete.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "research-result.schema.json"
REGISTRY_PATH = SKILL_ROOT / "schemas" / "public-research-tool-registry.json"
FAILURE_CLASSIFICATION = SKILL_ROOT / "schemas" / "failure-classification.json"

PLAN_MODES = {"plan"}
MAX_FORMAT_RETRIES = 3
MAX_REINFORCEMENT_ROUNDS = 1
# FR-ADP-001: explicit compatibility modes. adapter-validated means local
# Schema/semantic validation is the acceptance authority; provider-native means
# the gateway enforced the Schema at generation time.
ENFORCEMENT_MODES = {"provider-native", "adapter-validated"}


@dataclass
class Finding:
    severity: str
    rule: str
    message: str
    fix: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_schema(schema: dict, data: Any, path: str = "$") -> list[str]:
    """Minimal JSON Schema draft 2020-12 validator."""
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_type_ok(data, t) for t in types):
            return [f"{path}: expected {expected_type}"]
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}")
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema.get("maxLength", float("inf")):
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "minimum" in schema and int(data) < schema["minimum"]:
            errors.append(f"{path}: less than minimum {schema['minimum']}")
        if "maximum" in schema and int(data) > schema.get("maximum", float("inf")):
            errors.append(f"{path}: greater than maximum {schema['maximum']}")
    if isinstance(data, int):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: less than minimum {schema['minimum']}")
        if "maximum" in schema and data > schema.get("maximum", float("inf")):
            errors.append(f"{path}: greater than maximum {schema['maximum']}")
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(data) > schema.get("maxItems", float("inf")):
            errors.append(f"{path}: more than maxItems {schema['maxItems']}")
        if "items" in schema:
            for index, item in enumerate(data):
                errors.extend(validate_schema(schema["items"], item, f"{path}[{index}]"))
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}.{key}: missing required field")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in data:
                errors.extend(validate_schema(subschema, data[key], f"{path}.{key}"))
    return errors


def check_pure_json(raw_text: str) -> tuple[bool, Any, list[Finding]]:
    """Check output is pure UTF-8 JSON without BOM or prose wrapper."""
    findings: list[Finding] = []
    if raw_text.startswith("﻿"):
        findings.append(Finding("P0", "bom-detected", "Output has UTF-8 BOM.", "Remove BOM."))
    stripped = raw_text.lstrip("﻿").strip()
    if not stripped:
        findings.append(Finding("P0", "empty-output", "Output is empty.", "Provide JSON."))
        return False, None, findings
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        findings.append(Finding("P0", "not-json", f"Output is not valid JSON: {exc}", "Fix JSON."))
        return False, None, findings
    if not isinstance(parsed, dict):
        findings.append(Finding("P0", "not-object", "Output is JSON but not an object.", "Provide a JSON object."))
        return False, parsed, findings
    return True, parsed, findings


def check_semantic_gates(data: dict, registry_names: list[str]) -> list[Finding]:
    """Run semantic evidence gates on the parsed research result.

    FR-ADP-001 introduces an explicit ``schemaEnforcementMode``. In
    ``adapter-validated`` mode the local Schema + semantic gates are the
    acceptance authority (FR-ADP-005); the provider-native-only gates
    (toolRegistryMatch, toolCount, mcpSchemaVisible, canaryEvidence) are
    expected to be inherited from the frozen evidence ledger rather than
    enforced as live-native preconditions, so they are checked leniently.
    In ``provider-native`` mode the original strict gates remain.
    """
    findings: list[Finding] = []

    mode = data.get("schemaEnforcementMode")
    provider_native = data.get("providerNativeSchema")
    adapter_validated = mode == "adapter-validated"

    # FR-ADP-001: mode must be explicit and honest.
    if mode not in ENFORCEMENT_MODES:
        findings.append(Finding("P0", "enforcement-mode-missing", "schemaEnforcementMode must be provider-native or adapter-validated.", "Record the explicit compatibility mode."))
    if not isinstance(provider_native, bool):
        findings.append(Finding("P0", "provider-native-schema-missing", "providerNativeSchema must be a boolean.", "Record providerNativeSchema."))
    elif adapter_validated and provider_native is True:
        findings.append(Finding("P0", "silent-native-claim", "adapter-validated mode must record providerNativeSchema=false; provider-native Schema enforcement was not used.", "Set providerNativeSchema=false for adapter-validated mode."))
    elif mode == "provider-native" and provider_native is False:
        findings.append(Finding("P0", "native-mode-mislabeled", "provider-native mode recorded providerNativeSchema=false.", "Set providerNativeSchema=true for provider-native mode."))

    try:
        expected_hash = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
        if data.get("schemaSha256") != expected_hash:
            findings.append(Finding("P0", "schema-hash-mismatch", "schemaSha256 does not match the local schema.", "Regenerate output with the current schema hash."))
    except OSError as exc:
        findings.append(Finding("P1", "schema-hash-unavailable", f"Could not hash schema: {exc}", "Restore the schema file."))

    if data.get("completionClaim") == "complete" and data.get("evidenceComplete") is not True:
        findings.append(Finding("P0", "completion-with-incomplete-evidence", "completionClaim=complete requires evidenceComplete=true.", "Mark partial/blocked or complete evidence."))

    # An evidence-complete result cannot silently close unresolved P0/P1 gaps.
    # The gap arrays are intentionally inspected independently of source
    # verification because coverage defects are a separate completion gate.
    if data.get("completionClaim") == "complete":
        open_gaps: list[str] = []
        for key in ("p0p1Gaps", "gaps"):
            entries = data.get(key, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                severity = str(entry.get("severity") or entry.get("priority") or "").upper()
                if severity in {"P0", "P1"}:
                    open_gaps.append(f"{key}:{severity}:{entry.get('description') or entry.get('gap') or 'unresolved gap'}")
        if open_gaps:
            findings.append(Finding("P0", "completion-with-open-p0p1-gaps", "completionClaim=complete cannot coexist with unresolved P0/P1 gaps.", "Close the gaps, run the bounded reinforcement round, or mark the result partial/blocked."))

    # sessionFresh must be true
    if data.get("sessionFresh") is not True:
        findings.append(Finding("P0", "session-not-fresh", "sessionFresh must be true.", "Declare fresh session."))

    # mode must not be plan
    perm_mode = data.get("permissionMode", "")
    if perm_mode in PLAN_MODES:
        findings.append(Finding("P0", "plan-mode-blocked", "permissionMode is plan.", "Use a non-plan mode."))
    elif perm_mode and perm_mode not in {"acceptEdits", "auto", "default", "dontAsk"}:
        findings.append(Finding("P0", "invalid-mode", f"permissionMode is invalid: {perm_mode}.", "Use a valid mode."))

    # Provider-native-only gates. In adapter-validated mode these are inherited
    # from the frozen ledger; if they are absent the ledger-ref gate below
    # captures it, so we only fail when they are present-but-wrong.
    if adapter_validated:
        # toolRegistryMatch must be true when declared (it reflects the ledger).
        if data.get("toolRegistryMatch") is False:
            findings.append(Finding("P0", "registry-mismatch", "toolRegistryMatch is false.", "Match the registry in the frozen ledger."))
        # toolCount/mcpSchemaVisible/canary are not enforced as live-native gates;
        # but a declared failed canary still blocks (cannot lie about canary).
        canary = data.get("canaryEvidence")
        if isinstance(canary, dict) and canary.get("canaryPassed") is False:
            findings.append(Finding("P0", "canary-failed", "canaryEvidence.canaryPassed is false.", "Fix canary or mark blocked."))
        # FR-ADP-003/004: adapter-validated results must reference a frozen ledger.
        ledger_ref = data.get("evidenceLedgerRef")
        if not isinstance(ledger_ref, dict) or not ledger_ref.get("ledgerId") or not ledger_ref.get("ledgerSha256"):
            findings.append(Finding("P0", "evidence-ledger-missing", "adapter-validated results must reference a frozen evidence ledger.", "Freeze a retrieval evidence ledger before serialization."))
        # FR-ADP-006: adapter validation evidence.
        av = data.get("adapterValidation")
        if isinstance(av, dict):
            if av.get("localSchemaValid") is False:
                findings.append(Finding("P0", "adapter-validation-failed", "adapterValidation.localSchemaValid is false.", "Local Schema validation must pass before complete."))
            if av.get("semanticGatesPassed") is False:
                findings.append(Finding("P0", "adapter-validation-failed", "adapterValidation.semanticGatesPassed is false.", "Semantic gates must pass before complete."))
            if av.get("evidenceHashStable") is False:
                findings.append(Finding("P0", "evidence-hash-unstable", "adapterValidation.evidenceHashStable is false.", "All format attempts must use one unchanged evidence hash."))
    else:
        # provider-native: enforce the original strict gates.
        if data.get("toolRegistryMatch") is not True:
            findings.append(Finding("P0", "registry-mismatch", "toolRegistryMatch must be true.", "Match registry."))
        tool_count = data.get("toolCount", 0)
        if not isinstance(tool_count, int) or tool_count <= 0:
            findings.append(Finding("P0", "tool-count-zero", "toolCount must be > 0.", "Ensure MCP tools are visible."))
        if data.get("mcpSchemaVisible") is not True:
            findings.append(Finding("P0", "mcp-schema-absent", "mcpSchemaVisible must be true.", "Ensure MCP schema visibility."))
        canary = data.get("canaryEvidence")
        if not isinstance(canary, dict) or canary.get("canaryPassed") is not True:
            findings.append(Finding("P0", "canary-failed", "canaryEvidence.canaryPassed must be true.", "Fix canary."))

    # permissionDenials must be 0
    denials = data.get("permissionDenials", 0)
    if denials != 0:
        findings.append(Finding("P0", "permission-denials", f"permissionDenials must be 0, got {denials}.", "Resolve denials."))

    # formatRetries <= 3
    retries = data.get("formatRetries", 0)
    if not isinstance(retries, int) or retries > MAX_FORMAT_RETRIES:
        findings.append(Finding("P1", "format-retry-limit", f"formatRetries must be <= {MAX_FORMAT_RETRIES}.", "Reduce retries."))

    # reinforcementRounds <= 1
    rounds = data.get("reinforcementRounds", 0)
    if not isinstance(rounds, int) or rounds > MAX_REINFORCEMENT_ROUNDS:
        findings.append(Finding("P1", "reinforcement-limit", f"reinforcementRounds must be <= {MAX_REINFORCEMENT_ROUNDS}.", "Reduce rounds."))

    # Source mappings: each claim's sourceUrl must exist in sources
    sources = data.get("sources", [])
    if not isinstance(sources, list) or len(sources) == 0:
        findings.append(Finding("P0", "no-sources", "sources must be a non-empty array.", "Provide sources."))
    else:
        source_urls = set()
        unverified_sources = []
        for src in sources:
            if not isinstance(src, dict):
                findings.append(Finding("P0", "invalid-source", "source must be an object.", "Fix source."))
                continue
            url = src.get("url", "")
            if url:
                source_urls.add(url)
            if not src.get("verified"):
                unverified_sources.append(url)

        # Check claims reference valid source URLs
        claims = data.get("claims", [])
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            claim_url = claim.get("sourceUrl", "")
            if claim_url and claim_url not in source_urls:
                findings.append(Finding("P0", "invalid-source-mapping", f"Claim references unknown source: {claim_url}.", "Fix mapping."))

        # Unverified sources cannot be claimed complete
        evidence_complete = data.get("evidenceComplete", False)
        if unverified_sources and evidence_complete:
            findings.append(Finding("P0", "unverified-complete", "Unverified sources claimed as complete.", "Verify sources or mark incomplete."))

        # All sources must be verified for evidenceComplete
        if evidence_complete and unverified_sources:
            findings.append(Finding("P0", "unverified-sources-claimed-complete", f"Unverified sources: {unverified_sources}.", "Verify all sources."))

    return findings


def validate(raw_text: str) -> dict:
    """Full validation of research output text."""
    findings: list[Finding] = []

    # Load registry
    try:
        registry = load_json(REGISTRY_PATH)
        registry_names = registry.get("toolNames", [])
    except Exception as exc:
        registry_names = []
        findings.append(Finding("P1", "registry-load-failed", f"Could not load registry: {exc}.", "Fix registry."))

    # Check pure JSON
    is_json, parsed, json_findings = check_pure_json(raw_text)
    findings.extend(json_findings)
    if not is_json or parsed is None:
        return _result(findings, False)

    # Schema validation
    try:
        schema = load_json(SCHEMA_PATH)
        schema_errors = validate_schema(schema, parsed)
        for err in schema_errors:
            findings.append(Finding("P0", "schema-violation", err, "Fix field."))
    except Exception as exc:
        findings.append(Finding("P1", "schema-load-failed", f"Could not load schema: {exc}.", "Fix schema."))

    # Semantic gates
    if isinstance(parsed, dict):
        semantic_findings = check_semantic_gates(parsed, registry_names)
        findings.extend(semantic_findings)

    return _result(findings, is_json)


def _result(findings: list[Finding], is_json: bool) -> dict:
    p0 = sum(1 for f in findings if f.severity == "P0")
    p1 = sum(1 for f in findings if f.severity == "P1")
    p2 = sum(1 for f in findings if f.severity == "P2")
    status = "rejected" if p0 > 0 else "review-required" if p1 > 0 else "accepted"
    return {
        "status": status,
        "isJson": is_json,
        "summary": {"P0": p0, "P1": p1, "P2": p2},
        "findings": [f.to_dict() for f in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate research output")
    parser.add_argument("--input", required=True, help="Path to research output JSON file")
    parser.add_argument("--json", dest="json_output", default=None)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        result = {"status": "rejected", "error": f"file not found: {input_path}"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    raw = input_path.read_text(encoding="utf-8", errors="replace")
    result = validate(raw)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(output, encoding="utf-8")
    print(output)
    return 1 if result["summary"]["P0"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
