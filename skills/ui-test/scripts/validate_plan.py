import json
import sys
from pathlib import Path


ALLOWED_OPERATIONS = {
    "aiAct",
    "aiInput",
    "aiTap",
    "aiWaitFor",
    "aiQuery",
    "aiAssert",
}


def validate(plan: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["plan must be a JSON object"]

    for field in ("schemaVersion", "goal", "baseUrl", "module", "policy", "steps"):
        if field not in plan:
            errors.append(f"missing required field: {field}")

    policy = plan.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        if "readOnly" not in policy:
            errors.append("policy.readOnly is required")
        forbidden = policy.get("forbiddenActions")
        if not isinstance(forbidden, list) or not forbidden:
            errors.append("policy.forbiddenActions must be a non-empty array")

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty array")
        return errors

    seen: set[str] = set()
    for index, step in enumerate(steps):
        prefix = f"steps[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("id", "intent", "operation", "expectedResult", "verify", "evidence", "risk"):
            if not step.get(field):
                errors.append(f"{prefix}.{field} is required")
        step_id = step.get("id")
        if step_id in seen:
            errors.append(f"duplicate step id: {step_id}")
        if isinstance(step_id, str):
            seen.add(step_id)
        operation = step.get("operation")
        if operation not in ALLOWED_OPERATIONS:
            errors.append(f"{prefix}.operation is unsupported: {operation}")
        if not isinstance(step.get("verify"), dict):
            errors.append(f"{prefix}.verify must be an object")
        if not isinstance(step.get("evidence"), dict):
            errors.append(f"{prefix}.evidence must be an object")
        if step.get("risk") not in {"auto", "confirm", "forbidden"}:
            errors.append(f"{prefix}.risk must be auto, confirm, or forbidden")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_plan.py <plan.json>")
        return 2
    path = Path(sys.argv[1])
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        print(json.dumps({"valid": False, "errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 1
    errors = validate(plan)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
