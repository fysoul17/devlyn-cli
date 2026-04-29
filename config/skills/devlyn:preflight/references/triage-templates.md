# Triage — Promoted Item Spec + Accepted Divergences Templates

SKILL.md Phase 4 describes the triage contract. This file holds the file shapes so the contract stays compact.

## Promoted item spec (written per confirmed finding)

Place in the appropriate roadmap phase directory — same phase as the original item, or a new "fixes" phase if multiple phases are affected. Priority is derived from the finding's severity; complexity is estimated from the finding scope.

```markdown
---
id: "[phase].[next-number]"
title: "[Fix/Add: description]"
phase: [N]
status: planned
priority: [derived from finding severity]
complexity: [estimated from finding scope]
depends-on: []
---

# [id] [Title]

## Context
Preflight check identified this gap against the original roadmap specification.
[Brief context from the original commitment and what's wrong]

## Objective
[What needs to be true after this is fixed]

## Requirements
- [ ] [Specific fix requirement derived from the finding]
- [ ] [Verification step]

## Constraints
- Must align with original spec at docs/roadmap/phase-N/[original-item].md

## Out of Scope
- Changes beyond what the original spec requires
```

## Accepted divergences (`.devlyn/preflight-accepted.md`)

```markdown
# Accepted Divergences
# Findings marked as intentional — excluded from future preflight runs

- [item-id|none] [commitment|rule_id+locator]: [reason accepted]
```

For commitment-bound findings, use `[item-id] [commitment]`. For commitment-less findings (e.g. `PRINCIPLE_VIOLATION` fallback bucket: unjustified duplicate machinery, hand-rolled stdlib), use `[none] [rule_id]+[normalized_evidence_locator]` — e.g. `[none] [principle.unjustified-duplicate-machinery]+[src/utils/format-date.ts:12]`. The dedup logic in PHASE 3 step 3 matches accepted entries by `(rule_id, locator)` when no commitment id is present.

## STALE_DOC handling

STALE_DOC findings are factual corrections, not implementation decisions. Fix them directly:
- Update ROADMAP.md status columns
- Update item spec frontmatter (`status:` only — do not add `completed:` or other un-licensed fields per iter-0026; spec lifecycle notes typically license `status` flip only)
- Update VISION.md "What's Next" sections when the current next-up is outdated

## Triage completion message

```
Triage complete.
- [N] findings promoted to roadmap ([list item IDs])
- [N] divergences accepted
- [N] doc issues fixed directly

Next steps:
- To implement fixes: /devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/[id]-[name].md"
  - CRITICAL/complex DIVERGENT findings already get the cross-model GAN dynamic under default `--engine auto`. No extra flag needed.
- To re-run preflight after fixes: /devlyn:preflight [same flags]
- To add features discovered during audit: /devlyn:ideate expand
```
