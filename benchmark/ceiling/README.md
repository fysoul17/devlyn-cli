# Ceiling lane — operator's guide

Measures the 세계최고/moat axis (NORTH-STAR ops #17) and the no-degradation
(no-suppression) bars. Contracts: `autoresearch/NORTH-STAR.md` § ceiling,
`autoresearch/iterations/0068-discriminating-corpus.md` (isolation v2, gate
semantics, Amendments A2/A3, closure addenda). This README is the HOW.

## Instruments

| Instrument | Question | Status (2026-07-13) |
|---|---|---|
| **3-arm tranche** `scripts/run-ceiling-tranche.sh` | A (devlyn) vs B (bare) vs C (copycat) on the frozen corpus — moat = A>best_B ∧ A>best_C, blind matched-wall | Ran twice honestly (0064/0067), FAIL-pilot both; corpus does not discriminate bare terra (0068 VALID-NEGATIVE) |
| **No-degradation cell** `scripts/run-nodeg-cell.sh` | On rows bare already solves: does the harness preserve outcome / quality / wall (cap 3.0)? | **MEASURED `nodeg-20260713`: objective 7/7 PASS, quality 0/7 FAIL (bare blind-preferred; codex judge 28/28 axes), wall 0/7 (7.7-30.4×, median ~8.9×)** — judge replay completed under protocol a′ (0068 closure addendum 4); re-measure with 0071 levers = next |
| **Seat matrix** `../seats/recert-seats.sh` | Which model fits which position; re-certify on model drift | 5 cells live; fail-closed pins |
| **Purity canaries** `scripts/claude-purity-canary.sh` | Does user context leak into measured claude paths? | FLIPPED clean 2026-07-12 (0070a.2) |

## Commands

```bash
bash scripts/test-ceiling-harness.sh              # manifest-driven selftest (43 assertions)
bash scripts/test-nodeg-cell.sh                   # nodeg driver selftest (no models)
bash scripts/run-nodeg-cell.sh --run-id <fresh> [--tasks F7,F12] [--resume] [--check-only]
bash scripts/run-ceiling-tranche.sh --run-id <fresh> [--tasks <rows>] [--resume]
python3 scripts/nodeg-cell.py judge --run-id <id> --repo-root <repo> --ceiling-root <this-dir> --resume
```

## Binding rules

1. Sequential by design — never run two measured cells/tranches in parallel
   on one machine (wall comparability).
2. No main-checkout commits mid-cohort (runner-hash freeze kills the run).
3. No run-id reuse; dead cohorts keep their labels as data.
4. Frozen best_B for the nodeg cell = Amendment A2 pointers
   (cohort `iter0068-gate-20260711h` + `iter0068-f12supp2-20260712`);
   controls `[F7,F25,F26,F11,F12,F23,FS1]`, `excluded_unfair=[F21]`.
5. Wall cap 3.0 per row (E1 dated registration). Quality bar = both judges
   valid AND A never below B on any axis — never relaxed post-hoc.
6. Measured seats: codex `gpt-5.6-terra` explicit pin; claude via
   `scripts/claude-isolation.py` (opaque HOME, env -i, seeded credentials).
   sol = team-only; fable never a test arm.
7. Budget windows: an A-arm row ≈ 30-60 min of claude+codex; a 7-row cell
   needs a fresh account-limit window (cohort `nodeg-20260712` died mid-run
   on the claude session limit — Amendment A3).
