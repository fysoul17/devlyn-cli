# 0259 No overengineering ablation apparatus

`DESIGN.md` is frozen; frozen identities and SMOKE are in [`registration.md`](registration.md). B is 0257's sealed package; C deletes rule 2, changes the rule count to six, and renumbers rules 3–7 in three package files.

| File | 0258 origin and 0259 delta |
|---|---|
| `control.py` | Copy; apply the ordered rule deletion, count change, and renumbering exactly once per source text in each target. |
| `prepare.py` | Copy; experiment name only; B/C install stays unchanged. |
| `instructions.py` | Copy; assert the shared ordered edit in installed and loaded forms. |
| `run_cell.py` | Copy; experiment name only. |
| `generate_cells.py` | Copy; experiment name only. |
| `cells.tsv`, `smoke.tsv` | Byte-identical copies; 64 measured cells and two SMOKE cells. |
| `driver.py` | Copy; experiment name only. |
| `decide.py` | Copy; 0259 token and PRINCIPLE headlines. |
| `test_apparatus.py` | Copy; seven-rule fixtures, exact six-rule output and failure cases for every edit source, real B check when available, and pinned instrument hashes. |
| `results/operator/judge.py` | Copy; 0259 runtime variable; original witness output markers retained. |
| `results/witnesses/d3-parseoptions-override.js` | Byte-identical D3 witness. |
| `results/witnesses/f-malformed-json.js` | Byte-identical F10 probe. |
| `README.md` | Rewritten 0258 operator guide for the 0259 paths and ordered edit. |

1. Build the 0256 control root with B; run `python3 autoresearch/experiments/0259/control.py <control-root>` to build C.
2. Create `~/.local/share/nx01/0259-live/runtime.json` with 0257 fields, `prior_runtime` pointing to 0257's `runtime.json`, output in the 0259 root, and 95/95 caps.
3. Seal with `python3 autoresearch/experiments/0259/instructions.py seal <runtime.json>`.
4. Run SMOKE with `python3 autoresearch/experiments/0259/driver.py <runtime.json> autoresearch/experiments/0259/smoke.tsv`.
5. Seal forms with `python3 autoresearch/experiments/0259/instructions.py seal-forms <runtime.json>`.
6. Run measured cells with `python3 autoresearch/experiments/0259/driver.py <runtime.json> autoresearch/experiments/0259/cells.tsv`.
7. Set `NX01_0259_RUNTIME=<runtime.json>`; after grading, run `python3 autoresearch/experiments/0259/results/operator/judge.py probe <F10 cells>` and `python3 autoresearch/experiments/0259/results/operator/judge.py run autoresearch/experiments/0259/results/witnesses/d3-parseoptions-override.js <D3 cells>`.
8. Audit all attempts, prepare audit and severe judgments in 0257's JSON format, then decide with `python3 autoresearch/experiments/0259/decide.py <output> <audit.json> <severe.json>`.
