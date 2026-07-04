# iter-0054 — plan.md heading-level defect (authorized-surface sentinel)

**Status**: SHIPPED. Closes the "unrelated pre-existing `plan.md` heading-level
defect" flagged in `autoresearch/iterations/0047-ablation.md`'s guard matrix
(`claude-small` compliance cell recovered via 1 fix-loop round on it).

## Root cause

`config/skills/_shared/spec-verify-check.py`'s `FILES_TO_TOUCH_SECTION_RE`
(and its twin, `VERIFICATION_SECTION_RE`) hardcoded the heading immediately
after the machine sentinel to be exactly level-2 (`##`):

```python
FILES_TO_TOUCH_SECTION_RE = re.compile(
    r'(?ms)^<!--[ \t]*devlyn:authorized-surface[ \t]*-->[ \t]*\n(##[ \t]+[^\n]*\n.*?)(?=^##[ \t]+|\Z)'
)
```

The producer contract, `config/skills/devlyn:resolve/references/phases/plan.md`
line 18, never states a heading level — it only says "precede this section
with a `<!-- devlyn:authorized-surface -->` sentinel comment on its own line
directly above the heading (... the heading text itself is decorative, any
language)". "Decorative" was scoped to text/language by iter-0049's
language-neutral-machinery redesign; heading *level* was never addressed by
either the producer prompt or that redesign.

**Observed instance** (archived at
`/private/tmp/probe-iter0047-verify-claude-small-compliance-claude-small/.devlyn/runs/rs-20260704T121150Z-48054ee6f602/`):
PLAN (claude-small, sonnet) emitted `<!-- devlyn:authorized-surface -->` then
`# Files to touch` (H1). `build_gate.log.md` round 0:

> Round 0 FAILED with 1 CRITICAL finding (`scope.authorized-surface-malformed`):
> `.devlyn/plan.md`'s `Files to touch` heading was `#` (H1) instead of the
> required `##` (H2) immediately after the `<!-- devlyn:authorized-surface -->`
> sentinel, so `spec-verify-check.py`'s `FILES_TO_TOUCH_SECTION_RE` never
> matched and the JSON fence with `authorized_surface` was treated as absent.

`extract_authorized_surface_block()`'s only caller (`authorized_surface_findings()`,
`config/skills/_shared/spec-verify-check.py:1297`) discards `section_found`
(`_section_found`) and treats `block is None` as "malformed carrier" —
identical handling whether the sentinel is genuinely absent or the mandatory
heading-level prefix simply didn't match. One full BUILD_GATE fix-loop round
(real wall-time + tokens) was burned recovering.

## Adjudication

**Chosen: consumer-side fix.** Generalize both regexes' heading-level
requirement from literal `##` to `#{1,6}` (any valid ATX heading level) in
both the mandatory prefix group and the lookahead section-boundary
terminator — not a producer-prompt pin telling PLAN to always emit `##`.

**Named criterion**: the mechanism must enforce exactly what its own
documented producer contract promises — no more, no less. `plan.md` line 18
never promises H2; requiring H2 in the consumer is the consumer inventing an
undocumented constraint. Removing that invented constraint (consumer fix)
closes the defect *class* for every engine (Claude, Codex, ollama, future
adapters) that might reasonably choose a different nesting depth. Pinning the
producer prompt instead would only reduce recurrence probability for one
cooperative engine reading the prompt carefully — the identical false-CRITICAL
mechanism stays live for the next engine/model that picks H1 or H3.

**Verified before applying, not assumed**: grepped every consumer of
`VERIFICATION_SECTION_RE`/`FILES_TO_TOUCH_SECTION_RE` — `extract_verification_block()`
and `extract_authorized_surface_block()` are the *only* two, and both callers
use only the `(section_found, json_block)` tuple, never the captured heading
text/level itself. All other repo hits for `## Verification` / `## Files to
touch` are doc prose examples or self-test fixture strings (which already use
H2 by convention — backward compatible with the widened regex, confirmed by
running `--self-test` after the change, see Verification below).
`benchmark/auto-resolve/scripts/run-fixture.sh:441`'s sentinel-injection `sed`
matches the *fixture's own* pre-existing `## Verification` heading (fixture
prep, human-authored convention) — unaffected by widening the *consumer*
regex.

