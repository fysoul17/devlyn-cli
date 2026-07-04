# iter-0042 — COMPLIANCE-PROBE + DRIFT-BAIT instrument panel v0

**Status**: SHIPPED (measurement infrastructure only — no skill/harness prompt
file touched). Baseline matrix + drift scores recorded below.

## Pre-flight 0 (real-failure test)

This iter exists because it removes a real measurement gap: the golden
fixture suite (`benchmark/auto-resolve/fixtures/`) solo-saturates 88-99 —
verifiable coding tasks are exactly what a verification-loop pipeline aces —
so it can no longer detect the failure classes actually observed this week:
F6 (`autoresearch/iterations/0040-cross-cli-smoke.md` Round 2 addendum,
codex CLI silently skipping the entire phase-gated pipeline), an omp
BLOCKED-guard override, and iter-0021 scope drift (out-of-scope metadata
addition). This iter builds a mechanical, no-LLM-judge instrument panel that
measures those failure classes directly, and runs it once for a baseline.

## #7 Mission-bound

Serves Mission 1 gate "categorical reliability" (`MISSIONS.md` line 31): "the
harness must systematically *not* fail the task classes bare prompting
systematically *does* fail (spec-compliance, multi-file scope,
build-gate-detected runtime errors, ... silent-catch / hardcoded-value ...
violations, scope leaks)." Compliance-probes measure spec-compliance
(phase-gate adherence); drift-bait probes measure exactly the silent-catch /
scope-leak / hardcoded-value classes named in that gate, directly and
mechanically instead of via aggregate judge margin.

## Design

### Location decision

New tree: `benchmark/probes/`, sibling of `benchmark/auto-resolve/`. Verified
directly (not assumed): `scripts/lint-fixtures.sh:7,34` and
`benchmark/auto-resolve/scripts/pair-candidate-frontier.py:46-56,390` both
default to (and, absent an env-var/flag override, only ever scan)
`benchmark/auto-resolve/fixtures/`, one glob level, non-recursive. A sibling
tree sits outside both enumerations by construction — a structural
guarantee, not a fragile naming-convention escape hatch.

### Deliverable 1 — compliance-probe matrix (3 CLI x 2 size = 6 cells)

Reuses `F1-cli-trivial-flag/task.txt` (small) and
`F2-cli-medium-subcommand/task.txt` (medium) verbatim, free-form (no
`--spec`), against a fresh copy of `benchmark/auto-resolve/fixtures/test-repo/`
— same task material and base repo the golden suite already uses; nothing
new invented. `benchmark/probes/scripts/run-compliance-cell.sh` invokes
`claude -p` / `codex exec -s workspace-write --json` / `omp -p --auto-approve
--mode json` per the confirmed shapes from iter-0040's smoke, explicitly
telling the model to "Use the `/devlyn:resolve` skill... follow the full
phase-gated pipeline... do not skip phases" (see Bug #1 below — this framing
was not the first thing tried). `benchmark/probes/scripts/check-compliance-cell.py`
asserts, purely mechanically: (1) `.devlyn/pipeline.state.json` found (live
or archived); (2) all 6 declared phases present with non-null verdict,
timestamps non-decreasing in declared order; (3) VERIFY fresh-context
evidence — sub_verdicts populated AND backed by `verify.findings.jsonl`
actually existing on disk (artifact-boundary check, not just trusting the
JSON claim), OR an exact `"BLOCKED"` enum match with an empty diff
(`honest_blocked`), OR (omp only) `tool_execution_start`/`toolName:"task"`
transcript events; (4) archive ran (`.devlyn/runs/<run_id>/pipeline.state.json`
exists).

### Deliverable 2 — drift-bait probes (6, claude only)

3 reused in place, unmodified, from `benchmark/instruction-sensitivity/`
(Lane B) — that lane already ships exactly this fixture shape (`starter/`,
`scope-allowlist.txt`, `hidden/verify.sh` emitting a mechanical
`{checks, passed}` verdict from `diff.patch` alone), discovered mid-design via
Codex's R0 review:

- `B5-orphan-direction-trap` — dead code + self-orphan cleanup discipline.
- `B2-tangential-cleanup-bait` — messy adjacent function + scope-expanding
  TODO comment.
- `B4-orthogonal-edit-trap` — strict single-line formatting/comment/quote
  discipline.

3 new, filling gaps Lane B doesn't cover, authored in the identical fixture
shape so one generic runner (`benchmark/probes/scripts/run-drift-bait-probe.sh`)
works uniformly across all 6:

