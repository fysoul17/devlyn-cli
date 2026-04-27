# 0012 — `timed_out` derivation fix (watchdog signal, not elapsed wall time)

**Status**: SHIPPED
**Started**: 2026-04-27
**Decided**: 2026-04-27 (same-day, surgical — no benchmark gate; dry-run smoke + bash -n + Codex pre-edit review)

## Hypothesis

`benchmark/auto-resolve/scripts/run-fixture.sh:508` derives `timing["timed_out"] = elapsed >= timeout`, then propagates that into `result.json["timed_out"]` (`:532`) and into `invoke_failure` (`:534`). The watchdog at `:315–322` already writes a flag file (`$RESULT_DIR/.timed_out`) when it actually kills the child, and post-wait at `:332–336` flips `INVOKE_EXIT=124` and removes the flag. The flag is the truth source for "did the watchdog fire"; the elapsed-derived field is a coarser proxy that mislabels two cases:

1. **Natural exit at `elapsed == TIMEOUT` exactly** — the original `>=` comparator labels this `timed_out=true` even though no watchdog kill occurred.
2. **Clean exits >TIMEOUT** — possible because the watchdog only triggers if `kill -0 $CHILD_PID` returns true at the budget mark. A child that exits naturally between the watchdog's sleep wakeup and the `kill -0` check (or after the SIGTERM grace) gets `elapsed ≥ timeout` but no flag — old code labels it `timed_out=true` despite the clean exit.

iter-0012 derives `timed_out` from the actual watchdog signal via a Bash sentinel `WATCHDOG_FIRED`, exported to the Python aggregator. No new schema fields.

## Mechanism

