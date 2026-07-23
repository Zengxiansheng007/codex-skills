# Requirement Analysis Brief Template

Use this before formal test case generation.

```markdown
# Requirement analysis brief: {feature}

## Sources
| sourceId | type | title/path | version/time | confidence | notes |
|---|---|---|---|---|---|

## Scope
| item | zone | reason |
|---|---|---|

## Source-oracle decisions
| conflictId | sources | decision | reason | action |
|---|---|---|---|---|

## Module tree
| modulePath | sourceIds | reachability | notes |
|---|---|---|---|

## Rules and risks
| ruleId | type | statement | sourceIds | risk |
|---|---|---|---|---|

## Change impact
| changeId | before | after | impacted modules | regression boundary |
|---|---|---|---|---|

## Test design plan
| modulePath | techniques | target coverage | exclusions |
|---|---|---|---|

## Open questions
| questionId | severity | question | blocked cases |
|---|---|---|---|
```
