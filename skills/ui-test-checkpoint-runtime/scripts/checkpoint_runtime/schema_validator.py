from __future__ import annotations

from typing import Any


class SchemaValidationError(ValueError):
    def __init__(self, schema_id: str, errors: list[dict[str, str]]):
        self.schema_id = schema_id
        self.errors = errors
        summary = "; ".join(f"{item['path']}: {item['message']}" for item in errors)
        super().__init__(f"{schema_id} validation failed: {summary}")


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate(schema: dict[str, Any], data: Any, path: str, errors: list[dict[str, str]]) -> None:
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_type_ok(data, item) for item in expected):
            errors.append({"path": path, "message": f"expected one of {expected!r}"})
            return
    elif isinstance(expected, str) and not _type_ok(data, expected):
        errors.append({"path": path, "message": f"expected {expected}"})
        return

    if "const" in schema and data != schema["const"]:
        errors.append({"path": path, "message": f"expected const {schema['const']!r}"})
    if "enum" in schema and data not in schema["enum"]:
        errors.append({"path": path, "message": f"expected one of {schema['enum']!r}"})
    if isinstance(data, str) and schema.get("minLength") and len(data) < schema["minLength"]:
        errors.append({"path": path, "message": f"shorter than minLength {schema['minLength']}"})
    if isinstance(data, list) and schema.get("minItems") and len(data) < schema["minItems"]:
        errors.append({"path": path, "message": f"fewer than minItems {schema['minItems']}"})

    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append({"path": f"{path}.{key}", "message": "missing required field"})
        props = schema.get("properties", {})
        for key, value in data.items():
            if key in props:
                _validate(props[key], value, f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append({"path": f"{path}.{key}", "message": "additional property is not allowed"})
    if isinstance(data, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(data):
            _validate(schema["items"], item, f"{path}[{index}]", errors)


def validate_payload(schema: dict[str, Any], data: Any, schema_id: str) -> None:
    errors: list[dict[str, str]] = []
    _validate(schema, data, "$", errors)
    if errors:
        raise SchemaValidationError(schema_id, errors)
