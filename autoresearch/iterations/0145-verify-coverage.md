# 0145 — Verification coverage and sibling contract precedence

2026-09-11. Mission 1, core intent completeness first. Root implements without
resolve; actual Fable 5.1 and Grok 4.6 independently review the same source.
Baseline `1617fd203fe4f815a50204cf3a451c7392f3f913`; prospective task ownership
and `.devlyn/0145-coverage/prediction.json` precede implementation.

## Observed failure and root cause

VERIFY's old coverage paragraph required MECHANICAL coverage and changed code
for every axis. That contradicts the shared template's pure-design and residual
source-review clauses, and preservation requirements satisfied by unchanged
code. It also told a findings-only JUDGE to mutate state. The source-hash failure
instruction had the same ownership conflict. These are source contradictions;
no historical wrong native verdict is inferred from them.

Following that contract into the checker exposed actual execution failures:

| Control on baseline | Authoring check | Actual execution |
| --- | --- | --- |
| Valid pure-design sibling, prose Verification | exit 0 | exit 1: missing inline JSON fence |
| Valid pure-design sibling, stale inline command | exit 0 | exit 0, stale command executed |
| Empty runtime sibling, stale inline command | exit 2 | exit 0, stale command executed |

`stage_from_expected` distinguished sibling presence from command staging, but
main selected by staging alone. It also applied only shape validation, omitting
the existing command/pure-design consistency validator. Neither another prompt
warning nor an invented replacement check would fix these execution paths.

## Bounded repair

Select by sibling presence, validate it against the actual source markdown, and
reuse the existing validator. Its caller now passes the source path directly;
no optional filename flag or global shape-contract expansion is needed. Valid
zero-command contracts retain existing file/pattern/dependency checks and the
existing empty-results/null-process-carrier representation. Malformed siblings
fail closed; absent-sibling inline and benchmark prestaged precedence remain.

VERIFY explicitly covers binding Requirements and Constraints, permits cited
unchanged-code/design evidence where applicable, and preserves required sealed
executable evidence. JUDGE emits binding findings; the orchestrator records
`coverage_failed` telemetry before merge. State-schema wording names the same
owner. No parser, telemetry field, pair route or phase is removed.

No workaround / No guesswork motivate the reproduced execution fix;
No overengineering favors the existing validator over a new scanner or option.
Production ready requires both valid-contract acceptance and invalid-contract
rejection. Five actual CLI regressions cover pure prose, stale inline commands
with a nonstandard source filename, empty runtime, contradictory pure-design,
and missing required files. They also check empty results, stale staging removal
and rejection before command execution.

## Verification and limits

Candidate reproduction controls now accept valid pure-design, execute neither
stale inline nor staged commands, reject empty/malformed runtime contracts and
forbidden files, and preserve absent-sibling inline execution. Final full skill
lint passes in **279.374s**, including the five new CLI regressions; the earlier
kernel run passed in 269.373s. Mirror, exact-source and scope checks pass.

Final source verdict: **PASS_WITH_ISSUES**, zero unresolved binding findings and
zero CRITICAL/HIGH source defects. Exact Fable 5.1/high returned PASS_WITH_ISSUES;
exact Grok 4.6/high (emitted `grok-4.6-build`) returned PASS. Both final reviews
used fresh contexts, the same source packet, no peer output and zero tool calls.
These are standalone source reviews, not pipeline verdicts.

Fable's first review caught a root-authored control error: without Git, the
forbidden-file case failed as unverifiable, which did not prove the claimed
constraint detection. The corrected Git/base-bound control produces exactly
`scope.forbidden-file-touched`; initial output remains retained. Fable's null
carrier concern and Grok's remaining Requirements-only rubric wording were
fixed before both final reviews. Their pending-lint caveat is closed by the
final full run. Initial Grok attempted two tools, both denied; final review uses
the locally documented system-prompt override and performs no tool calls.
Ambient MCP declarations are not evidence of complete connection isolation.

Remaining advice concerns pre-existing custom-filename/carrier naming
asymmetry, generic malformed-contract fix hints, and unmeasured model adherence.
Root retains those limits rather than broadening this fix or claiming complete
semantic coverage. Required/forbidden-file controls execute; pattern/dependency
preservation additionally relies on unchanged-code inspection and existing tests.

This repair establishes a bounded runtime invariant and consistent review
instructions. It does not establish better semantic reviewer recall, complete
Any detection, prompt adherence, speed or causal pair value. Existing bootstrap
authoring preflight still defaults to sibling `spec.md`; only runtime staging's
actual source filename is addressed here. A16 and frozen comparisons stay closed.

Evidence is under `~/.local/share/nx01/iter0144/core-research/.devlyn/0145-coverage/`
and `.devlyn/0145-final/`:
prospective prediction, baseline/candidate CLI output, source-bound native review
packet, raw reviewer receipts and full lint output. Delivery and accepted custody
are owned by task receipt `.git/devlyn-completion/99f070b1b616c9260c193597/`.
