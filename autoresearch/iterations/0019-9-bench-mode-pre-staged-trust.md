# iter-0019.9 — bench-mode pre-staged trust + F9 false-signal verdict

**Status**: SHIPPED 2026-04-28 (commit `0f9e077`); F9 re-run verdict captured here
**Cost**: $0 patch + ~$10-15 paid F9 3-arm re-run on iter-0019.9 (RUN_ID `20260428T112748Z-0f9e077-iter-0019-9-F9-reverify`)

## Why this iter exists

iter-0020 Phase A preflight (5-fixture × 3-arm, RUN_ID `20260428T070814Z-7d5af00-iter-0020-phaseA-preflight`) computed `pair_policy_failure_count = 2` (F4 + F9). Investigation revealed F9's failure was **partially caused by iter-0019.8 itself**:

- F9 e2e novice flow runs `/devlyn:ideate` first, generating a NEW spec at `docs/roadmap/phase-1/1.1-gitstats.md`.
- That spec includes its OWN `## Verification` ` ```json ` block with `commitCount` / `topAuthors` field names + bullet-author format (ideate's interpretation of the user's vague task).
- iter-0019.8's `spec-verify-check.py:main()` UNCONDITIONALLY called `stage_from_source()` on any source markdown with a json block, **overwriting** the run-fixture-staged `.devlyn/spec-verify.json` that contained F9's `expected.json` truth (`commits` / `authors` / ranked).
- BUILD followed ideate's drifted contract; benchmark verifier rejected the run.

Without this fix the F9 row in iter-0020 Phase A read `verify=0.60 / score=74 / dq=true` — but those numbers measured iter-0019.8's bug, not pair-routing quality. Codex R-phaseA confirmed Q1 with file:line evidence and prescribed Option α: **fix iter-0019.8 first; then re-run F9**.

## Patch

`config/skills/devlyn:auto-resolve/scripts/spec-verify-check.py:main()`:

```python
pre_staged = spec_path.is_file()  # captured BEFORE any potential write
trust_bench_staged = bench_mode and pre_staged
if source_md is not None and not trust_bench_staged:
    # source-extract path — real-user mode, or benchmark with no
    # pre-staged file (rare future fixture without staging)
