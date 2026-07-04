# iter-0053 — fix verify-merge-findings.py:789 sub_verdicts TypeError

**Status**: SHIPPED. Root-cause fix for the writer/reader contract mismatch
that crashed `verify-merge-findings.py --write-state` on literally every
real VERIFY completion. First recorded (found, not fixed) in
`autoresearch/iterations/0046-mechanical-drift-gates.md`'s scope, ranked #3
in `0048-human-language-robustness.md`'s next-classes list, and confirmed
**blocking a real run** in `0049-language-neutral-machinery.md`'s English
regression e2e, whose terminal verdict was `BLOCKED:infra-merge-script-crash`
solely because of this bug.

## Why-chain (root cause)

1. Why did `verify-merge-findings.py --write-state` crash with
   `TypeError: 'NoneType' object does not support item assignment` at line
   792 (`sub[source] = source_verdict`)? — line 789's
   `sub = verify.setdefault("sub_verdicts", {})` returned `None`, not `{}`.
2. Why did `setdefault` return `None` instead of inserting the default? —
   `dict.setdefault(key, default)` only inserts `default` when `key` is
   **absent**. When `key` is present with value `None` (as it always was
   here), `setdefault` returns the existing `None` unchanged — this is
   standard Python behavior, not a bug in `setdefault` itself, but the call
   site's assumption ("key is either absent or already a dict") was wrong.
3. Why was `sub_verdicts` present-and-`None` on every real run? —
   `state-phase-write.py`'s `do_spawn()` (line 99) unconditionally sets
   `entry["sub_verdicts"] = None` on every phase spawn, including VERIFY,
   as part of a **documented, deliberate** per-round reset contract:
   `references/state-schema.md#write-protocol` states spawn "nulls
   `completed_at`/`duration_ms`/`verdict`/`artifacts`/`sub_verdicts`" so a
   respawn can never inherit a prior round's stale data (the fix that
   `state-phase-write.py` itself shipped for, `autoresearch/iterations/0044-state-hygiene-fix.md`).
