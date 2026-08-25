from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, resolve_ref
from .models import CheckpointRuntimeError, RegistryPaths, RuntimeTarget
from .schema_validator import SchemaValidationError, validate_payload
from .schemas import AUTH_REF, CHECKPOINT_INDEX, MODULE_MANIFEST, REGISTRY_INDEX, SYSTEM_MANIFEST


class CheckpointRegistry:
    def __init__(self, root: Path):
        self.paths = RegistryPaths(root=root.resolve(), registry_index=root.resolve() / "registry.index.json")
        self.index = read_json(self.paths.registry_index)
        self._validate(REGISTRY_INDEX, self.index, "registry.index.json")

    @staticmethod
    def _validate(schema: dict[str, Any], payload: dict[str, Any], label: str) -> None:
        try:
            validate_payload(schema, payload, schema.get("$id", label))
        except SchemaValidationError as exc:
            raise CheckpointRuntimeError(str(exc), "schema") from exc

    def _find_system_entry(self, system_id: str) -> dict[str, Any]:
        for system in self.index.get("systems", []):
            if system.get("system_id") == system_id:
                return system
        raise CheckpointRuntimeError(f"Unknown system_id: {system_id}", "registry")

    def load_system_manifest(self, system_id: str) -> dict[str, Any]:
        system = self._find_system_entry(system_id)
        manifest_ref = system.get("manifest_ref")
        if not manifest_ref:
            raise CheckpointRuntimeError(f"Missing manifest_ref for system: {system_id}", "registry")
        payload = read_json(resolve_ref(self.paths.root, manifest_ref))
        self._validate(SYSTEM_MANIFEST, payload, str(manifest_ref))
        return payload

    def load_module_manifest(self, target: RuntimeTarget) -> dict[str, Any]:
        system_manifest = self.load_system_manifest(target.system_id)
        module_ref = None
        for module in system_manifest.get("modules", []):
            if isinstance(module, dict) and module.get("module_id") == target.module_id:
                module_ref = module.get("manifest_ref")
                break
            if module == target.module_id:
                module_ref = f"systems/{target.system_id}/modules/{target.module_id}/module.manifest.json"
                break
        if not module_ref:
            raise CheckpointRuntimeError(f"Unknown module_id: {target.module_id}", "registry")
        payload = read_json(resolve_ref(self.paths.root, module_ref))
        self._validate(MODULE_MANIFEST, payload, str(module_ref))
        return payload

    def load_checkpoint_index(self, target: RuntimeTarget) -> dict[str, Any]:
        ref = f"systems/{target.system_id}/modules/{target.module_id}/checkpoint.index.json"
        payload = read_json(resolve_ref(self.paths.root, ref))
        self._validate(CHECKPOINT_INDEX, payload, ref)
        return payload

    def load_auth_ref(self, target: RuntimeTarget, module_manifest: dict[str, Any]) -> dict[str, Any]:
        auth_ref = module_manifest.get("auth_ref") or f"systems/{target.system_id}/modules/{target.module_id}/auth/auth-ref.json"
        payload = read_json(resolve_ref(self.paths.root, auth_ref))
        self._validate(AUTH_REF, payload, str(auth_ref))
        return payload
