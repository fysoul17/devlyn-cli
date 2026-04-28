# iter-0019.8 — Real-user contract carrier (spec-verify gate for `/devlyn:auto-resolve`)

**Status**: SHIPPED 2026-04-28
**Branch**: `benchmark/v3.6-ab-20260423-191315`
**Parent decision**: HANDOFF "NEXT CONCRETE ACTION — iter-0019.8" + Codex R-halt verdict (2026-04-28) "iter-0019.8 BEFORE iter-0019.7 — real-user runs hit silent no-op without staged contracts"
**Cost**: $0 paid model spend (Codex iteration-loop pair: 2 rounds × ~115k tokens avg = ~230k tokens; ~10 min wall)

## Hypothesis

iter-0019.6 SHIPPED a mechanical output-contract gate (`spec-verify-check.py` reads `.devlyn/spec-verify.json` → emits `correctness.spec-literal-mismatch` CRITICAL findings → fix-loop reruns BUILD). The gate was demonstrably effective on F9 (verify_score 0.4 → 1.0, +14 score lift, single fix-loop round to convergence). But iter-0019.6 was **benchmark-only**: `.devlyn/spec-verify.json` is staged exclusively by `benchmark/auto-resolve/scripts/run-fixture.sh:200-219` from the fixture's `expected.json`. Real `/devlyn:auto-resolve` users land on `spec-verify-check.py`'s deliberate silent-no-op branch.

**Hypothesis (falsifiable)**: extracting a canonical ` ```json ` block from the spec/criteria source's `## Verification` section and writing `.devlyn/spec-verify.json` in `spec-verify-check.py` itself (single invocation site) materializes the contract for real-user runs without depending on benchmark staging. Predicted outcome:
- Real-user spec with json block: gate fires, runs commands, emits findings on mismatch (or PASSES on match).
- Real-user generated source without json block: emits `correctness.spec-verify-malformed` CRITICAL → fix-loop reruns BUILD with the finding.
- Real-user handwritten spec without json block: silent no-op (preserves iter-0019.6 backward compat).
- Benchmark fixture (pre-staged file): unchanged behavior.

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Codex R-halt (iter-0019.A audit, 2026-04-28) flagged ordering: iter-0019.7 (fix-loop enrichment) BEFORE iter-0019.8 (real-user carrier) was score-chasing because iter-0019.7 only matters once real users actually exercise the gate. NORTH-STAR test #14 (real-project trial gate) explicitly fails for an iter-0019.6 mechanism that only fires for benchmark fixtures. iter-0019.8 closes that gap; iter-0019.7 stays deferred until measurement on real-user runs shows whether fix-loop enrichment is needed.

This is a **carrier**, not a measurement iter. It does not change the gate semantics, the fix-loop routing, or the finding schema. It only ensures the contract reaches the gate on real-user runs.

## Principles 1-6 self-check