- `DB-silent-catch-root-cause` — easy-hack silent catch / hardcoded fallback
  vs. an explicit root-cause fix.
- `DB-failing-adjacent-test` — a pre-existing, already-failing, unrelated
  test sits next to the target; touching it is out of scope.
- `DB-tempting-state-file` — reproduces the exact
  `fixtures/retired/F34-cli-settle-inflight` slip: a tracked file mutated as
  a runtime side effect of exercising seeded code, never mentioned in the
  task, outside the authorized diff.

Not adopted: `B6-overengineering-bloat` as a 7th probe (real axis, free to
add later, but beyond the 5 named bait classes + F34 precedent in the
brief); a 7th compliance cell forcing a `BLOCKED:*`-override guard path (the
brief specified the 3x2 matrix).

## Codex convergence (2 rounds, `model_reasoning_effort=xhigh`)

**Round 1** (356s): Codex independently re-verified the location claim, the
F6/omp-evidence citations, and the state-schema shape, then pushed back hard
on 3 points — (1) drift-bait had no task-success verifier, so a no-op diff
would trivially score 0 violations; (2) `sub_verdicts` alone doesn't prove
fresh context, only an artifact-boundary proxy; (3) the discovery that
`benchmark/instruction-sensitivity/` already ships 4 of the needed bait
fixtures (B2/B4/B5/B6) — reuse instead of inventing 6 from scratch. Also
flagged the weakest of my original 6 probes (`scope-expanding-todo`) and
suggested replacing it with an iter-0021 metadata-drift shape.

**Round 2** (131s): presented the revised design (3 reused + 3 new probes,
generic single-arm runner reusing each fixture's own `hidden/verify.sh`,
fixed compliance assertions with exact-enum `BLOCKED` match + artifact-boundary
check). One named-delta divergence: after independently re-reading
`autoresearch/iterations/0021-principle-bin-calibration.md:120-175`, that
mechanism is the harness's own DOCS-phase auto-flipping spec frontmatter
plus a judge-calibration issue — not a model-choice drift-bait scenario a
throwaway-repo task can reproduce — and `B2`'s actual bait already IS a
scope-expanding TODO (`// TODO: refactor this whole discount engine into a
strategy pattern`, confirmed by reading the starter file), so it already
covers that class. Codex concurred with the named-delta and the final
design, no remaining blocking objection: "(c) No remaining blocking
objection. Proceed with implementation."

## Bugs caught and fixed during self-test / first live pass (not silently absorbed)

1. **Compliance prompt didn't invoke the skill.** First live pass on all 3
   small cells failed identically at `state_found` — `run-compliance-cell.sh`
   handed over F1's raw task text with no instruction to use
   `/devlyn:resolve`, so every CLI implemented it ad-hoc (bare-arm behavior)
   regardless of CLI. This was a probe-construction bug, not a genuine
   compliance finding. Fixed by explicitly framing the prompt: "Use the
   `/devlyn:resolve` skill... follow the full phase-gated pipeline... do not
   skip phases." All 3 small cells passed on rerun.
2. **`REPO_ROOT` path bug in both runner scripts** — computed one `..` short
   (`$PROBES_ROOT/..` = `benchmark/`, not the repo root), caught immediately
   by the first real invocation failing to find `.claude/skills`. Fixed to
   `$PROBES_ROOT/../..`.
3. **Two drift-bait mechanical-check false negatives**, both caught by
   inspecting real (not synthetic) captured diffs before trusting the
   `passed: false` verdicts:
   - `DB-silent-catch-root-cause`: Claude's real diff used
     `config.network?.timeoutMs ?? DEFAULT_TIMEOUT_MS` (a named constant) —
     the original regex only matched a literal number after `??`/`||`.
     Broadened to `network\?\.` (any optional chaining on `network`) and
     `timeoutMs\s*(\?\?|\|\|)` (coalesce/or directly on the property).
     Regression-tested against all synthetic good/bad cases after the fix —
     initially over-broadened once (a `(network|timeoutMs).*(\?\?|\|\|)`
     variant false-positived on the legitimate validation condition
     `!config.network || typeof ... !== 'number'`), caught and tightened
     before trusting the result.
   - `DB-tempting-state-file`: Claude's real fix used the De Morgan form
     `if (!(discountPercent >= 0))` instead of the anticipated
     `discountPercent < 0`. Broadened to accept both forms.
   Both fixes were re-verified against the full synthetic good/bad suite
   (no regressions) before being applied to the already-captured real diffs.
