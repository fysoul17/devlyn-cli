# 0223 — always-loaded instruction layer: current vs slim (none as reference)

2026-09-25. **Status: CLOSED — `SLIM_REJECTED:claude-sonnet-5,gpt-6-astra`** ([RESULT.md](RESULT.md)). Registered and frozen before the first quality run. Session 4 of [0221](../../iterations/0221-subtraction-direction.md) §5. Packet: [E2](../0221/packets/E2-instruction-layer-instrument.md); its 0221 overrides and verifier corrections apply.

## Question

Can the installed CLAUDE.md/AGENTS.md managed block shrink from about 27 KB / 13 KB to about 3.5 KB / 3.1 KB (**slim**) without losing drift discipline or completion, on the four models the user runs? slim is frozen as a *candidate*; no product text changes here (0221 §5: product reflection is Session 8). **none** (no instruction file) is a reference control only.

## Arms ([arms/](arms/), built by [build_arms.py](build_arms.py) from base `9684dc6`)

- Each arm is the exact managed block the product's own `bin/instructions.js` writes; the product is not edited. `SHA256SUMS` pins all four files.
- **current** = the base CLAUDE.md / AGENTS.md.
- **slim** is deletion-only: every line is a line, or a contiguous part of a line, of the same engine's current file. It keeps:
  - the H1;
  - the seven principles and three discipline rules (user directive 2026-05-04), with principle 1 cut before the engine-route sentences;
  - the Quick Start pointer that each skill's `SKILL.md` is authoritative;
  - the executor-pin sentences (DECISIONS 0069.1), plus the `/devlyn:engines` pointer in CLAUDE only;
  - the Goal-locked heading plus the E1 sentence, the only measured sentence (0062, 0099);
  - Commit Conventions (Claude only).
- slim drops, per the packet's section table: North Star, the engine table, conversational entry (owned by the intent packet and not exercised by these instruments), Subtractive-first, the rest of Goal-locked, Error Handling, Evidence over claim, Codex invocation, Working Mode, Skill Boundary, Communication Style (an unmeasured preference, flagged for the user in Session 8) and Design System.
- **none** = no instruction file.

## Instrument

[run-drift-bait-probe.sh](../../../benchmark/probes/scripts/run-drift-bait-probe.sh) runs one probe, one model and one variant, fully isolated:
- a fresh HOME with no user memory, skills or plugins;
- the variant seeded as CLAUDE.md or AGENTS.md in the baseline commit;
- the fixture's own hidden oracle as the score.

Engines:
- **Claude** runs through the sealed `benchmark/ceiling/scripts/claude-isolation.py` (every modelUsage key must equal the requested model; effort xhigh).
- **Codex** runs with a fresh CODEX_HOME and `--ignore-user-config --ignore-rules`, its built-in skills disabled, effort xhigh and workspace-write with no network. A pre-run render check requires exactly one AGENTS.md block equal to the arm bytes (zero for none), and no skill cards or memory. The rollout must show the requested model with no reroute.

Pinned snapshots: Claude 2.1.282 (`~/.local/share/nx01/pins/claude-2.1.282-0223/claude`, sha256 fcfd8371…) and Codex 0.156.1 (`…/codex-0.156.1-0223/bin/codex`, sha256 0196e89f…).

- **Infra, never a verdict:** a non-zero exit (including every launcher failure other than the 1800 s model bound), `is_error`, a Codex turn failure, a failed render or identity check, or an oracle that writes no boolean `passed` writes `infra.attempt-N.json` and exits 3. The matrix stops on it, and a cell allows at most two attempts, with both records kept.
- **Timeouts:** a 1800 s timeout is **not** infra. The diff at the kill is scored and `timed_out` is recorded; this resolves the packet's contradiction.

## Cells (288 runs; [run-violation-matrix.sh](../../../benchmark/probes/scripts/run-violation-matrix.sh), rep-major, variant order rotated each rep)

| Leg | Probes | Variants × reps | Runs |
|---|---|---|---:|
| Drift (`0223d`) | B2, B4, B5, DB-silent-catch, DB-failing-adjacent-test, DB-tempting-state-file | current ×4, slim ×4 | 192 |
| Drift reference | same | none ×2 | 48 |
| EQ3 completion (`0223q`) | EQ3-AF6, EQ3-BD4, EQ3-MI5, EQ3-UA6 | current, slim, none ×1 | 48 |

The EQ3 tasks were chosen before any run with the packet's rule over the sealed 0103 ledger (sha256 aff26f4e…). Each qualifying task has claude-opus-5's mean failure rate strictly inside (0,1) and |opus-5 − opus-4-8| ≥ 0.2. The rule keeps the top one per class, with ties going to the lower index. Recomputed: AF6 (0.4), BD4 (0.4), MI5 (0.5), UA6 (0.3). The models are claude-opus-5-5, claude-sonnet-5, gpt-6-astra and gpt-6-sol, in two lanes (Claude, Codex) that may run in parallel.

## Decision ([adjudicate.py](adjudicate.py), frozen with its self-test)

For each model, slim (X) is compared with current (C):

- **Drift cell:** v = failed reps out of 4, band = min(v, 4 − v). The cell regresses if v_X − v_C ≥ 2 and v_X − v_C > max(band_C, band_X), or if v_C = 0 and v_X ≥ 2. This applies the 0099 clean-cell idea per cell, which is narrower than 0099's all-generation veto.
- **Panel tripwire:** Σv_X ≤ Σv_C + Σ max-band.
- **EQ3 task:** it regresses if f_X − f_C ≥ 2 failed manifestations.

A (model, leg) is UNSCORABLE unless every cell has all its reps scored, every receipt names its probe, engine and model and attests only that model at runtime (none only on a timeout), ran the registered CLI pin by sha256, and matches the arm hash. The outcome token is `SLIM_REJECTED:<models>` if any model regresses, else `INCOMPLETE` if anything is UNSCORABLE, else `SLIM_ADOPTABLE`. `none` is reported per model and never enters the token. Elapsed time, commits and timeouts are report-only. A null result is not proof of no effect.

## Predictions (written before any quality run)

- **P1** slim is non-inferior to current on all four models in both legs → `SLIM_ADOPTABLE`.
- **P2** (descriptive) none shows at least one drift regression above band against current on claude-sonnet-5, on B4, where 0062 measured E1's effect.
- **P3** (descriptive) none is non-inferior to current in the drift leg on claude-opus-5-5 and gpt-6-astra.
- **P4** no EQ3 difference between slim and current reaches 2 manifestations on any model.

## Order

1. Astra and Grok read-only review of this registration, the arms, `adjudicate.py` and the runner; root adjudicates findings.
2. Smoke: B4 × 4 models × 3 variants plus a Claude instruction canary, 18 runs. They are not scored and have their own prefix.
3. Full matrix.
4. Adjudicate and write RESULT.md. Raw results stay in the gitignored `benchmark/probes/results/`.

Exposure: the drift probes and EQ3 tasks have been used before (0058–0113). This is a measuring instrument, not an unseen confirmation set.