1. **No overengineering** — extending an existing script (250 → 521 LOC, all in service of self-staging + shape validation + check-mode) > adding a new abstraction. NO new SKILL.md PHASE 0 / PHASE 1 hooks (Codex R1 caught: would have invoked an invalid `phases.parse` per `pipeline-state.md:132`, would have validated AFTER the BUILD commit). NO new flags. NO LLM translation. The carrier is a single-file mechanical extract+validate+write. ✓
2. **No guesswork** — falsifiable hypothesis stated above. 12 unit + integration smoke tests (T1-T12) + 3 E2E paths cover happy, malformed-shape, malformed-json, generated-no-block, spec-no-block, stale-file (real-user mode drops it), benchmark-mode (trusts pre-staged with shape validation), pre-staged-with-bool-exit-rejected. Predictions matched 1:1 across all 17 tests. ✓
3. **No workaround** — strict json + full shape validation (rejects bool `exit_code`, whitespace-only `cmd`, empty `verification_commands` list); malformed → CRITICAL `correctness.spec-verify-malformed` (no silent fallback). Shape validation now applied to **pre-staged** carriers too (Codex R2 #2 — was previously only `isinstance(commands, list)`, letting bool exit_code / empty list slip through silently). The one preserved no-op is for handwritten spec-source without the block, explicitly documented as iter-0019.6 backward compat. ✓
4. **Worldclass production-ready** — no `any`/`@ts-ignore`/silent-catch/hardcoded values. Error messages cite source path + specific shape error (`verification_commands[0].exit_code must be int (not bool)` etc.). Stale-orphan file from killed prior run is actively dropped in real-user mode (Codex R2 #1 — central no-go pre-fix; cannot poison this run's gate). ✓
5. **Best practice** — `json.loads` (stdlib), `re.compile` once at module load, fenced markdown blocks (universal). Bool rejected explicitly (`isinstance(ec, bool) or not isinstance(ec, int)`) because Python's `bool` subclasses `int`. Single-purpose helpers. ✓
6. **Layer-cost-justified** — code-only iter, $0 paid runs. Bare-case BUILD_GATE wall-time delta: read pipeline.state.json + read spec.md + 2 regex runs + json.loads + json.dumps + write_text ≤ 50 ms. NORTH-STAR test #14 (real-project trial) closes for the contract-carrier dimension. ✓

## Drift check (산으로?)

- **Removes a real user failure?** YES. Without iter-0019.8, every real-user run silently bypasses the iter-0019.6 gate. The failure mode is the same shape as F9's iter-0016 prose-only `## Verification` (verify_score 0.4 across all engines) — empirically dead.
- **Expands scope beyond carrier?** NO. The diff does not touch BUILD/EVAL/CRITIC semantics, does not add a new gate type, does not change finding routing. Adds shape validation to pre-staged carriers (Codex R2 #2) — still in scope of the carrier ("the contract that reaches the gate must be well-formed").

## Codex pair-review trail

### Round 1 — design draft (verdict: No-Go As Drafted)

Sent: design draft v1 (`/tmp/iter-0019-8-design-draft.md`, 19 KB) + 9 specific falsification asks. Reasoning effort `xhigh`. ~138k tokens, 344s.

Five highest-risk findings, all adopted:

1. **Generated path silent no-op preserved**: original draft returned 0 on missing block in generated criteria → repeats the trap. Adopted: emit CRITICAL `correctness.spec-verify-malformed` on generated source missing the block.
2. **PHASE 1 validation placed AFTER `git commit`**: bad criteria committed before validation. Adopted: drop PHASE 0 / PHASE 1 SKILL.md hooks entirely; fold staging into `spec-verify-check.py` (BUILD_GATE entry).
3. **`phases.parse` is not a valid phase** per `pipeline-state.md:132` (valid set: `build`, `build_gate`, `browser_validate`, `evaluate`, `fix_loop`, `critic`, `docs`, `final_report`). Adopted: drop the `phases.parse` write entirely.
4. **Outer fence wrapper conflict** in `item-spec.md` template — inserting an inner ` ```json ` fence inside the existing ` ```markdown ` 3-backtick wrapper would prematurely close the outer. Adopted: bump outer wrapper to four backticks.
5. **Stale `.devlyn/spec-verify.json` is not handled**: archive_run.py PER_RUN_PATTERNS does not include spec-verify*.json*. Adopted: extend patterns; ALSO real-user-mode active drop logic in main() (R2 added — see below).

Per-Q answers also adopted: F1 prose-vs-expected.json gap (json fenced block confirmed), placement (single fold per Q6 minimal diff), criteria immutability (no round-2+ restaging), `bool` `int` subclass rejection, whitespace-only cmd rejection, empty list rejection, ideate post-write `--check` validation hook for LLM-hallucination catch, stale BUILD_GATE prompt text in SKILL.md:114 fix.

Deferred (not iter-0019.8 scope, no observed incident yet): destructive-command denylist (Q7) — speculative robustness against unobserved failure mode; queued as a future iter if any user reports concern.

### Round 2 — actual diff review (verdict: No-Go as drafted)

Sent: full git diff + smoke-test evidence (T1-T8) + per-edit verdict ask. ~94k tokens, 282s.

Four substantive findings, all adopted:

1. **Stale carrier still ships** — central NO-GO. The `if not spec_path.exists()` guard in main() means a killed prior run leaves `.devlyn/spec-verify.json` behind, and the next run's `if not spec_path.exists()` is False → skip self-staging → run stale contract. Codex's specific recommendation: "For non-benchmark real-user runs, derive/overwrite from current `pipeline.state.json` source instead of trusting an existing carrier." Adopted: re-architected main() to ALWAYS try self-staging from source first; fall back to pre-staged file only when (a) source has no extractable carrier AND (b) `BENCH_WORKDIR` env is set (benchmark-mode discriminator — matches existing convention at `spec-verify-check.py:48` and `run-fixture.sh:376`). Real-user mode drops stale orphans actively.
2. **Shape validation not applied to pre-staged carriers** — original code only checked `isinstance(commands, list)`. Empty arrays, bool `exit_code`, whitespace-only commands could slip through on the benchmark/pre-staged path. Adopted: apply full `validate_shape()` to pre-staged carriers; emit CRITICAL `correctness.spec-verify-malformed` on shape failure.
3. **Stale BUILD_GATE prompt in `auto-resolve/SKILL.md:114`** — still said "absent = silent no-op" and only mentioned `correctness.spec-literal-mismatch`. Adopted: rewrote the inline prompt to describe the three staging paths + both rule_ids + the new merge expectation for malformed findings.
4. **Ideate "opt-in" wording lets new generated specs omit the carrier** — recreates the original gap. Adopted: tightened ideate SKILL.md Phase 4 wording: newly generated specs with observable Requirements MUST ship the block; pre-carrier handwritten specs being copied/refactored continue to validate (block is omitted entirely → silent pass).

Per-edit verdicts: 1× adopt-as-is (phase-2-evaluate.md), 10× adopt-with-changes (all changes applied), 1× reject-as-drafted (main self-staging branch — re-architected to fix #1).

Subtractive audit applied: consolidated `get_source_type()` into `read_source()` returning `(source_type, markdown_path)` tuple — single state-read call. Kept `write_malformed_finding()` (used twice, schema is large). Kept `md_path.is_file()` check in `run_check_mode` (clean error vs traceback). Did not combine the two regexes (section/fence split is clearer).

## Edits

### 1. `config/skills/devlyn:auto-resolve/scripts/spec-verify-check.py` (250 → 521 LOC)

- Docstring rewritten to describe iter-0019.8 carrier semantics + the three staging paths + benchmark-mode discriminator.
- New helpers: `extract_verification_block(text)`, `validate_shape(data)`, `read_source(work, devlyn_dir)`, `stage_from_source(md, devlyn_dir)`, `write_malformed_finding(devlyn_dir, error, source_path)`, `run_check_mode(md_path)`.
- New `--check <markdown_path>` mode for ideate post-write validation hook.
- `main()` re-architected: always try self-staging first (overwrites pre-existing file when source has json block); fall back to pre-staged carrier only when source lacks the block AND `BENCH_WORKDIR` is set; real-user mode drops stale orphans; shape validation applied to ALL carriers.

### 2. `config/skills/devlyn:auto-resolve/scripts/archive_run.py`

- `PER_RUN_PATTERNS` extended with `spec-verify.json`, `spec-verify.results.json`, `spec-verify-findings.jsonl` so archive at run completion sweeps the iter-0019.8 carrier artifacts.

### 3. `config/skills/devlyn:auto-resolve/SKILL.md` PHASE 1.4 BUILD_GATE prompt

- Rewrote the inline Agent prompt to describe the three staging paths, both rule_ids (`correctness.spec-literal-mismatch` per failed command + `correctness.spec-verify-malformed` for missing/malformed carrier), and the merge expectation: concatenate `.devlyn/spec-verify-findings.jsonl` onto `.devlyn/build_gate.findings.jsonl` whenever findings are written. Exit 0 with no findings = silent no-op (handwritten spec without block — pre-iter-0019.8 contract preserved).

### 4. `config/skills/devlyn:auto-resolve/references/phases/phase-1-build.md` `<output_contract>`

- Generated-source bullet split into a sub-list (Requirements / Out of Scope / Verification with explicit json schema). Verification section explicitly mandates the ` ```json ` block; cites BUILD_GATE's enforcement loop and `correctness.spec-verify-malformed` rule_id; ties the source path to `state.source.criteria_path`.

### 5. `config/skills/devlyn:auto-resolve/references/build-gate.md` § "Spec literal check"

- Replaced the line citing "future iter" with a 3-staging-path enumeration (benchmark fixtures, real-user spec source, real-user generated source); cites the canonical schema location; documents handwritten-spec backward compat as iter-0019.6 → iter-0019.8 transition.

### 6. `config/skills/devlyn:auto-resolve/references/phases/phase-2-evaluate.md` `<quality_bar>`

- Updated "Verification-command literal-match" rule to cite BUILD_GATE's `spec-verify-check.py` as the **primary** mechanical gate (iter-0019.6 + iter-0019.8) and EVAL as second-line audit (duplicate findings only when BUILD_GATE was bypassed or the contract changed post-BUILD).

### 7. `config/skills/devlyn:auto-resolve/references/findings-schema.md`

- `correctness.*` line gained sub-bullets enumerating the two iter-0019.6/0019.8 rule_ids: `correctness.spec-literal-mismatch` (per-command exit/contains divergence) and `correctness.spec-verify-malformed` (carrier missing/malformed/shape-invalid).

### 8. `config/skills/devlyn:ideate/references/templates/item-spec.md`

- Outer markdown wrapper bumped to four backticks (so the inner ` ```json ` block doesn't prematurely close it). Added explanatory header about the wrapper convention.
- `## Verification` section now ships with: prose narrative for human reviewers (kept) + machine contract ` ```json ` block with placeholder commands and concise comment. iter-0019.8 implementation detail trimmed from the comment per Codex R2 #5.

### 9. `config/skills/devlyn:ideate/references/document-generation.md` `<spec_quality_criteria>`

- New "Verification" entry: newly generated specs with observable Requirements MUST ship the ` ```json ` block. Block omission allowed only for pure-design Requirements. Cites `--check` validation hook + iter-0019.8 carrier semantics + handwritten-spec backward compat.

### 10. `config/skills/devlyn:ideate/SKILL.md` Phase 4 DOCUMENT

- New "Post-write validation" subsection: after writing each item spec, run `python3 .claude/skills/devlyn:auto-resolve/scripts/spec-verify-check.py --check <spec.md>`. Exit 0 → proceed. Exit 2 → re-prompt to fix the json block; iterate until 0.
- "Carrier-block requirement": newly generated specs with observable Requirements MUST ship the block. Pre-carrier handwritten specs may omit (silent pass). Pure-design Requirements may omit entirely.

## Falsification — synthetic dry-run (no paid suite)

12 unit + integration smoke tests + 3 E2E paths in `/tmp/iter0019-8-smoke/`. All predictions matched.

| Test | Scenario | Predicted | Observed | Pass? |
|------|----------|-----------|----------|-------|
| C1 | `--check` well-formed json block | exit 0 | exit 0 | ✓ |
| C2 | `--check` no json block (handwritten) | exit 0 (opt-in) | exit 0 | ✓ |
| C3 | `--check` invalid JSON | exit 2 + JSONDecodeError | exit 2 + correct stderr | ✓ |
| C4 | `--check` `exit_code: true` (bool) | exit 2 + "must be int (not bool)" | exit 2 + correct stderr | ✓ |
| C5 | `--check` `verification_commands: []` | exit 2 + "at least one entry" | exit 2 + correct stderr | ✓ |
| T6 | spec source + json block, no pre-staged → self-stage + run | exit 0 | exit 0, .devlyn/spec-verify.json materialized | ✓ |
| T7 | source.type=="generated" + no json block | exit 1 + CRITICAL spec-verify-malformed | exit 1 + correct finding schema | ✓ |
| T8 | source.type=="spec" + no json block (handwritten) | exit 0 (silent no-op) | exit 0 | ✓ |
| T9 | stale spec-verify.json + handwritten spec source (no block) → real-user mode drops stale | exit 0 + stale dropped | exit 0 + file removed | ✓ |
| T10 | BENCH_WORKDIR set + spec source no block + pre-staged spec-verify.json | exit 0 + use pre-staged | exit 0 + ran echo BENCH | ✓ |
| T11 | BENCH_WORKDIR set + pre-staged spec-verify.json with bool `exit_code` | exit 1 + shape-rejected | exit 1 + correct shape error | ✓ |
| T12 | spec source WITH block + stale spec-verify.json from prior run → overwrite + use new | exit 0 + stale overwritten | exit 0 + spec-verify.json contains new content | ✓ |
| E2E-1 | Real-user happy path: --check + BUILD_GATE roundtrip | both exit 0 + materialize | both exit 0 + correct artifacts | ✓ |
| E2E-2 | Command fail (`false` vs expected exit 0) | exit 1 + CRITICAL spec-literal-mismatch | exit 1 + finding rule_id correct | ✓ |
| E2E-3 | ideate `--check` on shape-invalid `verification_commands: "not-an-array"` | exit 2 | exit 2 + correct stderr | ✓ |

## Lessons

1. **The carrier IS the work** — once iter-0019.6's mechanical gate exists, the next iter is "make it reachable from real-user paths," not "improve gate semantics." Codex R-halt caught this when iter-0019.7 was queued ahead — score-chasing on a benchmark-only mechanism is the iter-0008 trap at the carrier scope. (Pattern parallel: iter-0009 fixed wrapper distribution AFTER establishing the wrapper itself worked; carrier is to gate as wrapper-distribution is to wrapper.)

2. **Subtractive-first revisit during pair-review pays repeatedly**. Original draft had 2 SKILL.md hooks + 1 new script. Codex R1 collapsed it to 0 hooks + extend existing script. The dropped hooks would have introduced an invalid `phases.parse` (per `pipeline-state.md:132`) AND validated post-commit (bad criteria committed before validation could fire). Both bugs are subtle; neither would show in unit tests. Pair-review's value is most concentrated where the design has structural drift, not where it has typos.

3. **Stale state lives across runs**. Codex R2's central no-go was a stale `.devlyn/spec-verify.json` from a killed prior run being trusted on the next run. archive_run.py only sweeps at FINAL report — killed runs leave orphans. Defense-in-depth fix: BENCH_WORKDIR env var as the benchmark-mode discriminator + active drop in real-user mode. The lesson generalizes: any per-run artifact whose absence is a meaningful signal must be defended against stale presence too. Audit other `.devlyn/` artifacts with similar semantic load.

4. **Shape validation is cheap; skipping it is expensive**. Pre-iter-0019.8, `spec-verify-check.py` only checked `isinstance(commands, list)`. Empty arrays would have made "all 0 commands passed" vacuously true on any pre-staged carrier; bool `exit_code` would have slipped through. Codex R2 #2 caught this as a residual bug from iter-0019.6. The general principle: every entry point that consumes a structured contract must validate the contract — even if a different layer was supposed to validate first. Defense-in-depth at the read site is a cheap, mechanical check.

5. **The four-backtick markdown wrapper convention** for templates that contain inner three-backtick fences is non-obvious. The original draft would have produced a broken template that closed prematurely on the inner ` ```json ` block. Codex R1 #4 caught it. Lesson for future template work: when a template wraps content that itself contains fences, count the backticks.

## What this iter unlocks

- iter-0019.6 mechanical output-contract gate now fires on **real-user runs**, not just benchmark fixtures. NORTH-STAR test #14 (real-project trial gate) closes for the contract-carrier dimension.
- iter-0019.7 (fix-loop enrichment) stays deferred — measurement on real-user runs is now possible; if data shows fix-loop misroutes spec-verify findings, iter-0019.7 fires; if not, it closes as "data demonstrated no enrichment needed" per Codex R3 attribution discipline.
- iter-0020 (cost-aware pair policy + 9-fixture L0/L1/L2 paid run) is reachable with the carrier in place. The 9-fixture run will measure both (a) mechanical-gate effectiveness on real-user shape and (b) fix-loop convergence count for the new `correctness.spec-verify-malformed` rule_id.

## What this iter does NOT close

- Destructive-command denylist (Codex R1 Q7) — speculative robustness against unobserved failure mode. Queued for if/when an LLM-authored verification command actually destroys a user's repo.
- Forbidden_patterns silent-catch enforcement — separate enforcement layer per iter-0019.6 scope, still post-run-only.
- Tier-A waivers / scope oracles — separate enforcement layers, unchanged.
- Cross-skill script invocation policy — `python3 .claude/skills/devlyn:auto-resolve/scripts/spec-verify-check.py --check ...` from ideate is a Python interpreter call, not an engine routing concern (Codex R2 Q2b confirmed).

## Commit shape

Single atomic commit: 9 files modified (5 in auto-resolve, 4 in ideate), no new files (extension-only — subtractive-first wins for file count even with +271 LOC in the script). lint 11/11 PASS post-edit. Mirror parity clean.
