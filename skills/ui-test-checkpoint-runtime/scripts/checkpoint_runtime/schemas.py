from __future__ import annotations

from typing import Any


NON_EMPTY_STRING = {"type": "string", "minLength": 1}
STRING_ARRAY = {"type": "array", "items": NON_EMPTY_STRING}
RISK_V1 = {"enum": ["R0", "R1"]}


REGISTRY_INDEX: dict[str, Any] = {
    "$id": "checkpoint-runtime.registry.v1",
    "type": "object",
    "required": ["schema_version", "generated_at", "systems"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": "checkpoint-runtime.registry.v1"},
        "generated_at": NON_EMPTY_STRING,
        "systems": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["system_id", "system_name", "manifest_ref", "status", "modules_count"],
                "additionalProperties": False,
                "properties": {
                    "system_id": NON_EMPTY_STRING,
                    "system_name": NON_EMPTY_STRING,
                    "manifest_ref": NON_EMPTY_STRING,
                    "status": {"enum": ["active", "stale", "blocked"]},
                    "modules_count": {"type": "integer"},
                    "last_verified_at": {"type": ["string", "null"]},
                },
            },
        },
    },
}

SYSTEM_MANIFEST: dict[str, Any] = {
    "$id": "checkpoint-runtime.system-manifest.v1",
    "type": "object",
    "required": ["schema_version", "system_id", "system_name", "environment_aliases", "default_role_account_type", "modules", "risk_allowlist", "forbidden_actions"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": "checkpoint-runtime.system-manifest.v1"},
        "system_id": NON_EMPTY_STRING,
        "system_name": NON_EMPTY_STRING,
        "environment_aliases": STRING_ARRAY,
        "default_role_account_type": NON_EMPTY_STRING,
        "modules": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["module_id", "manifest_ref"],
                "additionalProperties": False,
                "properties": {"module_id": NON_EMPTY_STRING, "manifest_ref": NON_EMPTY_STRING},
            },
        },
        "risk_allowlist": {"type": "array", "items": RISK_V1},
        "forbidden_actions": STRING_ARRAY,
    },
}

MODULE_MANIFEST: dict[str, Any] = {
    "$id": "checkpoint-runtime.module-manifest.v1",
    "type": "object",
    "required": ["schema_version", "system_id", "module_id", "module_name", "environment_alias", "base_url", "route_hints", "module_assertions", "role_account_types", "auth_ref", "entry_chain", "function_buttons"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": "checkpoint-runtime.module-manifest.v1"},
        "system_id": NON_EMPTY_STRING,
        "module_id": NON_EMPTY_STRING,
        "module_name": NON_EMPTY_STRING,
        "environment_alias": NON_EMPTY_STRING,
        "base_url": NON_EMPTY_STRING,
        "route_hints": STRING_ARRAY,
        "module_assertions": {
            "type": "object",
            "required": ["title_contains", "url_contains", "visible_text"],
            "additionalProperties": False,
            "properties": {
                "title_contains": NON_EMPTY_STRING,
                "url_contains": NON_EMPTY_STRING,
                "visible_text": NON_EMPTY_STRING,
            },
        },
        "role_account_types": STRING_ARRAY,
        "auth_ref": NON_EMPTY_STRING,
        "entry_chain": STRING_ARRAY,
        "function_buttons": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["button_id", "button_name", "checkpoint_ref", "risk_level", "allowed_action", "forbidden_actions"],
                "additionalProperties": False,
                "properties": {
                    "button_id": NON_EMPTY_STRING,
                    "button_name": NON_EMPTY_STRING,
                    "checkpoint_ref": NON_EMPTY_STRING,
                    "risk_level": RISK_V1,
                    "allowed_action": NON_EMPTY_STRING,
                    "forbidden_actions": STRING_ARRAY,
                    "locator": {
                        "type": "object",
                        "required": ["strategy", "value"],
                        "additionalProperties": False,
                        "properties": {
                            "strategy": {"enum": ["role", "text", "test_id", "css"]},
                            "role": {"type": ["string", "null"]},
                            "value": NON_EMPTY_STRING,
                            "exact": {"type": "boolean"},
                        },
                    },
                    "result_assertions": {
                        "type": "object",
                        "required": ["url_contains", "visible_text"],
                        "additionalProperties": False,
                        "properties": {
                            "url_contains": NON_EMPTY_STRING,
                            "visible_text": NON_EMPTY_STRING,
                        },
                    },
                },
            },
        },
        "readonly_post_signatures": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["method", "path_sha256", "content_type", "query_keys", "body_keys", "max_requests_per_session"],
                "additionalProperties": False,
                "properties": {
                    "method": {"const": "POST"},
                    "path_sha256": {"type": "string", "minLength": 64, "maxLength": 64},
                    "content_type": NON_EMPTY_STRING,
                    "query_keys": STRING_ARRAY,
                    "body_keys": STRING_ARRAY,
                    "legacy_payload_keys": STRING_ARRAY,
                    "max_requests_per_session": {"type": "integer", "minimum": 1, "maximum": 4},
                },
            },
        },
    },
}

CHECKPOINT_INDEX: dict[str, Any] = {
    "$id": "checkpoint-runtime.checkpoint-index.v1",
    "type": "object",
    "required": ["schema_version", "system_id", "module_id", "checkpoints"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": "checkpoint-runtime.checkpoint-index.v1"},
        "system_id": NON_EMPTY_STRING,
        "module_id": NON_EMPTY_STRING,
        "checkpoints": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["checkpoint_id", "stage", "status", "risk_level", "current_ref", "last_run_ref"],
                "additionalProperties": False,
                "properties": {
                    "checkpoint_id": NON_EMPTY_STRING,
                    "stage": {"enum": ["CP1", "CP2", "CP3", "CP4", "CP4.1"]},
                    "status": {"enum": ["valid", "stale", "failed", "blocked", "degraded"]},
                    "risk_level": RISK_V1,
                    "current_ref": NON_EMPTY_STRING,
                    "last_run_ref": {"type": ["string", "null"]},
                },
            },
        },
    },
}

AUTH_REF: dict[str, Any] = {
    "$id": "checkpoint-runtime.auth-ref.v1",
    "type": "object",
    "required": ["schema_version", "auth_ref_id", "system_id", "role_account_type", "auth_mode", "created_at", "expires_at", "contains_secret", "reportable", "rag_allowed"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": "checkpoint-runtime.auth-ref.v1"},
        "auth_ref_id": NON_EMPTY_STRING,
        "system_id": NON_EMPTY_STRING,
        "role_account_type": NON_EMPTY_STRING,
        "auth_mode": {"enum": ["public-anonymous", "runtime-input"]},
        "runtime_env_keys": STRING_ARRAY,
        "created_at": NON_EMPTY_STRING,
        "expires_at": NON_EMPTY_STRING,
        "contains_secret": {"type": "boolean"},
        "reportable": {"const": False},
        "rag_allowed": {"const": False},
        "provenance": {"type": "object", "additionalProperties": True},
        "freshness": {"type": "object", "additionalProperties": True},
    },
}