Why-chain (extending iter-0011 at #53):

54. Why is `elapsed >= timeout` the wrong source of truth? → `timed_out` should answer "did the watchdog kill the child?"; elapsed only answers "did wall time cross the budget?". With a 5-second SIGTERM grace at `:320`, the two questions diverge by up to ~5s, plus they diverge at the exact-equal boundary.
55. Why a Bash sentinel rather than reading `INVOKE_EXIT==124`? → 124 is also a legal natural exit code from a child process (e.g., a nested `timeout` invocation, or a coincidence). Coupling `timed_out` to exit code 124 would re-introduce ambiguity. The flag file is the only tracer that's set if-and-only-if our watchdog ran the kill path.
56. Why not preserve the flag file for Python to read directly? → `:334` removes it before T_END / Python aggregator runs. Adding a second persistence path (skip the rm, or write a copy) doubles the surface; an exported env var is one line and survives the same control flow.
57. Why `WATCHDOG_FIRED=0` initialized at `:264` (before the `if DRY_RUN` branch)? → `set -euo pipefail` is on (`:15`); `set -u` will fail the script when `export INVOKE_EXIT WATCHDOG_FIRED` runs in a dry-run path that never assigned the var. Pre-branch initialization avoids the trap. (Codex iter-0012 R0 caution.)
58. Root: the watchdog flag is the only authoritative signal for "timed out"; tracing it through a sentinel env var corrects all elapsed-boundary mislabels with no schema or downstream-consumer changes.

## Predicted change

Static-only (no benchmark gate, single-script surgical fix):

- **bash -n PASSES** — syntax clean.
- **Dry-run on F1 PASSES** — `set -u` doesn't trip; `result.json.timed_out=false`; script exits 0 cleanly.
- **No downstream consumer regression** — only `run-fixture.sh:534` reads `timing["timed_out"]`, and the new derivation gives the semantically-correct value (timeout iff watchdog killed).
- **F1 classification unchanged** — F1's flagged failure (`invoke_exit=124, elapsed=481, transcript=0`) is a real watchdog kill; flag was set; new derivation still labels it `timed_out=true`. The fix only changes labeling for natural-exit-at-or-past-budget cases.

## Diff plan

Single file, 4 surgical edits:

1. `benchmark/auto-resolve/scripts/run-fixture.sh` `:259–264` — initialize `WATCHDOG_FIRED=0` (with comment) before the `if DRY_RUN` branch. Required for `set -u` correctness.
2. `:278–280` — comment block extension noting WATCHDOG_FIRED propagation.
3. `:340–344` — inside the `if [ -f "$TIMEOUT_FLAG" ]` block, add `WATCHDOG_FIRED=1` next to the existing `INVOKE_EXIT=124`.
4. `:507` and `:521` — `export INVOKE_EXIT WATCHDOG_FIRED` (was `export INVOKE_EXIT`); replace `timing["timed_out"] = elapsed >= timeout` with `timing["timed_out"] = os.environ.get("WATCHDOG_FIRED", "0") == "1"` plus an explanatory comment.

NOT in this diff:

- **Boundary race** (`kill -0 $CHILD_PID` succeeding for a just-exited, not-yet-reaped process). Codex iter-0012 R0: real but very narrow; truly robust fix needs a single owner of wait+timeout (Python wrapper). Out of scope for a 4-line surgical fix.
- **New `watchdog_killed` schema field** — duplicates corrected `timed_out`. Codex iter-0012 R0: do not expand schema.
- **SIGTERM grace tuning** — leave the hardcoded 5s alone. After this fix it no longer leaks into `timed_out`.

## Falsification gate result (2026-04-27)

All gates passed.

### Bash syntax

```
$ bash -n benchmark/auto-resolve/scripts/run-fixture.sh
syntax OK
```

### Touchpoint audit

```
260: # iter-0012: WATCHDOG_FIRED is the truth source ...
264: WATCHDOG_FIRED=0
286-287: comment update
299: TIMEOUT_FLAG="$RESULT_DIR/.timed_out"
300: rm -f "$TIMEOUT_FLAG"
326:   : > "$TIMEOUT_FLAG"
340-343: if [ -f "$TIMEOUT_FLAG" ]; then INVOKE_EXIT=124; WATCHDOG_FIRED=1; rm; fi
507: export INVOKE_EXIT WATCHDOG_FIRED
521: timing["timed_out"] = os.environ.get("WATCHDOG_FIRED", "0") == "1"
545: result.json inherits
547: invoke_failure inherits
```

### Dry-run smoke (F1, bare arm)

```
"elapsed_seconds": 0,
"timed_out": false,
"invoke_exit": 0,
"invoke_failure": false
```

`set -u` survived; the export didn't trip on unset `WATCHDOG_FIRED`. ✓

## Codex collaboration

- **R0 (pre-edit, read-only review)**: presented the 5-line plan plus 4 invariant claims and 4 questions. Codex verdict: fix is the right surgical change. Concrete corrections:
  - **Invariant (ii) was misstated**: `elapsed=TIMEOUT-1` was *already* `false` under `>=`. The genuine false-positives are `elapsed == TIMEOUT` exactly and clean exits >TIMEOUT where the watchdog didn't fire. (Iteration text corrected to match.)
  - **`set -u` caution**: `WATCHDOG_FIRED=0` initialization MUST precede the `if DRY_RUN` branch or `export INVOKE_EXIT WATCHDOG_FIRED` will tear down dry-run paths. Already in plan; reaffirmed in implementation comment.
  - **Don't add `watchdog_killed` field**: duplicates corrected `timed_out`, expands schema. Skipped.
  - **Don't touch SIGTERM grace**: existing behavior; no longer leaks into `timed_out` after this fix. Skipped.
  - **Race on `kill -0`**: real but narrow; defer to a future Python timeout wrapper. Skipped per Karpathy #3.

## Lessons

- **Source-of-truth alignment**: when two signals coexist for the same predicate (the flag file and `elapsed`), pick the one set by the action you want to detect (the watchdog kill) and trace it explicitly. `elapsed >= timeout` was a proxy that drifted from the real signal under SIGTERM grace and at the exact-equal boundary.
- **`set -u` traps are silent until they fire**: pre-initializing every variable that downstream `export` or `${...}` references, in the branch where it's introduced, is one line of insurance against a class of dry-run / cold-path bugs.
- **Schema thrift**: don't add new result.json fields when an existing field can be corrected. Codex iter-0012 R0 #4 — minimum-surface fix beats verbose-but-redundant fix.