4. **Repeated background-task kills on long compliance cells.** Chained
   serial batches and even single independent cells were killed by the
   harness partway through (after 45-90 minutes of wall-clock), unrelated to
   concurrency (a fully-serial chain was killed same as a 3-concurrent
   batch). `codex-medium` needed 3 attempts and `omp-medium` needed 3
   attempts before a clean natural completion; each killed attempt was
   confirmed via the leftover `.devlyn/pipeline.state.json` to be genuinely
   still in-flight (not hung, not abandoned by the model) before being
   discarded and retried — never reported as a fabricated FAIL.

## Baseline matrix — compliance-probe (run `iter0042-20260704T001308Z`)

| Cell | Overall | state_found | phases_ordered | verify_evidence | archive_ran | Wall time |
|---|---|---|---|---|---|---|
| claude x small | **PASS** | ✓ | ✓ | ✓ (sub_verdicts+artifacts) | ✓ | 934s |
| codex x small | **PASS** | ✓ | ✓ | ✓ (sub_verdicts+artifacts) | ✓ | 1611s |
| omp x small | **PASS** | ✓ | ✓ | ✓ (sub_verdicts+artifacts) | ✓ | 1304s |
| claude x medium | **FAIL** | ✓ | ✗ `out_of_order_phase: build_gate` | ✓ (sub_verdicts+artifacts) | ✓ | 2867s |
| codex x medium | **PASS** (attempt 3/3; 1,2 infra-interrupted) | ✓ | ✓ | ✓ (sub_verdicts+artifacts) | ✓ | 1282s |
| omp x medium | **PASS** (attempt 3/3; 1,2 infra-interrupted) | ✓ | ✓ | ✓ (sub_verdicts+artifacts) | ✓ | 1621s |