## Mandatory Codex cross-check (1 round, converged)

`codex-monitored.sh -s read-only -c model_reasoning_effort=xhigh`, gpt-5.5.
Presented the full diagnosis, the proposed `#{1,6}` fix, and 4 explicit
questions (agree with consumer-vs-producer fix? right generality level?
hidden level-2-dependent consumer? other failure modes?).

**Verdict: agree with the consumer-side fix.**

1. "The root cause is the consumer enforcing an undocumented H2-only
   contract... Pinning the producer prompt to H2 would reduce recurrence for
   cooperative producers, but would not remove the consumer's invented
   constraint."
2. "`#{1,6}` is the right generality. `#+` over-accepts invalid ATX headings.
   Tracking same-level-or-shallower boundaries is more Markdown-semantic, but
   not justified here" — checked `plan.md`, `spec-template.md`, and 47
   sentinel-bearing self-test fixtures; none nest a subheading before the
   JSON fence, so the added complexity would be unjustified per
   no-overengineering.
3. "No sentinel consumer depends on H2" — confirmed `lint-skills.sh` only
   greps doc *phrases*, never parses section shape; confirmed
   `run-fixture.sh`'s H2-specific injection is fixture prep, not the parser.
   Flagged: keep `.claude`/`.agents` mirrors in sync (done, see Verification).
4. "Bounded" hidden failure modes: blank line between sentinel and heading,
   and setext headings, remain unhandled — both pre-existing, out of scope
   (iter-0049 already fixed sentinel-to-heading adjacency as a hard
   requirement; unchanged here). Recommended H1/H3 regression coverage —
   added (see Verification).

No disagreement surfaced; round 1 converged.

## Falsifiable prediction (stated before testing)

> Calling `extract_authorized_surface_block()` directly on text reconstructing
> the exact archived round-0 shape (the round-1 archived `plan.md`, with its
> `## Files to touch` heading reverted to `# Files to touch`, single hash)
> will return `(False, None)` under the pre-fix regex — the mandatory prefix
> `##[ \t]+` requires two literal hash characters, and `# Files to touch`'s
> first two characters (`# `) fail to satisfy it. After generalizing `##` to
> `#{1,6}`, the identical text will return `(True, '{"authorized_surface": [...]}"')`.

**Actual — confirmed exactly, both halves, run before and after the edit**:

```
PREDICTION CHECK (pre-fix code): found=False block=None
Prediction CONFIRMED: pre-fix regex rejects H1 heading -> section_found=False, block=None
...
POST-FIX: found=True block='{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}'
PASS: post-fix code accepts the exact iter-0047 H1 shape and parses the correct authorized_surface JSON
PASS: pre-existing H2 convention still works
```

Additionally verified the new self-test assertion is a real regression guard
(not vacuous): copied the fixed file to scratch, reverted just the two regex
lines back to literal `##`, re-ran `--self-test` → fails with
`extract_authorized_surface_block rejected a '#' heading after the sentinel`,
exit 1. Same file with the regex fix in place → exit 0.

## Fix applied

`config/skills/_shared/spec-verify-check.py` (+ `.agents/skills` mirror;
`.claude/skills` is gitignored, refreshed locally for consistency, not
committed):

```diff
 VERIFICATION_SECTION_RE = re.compile(
-    r'(?ms)^<!--[ \t]*devlyn:verification[ \t]*-->[ \t]*\n(##[ \t]+[^\n]*\n.*?)(?=^##[ \t]+|\Z)'
+    r'(?ms)^<!--[ \t]*devlyn:verification[ \t]*-->[ \t]*\n(#{1,6}[ \t]+[^\n]*\n.*?)(?=^#{1,6}[ \t]+|\Z)'
 )
 FILES_TO_TOUCH_SECTION_RE = re.compile(
-    r'(?ms)^<!--[ \t]*devlyn:authorized-surface[ \t]*-->[ \t]*\n(##[ \t]+[^\n]*\n.*?)(?=^##[ \t]+|\Z)'
+    r'(?ms)^<!--[ \t]*devlyn:authorized-surface[ \t]*-->[ \t]*\n(#{1,6}[ \t]+[^\n]*\n.*?)(?=^#{1,6}[ \t]+|\Z)'
 )
```

