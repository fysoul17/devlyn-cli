# iter-0068 — discriminating ceiling corpus (bare-fails gate + categorical-reliability trap tasks)

status: PRE-REGISTERED 2026-07-08 — design frozen before implementation;
corpus freezes (with the bare-fails gate results) before any A/C arm runs.
Direction chosen by user 2026-07-08 (corpus pivot, option A) after the
iter-0067 verdict + iter-0068-STUB A-arm decomposition.

**Serves**: Mission 1 ceiling axis / ops test #17. iter-0067 FAIL-pilot on 3
saturated SWE rows proved the ceiling corpus was measuring the pipeline
where a single agent already excels (all rows objective-non-discriminating,
no moat, 8.33× wall). This iter fixes the corpus so the ceiling can answer
the question that actually matters: **does the pipeline earn its wall where
its designed value lives — the categorical-reliability classes bare
systematically fails?**

## Why this exists (pre-flight 0)

One sentence: this iter builds the FIRST discriminating ceiling corpus — one
where bare single-shot codex is MEASURED to fail — so the next ceiling
go/no-go decision is made on tasks where the harness can plausibly win,
instead of on saturated tasks where no honest positive is even possible.
Measurement iter, permitted as the attribution run before the wall/claim
policy call (PRINCIPLES #0 carve-out); it directly unlocks iter-0069's
wall-vs-value decision.

## The core defect it fixes (from iter-0067 + the STUB decomposition)

All three tranche-2 rows were objective-non-discriminating (SW3/SW5
all-solve, SW4 all-fail). On such a corpus, LC1/LC2 objective lift is
structurally 0 and the verdict can only be negative or vacuous. The A-arm
wall (`iter0068-attack-the-wall-STUB.md`) is dominated by pair-VERIFY
(488-800s; pair_judge agreed with primary 3/3, never changed a verdict) and
orchestrator correction-loop gaps — but shaving that wall on tasks the
pipeline cannot win is the wrong mountain. The fix is upstream: **measure on
tasks where bare fails.**

## Design (first-principles commit; R0 to stress-test)

### Instrument innovation — the bare-fails gate (the load-bearing new piece)

A candidate row is ADMITTED to the discriminating tranche only if oracle
smoke shows BOTH:
1. **gold reference PASSES** the hidden objective oracle (existing
   oracle-smoke check), AND
2. **bare single-shot codex FAILS** the oracle on ≥ ⌈2/3⌉ of 3 attempts
   (NEW: the discrimination gate).

A row where bare passes is REJECTED with reason `saturated:bare-resolves`
(FS1 is the built-in positive control — it must be rejected: bare solved it
14/14 in tranche-1). A row where gold fails is `oracle-invalid` (existing).
This is the direct corpus-informativeness fix the iter-0067 verdict demanded:
the corpus can no longer admit a saturated row.

### Substrate — reuse the ceiling harness (0064/0067), add the gate

The ceiling harness already has 3-arm (devlyn/bare/copycat) + blind neutral
judge (de-biased in 0067) + wall/LC1-LC4 + oracle smoke + per-instance
oracle gate + manifest-derived allowlist. The only additions: the bare-fails
admission gate at corpus-freeze, and FS-format task packaging for the trap
tasks.

### Task source — categorical-reliability trap tasks (pilot: 2 + 1 control)

Port the two strongest, distinct-class trap fixtures from
`benchmark/auto-resolve/fixtures/` into ceiling FS-format (git repo at a
base sha + visible `task.txt` + `hidden/<oracle>.py` pass/fail test +
`hidden/reference.patch` gold), each mapping to a specific harness gate so a
win is attributable, not luck:
- **DR1 ← F11-batch-import-all-or-nothing** (state-integrity class): bare
  tends to partial-write on a mixed valid/invalid batch; the harness's
  VERIFY state-consistency probe + risk-probes target exactly this. Oracle:
  mixed batch leaves the store byte-unchanged after failure + an all-valid
  batch succeeds with distinct ids in order.
- **DR2 ← F7-out-of-scope-trap** (scope-discipline class): bare tends to
  "while I'm here" edit an unrelated file; the harness's PLAN
  authorized_surface + BUILD_GATE scope gate (iter-0046) + finish-gate
  (iter-0063) target exactly this. Oracle: the required behavior works AND
  the tempting out-of-scope file is unchanged from base.
- **Control: FS1** (schedule max_runs) — known bare-passes; MUST be rejected
  by the bare-fails gate. Proves the gate discriminates.

Pilot is deliberately 2 admitted rows — enough to prove the discriminating
instrument works and produce the first "pipeline earns its keep" data point
or its honest absence; scale to more classes (F12 signature, F21 priority)
in a follow-up once the gate + one tranche are validated.

**Port mechanics (for R0 to judge fidelity)**: each F-fixture today is
`setup.sh` (stages a base repo state + node verifier scripts) +
`expected.json` (verification_commands + forbidden_patterns) on the shared
`test-repo/`. The FS-format port packages the fixture's pre-task state as a
standalone git repo, commits it → `base.json {repo:local-path, sha}`, and
converts the `expected.json` verifiers into ONE hidden pass/fail oracle
(`hidden/oracle.sh` or `.js`) that boots the app and asserts the same
state (F11: failed-batch-leaves-store-unchanged + all-valid-succeeds;
F7: version-json-works + out-of-scope-file-unchanged-from-base). Gold =
`hidden/reference.patch`. The visible `task.txt` is the de-leaked spec
(F7's "Only touch bin/cli.js…" scope line stays visible — it IS the trap;
F11's "all-or-nothing" phrasing is softened so bare is not handed the
answer). The ceiling FS eval already runs an arbitrary hidden oracle
against a cloned+patched repo (FS1 precedent), so no eval-engine change —
only the oracle must be self-contained and language-present in the repo
(node, already there).

### Arms / judge / LC — unchanged from 0067

3-arm (A devlyn = sonnet orch + codex executor + pair-verify; B bare codex;
C copycat codex), N = round(wall_A/wall_B) capped [1,3], neutral blind judge
(sonnet+codex), LC1-LC4, objective-first. Test arms codex/sonnet only.

## Predictions (frozen before implementation)

- **P1 (the gate works)**: the bare-fails gate REJECTS FS1
  (`saturated:bare-resolves`, bare ≥2/3 pass) and ADMITS DR1 + DR2 (bare
  ≥2/3 fail, gold passes). If FS1 is admitted or a trap row is rejected, the
  gate is mis-calibrated → fix before any tranche.
- **P2 (first earns-its-keep signal)**: on the admitted trap rows, devlyn A
  resolves the objective oracle on ≥1 row where bare B fails — i.e. LC1
  A_resolved > best_B_resolved on at least one admitted row. This is the
  first objective lift the ceiling has ever been able to express (tranche-2
  could not). Recorded raw; a NULL result (A also fails the traps) is itself
  a load-bearing finding (the harness does not deliver categorical
  reliability on real-shaped traps → a much deeper problem than wall).
- **P3 (moat attribution)**: copycat C (codex told the full method) tests
  whether the METHOD alone catches the trap or the HARNESS GATES do. If C
  also resolves, the moat is the method (portable, weak); if only A
  resolves, the moat is the harness's deterministic gates (the real
  product). Recorded, not gated.
