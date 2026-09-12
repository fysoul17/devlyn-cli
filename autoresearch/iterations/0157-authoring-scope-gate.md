# 0157 — Reuse the existing BUILD_GATE scope check

2026-09-12. Continuing the owner's sequential constraint-coverage work from
0156. Root implements directly; no resolve invocation. Prospective receipt
`1ef874fd940bcd78c554baf8` owns branch `codex/0157-authoring-scope` and scratch,
based on `7b346ca82a773497b82a03678040434eaff5757a`. Original/user worktrees,
0156's immutable failed proposal and frozen comparisons remain untouched.

## Observed failure and smallest repair

0156's extracted author wrote a whole-checkout scope scan inside its acceptance
script. It rejected runner metadata before checking the requested annotation
constraint. The actual BUILD_GATE already checks PLAN's `authorized_surface`
against the run diff and newly created untracked files, excluding `.devlyn/`
(`spec-verify-check.py:1722`, caller `:5517`). The template did not connect that
mechanism to check authoring; free-form mode also references this section for
diff scope (`free-form-mode.md:78`). This is a concrete missing connection,
not evidence that production ideate's execution/repair loop necessarily fails.

The only production change is a common note in `spec-template.md:98`: preserve
specific constraints, including narrower ones; describe the BUILD_GATE scope
mechanism with its recorded `state.base_ref.sha` precondition; avoid duplicating
it with a whole-checkout scan in verification commands. Both authoring lanes
read this existing reference. Python, schema and phase machinery are unchanged.

**No overengineering / Optimized:** reuse the existing gate; no generic `Any`
scanner, new API, fallback, duplicated free-form prose or product fixture helper.
**No workaround / Production ready:** specific file rules still reject and
malformed gate inputs fail closed when the existing gate is active.
**No guesswork / Worldclass:** actual CLI outcomes and native independent advice
precede acceptance. **Best practice:** preserve the existing carrier and phase
contracts rather than hand-roll a second scope implementation.

Fable returned an actual 429 usage-limit error before model output. The already
authorized native Opus 5 substitute and Grok 4.6 reviewed independently. Their
design advice rejected a proposed generic rewrite of the guard-control sentence;
that sentence remains unchanged. Opus's identified phase/base precondition and
narrower-constraint risks are addressed in the final note and actual controls.
Root decides from evidence, without a unanimity gate.

## Premise controls

The unchanged checker is invoked in disposable Git workspaces with a real
PHASE 0 untracked snapshot and a fixed PLAN surface. These are component checks,
not a full pipeline invocation or a regrade of the original 0156 draw.

Across 18 controls, a copy of the original script produces six false blocks;
all 18 commands stop at its whole-checkout scan, including the seven annotation
variants. Matching failure exits do not receive semantic-detection credit.
The diagnostic copy removing exactly `scope_guard()`'s call matches all 18
outcomes: three original allowed cases, seven attributable annotation failures,
pre-existing user files and runner metadata allowed, new untracked/staged scope
leaks rejected, malformed PLAN/missing baseline rejected, and a stricter
`forbidden_files` constraint rejected independently inside the allowed surface.
VERIFY MECHANICAL correctly does not rerun PLAN's general scope gate.

Two auxiliary controls characterize limits: an empty `base_ref.sha` skips the
existing scope gate, so the note explicitly states that precondition; removing
the required test file still yields `correctness.required-file-missing` from
the carrier after the diagnostic call deletion. No empty-base runtime repair is
claimed. A pre-existing required-file check inside the deleted function was
redundant with the carrier; the diagnostic is not a shippable checker shape.

Raw command streams and hashes are preserved in `.devlyn/0157/`. One initial
expected rule label was corrected from an invented `correctness.forbidden-file`
to the actual `scope.forbidden-file-touched`; input cases and allow/deny
predictions were unchanged, and the initial table remains retained.

## Source verification and known-task adherence smoke

Final native Opus 5 **PASS_WITH_ISSUES** and Grok 4.6 **PASS**; root accepts the
scoped note with no established in-scope CRITICAL/HIGH. Opus's optional explicit
"scripts they invoke" wording remains advisory: the command includes its invoked
script, and the actual smoke inspects that script. Full lint **PASS282.791s**,
bound to source-diff SHA-256
`556ca51f355a66331bc6e1578b16cece87af26cefe22b3e75f4d6ca1e9968857`.
Mirror, original-sentence preservation, source-scope and whitespace checks pass.

The registered smoke uses the same disclosed development task with truthful
BUILD_GATE context, root-only materialization, unchanged emitted artifacts,
and no native tools, retry or repair feedback. It is not disjoint confirmation,
a controlled before/after comparison with 0156's VERIFY-context apparatus,
or evidence of general semantic coverage. The existing guard-validation
instruction cannot be executed by the read-only native author in this extracted
screen; root evaluates the proposal separately. Ambient host-skill warnings may
still limit context-isolation claims.

The single admitted native Codex `gpt-6-astra/high` draw exits 0 in **367.963s**.
Root inspected all three proposed files, then executed the entire unchanged
carrier. All **18** controls match expected outcomes: three core allowed cases
pass, seven annotation violations fail with actual `new typing.Any annotation`
messages, and eight scope/phase controls preserve the existing gate's behavior.
No whole-checkout scope scan is present. No false block, registered miss, retry
or repair feedback. Original 0156 remains failed; this is one adherence
observation under different runtime context, not measured general improvement.

Native logs report CLI0.154.0, the requested model/effort and read-only sandbox,
with zero observed tool sections and eight ambient skill warnings. Reported
`tokens used` is 30,023; input/cache/output split is unknown. The emitted checker
explicitly leaves dynamic/late-bound binding, test-tampering and dependency-loading
semantics for source review. Its wildcard-looking `forbidden_files` strings have
only literal matching in the current checker; no wildcard coverage is credited.
The fixed PLAN scope excludes new dependency-manifest paths in this fixture.
Neither the task-specific checker nor a generic scanner is promoted.
Proposal SHA-256:
`dc4b5900d5861957c18f0cd3f72ce12b51ee0ee05bd90843991e1cf10f216d04`.

Source evidence is `.devlyn/0157-evidence.tar.gz`. Matching-source CI and delivery
are recorded separately in `.devlyn/0157-delivery/` and the task receipt. Broader
semantic coverage and the matched bare/solo/pair comparison remain open.