`extract_verification_block()`'s docstring updated to state the widened
contract ("any ATX heading level 1-6"). No producer-prompt (`plan.md`,
`spec-template.md`) edits — the fix is entirely in the consumer, per the
adjudication above.

**Self-test regression coverage added** (`run_self_test()`, new Test 8):
H1 and H3 headings accepted for both `extract_authorized_surface_block()` and
`extract_verification_block()`, plus a mixed-level document (`## Files to
touch` followed by `# Risks`, the exact iter-0047 shape once fixed) to confirm
the section-boundary lookahead still bounds correctly rather than swallowing
the rest of the document.

## Verification

- **Self-test**: `python3 config/skills/_shared/spec-verify-check.py --self-test`
  — exit 0. Same for `.agents/skills/_shared/spec-verify-check.py` and the
  local `.claude/skills` mirror.
- **Regression-guard sanity**: new Test 8 fails against a scratch copy with
  the old `##`-only regex (exit 1, correct error message), passes against the
  fixed file (exit 0) — confirms the added test isn't vacuous.
- **`state-phase-write.py --self-test`**: exit 0.
- **`verify-merge-findings.py --self-test`**: exit 0.
- **`bash scripts/lint-skills.sh`**: `All checks passed.` — no check pins the
  old regex literal or the widened docstring text.
- **Mirror parity**: `diff -rq config/skills/_shared .agents/skills/_shared`
  and `.claude/skills/_shared` — byte-identical (only `__pycache__`, removed,
  gitignored).
- **Compliance cell `claude-small` (MODEL=sonnet, run-id
  `iter0054-verify-claude-small-20260704T132052Z`)** — **PASS 4/4**
  (`state_found`, `phases_ordered`, `verify_evidence`, `archive_ran`; results
  at `benchmark/probes/results/iter0054-verify-claude-small-20260704T132052Z/compliance/claude-small/compliance-check.json`).
  `pipeline.state.json`'s `build_gate` phase: `"round": 0`, `"verdict": "PASS"`,
  `build_gate.findings.jsonl` empty — **zero fix-loop rounds**, unlike
  iter-0047's same cell (1 round burned on this exact defect). Caveat, stated
  honestly rather than overclaimed: this run's PLAN happened to emit
  `## Files to touch` (H2) on its own — LLM heading-level choice is
  non-deterministic per run, so this single live cell is corroborating, not a
  controlled same-shape A/B. The deterministic, reproducible proof is the
  direct-function-call prediction test above (old regex rejects the exact
  archived H1 shape; new regex accepts it) plus the new self-test Test 8,
  which is guaranteed to exercise H1/H3 every run regardless of what any
  given LLM invocation happens to choose.

## Scope discipline note

The fix touches `VERIFICATION_SECTION_RE` in addition to the
`FILES_TO_TOUCH_SECTION_RE` the brief named. This is a deliberate, disclosed
inclusion, not scope creep: the two regexes are byte-identical twins of the
same hardcoded-level defect in the same function block of the same file: an
asymmetric fix (only `FILES_TO_TOUCH_SECTION_RE`) would leave the identical
false-CRITICAL mechanism live for `<!-- devlyn:verification -->` (ideate specs
/ free-form criteria), reproducible by the exact same class of engine
heading-level choice. "Fix classes not cases" — leaving a byte-identical twin
of a just-diagnosed bug unfixed in the same commit is the drift this
guidance exists to prevent, not an expansion of it.

## Commit

See `git log --oneline -- autoresearch/iterations/0054-plan-heading-fix.md`.
