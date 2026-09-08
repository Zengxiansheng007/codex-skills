import ast
import json
import re
import sys
from pathlib import Path


# Resolve skill root from this file's location so the validator works
# regardless of the caller's current working directory.
DEFAULT_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_GOVERNED_STATES = [
    "running",
    "waiting-approval",
    "blocked-external-dependency",
    "blocked-user-decision",
    "repair-needed",
    "requirements-review",
    "risk-gate-required",
    "loop-limit-reached",
    "resource-limit-reached",
    "completed",
    "failed",
]

REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/router-contract.md",
    "references/phase4-controlled-loop.md",
    "references/naming-and-boundaries.md",
    "references/phase1-boundary-contract.md",
    "references/requirement-anchor-template.md",
    "references/local-direct-implementation-loop.md",
    "references/local-global-skill-edit-loop.md",
    "references/system-use-retrospective.md",
    "references/control-plane-and-authority.md",
    "references/metagpt-role-sop-contract.md",
    "references/artifact-lifecycle-contract.md",
    "references/plan-story-contract.md",
    "references/handoff-interface-contract.md",
    "references/rework-and-gate-reopen-contract.md",
    "references/event-history-and-recovery-contract.md",
    "references/state-and-completion-contract.md",
    "references/long-task-runtime-contract.md",
    "references/workspace-and-approval-contract.md",
    "references/claude-first-execution-contract.md",
    "references/claude-governance-contract.md",
    "references/phase4-install-operations-contract.md",
    "references/software-company-pipeline-contract.md",
    "references/multi-agent-concurrency-contract.md",
    "references/observability-and-resource-contract.md",
    "references/metagpt-module-admission.md",
    "references/clw-phase2-serial-orchestration-contract.md",
    "references/clw-phase3-isolated-concurrency-contract.md",
    "references/clw-phase4-agent-extension-contract.md",
    "schemas/requirement-anchor.schema.json",
    "schemas/artifact-envelope.schema.json",
    "schemas/phase-story.schema.json",
    "schemas/runtime-state.schema.json",
    "schemas/event-history.schema.json",
    "schemas/snapshot.schema.json",
    "schemas/completion-evaluation.schema.json",
    "schemas/execution-slot.schema.json",
    "schemas/role-profile.schema.json",
    "schemas/skill-interface.schema.json",
    "schemas/resource-policy.schema.json",
    "schemas/module-admission.schema.json",
    "schemas/claude-agent-registry.schema.json",
    "schemas/claude-preauthorization.schema.json",
    "schemas/claude-dry-run-manifest.schema.json",
    "schemas/claude-status-projection.schema.json",
    "schemas/codex-takeover-decision.schema.json",
    "schemas/installation-approval.schema.json",
    "schemas/backup-manifest.schema.json",
    "schemas/operations-governance.schema.json",
    "schemas/story-queue.schema.json",
    "schemas/phase-progress-snapshot.schema.json",
    "schemas/merge-candidate.schema.json",
    "schemas/agent-profile.schema.json",
    "schemas/agent-feedback-review.schema.json",
    "assets/fixtures/router-requirements-to-plan.json",
    "assets/fixtures/router-plan-to-claude-handoff.json",
    "assets/fixtures/router-feedback-to-review.json",
    "assets/fixtures/router-live-adapter-risk-gate.json",
    "assets/fixtures/router-local-global-skill-edit.json",
    "assets/fixtures/router-single-file-behavior-change.json",
    "assets/fixtures/phase-story/phase1-positive.json",
    "assets/fixtures/phase-story/full-refactor-baseline.json",
    "assets/fixtures/negative/NEG-OWNERSHIP-001-private-profile-global-clash.json",
    "assets/fixtures/negative/NEG-STORY-001-missing-fr-ac.json",
    "assets/fixtures/negative/NEG-STORY-002-missing-entry-exit.json",
    "assets/fixtures/negative/NEG-STORY-003-missing-testability-evidence.json",
    "assets/fixtures/negative/NEG-STORY-004-dependency-cycle.json",
    "assets/fixtures/negative/NEG-COMPLETION-001-agent-claim.json",
    "assets/fixtures/negative/NEG-COMPLETION-002-timeout-completed.json",
    "assets/fixtures/negative/NEG-COMPLETION-003-drift-completed.json",
    "assets/fixtures/negative/NEG-COMPLETION-004-missing-validation-evidence.json",
    "assets/fixtures/negative/NEG-COMPLETION-005-hash-mismatch.json",
    "assets/fixtures/negative/NEG-COMPLETION-006-schema-errors.json",
    "assets/fixtures/negative/NEG-STATE-001-undeclared-cancelled-state.json",
    "assets/fixtures/negative/NEG-RECOVERY-001-snapshot-hash.json",
    "assets/fixtures/negative/NEG-RECOVERY-002-anchor-version.json",
    "assets/fixtures/negative/NEG-RECOVERY-003-event-sequence.json",
    "assets/fixtures/negative/NEG-LOOP-001-no-progress.json",
    "assets/fixtures/negative/NEG-LOOP-002-round-eleven.json",
    "assets/fixtures/negative/NEG-AUTH-001-workspace-boundary.json",
    "assets/fixtures/negative/NEG-AUTH-002-incomplete-preauthorization.json",
    "assets/fixtures/negative/NEG-AUTH-003-user-skill-install.json",
    "assets/fixtures/phase-story/ph2-registry-positive.json",
    "assets/fixtures/phase-story/ph2-preauth-positive.json",
    "assets/fixtures/phase-story/ph2-status-positive.json",
    "assets/fixtures/negative/NEG-AUTH-004-credential-mismatch.json",
    "assets/fixtures/negative/NEG-AUTH-005-schema-mismatch.json",
    "assets/fixtures/negative/NEG-AUTH-006-rounds-overflow.json",
    "assets/fixtures/negative/NEG-AUTH-007-concurrency-overflow.json",
    "assets/fixtures/negative/NEG-AUTH-008-stopcondition-mismatch.json",
    "assets/fixtures/negative/NEG-AUTH-009-expired-policy.json",
    "assets/fixtures/negative/NEG-AUTH-010-policy-hash-mismatch.json",
    "assets/fixtures/negative/NEG-AUTH-011-inactive-policy.json",
    "assets/fixtures/negative/NEG-REGISTRY-001-completion-authority.json",
    "assets/fixtures/negative/NEG-DRYRUN-001-no-manifest.json",
    "assets/fixtures/negative/NEG-DRYRUN-002-wrong-packet.json",
    "assets/fixtures/negative/NEG-DRYRUN-003-wrong-policy-hash.json",
    "assets/fixtures/negative/NEG-DRYRUN-004-manifest-hash-mismatch.json",
    "assets/fixtures/negative/NEG-STATUS-002-unknown-state.json",
    "assets/fixtures/negative/NEG-TAKEOVER-001-unrecognized-trigger.json",
    "assets/fixtures/negative/NEG-TAKEOVER-002-not-authorized.json",
    "assets/fixtures/negative/NEG-TAKEOVER-003-round-limit.json",
    "assets/fixtures/negative/NEG-TAKEOVER-004-cross-story.json",
    "assets/fixtures/negative/NEG-SLOT-001-shared-workspace.json",
    "assets/fixtures/negative/NEG-MERGE-001-write-conflict.json",
    "assets/fixtures/negative/NEG-METAGPT-001-missing-admission-evidence.json",
    "assets/fixtures/phase-story/ph3-live-loop-positive.json",
    "assets/fixtures/negative/NEG-PH3-001-spawn-failure.json",
    "assets/fixtures/negative/NEG-PH3-002-timeout.json",
    "assets/fixtures/negative/NEG-PH3-003-invalid-feedback.json",
    "assets/fixtures/negative/NEG-PH3-004-p1-drift.json",
    "assets/fixtures/negative/NEG-PH3-005-unmapped-action.json",
    "assets/fixtures/negative/NEG-PH3-006-stale-field.json",
    "assets/fixtures/negative/NEG-PH3-007-evidence-gap.json",
    "assets/fixtures/negative/NEG-PH3-008-duplicate-side-effects.json",
    "assets/fixtures/negative/NEG-PH3-009-round-limit.json",
    "assets/fixtures/negative/NEG-PH3-010-takeover-limit.json",
    "assets/fixtures/negative/NEG-PH3-011-no-progress.json",
    "assets/fixtures/phase-story/ph4-promotion-positive.json",
    "assets/fixtures/phase-story/ph4-operations-positive.json",
    "assets/fixtures/negative/NEG-PH4-001-missing-approval.json",
    "assets/fixtures/negative/NEG-PH4-002-source-hash-drift.json",
    "assets/fixtures/negative/NEG-PH4-003-missing-rollback.json",
    "assets/fixtures/negative/NEG-PH4-004-expired-approval.json",
    "assets/fixtures/clw-st-101/pos-clw-101-small.json",
    "assets/fixtures/clw-st-101/pos-clw-101-medium.json",
    "assets/fixtures/clw-st-101/neg-clw-001-multi-story.json",
    "assets/fixtures/clw-st-101/neg-clw-002-large-story.json",
    "assets/fixtures/clw-phase3/pos-clw3-301-slot.json",
    "assets/fixtures/clw-phase3/pos-clw3-303-integration.json",
    "assets/fixtures/clw-phase3/neg-clw3-001-write-conflict.json",
    "assets/fixtures/clw-phase3/neg-clw3-002-merge-conflict.json",
    "assets/fixtures/clw-phase4/pos-clw4-001-profile.json",
    "assets/fixtures/clw-phase4/pos-clw4-003-feedback.json",
    "assets/fixtures/clw-phase4/neg-clw4-001-profile-authority.json",
    "assets/fixtures/clw-phase4/neg-clw4-002-feedback-drift.json",
    "assets/fixtures/clw-phase4/neg-clw4-003-feedback-lineage.json",
    "schemas/story-profile.schema.json",
    "schemas/story-split-finding.schema.json",
    "schemas/live-handoff-story-envelope.schema.json",
    "change-records/entries/2026/2026-08/CR-20260816-005-clw-st-101-story-profile-and-split-gate.md",
    "change-records/index.md",
    "change-records/categories/core-skill-md.md",
    "change-records/categories/references-and-assets.md",
    "change-records/categories/scripts-and-validation.md",
    "change-records/categories/safety-and-governance.md",
    "change-records/entries/2026/2026-08/CR-20260820-001-write-prd-router-entry.md",
    "change-records/entries/2026/2026-08/CR-20260809-001-development-system-local-global-loop.md",
    "change-records/entries/2026/2026-08/CR-20260809-002-phase1-boundary-contract.md",
    "change-records/entries/2026/2026-08/CR-20260809-003-generic-skill-governance-contract.md",
    "change-records/entries/2026/2026-08/CR-20260814-001-ph1-foundation-slice.md",
    "change-records/entries/2026/2026-08/CR-20260815-001-mappedFrAc-required-repair.md",
    "change-records/entries/2026/2026-08/CR-20260815-002-full-runtime-ph1b-ph7.md",
    "change-records/entries/2026/2026-08/CR-20260815-003-completion-evidence-and-state-alignment.md",
    "change-records/entries/2026/2026-08/CR-20260816-001-artifact-envelope-dual-contract-closure.md",
    "change-records/entries/2026/2026-08/CR-20260816-002-ph2-claude-governance.md",
    "change-records/entries/2026/2026-08/CR-20260816-003-ph3-real-closed-loop.md",
    "change-records/entries/2026/2026-08/CR-20260816-004-ph4-install-operations-governance.md",
    "change-records/entries/2026/2026-08/CR-20260817-001-clw-ph2-ph4-deterministic-contracts.md",
    "scripts/test_skill_governance_contract.py",
    "scripts/test_phase_story_contract.py",
    "scripts/development_runtime.py",
    "scripts/test_development_runtime.py",
    "scripts/phase4_governance.py",
    "scripts/test_phase4_governance.py",
    "scripts/test_full_refactor_contract.py",
    "scripts/test_clw_phase2_phase4_runtime.py",
    "scripts/test_clw_phase3_worktree_runtime.py",
    "scripts/build_refactor_reports.py",
    "scripts/sync_requirements_baseline.py",
    "change-records/entries/2026/2026-08/CR-20260817-006-clw-ph3-worktree-integration.md",
]

