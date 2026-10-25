# 0258 one-clause ablation apparatus

`DESIGN.md` is frozen; frozen identities and SMOKE are in [`registration.md`](registration.md). B is 0257's package; C deletes the registered clause in three package files. No cell has run.

| File | Origin and 0258 change |
|---|---|
| `control.py` | 0256 manifest mechanism; copy B to C, make exactly three byte deletions, seal both packages. |
| `prepare.py` | 0257 preparation; Claude-only B/C installs, arm package digest in each plan. |
| `instructions.py` | 0257 instruction assertion; separate B/C installer and Claude-form seals, B equality to 0257. |
| `run_cell.py` | 0257 runner; Claude-only instruction seal and arm package digest; Codex assessor limit guard remains. |
| `generate_cells.py`, `cells.tsv`, `smoke.tsv` | 0257 scheduler; two SMOKE then 64 serial D3/F10 B/C cells. |
| `driver.py` | 0257 driver and amendments 1–3; 95/95 caps from first dispatch, 14-day deadline. |
| `decide.py` | 0257 Fisher, Holm and attempt costs; 0258 P1/P2 readiness, headline, flags and predictions. |
| `results/operator/judge.py` | 0257 judge; two-pass D3 witness and one retry for unresolved F10 probe. |
| `results/witnesses/f-malformed-json.js` | Unchanged 0257 F10 probe. |
| `results/witnesses/d3-parseoptions-override.js` | New public parseOptions witness with a 10-second timeout. |
| `test_apparatus.py` | Offline fixtures and driver controls adapted from 0257. |

Common `cell.py`, `control.py` manifest helper, usage, checks, assessors and routes load unchanged from 0256/0233.

1. Build a 0256 control root with B, then run `python3 control.py <control-root>` to add C.
2. Create `runtime.json` under `~/.local/share/nx01/0258-live/` with the 0257 runtime fields, `output` in that root, `prior_runtime` pointing to 0257's `runtime.json`, and caps `{"seven_day":95,"five_hour":95}`.
3. Run `python3 instructions.py seal <runtime.json>`; run `python3 driver.py <runtime.json> smoke.tsv`.
4. Run `python3 instructions.py seal-forms <runtime.json>`; then `python3 driver.py <runtime.json> cells.tsv`.
5. Set `NX01_0258_RUNTIME` to `runtime.json`. After grading, run `judge.py probe <F10 cells>` and `judge.py run <d3-parseoptions-override.js> <D3 cells>`; both write under 0258 output.
6. Prepare audit and severe judgments in 0257's JSON formats, including every archived attempt. Run `python3 decide.py <output> <audit.json> <severe.json>`.
