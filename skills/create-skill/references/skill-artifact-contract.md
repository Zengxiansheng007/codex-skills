# Skill Artifact Contract

Use this contract when delivering a skill package or review result.

## Required Package Files

```text
skill-name/
  SKILL.md
  agents/openai.yaml
```

Optional files must be justified:

```text
references/
scripts/
assets/
```

## Report Contract

When producing a report, prefer Chinese HTML with embedded JSON:

```html
<script type="application/json" id="skill-evidence">
{
  "skill": "skill-name",
  "status": "accepted-with-constraints",
  "findings": [],
  "validatedCommands": [],
  "openRisks": []
}
</script>
```

## Adoption Status

Use one of:

- `draft`: files generated but not validated;
- `review-required`: human review needed before use;
- `sandbox-only`: can only be tested in isolation;
- `accepted-with-constraints`: usable with documented limits;
- `accepted`: validated and ready for normal use;
- `rejected`: unsafe or structurally unsuitable;
- `rerun`: structure is invalid or evidence is incomplete.

## Evidence Checklist

- Source requirement or brief path.
- Skill folder path.
- Frontmatter status.
- File inventory.
- Link/resource validation.
- Script test result.
- Secret scan result.
- Forward-test prompt and result.
- Known limitations.
