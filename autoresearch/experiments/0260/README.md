# 0260 Saint-Exupéry rule ablation apparatus
`DESIGN.md` governs this run. B is 0257's sealed package; C removes the Saint-Exupéry bullet and changes “Three discipline rules” to “Two” in three package files. All apparatus files below come from 0259.

| File | 0259 origin and 0260 delta |
|---|---|
| `control.py` | Ordered two-source package edit; 0256 control import retained. |
| `prepare.py` | Experiment name only; B/C installation retained. |
| `instructions.py` | 0260 module names; validates the two-source edit and 0257 B seal. |
| `run_cell.py` | Experiment name only; loads local `quota.py`. |
| `quota.py` | 0259 retry-only authentication classifier; name only. |
| `driver.py` | Experiment name only; archives STOP and reruns the same slot. |
| `generate_cells.py` | Experiment name only. |
| `cells.tsv` | Byte-identical 0259 measured schedule. |
| `smoke.tsv` | Byte-identical 0259 SMOKE schedule. |
| `decide.py` | 0260 token; `RULE_IMPLICATED` and `RULE_PARTIAL` headlines. |
| `test_apparatus.py` | Two-rule fixtures, 0259 contract coverage, create/start failure tests. |
| `results/operator/judge.py` | 0260 runtime variables; Docker create/start and cleanup. |
| `results/witnesses/d3-parseoptions-override.js` | Byte-identical 0259 D3 witness. |
| `results/witnesses/f-malformed-json.js` | Byte-identical 0259 F10 probe. |
| `README.md` | 0259 operator guide adapted to this run. |

1. Build B's 0256 control root, then run `python3 autoresearch/experiments/0260/control.py <control-root>` to build C.
2. Create `~/.local/share/nx01/0260-live/runtime.json` with 0257 fields, `prior_runtime` pointing to 0257's `runtime.json`, 0260 output, and 95/95 caps.
3. Run `python3 autoresearch/experiments/0260/instructions.py seal <runtime.json>`.
4. Run SMOKE: `python3 autoresearch/experiments/0260/driver.py <runtime.json> autoresearch/experiments/0260/smoke.tsv`.
5. Run `python3 autoresearch/experiments/0260/instructions.py seal-forms <runtime.json>`.
6. Run measured cells with `python3 autoresearch/experiments/0260/driver.py <runtime.json> autoresearch/experiments/0260/cells.tsv`.
7. Set `NX01_0260_RUNTIME=<runtime.json>`; after grading run `python3 autoresearch/experiments/0260/results/operator/judge.py probe <F10 cells>` and `python3 autoresearch/experiments/0260/results/operator/judge.py run autoresearch/experiments/0260/results/witnesses/d3-parseoptions-override.js <D3 cells>`.
8. Audit every attempt, prepare audit and severe judgments in 0257's JSON format, then run `python3 autoresearch/experiments/0260/decide.py <output> <audit.json> <severe.json>`.
9. If `judge.py` stops because a container could not be created, never started or had no readable state, fix Docker or set `NX01_0260_JUDGE_SCRATCH` to an absolute directory under `/private/tmp`, then repeat the call; earlier cells stay recorded and the failed cell has no attempt.
