# System Use Retrospective

Use this reference when the user asks to evaluate `development-system` or after a substantial Skill development run that used this system.

## Purpose

The retrospective reviews the system's actual behavior, not only the delivered feature. It should identify whether the router helped preserve requirements, whether it introduced friction, and which rules should be changed.

## Required Sections

- outcome and final next-state decision;
- requirement anchor sufficiency;
- route decisions used and skipped;
- evidence and grill gate quality;
- approval boundary handling;
- local implementation or A2A loop quality;
- validation and completion judgment quality;
- defects and optimization points with severity;
- candidate updates to `development-system` or downstream Skills.

## Severity Guide

- `P0`: the system allowed unsafe, unauthorized, or requirement-breaking completion.
- `P1`: the system omitted a rule needed for repeatable safe execution.
- `P2`: the system worked, but required avoidable judgment, extra manual reconstruction, or cleanup.
- `P3`: wording, naming, or ergonomics improvement.

## Completion Rule

The retrospective is complete only when each finding has:

- severity;
- evidence;
- impact;
- recommended update;
- owner Skill or artifact.

