# 0146 — Canonical contracts for named specs

2026-09-11. Mission 1. Root implements without resolve and decides after
independent actual Fable 5.1 and Grok 4.6 review. Baseline `e19e160` includes
0145. Prospective receipt and `.devlyn/0146-carriers/prediction.json` precede
the source changes. Original workspace WIP and frozen research remain untouched.

## User contract and reproduced failures

Resolve explicitly documents `--spec docs/roadmap/phase-N/X.md` with sibling
`spec.expected.json` (`config/skills/devlyn:resolve/SKILL.md:66`). This is a
supported input, not a filename inferred from permissive parsing. Inspection
after 0145 found consumers deriving `X.expected.json` and a bootstrap check
reading a neighboring `spec.md` instead of the actual source.

Isolated controls against baseline confirm all six consequences:

| Control | Before | Candidate |
| --- | --- | --- |
| Named source's declared IMPLEMENT obligation | empty list | declared obligation found |
| IMPLEMENT checkpoint without required evidence | accepted | BLOCKED |
| Valid X.md beside invalid spec.md | rejected | accepted and bound to X.md |
| Invalid X.md beside valid spec.md | accepted | rejected |
| Canonical expected file in completion custody | omitted | byte-preserved |
| Completion without named source's required evidence | accepted | BLOCKED before publication |

Completion controls exercise production acceptance through the existing test
fixture's fake `gh` and local bare Git repository; no real PR is created by
these controls. An earlier control draft used `--local-only`, which bypasses
acceptance; its result is retained and excluded. `baseline-acceptance` is the
actual before measurement. No full resolve run is claimed.

## Smallest repair

Use `spec.expected.json` in process-evidence lookup and both completion lookup
sites. Preserve the existing generated-criteria sidecar behavior. Move actual
source complexity validation into the existing sibling staging function, then
remove bootstrap's redundant sibling `--check-expected` subprocess. The legacy
absent-sibling `--check <actual source>` remains. Standalone `--check-expected`
keeps its documented `spec.md` convention; no new flag or schema is needed.

No workaround / No guesswork require one authoritative contract and rejection
of missing declared evidence. No overengineering / Optimized favor deleting
the duplicate validation route and reusing the existing validator. Path escape,
symlink, immutable evidence and custody checks remain in place.

Regressions cover named-source obligation discovery despite a decoy
`X.expected.json`, canonical-sibling absence, both bootstrap source/distractor
combinations, completion custody and missing-evidence refusal. Existing
canonical-name, generated-source and evidence tampering tests remain.

## Verification and continuation

All six owner controls now meet their expected behavior. Full skill lint passes
in **296.937s**, including 25 completion tests and the added bootstrap/process
regressions. Canonical/mirror parity, exact reviewed-source hashes and scoped
diff checks pass. This is no whole-run speed comparison.

Final source verdict: **PASS_WITH_ISSUES**, no unresolved binding findings or
CRITICAL/HIGH source defects. Fresh exact Fable 5.1/high returned
PASS_WITH_ISSUES; exact Grok 4.6/high (emitted `grok-4.6-build`) returned PASS.
They reviewed the same source independently with zero tool calls. Root closed
their pending-test limitations using the full lint output.

Fable proposed that editing `spec.expected.json` after verification could bypass
completion. The supplied excerpt omitted `complete`'s earlier workspace guard:
`task-complete.py:406,544–549`. Root registered and ran that counterexample; it
returns BLOCKED for dirty/untracked contents with **zero pushes**, so the
proposed live-completion bypass is not accepted as a finding. That control
does not establish every possible contract-integrity guarantee.

Remaining LOW advice: complexity errors name the expected file rather than the
source markdown, and nested completion/stronger decoy tests could extend coverage.
Old undocumented stem-named files gain no compatibility fallback. The explicit
canonical contract and reproduced failure are the scope; no speculative warning,
new filename option or unrelated integrity redesign is added.

This closes concrete contract lookup failures. It does not prove prompt
adherence, semantic reviewer recall, improved speed, or causal pair value.
Those HANDOFF priorities still require registered comparisons and untouched
confirmation; A16 and historical negative results remain unchanged.

Evidence root: `~/.local/share/nx01/iter0144/core-research/.devlyn/`, directories
`0146-carriers/` and `0146-final/`. Prospective task receipt:
`.git/devlyn-completion/7b707fd961cf945fbfde6e61/`. Acceptance/custody and delivery
are recorded separately from product validation. No npm release/version bump.
