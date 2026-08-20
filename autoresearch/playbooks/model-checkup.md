# Model-checkup playbook — new model ID → one-page verdict → re-pin

## 1. Purpose + trigger

Standing loop for a RECURRING event: a vendor ships model ID `M`, the harness
measures it, findings tighten the harness, the seat pin is re-decided. The three
instruments bound here are individually proven — recert + violation matrix
certified both exact opus IDs with `failures: []`
(`benchmark/seats/results/ckf0099-recert/recert-status.json`), and the frozen
discovery-corpus band returned two terminal verdicts on one sealed corpus
(`DECISIONS.md` 0102.1, 0103.1). Nothing here is a new instrument; this file is
the binding, the registration template (§9), and the tightening lane (§7).

**Trigger**: a new model ID becomes available for a seat this repo pins
(`.devlyn/engines.json`), or an existing pin's model version changes under it —
`CLAUDE.md:132` requires seat re-certification on any model/version change
BEFORE re-pinning. The user shorthand is "모델 체크업".

**It never writes a pin.** `seat-matrix.py` writes exactly two files,
`seat-matrix-<date>.json` and `.md` (`benchmark/seats/seat-matrix.py:707-713`);
`/devlyn:engines` is the only surface that touches `.devlyn/engines.json`
(`config/skills/devlyn:engines/SKILL.md:43,45,47`). The verdict page is a
decision input; the re-pin is a human act (§8).

## 2. Operator preconditions (binding — all pre-existing hard rules)

1. **Quiet account.** Never launch a matrix arm while other Claude sessions or
   headless reviews share the account (`HANDOFF.md:73-75`) — 0102 attempt 1 was
   burned this way, 45/128 rows session-limited (`DECISIONS.md` 0102.1).
2. **Launch window.** No launch between 23:00 and 01:00 KST
   (`HANDOFF.md:41-42`; frozen per-instance at
   `iterations/0103-opus-line-regression-cell.md:90`).
3. **Detached long runs + pre-frozen scorers.** Long unattended matrices detach
   via `python os.setsid()` — macOS has no `setsid`, and harness-tracked drivers
   were killed 3× before this rule; any scoring apparatus is frozen and
   pair-audited BEFORE its inputs complete (`HANDOFF.md:95`).
4. **Writer check** *(0104 binding — generalized from the instances below; no
   prior source states the general rule)*. Before any pipeline or matrix
   launch, confirm no other process is writing this repo's `.devlyn`. Observed
   instances that produced the rule are the PLAN-canary pre-launch writer
   checks (`iterations/0090-*.md:178`, `iterations/0091-*.md:247`); the
   operationalization is the 0103 preflight's `ps` snapshot, which blocks on
   any live `claude -p` / `codex exec` / `grok -p`
   (`~/.local/share/nx01/iter0103/prelaunch-and-arm.sh`, step 2).
5. **ONE evaluation per registration.** Attempts 1..3 exist ONLY to replace
   infrastructure-invalid launches on byte-identical digests; a valid miss is
   terminal, and there is no retuning
   (`iterations/0102-executor-quality-discovery-corpus.md:354-361`).

## 3. Step 0 — Compatibility preflight (run BEFORE anything else)

Resolve three identities, in this order. Each is a separate set; conflating
them is the failure this step exists to prevent.

**(a) Candidate** = the exact new model ID, verbatim as the CLI attests it in
`modelUsage` (e.g. `claude-opus-5`). Never an alias.

**(b) Recert set** = `{candidate} ∪ recert-legal seat incumbents`, where **seat
incumbents means the incumbents of EVERY seat this repo currently pins** — not
only the seat under decision. A checkup re-certifies the full pinned surface.
(Today only `executor` is pinned, so both readings coincide;
`.devlyn/engines.json`.)
`recert-seats.sh:108,114-123` admits exactly an exact ID matching
`^claude-[A-Za-z0-9.-]+$`, the legacy bare aliases `sonnet` / `opus`, or
`codex`; anything else exits 1 with `unsupported engine`. Use exact IDs only —
bare aliases record `"<claude --version>/<alias>"` as the model version
(`recert-seats.sh:179-180`), the alias-not-exact-ID hole iter-0099 shipped
exact-ID support to close (`DECISIONS.md` 0099.1). Corpus-only baselines never
enter the recert CSV.

