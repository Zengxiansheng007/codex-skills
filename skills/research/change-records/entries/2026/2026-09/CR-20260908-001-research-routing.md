# CR-20260908-001 - Research routing split

| Field | Value |
|---|---|
| Status | validated / candidate only |
| Target Skill | research |
| Author | Codex |
| Scope | candidate only |

## Summary

Implement the approved split, pause and recovery boundary within the isolated candidate.

## Context And Problem

User approved seven review decisions and subsequent local development up to global deployment.

## Sections Changed

See package delta manifest; original guided schemas/scripts remain unchanged unless a documented entry reference requires adaptation.

## Decision And Alternatives

Reuse official anysearch; router-owned guards; no research-anysearch or guided schema rewrite.

## Detailed Change

Metadata and semantic references follow the new entry/executor boundary. Runtime changes belong to research.

## Impact Analysis

Common research requests change default backend; explicit guided/Claude callers retain their workflow.

## Validation Evidence

Candidate structure and change-record validators passed with P0/P1/P2 zero. Router offline suite 32/32; preserved guided suites 26/26 and 32/32 plus Skill tests passed. Source scripts and schemas are byte-identical to the baseline. Evidence: evidence/candidate-validation.json in the development workspace. Three real AnySearch smoke operations passed; real quota exhaustion was not forced and no Claude call was executed.

## Safety And Privacy

No global installation or live Claude occurred. User-authorized AnySearch configuration and three bounded public smoke operations passed; no credential values were saved in artifacts.

## Risks And Follow-up

Live provider compatibility and separate global deployment review remain outstanding.


Current formatting compatibility additions preserve original historical claims; see evidence/record-format-repairs.json. Recovery-probe gating prevents old evidence from completing a task immediately after resume.