4. Why did the crash go unnoticed until a real e2e run? — `git log --oneline
   -- config/skills/_shared/state-phase-write.py` shows exactly one commit,
   `f02d06d` ("deterministic phase-lifecycle writer closes iter-0042
   state-hygiene defect"), which introduced the unconditional `sub_verdicts =
   None` nulling. `git log --oneline -- config/skills/_shared/verify-merge-findings.py`
   does **not** include `f02d06d` — the commit that changed what `sub_verdicts`
   legally looks like after spawn never touched the one function that reads
   it. A genuine writer/reader contract drift: one file's contract changed,
   the other file's assumption didn't move with it.
5. Why did the file's own `--self-test` not catch this regression? — every
   one of the pre-existing `self_test()` scenarios that reaches
   `write_state()` hand-seeds `"sub_verdicts": {}` directly in its fixture
   JSON (never `None`), sidestepping the actual shape a real
   `state-phase-write.py spawn` call produces. The self-test suite tested a
   state that never occurs in production and missed the state that always
   does.

Root invariant violated: **a value's legal shape must be verified where it
is consumed, not assumed from where it was last written.** `setdefault` is
the wrong tool whenever a key can legitimately already exist with a
placeholder value — it only guards absence, not shape.

## Legal-vs-illegal adjudication (per team brief)

- **`sub_verdicts is None` — LEGAL.** This is the intended, documented,
  always-present state immediately after any VERIFY spawn
  (`state-schema.md#write-protocol`), not a race condition, not a caller
  bug, and not conditional on timing — every real VERIFY phase completion
  goes `spawn` (nulls it) → checks run → `write_state` (must populate it) →
  `complete`. `write_state()` must model this state explicitly: treat it as
  "not yet computed" and populate a fresh `{}`.
- **`sub_verdicts` present as any other non-dict (string, list, number) —
  ILLEGAL.** No legitimate writer in this codebase ever produces this shape;
  it can only mean corrupted or hand-edited state. Per this repo's
  no-silent-fallback error-handling philosophy, this must fail loud with an
  explicit, actionable `SystemExit`, not be silently coerced into an empty
  dict alongside the legal `None` case — that would mask real corruption
  the same way a blanket `except: pass` would.

## Fix

`config/skills/_shared/write_state()` (and its `.agents` mirror):

```diff
-    sub = verify.setdefault("sub_verdicts", {})
+    sub = verify.get("sub_verdicts")
+    if sub is None:
+        sub = {}
+        verify["sub_verdicts"] = sub
+    elif not isinstance(sub, dict):
+        raise SystemExit(
+            f"error: phases.verify.sub_verdicts must be null or an object, got {type(sub).__name__}"
+        )
```

The fix lives entirely in the reader (`verify-merge-findings.py`), not the
writer (`state-phase-write.py`) — see Codex round below for why.

## Codex cross-check (1 round, `model_reasoning_effort=xhigh`, read-only isolated)

Presented the diagnosis, repro evidence, and an initial fix that blanket-coerced
any non-dict `sub_verdicts` to `{}`. Codex's response, read from the actual
source files (not the prompt alone):

1. Confirmed null/missing → fresh `{}` is correct: `do_spawn()`'s reset
   contract and `state-schema.md` both establish this as intentional.
2. Confirmed the fix belongs in `verify-merge-findings.py`, not
   `do_spawn()` — changing spawn to omit the key would contradict the
   explicit null-reset contract; changing spawn to write `{}` instead of
   `None` would weaken the "not yet computed" sentinel and populate
   `sub_verdicts` for every phase, when the schema says it is only ever
   populated for VERIFY.
3. **Substantive delta, adopted**: my initial blanket
   `if not isinstance(sub, dict): sub = {}` silently swallows genuine state
   corruption (e.g., a stray string) as if it were the legal placeholder.
   Proposed splitting `None` (coerce) from any other non-dict (fail loud) —
   exactly the pattern this repo's CLAUDE.md requires for error handling.
   Adopted verbatim (see Fix above).
4. Flagged (correctly, out of this iteration's scope): a *different*,
   pre-existing risk — `read_findings()` reads fixed filenames from disk
   regardless of round, and `do_spawn()` resets JSON state but not
   `.devlyn/verify.pair.findings.jsonl`-style artifacts, so a fix-loop
   respawn that runs a narrower check set than a prior round could still
   pick up stale prior-round findings files. Not this bug's failure mode
   (no crash, no wrong verdict from the None-handling this iteration
   closes) — noted here as a follow-up candidate, not silently dropped.
5. Noted the `.agents` mirror still had the pre-fix code at the moment of
   critique — already resolved by re-syncing after the delta was adopted
   (see Changes below).

One round converged with a concrete, adopted correction — no unresolved
disagreement, consistent with the team brief's "1+ round given small scope."

## Repro (before/after, real CLI calls — not fabricated JSON)

**Falsifiable prediction, stated before running**: with `pipeline.state.json`
containing `phases.verify.sub_verdicts: null` (the real, unedited output of
a `state-phase-write.py ... spawn` call), invoking
`verify-merge-findings.py --write-state` on the pre-fix code would raise
`TypeError: 'NoneType' object does not support item assignment` at line 792;
the same command on the fixed code would instead succeed and populate
`sub_verdicts` as a dict.

Actual, in a throwaway `.devlyn` dir:

```
$ python3 state-phase-write.py --devlyn-dir .devlyn --phase verify spawn --round 0 --engine claude
$ cat .devlyn/pipeline.state.json   # sub_verdicts: null, confirmed real spawn output

# pre-fix code:
$ python3 verify-merge-findings.py --devlyn-dir .devlyn --write-state
Traceback (most recent call last):
  ...
  File ".../verify-merge-findings.py", line 792, in write_state
    sub[source] = source_verdict
TypeError: 'NoneType' object does not support item assignment

# post-fix code, identical state:
$ python3 verify-merge-findings.py --devlyn-dir .devlyn --write-state
{"findings_count": 0, ..., "verdict": "PASS"}   # exit 0
$ python3 -c "..."  # phases.verify.sub_verdicts == {"judge": "PASS", "mechanical": "PASS", "pair_judge": "PASS"}

# illegal-shape path, post-fix:
$ python3 -c "... s['phases']['verify']['sub_verdicts'] = 'corrupt' ..."
$ python3 verify-merge-findings.py --devlyn-dir .devlyn --write-state
error: phases.verify.sub_verdicts must be null or an object, got str   # exit 1
```

Prediction confirmed exactly; the illegal-shape fail-loud path (added per
Codex's delta) also confirmed.

## Self-test additions

`verify-merge-findings.py --self-test` gained two scenarios (previously
every fixture that reaches `write_state()` hand-seeded `"sub_verdicts": {}`
directly, which is exactly why this regression shipped unnoticed):

1. Real spawn shape (`sub_verdicts: null`, `verdict: null`) → `write_state()`
   populates `sub_verdicts` correctly, no crash.
2. Corrupted shape (`sub_verdicts: "corrupt"`) → `write_state()` raises
   `SystemExit` with the expected message, not a silent coercion.

`python3 config/skills/_shared/verify-merge-findings.py --self-test` — exit
0, all scenarios pass (verified after each edit, not just at the end).
`python3 config/skills/_shared/state-phase-write.py --self-test` — exit 0,
unaffected (file not touched).

## Lint

`bash scripts/lint-skills.sh` — first run surfaced one failure,
`benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh: failed`
(Check 11's gate-test loop), in a file this iteration never touched.
Standalone re-run of that exact test script, both with this iteration's
diff stashed and unstashed, passed cleanly (exit 0) either way — attributed
to transient interference from a concurrent teammate's uncommitted edits to
`benchmark/probes/scripts/run-compliance-cell.sh` in the same shared working
tree during the first run, not a regression from this change. A second full
`lint-skills.sh` run immediately after: **all checks passed, 0 failures.**

## Real e2e (sonnet, throwaway repo, real `claude -p` subprocess)

Repro'd the exact scenario iter-0049 documented as `BLOCKED` on: a
hand-authored English spec (`<!-- devlyn:verification -->` sentinel +
sibling `spec.expected.json`) adding a `--loud` flag to a trivial
`bin/cli.js`, run via `/devlyn:resolve --spec docs/specs/loud-flag/spec.md`
in a fresh throwaway git repo with devlyn skills installed from this
iteration's fixed `config/skills/`.

**Before this iteration's fix** (per iter-0049's documented run of the
identical scenario): terminal verdict `BLOCKED:infra-merge-script-crash` —
VERIFY's own merge computation succeeded (`PASS_WITH_ISSUES`, 0 HIGH/CRITICAL)
but the pipeline crashed writing that verdict back to state.

**After this iteration's fix** (run id `rs-20260704T113650Z-c47c1525ac7c`,
archived at `.devlyn/runs/rs-20260704T113650Z-c47c1525ac7c/` in the throwaway
repo): terminal verdict `PASS` across every phase — plan (50s), implement
(43s), build_gate (74s, 0 findings), cleanup (35s), verify (mechanical+judge
PASS, pair not triggered), final_report (PASS). Direct read of the archived
`pipeline.state.json` confirms `phases.verify.sub_verdicts` is a fully
populated dict (`{"judge": "PASS", "mechanical": "PASS", "pair_judge":
"PASS"}`, matching `verify-merge.summary.json`'s `source_verdicts`) — the
exact transition from the `null` spawn state (confirmed mid-run, before this
fix would have crashed here) to a populated dict that used to `TypeError`.
The throwaway repo's own git log (`3140d9c chore(pipeline): implement`)
shows a real commit; `node bin/cli.js --loud` → `HELLO LOUD`, `node bin/cli.js`
→ `HELLO` — the feature actually works, not just the pipeline plumbing.

## Adjacent, explicitly NOT fixed this iteration

- Stale findings-file reuse across a fix-loop respawn (Codex point 4 above)
  — a different bug class (no crash, not exercised by this iteration's
  scope), flagged as a follow-up candidate, not silently absorbed or
  ignored.

## Changes

- `config/skills/_shared/verify-merge-findings.py` — `write_state()`'s
  `sub_verdicts` handling (the fix above) + two new `--self-test` scenarios.
- `.agents/skills/_shared/verify-merge-findings.py` — synced byte-identical.
  (`.claude/skills/_shared/` is a gitignored local runtime install artifact,
  not a tracked mirror — regenerated by `node bin/devlyn.js`, not hand-synced.)