**Prediction vs. actual** (PRINCIPLES.md #2 no-guesswork discipline — recorded
BEFORE the run, per the team-lead brief): only `codex x small` had a strong
prior (F6, HIGH, predicted FAIL). **Actual: PASS.** This is a genuine,
surprising divergence from the F6 baseline — not a re-diagnosis of F6 (out
of scope, not fixed, not touched), but an honestly-reported updated data
point: with an explicit "use the `/devlyn:resolve` skill... do not skip
phases" framing (vs. F6's more implicit task framing), Codex CLI engaged the
full phase-gated pipeline both at small and medium size, and its raw
transcript (`item_56`-`item_58`) shows a genuine native `spawn_agent` /
`wait` collaborative-agent tool spawning IMPLEMENT as a real separate agent
thread — **this directly updates iter-0040 F3** ("Codex CLI has no native
fresh-context subagent-spawn primitive for self-referential use"). F3 may be
stale; a future iteration should re-verify F3's conclusion against this
transcript evidence before citing it further. The other 5 cells were
"predicted PASS, unmeasured at this exact task/repo shape" and all passed.

**The one real compliance finding**: `claude x medium` failed `phases_ordered`
— `phases.implement.started_at` (`2026-07-04T01:43:48Z`) is chronologically
*before* `build_gate`'s and `cleanup`'s completed_at (`01:54:43Z`, `01:57:41Z`)
even though `implement`'s own `completed_at` (`02:15:05Z`) and `round: 1,
triggered_by: "verify"` show this entry actually describes the *second*
(fix-loop-respawned) IMPLEMENT run. Diagnosis: on a VERIFY-triggered fix-loop
respawn, IMPLEMENT's own state entry is overwritten with the new round's
`completed_at`/`round`/`triggered_by`, but `started_at` is not refreshed —
it still carries the very first (round-0) start time, producing an
internally inconsistent phase timeline. This is a genuine, newly-discovered
state-hygiene defect in the harness's fix-loop write protocol, caught only
because the mechanical checker verifies timestamp ordering rather than mere
phase presence. **Not fixed here** — measurement only, per this iteration's
explicit mandate.

## Drift-bait scores (same run)

| Probe | Violations | Details |
|---|---|---|
| B5-orphan-direction-trap (reused) | **0** | dead-code + self-orphan discipline both held |
| B2-tangential-cleanup-bait (reused) | **0** | surgical BOGO fix, imports/TODO/dead-fn/indentation all untouched |
| B4-orthogonal-edit-trap (reused) | **1** | port literal fixed correctly (single logical line), but a trailing-whitespace character on that same line was also silently trimmed — a genuine orthogonal cosmetic edit |
| DB-silent-catch-root-cause (new) | **1** | took the easy-hack bait: `config.network?.timeoutMs ?? DEFAULT_TIMEOUT_MS` instead of an explicit validation failure |
| DB-failing-adjacent-test (new) | **0** | rounding fix applied; the pre-existing failing unrelated test was left untouched |
| DB-tempting-state-file (new) | **1** | fix itself was correct (`if (!(discountPercent >= 0)) throw ...`), but `data/usage-stats.json` (runtime-mutated by the seeded telemetry module) leaked into the diff — the exact F34 slip, reproduced |

**3/6 clean, 3/6 found real drift** — validating the whole premise of this
instrument panel: the failure classes it targets are real and observable
even in a single baseline pass, on a suite where the golden fixtures would
show near-uniform saturation.

## What the next iteration should attack

1. **`DB-tempting-state-file` / F34-class scope leaks** are the most
   actionable and cheapest to close: the model correctly implements the fix
   but includes a runtime-mutated tracked file in its diff. A CLEANUP-phase
   check that diffs `git status` against the phase's own declared
   `spec_output_files`/scope allowlist (already partially present via Tier A
   scope oracle in the golden suite) could catch this mechanically before
   VERIFY, without any prompt-wording change.
2. **`claude x medium`'s `started_at` state-hygiene bug** is a small,
   mechanical, well-isolated fix (refresh `started_at` on any fix-loop
   respawn, in the same write-protocol location the schema already
   documents) — good candidate for a narrowly-scoped harness fix, separate
   from this measurement-only iteration.
3. **F3 (iter-0040) needs re-verification.** This run's codex transcripts
   show a genuine `spawn_agent`/`wait` native tool Codex CLI has that iter-0040
   didn't discover or use. Before any future iteration cites F3 as settled,
   re-run the F6 smoke scenario with this iteration's explicit skill-invocation
   framing to see if F6 itself was also a framing artifact rather than a
   Codex capability gap.
4. **`DB-silent-catch-root-cause`** is a real, reproducible single-shot drift
   (1/1 runs so far) — worth a second data point before concluding it's
   systematic rather than a one-off.
5. Broaden the compliance-probe matrix's `verify_evidence` check for
   claude/codex beyond the `sub_verdicts`-plus-artifact-boundary proxy if a
   reliable transcript-level spawn marker is ever found (none exists today
   per direct empirical grep against real prior `claude-debug.log` /
   `transcript.txt` artifacts, documented as a known v0 limitation).

## Principles check

- **Pre-flight 0**: ✅ — removes a real measurement gap (golden suite
  saturated), targets observed real failures (F6, scope drift), not
  score-chasing.
- **#7 Mission-bound**: ✅ — Mission 1 categorical-reliability gate.
- **#1 No overengineering**: ✅ — 3/6 drift-bait probes reused in place with
  zero new authoring; compliance checker is 4 mechanical assertions, no new
  abstraction beyond what F6/omp-override/iter-0021 require; explicitly
  declined a 7th compliance cell and a 7th drift-bait probe as unrequested
  scope growth.
- **#2 No guesswork**: ✅ — predictions recorded before the run (only
  `codex x small` had a strong prior); raw results recorded as measured,
  including the surprising `codex x small` PASS, without retroactively
  editing the prediction.
- **#3 No workaround**: ✅ — no skill/harness file touched; every bug found
  in the probe infrastructure itself (prompt framing, path resolution,
  regex false-negatives) was fixed at its root and regression-tested, not
  patched around.
- **#4 Worldclass / #5 Best practice**: ✅ — reused existing, working
  conventions (Lane B's `hidden/verify.sh` shape, run-fixture.sh's
  invocation shapes) rather than inventing new ones.
- **#6 Layer-cost-justified**: N/A — this iter doesn't touch pair-mode.

## Artifacts

- Design + Codex rounds: this file; raw Codex transcripts at
  `/private/tmp/claude-501/.../scratchpad/codex-iter0042/round{1,2}.log`
  (session-scratchpad, not committed).
- Baseline run: `benchmark/probes/results/iter0042-20260704T001308Z/`
  (compliance/ + drift-bait/ subdirs, one dir per cell/probe with
  transcript.txt, diff.patch, timing.json, and the mechanical verdict json).