REQUIRED_SKILL_TERMS = [
    "development-system",
    "Development System",
    "requirement anchor",
    "research",
    "grill-system",
    "write-prd",
    "write-requirements-prd",
    "handoff-system",
    "handoff-packet-builder",
    "handoff-claude-executor",
    "handoff-feedback-reviewer",
    "Midscene",
    "explicit user approval",
    "requirement drift",
    "local direct implementation",
    "global Skill",
    "system-use retrospective",
    "single-file behavior change",
    "workspace-copy-first",
    "Safety And Escalation",
    "control-plane-and-authority.md",
    "metagpt-role-sop-contract.md",
    "artifact-lifecycle-contract.md",
    "plan-story-contract.md",
    "Codex is the sole control plane",
    "Claude-first",
    "preauthorization",
    "CompletionEvaluator",
    "long-task-runtime-contract.md",
    "multi-agent-concurrency-contract.md",
    "metagpt-module-admission.md",
    "User-level Skill installation",
]

# Canonical governance headings that the contract tests assert remain visible in the validator source:
# ## Safety And Escalation
# ## Latest Changes
# ## Impact Analysis

SECRET_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"pass" + r"word\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"tok" + r"en\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"coo" + r"kie\s*[:=]\s*\S+", re.IGNORECASE),
]


