# Strong Gate And Light Path

## Purpose

Define the mandatory research gate and the only allowed exception for very simple tasks.

## Default Rule

Every `research` invocation starts in strong-gate mode.

Strong gate means:

1. Codex designs the research direction and outline.
2. Claude performs retrieval and initial review.
3. Codex performs coverage review.
4. If needed, Claude performs one reinforcement round.
5. Codex makes the final decision.

## Light-Path Exception

Light research is allowed only when all of the following are true:

- the task is objectively simple;
- the task does not need comparative source coverage;
- the task does not involve high-impact, safety, privacy, or compliance decisions;
- Codex explicitly tells the user why the task qualifies for light mode;
- the user explicitly confirms the downgrade.

If the user does not confirm, continue with the strong gate.

## Simple-Task Checklist

Treat a task as a light-path candidate only when it is:

- a single factual lookup;
- low risk;
- unlikely to need a second evidence round;
- not dependent on conflicting external sources;
- not a requirement, design, or test decision.

## Recording Requirements

Record all of the following in the research packet:

- mode selected;
- why that mode was selected;
- whether the user confirmed a downgrade;
- sources used;
- final decision;
- any gap that forced the task back to strong-gate mode.

## Anti-Patterns

- Silent downgrade to light mode.
- Treating "simple" as a reason to skip confirmation.
- Using light mode for high-impact decisions.
- Hiding the downgrade decision from the final report.