- **P4 (wall in context)**: LC3 wall ratio recorded — but now against a
  bare that FAILS, so "8× the wall of a wrong answer" reframes the
  efficiency question entirely (bare-best-of-N of a failing arm never
  resolves, so the economic baseline math changes). This is the reframe
  that makes the wall question honest.

## Loss conditions

- **L1**: P1 falsified (gate admits FS1 or rejects a trap row) → gate
  mis-calibrated, revert/re-tune before tranche.
- **L2**: oracle-invalid on a ported trap (gold fails its own oracle) →
  the port is wrong, fix the oracle before admitting.
- **L3**: the ported trap task leaks the trap answer in the visible
  `task.txt` (bare would pass by reading the spec) → re-author the visible
  spec to hide the leading keywords (the pair-fixture discipline:
  "public spec must hide leading keywords or solo aces").

## Implementation deliverables (Codex CLI; verification by orchestrator)

1. `ceiling` harness: bare-fails admission gate — a new
   `ceiling-corpus-gate` step (or extend oracle-smoke) that runs N bare
   attempts per candidate, records pass/fail, and writes admit/reject +
   reason into the manifest freeze. Reuse `run-ceiling-arm.sh --arm B` for
   the bare attempts; no new solver.
2. `benchmark/ceiling/corpus/DR1-batch-atomic/` + `DR2-scope-trap/`:
   FS-format port of F11 + F7 (base.json/task.txt/hidden oracle + reference)
   with the visible spec de-leaked per L3.
3. Manifest `tranche3` (or `discriminating` section) frozen with hashes +
   bare-fails gate results after the gate runs.
4. Oracle smoke: gold 2/2 pass + bare-fails evidence recorded.

## Pair rounds

- R0 (pending): Codex read-only xhigh on this pre-registration — stress the
  bare-fails gate honesty, the F11/F7→FS port fidelity, the 2-row pilot
  size, and the copycat-collapses-the-moat risk.
- R1 (pending): on the frozen corpus + gate results before A/C arms.

## Execution record

(pending)
