# Non-coding instrument lane — operator's guide

Measures the harness's NON-coding value axes (Block 8/10): intent-grasp and
work-packet quality, scored mechanically by hidden oracles — never by an LLM
"good plan" rubric. Frozen contract: `autoresearch/iterations/0070a-noncoding-instruments.md`
(pre-registration v2 + R1 amendment + Amendment 2). This README is the HOW;
the iteration file is the WHY and the binding rules.

## Instruments in this directory

| Instrument | Question it answers | Status (2026-07-13) |
|---|---|---|
| **Packet calibration (T0/T1)** — `calibration/` | Does packet quality causally drive a fixed executor's outcome? (prerequisite for Cell 2) | T0 PASS both seats; T1: catalog→sonnet ONLY, credential→terra ONLY (complementary override, risk-diff 1.0) → **routed-seat v2 protocol pending validation** (Amendment 2) |
| **Cell 1 Intent Holdout** — `cells/intent/` | Given identical goals, does the agent read repo evidence and act/ask correctly? (R = must proceed; Q = must ask THE discriminating question) | Fixtures frozen + replay-calibrated (20 replays). Bare-fails admission NOT yet run; report terra-conditional only |
| **Cell 2 Packet Utility Differential** | Whose packet (A harness / B bare / C method-card) makes the next agent succeed? | BLOCKED until routed-seat v2 validation passes |

## Commands

```bash
# Selftest everything (fast, run before/after any change here)
bash scripts/test-noncoding-harness.sh
bash cells/intent/test-intent-cell.sh

# Freeze-time hidden-input conformance gate (fixture dirs as args)
python3 scripts/conformance-gate.py calibration/catalog-source-order cells/intent/ledger-time-r ...

# One packet attempt (calibration path; --validate-only / --preview-prompt for dry checks)
python3 scripts/run-packet-attempt.py --fixture <id> --packet <path> --seat terra|sonnet \
  --attempt 1 --run-id <id> [--validate-only|--preview-prompt]

# Calibration cohort (T0 = 3× smoke/death; T1 = 16× establishing bar)
python3 scripts/calibration-driver.py --tier t0|t1 [--seats terra,sonnet] \
  --run-id <fresh-id> --interleave-seed <int>

# Cell 1 attempt / oracle replay (no models in replay mode)
python3 cells/intent/run-intent-attempt.py --help
```

Results land under `results/<run-id>-<tier>-<seat>/` (manifest.json = cohort
verdict + per-attempt ledger). Reference cohorts: `iter0070a-t0c-20260712`
(T0 PASS), `iter0070a-t1s/t1t-20260713` (the T1 seat×defect matrix).

## Binding rules (violations invalidate the measurement)

1. **No fixture retuning after results open** (anti-tuning). A failed fixture is
   reported dead, never repaired-and-rerun. Pre-count instrument defects get a
   DATED repair recorded in the iteration file.
2. **No main-checkout commits while a cohort runs** — the runner-hash freeze
   kills the cohort on any HEAD move (by design).
3. **No run-id reuse** — a dead/invalid cohort keeps its label; relaunch fresh.
4. **T1 frozen bar**: each good ≥12/16, each bad ≤4/16, risk-diff ≥0.50 with
   positive 95% interval, equivalent-good Δ≤2/16, no-op fails exactly.
5. **Seats**: measured codex = `gpt-5.6-terra` (explicit pin, never ambient
   config, never sol); claude = sonnet via `../ceiling/scripts/claude-isolation.py`.
   sol is team-review-only; fable is never a test arm.
6. **Budget windows**: cohorts consume the shared account limits (a T1 seat
   ≈160 attempts; the 2026-07-12 terra cohort died mid-run on a limit).
   Launch at a fresh window; keep other engine activity minimal.
7. **Routed-seat v2** (Amendment 2, unanimous): before Cell 2, freeze
   defect-family classifier + seat map, author ≥2 NEW fixtures per route
   OUTCOME-BLIND (authors never see T1 transcripts; Codex sol excluded),
   validate routed seat at full T1 + non-routed N=3 canary.
