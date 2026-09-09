---
id: proportional-conversational-execution
title: Complete bounded conversational edits without unnecessary pipeline entry
complexity: medium
---

# Complete bounded conversational edits without unnecessary pipeline entry

## Context and falsifiable prediction

The user reports disproportionate latency and persisting errors in v3.0.0.
CLAUDE.md explicitly says small tasks invoke resolve, while DECISIONS 0069.1
and the executor paragraph already allow direct conversational implementation.
Resolve's description broadly triggers on any fix/implement request. The 0140
same-model public-task screen took 706.187s with the harness vs 142.589s bare,
with equal mandatory correctness; the 821.702s solo harness missed an explicit
ban on new Any annotations. This exposed security/API task remains full-route
work, not a candidate for treating every small patch as low risk.

Prediction: replacing the blanket entry instruction with a bounded direct route
lets ordinary low-risk local edits finish with decisive checks and diff review
without pipeline startup. Explicit/full-risk/spec/queue requests retain full
resolve. Better constraint authoring can reject a known prohibited change via
existing mechanical carriers; prompt edits alone do not prove future accuracy.

## Requirements

1. In both AGENTS.md and CLAUDE.md, replace the blanket conversational
   small-task resolve instruction with a proportional pre-entry decision.
   Inspect the requested files and relevant callers/tests first. Direct
   execution is the default only for clear, local, reversible, low-risk work
   with a decisive existing or small task-specific acceptance check. Preserve
   the user's requested behavior, scope, explicit constraints and executor pin;
   perform the scoped change, relevant required checks and final diff review,
   then report what changed and evidence. Do not create a spec, pipeline state,
   phase workers, or extra approval round merely for such an ordinary edit.
2. Escalate when inspection reveals material ambiguity, subsystem/design work,
   security/auth/payment/persistence/concurrency/public-API-contract changes,
   or no decisive acceptance check. Changed-line/file/word count alone does not
   establish low risk. A user-requested resolve invocation, formal spec workflow,
   or queue drain retains all canonical phases, pin behavior, independent
   verification and failure handling. Choose before writes; if new risk appears
   mid-edit, preserve that delta and include it in the full run's scope/evidence
   rather than making it invisible in a new baseline. Existing authorization
   remains sufficient; do not add a mandatory reconfirmation.
3. Align resolve's skill discovery description and concise README entry guidance
   with this boundary. Keep explicit small resolve supported with its existing
   full phase graph. Do not add a fast flag, new classifier, automatic bypass,
   phase/worker/judge omission, model change, or runtime/schema mechanism.
4. Correct spec authoring at the existing spec template: mechanically decidable
   constraints in Requirements as well as Constraints must enter the existing
   verification_commands/forbidden_patterns/forbidden_files/max_deps_added
   carriers. Regex is for literal syntax constraints; semantic annotation or
   exception-handling rules require a suitable syntax-aware/executable check.
   Explain that forbidden_patterns scans the entire diff, so an additions-only
   rule must exclude context, deletions and diff headers. Validate a new guard
   against a violating and an allowed control, preserving allowed pre-existing
   occurrences. Reuse this guidance for free-form mini-spec authoring and ideate
   generation; keep supplied specs and expected files immutable inside resolve.
   Do not add generic judge rubric prose or claim regex proves semantics.
5. Keep canonical and tracked .agents skill mirrors identical. Limit product
   changes to the listed surfaces. No version bump, publication, unrelated
   cleanup, generated validation framework, historical-result edits or claims
   of broad quality/speed superiority. Preserve pre-existing dirty HANDOFF.md
   and untracked 0139 preparation byte-for-byte.

## Authorized product surface

- AGENTS.md
- CLAUDE.md
- README.md
- config/skills/devlyn:resolve/SKILL.md
- .agents/skills/devlyn:resolve/SKILL.md
- config/skills/devlyn:resolve/references/free-form-mode.md
- .agents/skills/devlyn:resolve/references/free-form-mode.md
- config/skills/devlyn:ideate/SKILL.md
- .agents/skills/devlyn:ideate/SKILL.md
- config/skills/devlyn:ideate/references/spec-template.md
- .agents/skills/devlyn:ideate/references/spec-template.md

## Out of Scope

Runtime phase graph or state/evidence schema changes; automatic routing service;
new flags; changes to published 3.0.0; reopening 0140/copycat/A16; global language
linters; external-human Mission 1 closure. New native comparisons are separate,
pre-registered development evidence and do not alter prior results.

<!-- devlyn:verification -->
## Verification

The sibling expected file carries these commands:

```json
{"verification_commands": [{"cmd": "git diff --check", "exit_code": 0, "timeout_sec": 60}, {"cmd": "bash scripts/lint-skills.sh", "exit_code": 0, "timeout_sec": 600}]}
```

Both commands pass all existing package/skill checks.
- Independent source review checks both entry contracts, explicit-route and
  pin preservation, supplied-spec immutability and semantic-check boundaries.
- Root subsequently runs the separately registered natural-entry comparisons
  and negative/allowed constraint controls; no efficiency/accuracy claim is
  accepted from prompt length or static checks alone.
