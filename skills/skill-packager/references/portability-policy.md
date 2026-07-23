# Portability Policy

## Package Levels

- L0: `SKILL.md` only. Not suitable for migration.
- L1: `SKILL.md` plus references/assets/scripts. Usable on same runtime.
- L2: Includes manifest, hashes, validation report, and adapter notes.
- L3: Includes target-specific package, dry-run install, backup, and validation logs.
- L4: Includes cross-model and cross-agent behavior tests.

`skill-packager` targets L3 by default.

## Required Package Metadata

- source path;
- generated timestamp;
- source file inventory;
- SHA256 hashes;
- target runtime;
- excluded files and reasons;
- validation commands;
- deployment target and backup path if deployed.

## Safety Rules

Block packaging on obvious secrets.

Warn and require confirmation for:

- private URLs;
- internal-only service names;
- tool preauthorization fields;
- destructive commands;
- target directory overwrite.