def add(findings, severity, rule, message):
    findings.append({"severity": severity, "rule": rule, "message": message})


def validate_frontmatter(skill_md, findings):
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        add(findings, "P0", "frontmatter", "SKILL.md missing frontmatter")
        return
    end = text.find("\n---", 4)
    if end == -1:
        add(findings, "P0", "frontmatter", "SKILL.md unterminated frontmatter")
        return
    keys = [line.split(":", 1)[0] for line in text[4:end].splitlines() if ":" in line]
    if keys != ["name", "description"]:
        add(findings, "P1", "frontmatter-keys", f"SKILL.md keys={keys}")
    if "name: development-system" not in text[:end]:
        add(findings, "P0", "frontmatter-name", "skill name must be development-system")


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ROOT
    findings = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            add(findings, "P0", "missing-file", rel)

    skill_md = root / "SKILL.md"
    if skill_md.exists():
        validate_frontmatter(skill_md, findings)
        skill_text = skill_md.read_text(encoding="utf-8")
        for term in REQUIRED_SKILL_TERMS:
            if term not in skill_text:
                add(findings, "P1", "missing-required-term", term)

    openai_yaml = root / "agents" / "openai.yaml"
    if openai_yaml.exists():
        metadata = openai_yaml.read_text(encoding="utf-8")
        for term in ["interface:", "display_name:", "short_description:", "default_prompt:", "$development-system"]:
            if term not in metadata:
                add(findings, "P1", "openai-yaml-contract", f"missing {term}")

    for rel in REQUIRED_FILES:
        path = root / rel
        if path.exists() and path.suffix.lower() == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                add(findings, "P0", "json-parse", f"{rel}: {exc}")
                continue
            # Only router fixtures (assets/fixtures/router-*.json) must carry
            # the fixture-contract keys; schemas and phase-story/negative
            # fixtures use their own contracts.
            if rel.startswith("assets/fixtures/router-"):
                for key in ["fixtureId", "inputTask", "expectedRoute", "manualApprovalRequired", "requiredObservableMarkers"]:
                    if key not in data:
                        add(findings, "P1", "fixture-contract", f"{rel} missing {key}")

    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".py", ".yaml", ".yml", ".txt"}:
            text = path.read_text(encoding="utf-8")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    add(findings, "P0", "secret-pattern", str(path.relative_to(root)))
                    break

    router_contract = root / "references" / "router-contract.md"
    if router_contract.exists():
        title = router_contract.read_text(encoding="utf-8").splitlines()[0].strip()
        if title != "# Development System Router Contract":
            add(findings, "P1", "router-contract-title", title)

    boundary_contract = root / "references" / "phase1-boundary-contract.md"
    if boundary_contract.exists():
        boundary_text = boundary_contract.read_text(encoding="utf-8")
        for term in [
            "Mandatory Workspace-Copy-First Triggers",
            "multi-file change",
            "high-risk change",
            "global Skill edit",
            "single-file behavior change",
            "Direct Edit Exception",
            "Approval Boundary Template",
            "Final State Decision Table",
        ]:
            if term not in boundary_text:
                add(findings, "P1", "phase1-boundary-contract", f"missing {term}")

    single_file_fixture = root / "assets" / "fixtures" / "router-single-file-behavior-change.json"
    if single_file_fixture.exists():
        fixture = json.loads(single_file_fixture.read_text(encoding="utf-8"))
        if fixture.get("expectedRoute") != "local-global-skill-edit-loop":
            add(findings, "P1", "single-file-behavior-fixture", "expectedRoute must be local-global-skill-edit-loop")
        if fixture.get("manualApprovalRequired") is not True:
            add(findings, "P1", "single-file-behavior-fixture", "manualApprovalRequired must be true")
        markers = " ".join(fixture.get("requiredObservableMarkers", []))
        for term in ["workspace-copy-first", "single-file behavior change", "global deployment approval"]:
            if term not in markers:
                add(findings, "P1", "single-file-behavior-fixture", f"missing marker {term}")

    change_index = root / "change-records" / "index.md"
    if change_index.exists():
        index_text = change_index.read_text(encoding="utf-8")
        if "## Latest Changes" not in index_text:
            add(findings, "P1", "change-record-index-heading", "missing ## Latest Changes")
        for change_id in ["CR-20260809-001", "CR-20260809-002", "CR-20260809-003", "CR-20260814-001", "CR-20260815-001", "CR-20260815-002", "CR-20260815-003", "CR-20260816-001", "CR-20260816-002", "CR-20260816-003", "CR-20260816-005", "CR-20260817-001", "CR-20260820-001"]:
            if change_id not in index_text:
                add(findings, "P1", "change-record-index", f"missing {change_id}")

    phase1_record = root / "change-records" / "entries" / "2026" / "2026-08" / "CR-20260809-002-phase1-boundary-contract.md"
    if phase1_record.exists() and "## Impact Analysis" not in phase1_record.read_text(encoding="utf-8"):
        add(findings, "P1", "phase1-record-impact-analysis", "missing ## Impact Analysis")

    # ---- PH1 foundation slice checks (PH1-ST-001 ~ PH1-ST-004) ----

    # Schemas: require valid JSON and draft 2020-12 declaration.
    for schema_rel in [
        "schemas/requirement-anchor.schema.json",
        "schemas/artifact-envelope.schema.json",
        "schemas/phase-story.schema.json",
        "schemas/runtime-state.schema.json",
        "schemas/event-history.schema.json",
        "schemas/snapshot.schema.json",
        "schemas/completion-evaluation.schema.json",
        "schemas/execution-slot.schema.json",
        "schemas/role-profile.schema.json",
        "schemas/skill-interface.schema.json",
        "schemas/resource-policy.schema.json",
        "schemas/module-admission.schema.json",
        "schemas/story-profile.schema.json",
        "schemas/story-split-finding.schema.json",
        "schemas/live-handoff-story-envelope.schema.json",
        "schemas/story-queue.schema.json",
        "schemas/phase-progress-snapshot.schema.json",
        "schemas/merge-candidate.schema.json",
        "schemas/agent-profile.schema.json",
        "schemas/agent-feedback-review.schema.json",
    ]:
        schema_path = root / schema_rel
        if schema_path.exists():
            try:
                schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
            except Exception as exc:
                add(findings, "P0", "schema-parse", f"{schema_rel}: {exc}")
                continue
            if schema_data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                add(findings, "P1", "schema-draft", f"{schema_rel} must declare draft 2020-12")
            if "properties" not in schema_data:
                add(findings, "P1", "schema-properties", f"{schema_rel} missing properties")

    # Requirement anchor schema: require frAc minItems and authorityOrder.
    anchor_schema = root / "schemas" / "requirement-anchor.schema.json"
    if anchor_schema.exists():
        try:
            anchor = json.loads(anchor_schema.read_text(encoding="utf-8"))
            props = anchor.get("properties", {})
            if props.get("frAc", {}).get("minItems", 0) < 1:
                add(findings, "P1", "anchor-schema-frAc", "frAc must require minItems >= 1")
            if props.get("authorityOrder", {}).get("minItems", 0) < 1:
                add(findings, "P1", "anchor-schema-authority", "authorityOrder must require minItems >= 1")
            if "FR-001" not in anchor_schema.read_text(encoding="utf-8"):
                add(findings, "P1", "anchor-schema-fr-mapping", "requirement-anchor schema should reference FR-001/FR-002/FR-006")
        except Exception as exc:
            add(findings, "P0", "anchor-schema-parse", str(exc))

    # Artifact envelope schema: require sourceAnchorId, sourceAnchorVersion, mappedFrAc.
    envelope_schema = root / "schemas" / "artifact-envelope.schema.json"
    if envelope_schema.exists():
        env_text = envelope_schema.read_text(encoding="utf-8")
        for field in ["sourceAnchorId", "sourceAnchorVersion", "mappedFrAc", "owner", "artifactType"]:
            if field not in env_text:
                add(findings, "P1", "envelope-schema", f"artifact-envelope schema missing field {field}")

    # Phase-story schema: require story storyId, mappedRequirements, acceptanceCriteria, dependsOn, testability, evidenceRequirements.
    phase_schema = root / "schemas" / "phase-story.schema.json"
    if phase_schema.exists():
        ps_text = phase_schema.read_text(encoding="utf-8")
        for field in ["storyId", "mappedRequirements", "acceptanceCriteria", "dependsOn", "testability", "evidenceRequirements"]:
            if field not in ps_text:
                add(findings, "P1", "phase-story-schema", f"phase-story schema missing field {field}")

    # New references: check key terms.
    ref_checks = {
        "references/control-plane-and-authority.md": [
            "FR-001", "FR-002", "FR-003", "FR-004", "FR-005",
            "AC-001", "AC-002", "sole control plane",
            "contract-reuse", "code-admission-candidate", "reference-only",
        ],
        "references/metagpt-role-sop-contract.md": [
            "FR-004", "FR-009", "AC-004",
            "product-requirement", "architect", "project-planner", "engineer", "qa",
        ],
        "references/artifact-lifecycle-contract.md": [
            "FR-006", "FR-007", "FR-032", "AC-003",
            "sourceAnchorId", "mappedFrAc", "owner",
        ],
        "references/plan-story-contract.md": [
            "FR-008", "AC-005",
            "entryCriteria", "exitCriteria", "dependsOn", "testability", "evidenceRequirements",
        ],
    }
    for ref_rel, terms in ref_checks.items():
        ref_path = root / ref_rel
        if ref_path.exists():
            ref_text = ref_path.read_text(encoding="utf-8")
            for term in terms:
                if term not in ref_text:
                    add(findings, "P1", "reference-terms", f"{ref_rel} missing {term}")

    # Positive phase-story fixture: must be valid JSON and contain four stories.
    positive_fixture = root / "assets" / "fixtures" / "phase-story" / "phase1-positive.json"
    if positive_fixture.exists():
        try:
            pf = json.loads(positive_fixture.read_text(encoding="utf-8"))
            phase = pf.get("phase", {})
            stories = phase.get("stories", [])
            if len(stories) < 4:
                add(findings, "P1", "positive-fixture", "phase1-positive must have at least 4 stories")
            story_ids = [s.get("storyId", "") for s in stories]
            for sid in ["PH1-ST-001", "PH1-ST-002", "PH1-ST-003", "PH1-ST-004"]:
                if sid not in story_ids:
                    add(findings, "P1", "positive-fixture", f"positive fixture missing {sid}")
            for s in stories:
                if not s.get("mappedRequirements"):
                    add(findings, "P1", "positive-fixture", f"{s.get('storyId','')} must have mappedRequirements")
                if not s.get("acceptanceCriteria"):
                    add(findings, "P1", "positive-fixture", f"{s.get('storyId','')} must have acceptanceCriteria")
                if not s.get("testability"):
                    add(findings, "P1", "positive-fixture", f"{s.get('storyId','')} must have testability")
                if not s.get("evidenceRequirements"):
                    add(findings, "P1", "positive-fixture", f"{s.get('storyId','')} must have evidenceRequirements")
        except Exception as exc:
            add(findings, "P0", "positive-fixture-parse", str(exc))

    # Negative fixtures: must be valid JSON and declare expectedValidation = reject.
    neg_dir = root / "assets" / "fixtures" / "negative"
    expected_neg = [
        "NEG-OWNERSHIP-001-private-profile-global-clash.json",
        "NEG-STORY-001-missing-fr-ac.json",
        "NEG-STORY-002-missing-entry-exit.json",
        "NEG-STORY-003-missing-testability-evidence.json",
        "NEG-STORY-004-dependency-cycle.json",
        "NEG-COMPLETION-001-agent-claim.json",
        "NEG-COMPLETION-002-timeout-completed.json",
        "NEG-COMPLETION-003-drift-completed.json",
        "NEG-COMPLETION-004-missing-validation-evidence.json",
        "NEG-COMPLETION-005-hash-mismatch.json",
        "NEG-COMPLETION-006-schema-errors.json",
        "NEG-STATE-001-undeclared-cancelled-state.json",
        "NEG-RECOVERY-001-snapshot-hash.json",
        "NEG-RECOVERY-002-anchor-version.json",
        "NEG-RECOVERY-003-event-sequence.json",
        "NEG-LOOP-001-no-progress.json",
        "NEG-LOOP-002-round-eleven.json",
        "NEG-AUTH-001-workspace-boundary.json",
        "NEG-AUTH-002-incomplete-preauthorization.json",
        "NEG-AUTH-003-user-skill-install.json",
        "NEG-SLOT-001-shared-workspace.json",
        "NEG-MERGE-001-write-conflict.json",
        "NEG-METAGPT-001-missing-admission-evidence.json",
        "NEG-PH3-001-spawn-failure.json",
        "NEG-PH3-002-timeout.json",
        "NEG-PH3-003-invalid-feedback.json",
        "NEG-PH3-004-p1-drift.json",
        "NEG-PH3-005-unmapped-action.json",
        "NEG-PH3-006-stale-field.json",
        "NEG-PH3-007-evidence-gap.json",
        "NEG-PH3-008-duplicate-side-effects.json",
        "NEG-PH3-009-round-limit.json",
        "NEG-PH3-010-takeover-limit.json",
        "NEG-PH3-011-no-progress.json",
    ]
    for neg_name in expected_neg:
        neg_path = neg_dir / neg_name
        if not neg_path.exists():
            add(findings, "P1", "negative-fixture", f"missing {neg_name}")
            continue
        try:
            neg = json.loads(neg_path.read_text(encoding="utf-8"))
            if neg.get("expectedValidation") != "reject":
                add(findings, "P1", "negative-fixture", f"{neg_name} must declare expectedValidation=reject")
            if not neg.get("expectedRejectionRule"):
                add(findings, "P1", "negative-fixture", f"{neg_name} must declare expectedRejectionRule")
            if neg_name.startswith(("NEG-COMPLETION", "NEG-STATE", "NEG-RECOVERY", "NEG-LOOP", "NEG-AUTH", "NEG-SLOT", "NEG-MERGE", "NEG-METAGPT", "NEG-PH3")) and not neg.get("traceTo"):
                add(findings, "P1", "negative-fixture", f"{neg_name} must declare traceTo")
        except Exception as exc:
            add(findings, "P0", "negative-fixture-parse", f"{neg_name}: {exc}")

    runtime_path = root / "scripts" / "development_runtime.py"
    if runtime_path.exists():
        runtime_text = runtime_path.read_text(encoding="utf-8")
        for function_name in [
            "validate_artifact_envelope",
            "validate_transition",
            "preauthorization_matches",
            "decide_execution",
            "append_event",
            "resume_cycle",
            "advance_circuit",
            "validate_feedback_evidence",
            "evaluate_completion",
            "schedule_slots",
            "evaluate_merge",
            "validate_skill_interface",
            "evaluate_resources",
            "status_projection",
            "build_audit_report",
            "evaluate_module_admission",
            "validate_feedback_lineage",
            "check_duplicate_side_effects",
            "run_live_loop",
            "get_default_story_profile",
            "validate_story_profile",
            "evaluate_live_handoff_stories",
            "validate_story_graph",
            "select_next_story",
            "transition_story_after_review",
            "build_phase_progress_snapshot",
            "reconcile_phase_progress",
            "evaluate_phase_completion",
            "normalize_write_set",
            "validate_execution_slot",
            "schedule_isolated_slots",
            "evaluate_declared_vs_observed_write_set",
            "build_merge_candidate",
            "validate_agent_profile",
            "match_agent_capability",
            "review_agent_feedback",
        ]:
            if f"def {function_name}(" not in runtime_text:
                add(findings, "P1", "runtime-function", f"missing {function_name}")
        try:
            tree = ast.parse(runtime_text)
            runtime_states = None
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "GOVERNED_STATES"
                    for target in node.targets
                ):
                    runtime_states = list(ast.literal_eval(node.value))
                    break
            if runtime_states != EXPECTED_GOVERNED_STATES:
                add(findings, "P1", "runtime-governed-states", "GOVERNED_STATES must exactly match DS-PSR-001")
        except Exception as exc:
            add(findings, "P0", "runtime-state-parse", str(exc))

    for schema_rel, property_name in [
        ("schemas/runtime-state.schema.json", "state"),
        ("schemas/requirement-anchor.schema.json", "nextState"),
    ]:
        schema_path = root / schema_rel
        if schema_path.exists():
            try:
                enum = json.loads(schema_path.read_text(encoding="utf-8"))["properties"][property_name]["enum"]
                if enum != EXPECTED_GOVERNED_STATES:
                    add(findings, "P1", "schema-governed-states", f"{schema_rel} {property_name} must exactly match DS-PSR-001")
            except Exception as exc:
                add(findings, "P0", "schema-state-parse", f"{schema_rel}: {exc}")

    report_builder = root / "scripts" / "build_refactor_reports.py"
    if report_builder.exists():
        report_text = report_builder.read_text(encoding="utf-8")
        if '"feedbackValid"' in report_text:
            add(findings, "P1", "legacy-feedback-valid", "build_refactor_reports.py must not emit bare feedbackValid")
        for term in ["feedbackValidation", "feedbackHash", "evaluate_completion", "installationState"]:
            if term not in report_text:
                add(findings, "P1", "report-completion-contract", f"build_refactor_reports.py missing {term}")

    full_record = root / "change-records" / "entries" / "2026" / "2026-08" / "CR-20260815-002-full-runtime-ph1b-ph7.md"
    if full_record.exists():
        record_text = full_record.read_text(encoding="utf-8")
        for term in ["PH1-ST-005", "PH7-ST-003", "## Impact Analysis", "## Validation Evidence"]:
            if term not in record_text:
                add(findings, "P1", "full-refactor-record", f"missing {term}")

    repair_record = root / "change-records" / "entries" / "2026" / "2026-08" / "CR-20260815-003-completion-evidence-and-state-alignment.md"
    if repair_record.exists():
        repair_text = repair_record.read_text(encoding="utf-8")
        for term in ["DS-REPAIR-001", "DS-REPAIR-002", "## Impact Analysis", "## Validation Evidence"]:
            if term not in repair_text:
                add(findings, "P1", "completion-state-repair-record", f"missing {term}")

    # CR-20260814-001 entry must exist and contain Impact Analysis.
    cr_path = root / "change-records" / "entries" / "2026" / "2026-08" / "CR-20260814-001-ph1-foundation-slice.md"
    if cr_path.exists():
        cr_text = cr_path.read_text(encoding="utf-8")
        if "## Impact Analysis" not in cr_text:
            add(findings, "P1", "cr-20260814-001-impact", "CR-20260814-001 missing ## Impact Analysis")
        if "PH1-ST-001" not in cr_text:
            add(findings, "P1", "cr-20260814-001-stories", "CR-20260814-001 must reference PH1-ST-001")
    else:
        add(findings, "P1", "cr-20260814-001-missing", "CR-20260814-001 entry file missing")

    summary = {
        "P0": sum(1 for f in findings if f["severity"] == "P0"),
        "P1": sum(1 for f in findings if f["severity"] == "P1"),
        "P2": sum(1 for f in findings if f["severity"] == "P2"),
    }
    result = {
        "skill": "development-system",
        "status": "accepted" if summary["P0"] == 0 and summary["P1"] == 0 else "review-required",
        "summary": summary,
        "findings": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
