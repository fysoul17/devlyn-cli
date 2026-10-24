# 0257 apparatus

`DESIGN.md` is frozen; the measured result is in [`RESULT.md`](RESULT.md); [`amendment-1.md`](amendment-1.md) (2026-10-22) replaces its account rule, [`amendment-2.md`](amendment-2.md) (2026-10-22) replaces its window reserve with a 95% exhaustion guard, and [`amendment-3.md`](amendment-3.md) (2026-10-23) handles proven Docker daemon loss as an archived infrastructure fault. All measured cells are fresh; 0256 data only qualifies the apparatus.

| File | Origin and delta |
|---|---|
| `generate_cells.py`, `cells.tsv`, `smoke.tsv` | 0256 generator; 328-cell interleaved schedule, four SMOKE cells. |
| `endpoints.json` | New frozen 43-test development and 11-test confirmation families per engine. |
| `decide.py` | 0256 decision; pooled counts and witnesses, safety for both arms, exact Fisher/Holm, Wilson-MOVER, attempts, predictions and unscored probes. |
| `driver.py` | 0256 dispatcher; any host account; 95% Claude window guard, per-cell account fingerprints, restart-safe 21-day deadline, amendment-bound harm latch, SMOKE qualification gate, and Docker teardown proof before fault archive. |
| `prepare.py` | 0256 preparation; records pre/post instruction hashes, both installed skills and installer output. Uses 0256's task override. |
| `run_cell.py` | 0256 runner; instruction assertion before grading and two added seal digests. |
| `instructions.py` | New offline installer and owner-form seals; checks all four SMOKE cells after sealing, then per-cell instructions. |
| `fixtures/instruction-shapes.json` | Minimal non-secret transcript/trace shapes from 0256 d02/d03; content shortened. |
| `fixtures/endpoint-ids.json` | Oracle row IDs extracted from six 0256 verdicts; validates the frozen families offline. |
| `results/operator/judge.py` | 0256 judge; 0257 runtime and malformed-JSON probe command with bounded timeout cleanup. |
| `results/witnesses/f-malformed-json.js` | New non-gating F10/F11 malformed-JSON probe with absolute request deadline and independent POST class. |
| `test_apparatus.py` | 0256 contract themes adapted to 0257; changed rules tested offline with fakes. |

Unchanged `cell.py`, `control.py`, `record_usage.py`, and other common modules load from 0256/0233; no copies are kept here. No direct runner is registered.

Before SMOKE, create the run's `runtime.json` with `output` under the 0257 runtime root and caps `{"seven_day":85,"five_hour":70}`; run `python3 instructions.py seal <runtime.json>`. Run `smoke.tsv` alone; after all four SMOKE sessions, run `python3 instructions.py seal-forms <runtime.json>`. It refuses a violation and records passed qualification, required before `driver.py` dispatches `cells.tsv`. The operator tool reads `NX01_0257_RUNTIME`: `judge.py probe <cell>...` writes 0257 `probes.json`; `judge.py qualify-probe <0256-runtime.json> c01-F10-claude-A-r1 c02-F10-claude-B-r1` prints qualification results without modifying 0256. `driver.py --clear-latch <existing-amendment-file> <runtime.json>` records the amendment and latched verdict digest before clearing; after SMOKE, set caps to `{"seven_day":95,"five_hour":95}` and run `driver.py --amend-caps amendment-2.md <runtime.json>` to register the dated change.
