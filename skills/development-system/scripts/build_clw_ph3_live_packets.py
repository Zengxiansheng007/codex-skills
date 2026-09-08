"""Build two bounded PH-3 live packets from the approved fixture manifests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "test-runs" / "clw-ph3-runtime-20260817" / "live-repo-001"
POLICY = ROOT / "handoff" / "claude-windows-adaptive-loop-ph3-preauthorization-2026-08-17.json"


def build_packet(slot: dict, policy: dict, index: int) -> dict:
    """Build one live packet without normalizing exact-match policy fields."""
    story_id = f"CLW-LIVE-STORY-{chr(64 + index)}"
    packet_id = f"HND-CLW-PH3-{story_id}-20260817-001"
    write_path = slot["declaredWriteSet"][0]
    feedback_schema = policy["feedbackSchema"]
    packet = {
        "packetId": packet_id,
        "packetType": "handoff",
        "version": "1.0",
        "createdBy": "Codex",
        "targetAgent": "Claude Code",
        "fieldMode": "complete",
        "executionLineage": {"anchorId": "CLW-PH3-CONCURRENCY-REQ-20260817-001", "phaseId": "CLW-PH-3", "storyId": story_id, "cycleId": "CLW-PH3-LIVE-CYCLE-20260817-001", "roundNumber": 1},
        "storyProfile": {"profileId": "CLW-PROFILE-SMALL", "size": "small", "initialTimeoutSeconds": 600, "noProgressTimeoutSeconds": 900, "extensionSliceSeconds": 300, "attemptHardDeadlineSeconds": 1200, "storyTotalDeadlineSeconds": 1800, "maxRounds": 1},
        "runtimeToolRules": ["Read", "Write", "Edit"],
        "stories": [{"storyId": story_id, "title": f"PH-3 live isolated slot {index}", "goal": f"Create only {write_path} in this isolated worktree and return traceable feedback.", "mappedRequirements": ["FR-CLW3-001", "FR-CLW3-003", "FR-CLW3-007"], "acceptanceCriteria": ["AC-CLW3-001", "AC-CLW3-003", "AC-CLW3-008"]}],
        "requirementAnchor": {
            "originalGoal": "Validate two independent Windows Claude slots with Codex-owned integration.",
            "approvedScope": [f"Edit only {write_path} in the assigned worktree", "Return structured feedback", "Do not run shell or Git commands"],
            "nonGoals": ["Merge branches", "Modify shared refs", "Edit the other slot", "Network", "Dependency installation"],
            "frAc": ["FR-CLW3-001", "FR-CLW3-003", "FR-CLW3-007", "AC-CLW3-001", "AC-CLW3-003", "AC-CLW3-008"],
            "confirmedGrillDecisions": ["Two independent Windows worktrees", "Codex-only commit and integration", "No shell or shared ref mutation by Agent"],
            "authorityOrder": ["Codex control plane", "CLW-PH3 requirement anchor", "Claude feedback"],
            "allowedActions": ["Read assigned worktree files", f"Write {write_path}", "Return structured feedback"],
            "forbiddenActions": ["Read or write other slot", "Run PowerShell", "Run Git", "Merge", "Delete", "Network", "Install dependencies", "Claim completion authority"],
            "manualConfirmActions": ["Any workspace, data, tool or network boundary expansion", "User-level installation", "Production, publish, delete, migration or external-message action"],
            "sourceBaseline": ["CLW-PH3-CONCURRENCY-REQ-20260817-001@1.0.0", slot["baselineCommit"]],
            "currentIterationObjective": f"Complete {story_id} in its isolated worktree."
        },
        "requiredAuthorization": {
            "policyId": policy["policyId"], "policyHash": policy["policyHash"], "workspace": slot["worktreePath"],
            "actions": list(policy["actions"]), "tools": list(policy["tools"]),
            "data": list(policy["data"]), "network": list(policy["network"]),
            "credentialBoundary": policy["credentialBoundary"],
            "feedbackSchema": feedback_schema,
            "timeoutSeconds": 1200, "rounds": 1, "concurrency": 2,
            "stopConditions": list(policy["stopConditions"])
        },
        "taskInstructions": [f"Work only in the assigned isolated worktree: {slot['worktreePath']}", f"Create or edit only {write_path} with a short deterministic marker.", "Use only Read, Write and Edit. Do not invoke PowerShell, Git, shell, network or dependencies.", "Return schema-valid feedback with lineage, changedFiles, evidenceRefs and validation results. Codex owns commit, merge and completion."],
        "expectedFeedbackSchema": feedback_schema,
        "stopConditions": ["boundary drift", "invalid feedback", "credential-like output", "hard deadline"],
        "riskGates": ["isolated worktree only", "no shared ref mutation", "Codex completion authority"],
        "iteration": 1
    }
    if packet["requiredAuthorization"]["feedbackSchema"] != feedback_schema or packet["expectedFeedbackSchema"] != feedback_schema:
        raise RuntimeError("feedbackSchema must exactly match the active policy")
    return packet


def main() -> int:
    manifest = json.loads((RUN / "slot-manifests.json").read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    out = ROOT / "handoff"
    out.mkdir(parents=True, exist_ok=True)
    for index, slot in enumerate(manifest["slots"], start=1):
        packet = build_packet(slot, policy, index)
        packet_id = packet["packetId"]
        path = out / f"{packet_id}.json"
        path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