```

Real-user mode (BENCH_WORKDIR unset): unchanged. Source-extract still always overwrites; stale orphan dropped (Codex R2 #1 from iter-0019.8 stays closed).

Benchmark mode (BENCH_WORKDIR set):
- Pre-staged file exists at script start → SKIP source-extract → trust the pre-staged contract.
- No pre-staged file at start → source-extract fires (covers any future benchmark fixture without expected.json staging).

Plus closed a small Codex R2 caveat (real-user no-source-md + stale spec-verify.json now drops the stale, T17 added to smoke).

## Codex pair-review

- **R-phaseA** (68k tokens, 201s, xhigh): independently verified the diagnosis with file:line evidence at `run-fixture.sh:208`, `spec-verify-check.py:160` + `:256`, `diff.patch:249/266/89/96`, `expected.json:4/15`, `verify.json:4`. Verdict Option α (patch first, then re-run F9). Q3 also identified F4 as `browser=true → BUILD=Claude` candidate (later refined in iter-0020 Phase B scope).
- **R2** (61k tokens, 132s, xhigh) on actual diff: NO blocking findings. 4 small adopt-with-changes refinements: rename `skip_source_extract` → `trust_bench_staged`, fix stale fall-through comment, close real-user no-source-md gap (T17), update `build-gate.md:140` + `auto-resolve/SKILL.md:114` prose. All adopted before commit.

## F9 re-run on iter-0019.9 — verdict data

| Arm | Score | Verify | Wall | DQ | Critical findings |
|---|---|---|---|---|---|
| variant (L2) | 71 ⚠DQ | 1.00 (5/5) | 2772s | yes (judge-side silent-catch) | 3 (silent-catch in `safeReaddir`, unranked author lines, non-exact `Error:` stderr) |
| solo_claude (L1) | 92 | 1.00 (5/5) | 1506s | no | 1 (unranked author lines minor) |
| bare (L0) | 57 | 0.60 | 109s | no | 4 |

**Margins**: L2-L0 = +14 (PASS preferred ≥+8); L1-L0 = **+35** (PASS preferred ≥+8); L2-L1 = **-21** (FAIL floor +5).
**Wall ratios**: L2/L0 = 25.4×, L1/L0 = 13.8×, L2/L1 = 1.84×.

iter-0019.9 fix CONFIRMED:
- F9 verify mechanical contract now correctly enforced for both pair arms (verify=1.00 not 0.60).
- spec-verify.json post-fix contains BENCHMARK contract (`Commits:`, `commits`, `authors`) — verified via workdir inspection during run.

But F9's L2-L1 gap WIDENED (was -7 in stale Phase A, now -21):
- L1 jumped 81 → 92 because L1 was ALSO previously polluted by iter-0019.8's overwrite (Codex R-phaseA's prediction confirmed).
- L2 dropped 74 → 71 because judge still finds silent-catch + format issues that mechanical gate doesn't catch.

The pair-mode failure on F9 e2e is REAL and bigger than Phase A indicated. iter-0020 Phase B uses this verdict data.

## Principles 1-6 self-check

1. **No overengineering** — single guard expression `bench_mode and pre_staged` + 1 added cleanup branch (T17). No new abstractions, no new files. ✓
2. **No guesswork** — falsifiable hypothesis: "fix lets benchmark mode trust pre-staged carrier; real-user mode unchanged." 4 unit smoke tests + F9 paid re-run all matched predictions 1:1. ✓
3. **No workaround** — explicit BENCH_WORKDIR discriminator (the existing benchmark-mode signal at `run-fixture.sh:376`); not a heuristic. ✓
4. **Worldclass production-ready** — pre_staged captured BEFORE any potential write to avoid race; explicit error path on malformed pre-staged carrier (existing iter-0019.8 shape validation now applies universally per Codex R2 #2 from iter-0019.8). ✓
5. **Best practice** — uses the same env-var pattern already established by iter-0019.6's BENCH_WORKDIR usage; consistent with `os.environ.get("BENCH_WORKDIR")` semantics elsewhere in the script. ✓
6. **Layer-cost-justified** — patch is $0; F9 re-run was $10-15 (clean 3-arm baseline preferred over $5-10 variant-only that would have left L1 polluted per principle of same-instrumentation accounting). The re-run unblocks iter-0020 Phase B with trustworthy data. ✓

## Drift check (산으로?)

- **Removes a real user failure?** YES — closes the iter-0019.8 carrier-overwrite regression for benchmark mode. Real users without ideate-as-spec-source unaffected.
- **Expands scope beyond the diagnosed regression?** NO — single guard + small no-source-md cleanup. Nothing else touched.

## Lessons

1. **Synthetic pair-review can't see ALL run interactions.** Codex R1 + R2 in iter-0019.8 both reviewed scenarios but neither raised "what if the benchmark pre-stages AND the source has its own block?" because that scenario only exists when ideate runs as a sub-step of a benchmark fixture (F9). Defense: when a script touches a path consumed by both real-user and benchmark flows, the synthetic test matrix MUST include the "benchmark-with-source-block" cell explicitly named, not just "benchmark" + "real-user" axes. Updated iter-0019.8's lesson #1 ("pair-review with hypothetical scenarios is necessary but insufficient") with this concrete test-matrix prescription.

2. **The "fix increases visible damage" pattern.** iter-0019.9 fixed the carrier bug AND L1's score jumped +11. Both arms had been corrupted; fixing the bug exposed L1's real ceiling. When fixing measurement bugs, expect baseline shifts on ALL arms, not just the failing one. Plan baseline re-runs accordingly.

3. **Benchmark-mode signal hierarchy**. `BENCH_WORKDIR` is the load-bearing benchmark/real-user discriminator across iter-0019.6 onwards. New env signals (BENCH_FIXTURE_CATEGORY, BENCH_FIXTURE in iter-0020) all gate on BENCH_WORKDIR being also set, preserving the convention that real-user runs see no benchmark-mode behavior even if individual envs leak.

## What this iter unlocks

- iter-0020 Phase B routing decision (e2e → Claude) backed by trustworthy F9 re-run data.
- F9 carrier-overwrite class of bugs closed for benchmark-mode runs going forward.