**Name → exact ID, resolved BEFORE composing the CSV.** An incumbent is often
known only as an adapter/engine NAME (`.devlyn/engines.json` holds names, §8),
or the seat is unpinned and resolves by the binary claude↔codex complement
(`config/skills/_shared/engine-preflight.md:18-19`). Resolve first:

- `claude` → the exact ID the CLI currently defaults to, established by the
  1-turn `modelUsage` exact-ID smoke (§8 layer-2 mechanism); that exact ID, not
  the name, enters the CSV.
- `codex` → enters as the `codex` alias, the only recert-legal form for it.
  **Documented limitation**: recert does not attest a codex exact ID. It records
  `"<codex --version>/<$CODEX_MODEL or $OPENAI_MODEL>"` when both are present,
  otherwise the bare version string, otherwise the literal `"codex"`
  (`recert-seats.sh:181-183`) — an environment-declared value, never a probe of
  what actually answered. Note the asymmetry: an empty `claude --version` is a
  hard exit (`recert-seats.sh:165-168`); codex has no equivalent guard.

**(c) Corpus reference** — decision rule, FROZEN:

> IF the current seat incumbent (`.devlyn/engines.json` + the latest
> `benchmark/seats/seat-matrix-<date>.json`) is **runner-compatible** with the
> frozen corpus apparatus — i.e. a Claude-family exact ID that the pinned CLI
> can attest, because the driver invokes the pinned `claude` binary with
> `--model <engine>` and rejects anything outside `ALLOWED_ENGINES`
> (`benchmark/executor-quality/scripts/mx-driver.py:190-208,304-305`) — THEN
> reference = incumbent.
>
> ELSE (today's live pin is `{"executor": "codex"}`, `.devlyn/engines.json`)
> the band still runs against the last band-CURRENT Claude reference —
> `claude-opus-5` per `DECISIONS.md` 0102.1/0103.1 — to answer the
> Claude-family seat question, AND the verdict page carries the fail-closed
> label **"no cross-provider re-pin authority from this instrument"** on the
> incumbent comparison.

**The ELSE-branch reference is a corpus-only baseline.** It is chosen to make
the band runnable, not to be certified: it never enters the recert CSV (§3b),
its cells do NOT gate §6 row 1, and any pre-existing seat-matrix cells it
happens to carry may be cited on the verdict page as report-only comparison
context.

**Predecessor arm is OPT-IN.** Running `candidate vs same-line predecessor` (the
0103 shape) is added only when the regression question is explicitly asked.
Both arms only when both questions are asked — wall doubles: one 128-run cohort
is ~80-93 min at 2 lanes
(`iterations/0102-*.md:840`; `iterations/0103-*.md:222-223`).

## 4. Step 1 — Seat recert (instruments ① + ②), one invocation

```bash
bash benchmark/seats/recert-seats.sh \
  --engines <exact-id-csv> --run-prefix ck<NNNN>-<slug> [--reps 4]
```

`--reps` defaults to 4 (`recert-seats.sh:34`). The suites are `violation,
compliance, judge_quality, seat_matrix` (`recert-seats.sh:7-9`); the violation
matrix runs INSIDE the recert as the 6-probe drift-bait panel × models × reps
(`recert-seats.sh:128-133` → `benchmark/probes/scripts/run-violation-matrix.sh:30-39`),
compliance is one cell per engine (`:135-154`), judge quality is 2 reps
(`:156-161`), and `seat_matrix` runs last with the attested engine versions
(`:188-192`). An empty `claude --version` fails closed before any matrix is
written (`:163-168`).

Naming: run prefix is `ck<NNNN>-<slug>`; the suite derives the probe result
dirs as `<prefix>-violation-<model>-r<N>`
(`recert-seats.sh:57-59,128-133` → `run-violation-matrix.sh:41-48`).

Outputs: `benchmark/seats/results/<prefix>/recert-status.json` with
`{run_prefix, date, engines[], skip[], failures[]}` (`recert-seats.sh:66-82`)
plus `benchmark/seats/seat-matrix-<date>.json` / `.md` (`seat-matrix.py:710-713`).
A non-empty `failures[]` exits 1 (`recert-seats.sh:200-203`).

**Wall anchor** (measured, `ckf0099-recert` timing receipts,
`benchmark/probes/results/ckf0099-recert-violation-<model>-r*/drift-bait/*/timing.json`):
violation ≈ **26 min per model at reps=4** — 24 probe runs summing 1502 s
(`claude-opus-4-8`) and 1620 s (`claude-opus-5`).

**Guard**: do NOT add suites to `recert-seats.sh` during a checkup. A checkup
measures the model, not the instrument.

## 5. Step 2 — Discovery-corpus band (instrument ③), 0103-style

Instantiate §9's template into `autoresearch/iterations/<NNNN>-<slug>.md`, then
build the apparatus by the frozen recipe below.

**Apparatus derivation.**
- Copy the live canonical seed `benchmark/executor-quality/scripts/mx-driver.py`
  into the instance apparatus dir; the frozen copy — not later source edits — is
  the run receipt (`benchmark/executor-quality/README.md:35`).
- Inherit launcher, `run-bounded.py`, launch gate, and the sealed
  candidate-manifest from the most recent frozen apparatus
  (`iterations/0103-*.md:36-55`) **by full 64-hex digest**
  (`iterations/0103-*.md:178-188`) — every base bound by source path AND digest.
  An unavailable base fails closed, no substitution *(0104 binding — new; 0102
  and 0103 bind the digests but state no unavailability rule)*.

**Enumerated deltas (COMPLETE list per instance — nothing else changes;
`iterations/0103-*.md:57-81`):**

1. **Driver `ALLOWED_ENGINES` + launcher `ENGINES` → `{candidate, reference}`.**
   A TUPLE REPLACEMENT of whatever the live seed carries — today
   `frozenset({"claude-opus-5", "claude-opus-4-8"})` (`mx-driver.py:31`) —
   never a named-model `sed`. The driver's set governs membership
   (`mx-driver.py:304-305`); the launcher's `ENGINES` carries the ORDER, and it
   must be the same ordered pair as the derived scorer's
   (`iterations/0103-*.md:70-72`). Docstrings follow. Nothing else.
2. **Derived scorer.** Copy `benchmark/executor-quality/scripts/score-cohort.py`;
   single transformation `ENGINES` → `(candidate, reference)` with
   `ENGINES[0] = candidate` (`score-cohort.py:19`), so
   `delta = fail(ENGINES[0]) − fail(ENGINES[1])` = fail(candidate) −
   fail(reference) and **positive = candidate-worse**
   (`score-cohort.py:225-226`; order convention `iterations/0103-*.md:26-34`).
   The transformed `--self-test` must pass in full and is recorded pre-arm. The
   repo scorer and `freeze/scripts.sha256` are NOT modified.
3. **Launch-gate constants + freeze-file name**: `ENGINES` ordered pair, the
   receipt `engines` field, `FREEZE_FILE` → `frozen-<NNNN>-apparatus.sha256`,
   the inventory/`required` entry list, and the derived scorer's absolute path.

**Freeze inventory + trust invariants.** Commit the inventory to git — full
64-hex, one line per apparatus file (driver, launcher, `run-bounded.py`,
candidate-manifest, derived scorer, launch gate); the 0103 instance is
`iterations/0103-*.md:178-188`. Then the two pre-committed rules, PARAMETERIZED
(invariants preserved verbatim; only registration revision, freeze filename,
scorer filename, inventory keys, and digests vary):

- **R-A (pre-launch)** — immediately before the gate runs, the live
  `frozen-<NNNN>-apparatus.sha256` must equal the committed inventory (exact
  full-digest comparison against `git show <committing-revision>:<iteration
  file>`), AND the live files must hash to it. Any mismatch → **no launch**.
- **R-B (pre-score)** — before the derived scorer runs, for EVERY key in the
  freeze inventory the launch receipt's `apparatus_sha256[key]` must equal the
  committed digest. Mismatch → cohort **UNSCORED** (infrastructure-invalid),
  never scored. (The receipt legitimately carries one extra key, the pinned CLI
  `claude`, which the driver pins separately at `mx-driver.py:24-25`; it is not
  an inventory entry.)

These exist because the gate learns driver/launcher/self hashes from the
*mutable* freeze file — R-A/R-B close that coordinated-tamper class
(`iterations/0103-*.md:190-202,206-213`).

**Arming.** Sandbox tamper probes fail-closed, then **two-seat FREEZE-ARM**
(sol + grok, liveness, residual attack rights) before the launch
(`iterations/0102-*.md:417-421`; instance record `iterations/0103-*.md:206-216`).

**Evaluation.** ONE evaluation. The scorer's terminal token IS the decision and
the bijection is frozen (`score-cohort.py:185-193`, threshold `Fraction(3,20)`):

| token | meaning at this shape |
|---|---|
| `H1_CONFIRMED` | CI lower bound > 3/20 → candidate fails MATERIALLY MORE than the reference |
| `H1_MATERIAL_GAP_REFUTED` | CI upper bound < 3/20 → a material candidate-worse gap is EXCLUDED |
| `SATURATED` | both engines ≥ `run_count − 1` clean → band non-transfer datum |
| `INCONCLUSIVE_AT_PILOT_N` | CI straddles 3/20 |

`SATURATED` and `INCONCLUSIVE_AT_PILOT_N` neither confirm nor refute. The
cohort validity gate (2 exact engine IDs × 32 frozen tasks × 2 reps, unique run
ids, complete cell matrix, zero `infra_invalid`, requested==attested) is
mechanical (`score-cohort.py:83-161`; `benchmark/executor-quality/README.md:33`).

## 6. Step 3 — One-page verdict (manual assembly; no assembler script)

Fill this table by hand from the exact paths. Nothing is left to invention.

| Field | Source path |
|---|---|
| suite failures | `benchmark/seats/results/<prefix>/recert-status.json` → `failures[]` (empty = all suites passed) |
| engines + suites actually run | same file → `engines[]`, `skip[]` |
| seat recommendation — **REPORT-ONLY, not a decision input** (see the regress note below the decision table) | `benchmark/seats/seat-matrix-<date>.json` → `recommendation.executor`, `recommendation.pair_judge_priority` (`seat-matrix.py:565-569`) |
| per-seat cells | same file → `cells[]` each `{seat, engine_alias, metric, value, n, status, model_version.value, artifact}`; `status` ∈ `current`/`stale`/`unmeasured` (`seat-matrix.py:109-114,134-147`) |
| judge certification | same file → `judge_certification.<judge>` `{recall_rate, false_positive_rate, parse_errors, certified}` (`seat-matrix.py:314-326`) |
| drift totals | `cells[]` where `metric == "non_violation_rate"`, `value = (reps−violations)/reps`, `n = reps` (`seat-matrix.py:224-234`) |
| violations/reps + flip band | run `python3 benchmark/probes/scripts/violation-rate-matrix.py --run-prefix <prefix>-violation --out <path>` → `totals.<model>.{violations,reps}` and `matrix.<model>.<probe>.flip_band` (`violation-rate-matrix.py:58-64,74-75`). recert does NOT run this aggregator — it only writes the per-rep verdicts (`recert-seats.sh:128-133`) |
| corpus verdict | `<attempt-dir>/cohort-verdict.json` → `terminal`, `delta`, `ci`, `R`, `completion_rate`, `failed_tasks_by_class`, `ledger_sha256`, `per_task_d` (`score-cohort.py:239-250`) |
| cohort health | cohort ledger rows: attested N/N and `catastrophic` / `incomplete` / `infra_invalid` counts. Requested-vs-attested is enforced at `score-cohort.py:83,122`; cohort-level validity at `:133-161` |
| apparatus binding | `<attempt-dir>/launch-receipt.json` → `apparatus_sha256`, `engines`, `attempt`, `run_id`, `candidate_tree_sha256` |

**Then the TOTAL re-pin decision table.** Inputs: (i) the recert set's
suite-produced cells — **current** — and the run's **clean** bit;
(ii) corpus Δ sign + CI bounds (the
scorer's own threshold is +3/20, one-sided, in both terminal tests);
(iii) terminal token; (iv) runner-compatibility label from Step 0(c); (v) the
live pin.

Two predicates, mechanical — no other predicate words are used below:

- **clean** = `recert-status.json` `failures[]` is empty
  (`recert-seats.sh:66-82,200-203`).
- **current** = for EACH engine in the recert set, every cell its class's recert
  suites are EXPECTED to produce must **exist AND** have `status: "current"`
  (`seat-matrix.py:109-114`). A class-expected cell that is entirely MISSING is
  NOT current — existence is not guaranteed, because `add_unmeasured_cells`
  emits `unmeasured` placeholders only for seats with no populated cell at all,
  keyed on seat alone, so a seat populated by one engine leaves another engine's
  gap silently absent rather than `unmeasured` (`seat-matrix.py:515-531`). The
  ONLY exemption is a cell that is structurally absent by class (codex has no
  `drift_resistance`, below). The predicate is suite-scoped per engine class,
  never a flat "all three seats for every engine" — the suites do not route
  identically:

  | engine class | suites that run | seats produced |
  |---|---|---|
  | Claude-family (exact ID, or `sonnet`/`opus`) | violation + compliance + judge quality | `drift_resistance`, `orchestrator`, `verify_primary_judge` |
  | `codex` | compliance + judge quality only | `orchestrator`, `verify_primary_judge` |

  The routing is mechanical: only Claude tokens enter `CLAUDE_MODELS`, while
  `codex` joins `COMPLIANCE_ENGINES` and `JUDGES` alone
  (`recert-seats.sh:103-124`), and the violation suite runs solely over
  `CLAUDE_MODELS` (`recert-seats.sh:128-133`). Suite→seat identifiers come from
  the `make_cell(seat=…)` arguments — `drift_resistance` at
  `seat-matrix.py:180,227`, `orchestrator` at `:261`, `verify_primary_judge` at
  `:335` — not from `recert-seats.sh`, which names only suites.

  **Consequence, stated so row 2 stays reachable**: under a `codex` incumbent,
  codex's `orchestrator` and `verify_primary_judge` cells DO gate row 1, but its
  structurally-absent `drift_resistance` cell does NOT — an absent cell for a
  class that never produces one is not a freshness failure. Reading the
  predicate as "all three seats for every tested engine" would make row 1
  permanently true again and kill row 2. Related, and report-only: a codex cell
  can read `current` while its model identity is environment-declared rather
  than probed (§3b) — that limitation is context on the page, never a gate.

**Excluded from the predicate, by construction**: `implement_executor`,
`verify_pair_judge`, and `plan_ideate_designer` cells are built from HISTORICAL
run artifacts that no recert suite rewrites. Per-collector provenance, as the
live matrix carries it:

| seat | cells | built by |
|---|---|---|
| `verify_pair_judge` | 2/2 | two frozen auto-resolve gate JSONs (`seat-matrix.py:348-396`) |
| `implement_executor` | 6 of 8 | the 2026-05-10 combined-proof `judge.json`/`result.json` files (`seat-matrix.py:399-451`) |
| `implement_executor` | 2 of 8 | frozen `ceiling-verdict.json` runs, alias `codex` (`seat-matrix.py:492-501`, inside `collect_ceiling_cells` `:477-512`) |
| `plan_ideate_designer` | 2/2 | the same ceiling verdicts, alias `sonnet+codex stack` (`seat-matrix.py:502-511`) |

They are therefore permanently `stale` and CANNOT satisfy a freshness gate.
Live proof: after `ckf0099-recert` returned `failures: []`,
`seat-matrix-2026-08-05.json` still carries `implement_executor` 8/8 stale,
`verify_pair_judge` 2/2 stale, `plan_ideate_designer` 2/2 stale, while the
refreshed seats each hold current cells. 0100 already records the same hole — "`recommendation()['executor']`
remains unchanged and must not consume this seat … the empty `implement_executor`
hole" (`iterations/0100-main-ai-executor-quality.md:196-199`).

**Rows are evaluated TOP-DOWN, FIRST MATCH WINS.** The outcomes are exhaustive
but NOT mutually exclusive, so the order below IS the rule:

| # | Outcome | Fires when |
|---|---|---|
| 1 | **RECERT-REQUIRED** | not **clean** (`failures[]` non-empty), OR not **current** — i.e. some engine in the recert set has a class-expected cell that is `stale`/`unmeasured` OR entirely MISSING. Both predicates exactly as defined above; the sole exemption is a cell structurally absent by class (codex `drift_resistance`). Fail closed — no adoption call. |
| 2 | **NO-CROSS-PROVIDER-AUTHORITY** | incumbent is not runner-compatible (Step 0(c) ELSE branch). The page still carries the Claude-family-internal recommendation INSIDE this row — a decisive candidate-beats-reference result under a `codex` incumbent lands here, not on row 3 — but the incumbent comparison is not authorized by this instrument. |
| 3 | **RECOMMEND-REPIN(candidate)** | cells current + clean AND the corpus Δ is negative with the CI **upper bound below 0** (candidate fails strictly less) AND the terminal token is `H1_MATERIAL_GAP_REFUTED` — the only token compatible with adoption, since `H1_CONFIRMED` means candidate-worse. |
| 4 | **KEEP-INCUMBENT** | anything else — `SATURATED`, `INCONCLUSIVE_AT_PILOT_N`, Δ ≥ 0, a CI that includes 0, or `H1_CONFIRMED` (which, with `ENGINES[0] = candidate`, means the candidate is materially WORSE). |

**Why `recommendation.*` is NOT a row-1 condition.** `best_current()` and
`pair_priority()` return the `{"recommendation": "recert required", "seat": …}`
object whenever the seat has no `current` cell in their metric set
(`seat-matrix.py:534-545,548-562`). Because `implement_executor` and
`verify_pair_judge` are fed only by the historical collectors above, that object
is returned *permanently* — gating row 1 on it would make row 1 always true and
rows 2-4 unreachable, which is the infinite-"recert required" regress iter-0064
already had to close once (`iterations/0064-ceiling-seat-instrument.md:386-387`).
The fields stay on the page as report-only context.

**Explicit rule**: `H1_MATERIAL_GAP_REFUTED` alone NEVER decides adoption. It
covers both "candidate is clearly better" and "candidate is merely not
materially worse" — 0102 (Δ=−0.047, CI [−0.116,+0.016]) and 0103 (Δ=−0.181,
CI [−0.256,−0.109]) carry the same token and are not the same finding
(`DECISIONS.md` 0102.1, 0103.1). Adoption reads Δ sign + CI bounds.

**The recommendation at this step is PROVISIONAL** — it precedes tightening.

## 7. Step 4 — Tightening lane (standing process)

Every checkup surfaces harness defects, taxonomy gaps, and instrument misfires.
They are not footnotes; closing them is the loop's second half.

- **Register per finding** (id, evidence file:line, class), then close
  batch-style.
- **Implement**: terra direct-drive, depth-first — one finding fully closed
  before the next (`HANDOFF.md:36-45`: corpus authoring, apparatus builds, and
  repetitive runs go to the terra lane; fable stays design / adjudication /
  verification / planning).
- **Verify**: the trio — fable (mechanical + adjudication) + sol + grok. Round
  shape R0 findings → fix → R1 → FREEZE.
- **Receipts**: `~/.local/share/nx01/harness-<batch>-<date>/`.
- **Measurement-validity findings jump the queue.** A finding that touches
  whether the cohort measured what it claims forces the invalidate/re-run
  decision BEFORE the final recommendation is written.

Closed batch narratives live in `HANDOFF.md` and `DECISIONS.md`, never here —
this section is the process only.

## 8. Step 5 — Final re-pin (human act)

Order is **measure → tighten → re-pin** (`HANDOFF.md:21-22`, START-HERE
verbatim). The final recommendation follows tightening adjudication, not Step 3.

**No enactment on a non-adoption outcome.** Row 3 RECOMMEND-REPIN is the ONLY
§6 outcome that authorizes an enactment. On any of the three non-adoption rows —
RECERT-REQUIRED (1), NO-CROSS-PROVIDER-AUTHORITY (2), KEEP-INCUMBENT (4) —
NEITHER layer below applies: nothing is written to `.devlyn/engines.json`, and
no smoke attestation is run as enactment. The verdict page is retained as
report-only context for a future seat decision.

**Enactment is TWO-LAYER, and the checkup's verdict usually lands on layer 2**
*(0104 clarification — new; no prior source separates the layers)*. The reason
is mechanical: `/devlyn:engines` pins take an **adapter/engine NAME**, and any
name without a `_shared/adapters/<name>.md` file halts with
`BLOCKED:invalid-engine-config` (`config/skills/_shared/engine-preflight.md:21`;
`config/skills/devlyn:engines/SKILL.md:43-44`). Shipped adapter names today are
`claude`, `codex`, `grok`, `omp` (`config/skills/_shared/adapters/`). **An exact
model ID is therefore NOT a legal pin value.**

- **Layer 1 — seat ENGINE change** (e.g. `codex` → `claude`): the human writes
  the subcommand matching the SEAT UNDER DECISION — `executor <adapter-name>`
  for the executor seat, `pair <name>[,<name>...]` for the pair-judge seat;
  both surfaces exist and are not interchangeable
  (`config/skills/devlyn:engines/SKILL.md:43-45`). Pins are promises: pinned-but-unavailable stops with
  `BLOCKED:<engine>-unavailable`, never a silent downgrade
  (`engine-preflight.md:21`; `CLAUDE.md:48`).
- **Layer 2 — model WITHIN the `claude` engine** (the usual checkup outcome):
  `.devlyn/engines.json` is UNCHANGED. The claude adapter deliberately omits
  `--model` and uses the CLI's configured default
  (`config/skills/_shared/adapters/claude.md:33-34`), so the model selection
  lives in the engine CLI's own configuration, not in this repo. Enactment is
  therefore bound to the certified exact ID by an **exact-ID smoke
  attestation**, whose contract is:

  > One `claude -p` turn carrying `--model <exact-id> --output-format json`;
  > parse the JSON and assert `is_error` is `false` AND the `modelUsage` keys
  > equal exactly `[<exact-id>]`. Any other key set, or a missing/empty
  > `modelUsage`, fails the attestation — that is the uncertified-seat class.

  0103's preflight ran exactly this class of check before its launch
  (`iterations/0103-*.md:91-93` precheck — "modelUsage exact-ID, 1-turn smoke";
  `:218-221` prelaunch — "exact-ID smoke opus-5 + opus-4-8 OK"). A concrete
  argv exists at `~/.local/share/nx01/iter0103/prelaunch-and-arm.sh` step 4
  (`-p "Reply with exactly: OK" --model "$M" --output-format json
  --strict-mcp-config --allowedTools "Read"`, then `is_error is False and
  list(modelUsage) == [M]`) — **machine-local receipt, not a repo artifact**;
  the contract above is the durable form. Without that
  attestation the layer-2 re-pin is unverified: the seat is then certified by
  CLI-DEFAULT ALIAS rather than exact model ID — the exact gap the 2026-07-28
  diagnosis named and iter-0099 shipped exact-ID support to close
  (`docs/specs/iter0098-recert-exact-model-id/spec.md:7-15`), and the class the
  0103 lineage records as "an uncertified seat + one mis-score"
  (`iterations/0103-*.md:14-17`). The same iter also caught a live fail-open
  where an empty `claude --version` silently recorded a bare-token identity
  (`DECISIONS.md` 0099.1).

## 9. Registration template (copy to `autoresearch/iterations/<NNNN>-<slug>.md`)

Inherit this playbook's rule blocks BY REFERENCE. Do not copy §3-§8 prose into
an instance; cite the section. `⟨fill⟩` marks what each instance supplies.

**Identity is mechanical, not a judgment call.** `NNNN` = the next unused
integer after the last entry in `autoresearch/iterations/`
(`playbooks/iteration-loop.md:11`) — then a **reservation tie-break**: also scan
`HANDOFF.md` START-HERE and the `DECISIONS.md` tail for next-iteration numbers
reserved in prose, and take the lowest integer that is neither used by a file
nor reserved.
The slug is kebab-cased lowercase words; for a checkup it is FROZEN, leaving no
naming choice:

> slug = `model-checkup-` + the candidate exact ID with its vendor prefix
> stripped, where the vendor prefix is the leading segment up to and including
> the first `-` (e.g. `claude-`). An ID containing no `-` has no vendor prefix
> to strip and uses the full ID as-is.

Worked: candidate `claude-opus-6` → slug `model-checkup-opus-6` → iteration file
`autoresearch/iterations/<NNNN>-model-checkup-opus-6.md` → recert run prefix
`ck<NNNN>-model-checkup-opus-6` (§4). No-hyphen case: candidate `sonnet` → slug
`model-checkup-sonnet`.

````markdown
---
id: "⟨NNNN⟩-⟨slug⟩"
title: "Model checkup — ⟨candidate exact ID⟩ vs ⟨reference exact ID⟩"
kind: instrument
status: ⟨REGISTERED | DESIGN-FROZEN | CLOSED ⟨date⟩ — TERMINAL ⟨token⟩⟩
complexity: medium
depends_on: ["0102-executor-quality-discovery-corpus", "0103-opus-line-regression-cell"]
---

## Why this iter exists (pre-flight 0)
⟨What released, which seat it could take, why now.⟩ Flow, preconditions,
decision table, and tightening lane inherited from
`autoresearch/playbooks/model-checkup.md` §2-§8 — not restated here.

## Decisive criterion
The derived scorer's terminal token + Δ/CI decide; the §6 decision table maps
them to one of RECOMMEND-REPIN / KEEP-INCUMBENT / RECERT-REQUIRED /
NO-CROSS-PROVIDER-AUTHORITY.

## Step-0 resolution
- candidate: ⟨exact ID⟩ · recert set: ⟨csv⟩ · corpus reference: ⟨exact ID⟩
- runner-compatibility of the live incumbent: ⟨compatible | NOT — label carried⟩
- predecessor arm: ⟨not requested | requested because ⟨question⟩⟩

## Inherited by reference (all FROZEN)
| base | source path | full sha256 |
|---|---|---|
| corpus manifest | ⟨path⟩ | ⟨fill-at-derivation⟩ |
| launcher | ⟨path⟩ | ⟨fill-at-derivation⟩ |
| run-bounded | ⟨path⟩ | ⟨fill-at-derivation⟩ |
| launch gate | ⟨path⟩ | ⟨fill-at-derivation⟩ |

Any base unavailable → fail closed, no substitution. A base carried with ZERO
delta may have its digest filled in AT REGISTRATION TIME from the parent's
committed inventory — that digest is an already-committed fact, not a
derivation output. Any base receiving a delta, every fresh copy of a live seed,
and the derived scorer stay ⟨fill-at-derivation⟩ / ⟨fill-at-freeze⟩.

## Enumerated deltas (COMPLETE list)
1. driver `ALLOWED_ENGINES` → tuple replacement `{⟨candidate⟩, ⟨reference⟩}`
2. derived scorer `ENGINES` → `("⟨candidate⟩", "⟨reference⟩")`, `--self-test` full pass ⟨sha⟩
3. launch-gate constants + `FREEZE_FILE` → `frozen-⟨NNNN⟩-apparatus.sha256`

Nothing else.

## Pre-registered prediction
- **P-⟨NNNN⟩-1**: ⟨falsifiable statement about Δ⟩. Bijection:
  `H1_CONFIRMED` ⇔ ⟨narrative⟩ · `H1_MATERIAL_GAP_REFUTED` ⇔ ⟨narrative⟩ ·
  `SATURATED` and `INCONCLUSIVE_AT_PILOT_N` carried verbatim, neither confirms
  nor refutes.

## Freeze inventory (immutable root)
```
⟨64-hex⟩  mx-driver.py
⟨64-hex⟩  mx-launcher.py
⟨64-hex⟩  run-bounded.py
⟨64-hex⟩  candidate-manifest.json
⟨64-hex⟩  score-cohort-⟨NNNN⟩.py
⟨64-hex⟩  launch-detached.py
```
- **R-A (pre-launch)**: live `frozen-⟨NNNN⟩-apparatus.sha256` == this inventory
  (`git show ⟨committing-revision⟩:⟨this file⟩`) AND live files hash to it;
  mismatch → no launch.
- **R-B (pre-score)**: for every inventory key, launch-receipt
  `apparatus_sha256[key]` == the committed digest; mismatch → cohort UNSCORED
  (infrastructure-invalid), never scored.

## Sequencing
registration → seat review → FREEZE → apparatus build → inventory commit →
sandbox tamper probes → two-seat FREEZE-ARM ×2 → launch gate → ONE evaluation →
DECISION recorded here.

## Information boundary
This registration is FROZEN before any cohort row CONTENT or score is read;
only opaque row counts may be observed while a cohort runs.

## Budget/wall (informational)
violation ≈26 min/model at reps=4 (§4) · 128-run band ≈80-93 min at 2 lanes
(§3) · 64-run sonnet calibration ~35 min (`iterations/0102-*.md:791-792`).

## Receipts layout
`~/.local/share/nx01/iter⟨NNNN⟩/` — apparatus/ (incl. derived scorer), freeze
file, attempt dirs, cohort receipts, evaluation output
(`iterations/0102-*.md:491-503`). Cohort id = `mx<n>-<UTCSTAMP>Z`
(`iterations/0103-*.md:85-86`).

## Execution log
⟨append-only, dated; ends in a bolded DECISION paragraph⟩
````
