# Markdown Format

Use stable hierarchy so test case management tools and validators can parse the output.

## Structure

```markdown
# Suite title

## Top group

### Module group

#### Lowest level module

##### tc-P0:Case title

###### Step 1: Click the real control name
* Expected: The exact expected result is visible or measurable
* rc: Source: SRC-001
```

## Rules

- `#` is the suite title.
- `##` is a top-level group.
- `###` is a module group.
- `####` is the lowest-level module or a path-style module.
- `##### tc-PX:` is a test case under a lowest-level module.
- `###### Step N:` is an action step.
- Each step must have at least one `* Expected:` line.
- Each formal case must have at least one `* rc: Source: SRC-...` note or a matching JSON `sourceIds` entry.
- Do not create peer groups named only "End-to-end", "Extra tests", or "Regression" when they hide the real module. Put those cases under the primary triggering module.
- Steps must name actual pages, tabs, controls, fields, dialogs, messages, APIs, statuses, or data conditions.
- Avoid vague actions such as "enter page", "click button", "select content", "submit form", or "check list" unless the actual target is named.
- If source evidence does not provide the actual control or message, write an open question instead of a formal step.

## Priority

- `P0`: smoke or release-blocking path.
- `P1`: important branch, rule, or error handling.
- `P2`: ordinary regression or secondary condition.
- `P3`: low-frequency or nice-to-have coverage.

In change-scope mode, priority follows change risk rather than a fixed percentage.
