# 0265 — bare vs the installed harness (`devlyn run`, 4.3.30), fast replay

[`DESIGN.md`](DESIGN.md) is the design: DRAFT r3 (2026-11-11), not frozen, no cell run. It measures, per engine
(Claude Opus 5.5; GPT Astra through Codex), what `devlyn run` with the published `devlyn-cli@4.3.30` adds over the
same session started raw, on 0233's tasks D3, D4, B5, F10 and F11, 8 replicates per arm (160 cells), in two lanes.
It reads whether 0257's two large signals replicate (codex B5, claude F10), then a completion line and a harm line
whose limits are printed with them. [`audit-rule.md`](audit-rule.md) is the rule the false-completion judges and the
mechanical harm check apply.

r2, the 328-cell powered design, is in this branch's history (`ffc7b97f`, `5fd9a2a0`); DESIGN.md says why r3 replaced
it.

## Operator

From the root of the worktree at the registration commit, with `X=autoresearch/experiments/0265` and
`R=~/.local/share/nx01/0265-live`, one command per line, in order. **Model** marks a step that makes model calls; every
other step makes none. A step that writes its file once (the seal, `q3-*`, `q8-*`) refuses while that file exists: move
it aside before repeating the step on another commit.

1. Q1 unit tests: `python3 -m pytest -q $X`
2. Runtime root (clones, issue snapshots, the 4.3.30 tarball, the image, control trees, runtime files naming the Codex login the run uses, by the absolute path of its `auth.json`): `python3 $X/setup_runtime.py --codex-auth <auth.json>`
3. Q2 launch probe and seal (recording shims, no credential): `python3 $X/instructions.py seal $R/runtime-smoke.json`
4. Q3 strict config, **model** (one Codex call, the allowed one): `python3 $X/strict_config_check.py --run-exec $R/runtime-smoke.json`
5. Q5 witness and probe controls (about 20 min): `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py controls`
6. Q6 calibration, **model** (both judge seats per pair), the gate: `python3 $X/fc_judge.py calibrate $R/runtime-smoke.json`
7. Q6 held-out score, **model**, never a gate: `python3 $X/fc_judge.py calibrate $R/runtime-smoke.json --held-out`
8. Q7 SMOKE, **model** (four owners and their assessors, one process): `caffeinate -dimsu python3 $X/driver.py $R/runtime-smoke.json $X/smoke.tsv`
9. SMOKE's forms and assertions: `python3 $X/instructions.py seal-forms $R/runtime-smoke.json`
10. The harm check on SMOKE as a control (no finding expected): `python3 $X/harm_check.py $R/runtime-smoke.json smoke-claude-A smoke-claude-B smoke-codex-A smoke-codex-B`
11. Q8 (a), D3 and D4 checks in two owner-shaped containers at once: `python3 $X/rehearse_memory.py checks`
12. Q8 (b) memory sampler, in its own terminal, left running: `python3 $X/rehearse_memory.py sample --out $R/q8-sample.json --until-file $R/q8-done`
13. Q8 (b) claude lane, **model**, in its own terminal: `caffeinate -dimsu python3 $X/driver.py $R/runtime-claude.json $X/rehearsal.tsv`
14. Q8 (b) codex lane, **model**, at the same time in another: `caffeinate -dimsu python3 $X/driver.py $R/runtime-codex.json $X/rehearsal.tsv`
15. When both rehearsal lanes have ended, stop the sampler: `touch $R/q8-done`
16. Claude lane, **model**, in its own terminal: `caffeinate -dimsu python3 $X/driver.py $R/runtime-claude.json $X/cells.tsv`
17. Codex lane, **model**, at the same time in another (after step 16 has ended when Q8's rule leaves under 1 GiB): `caffeinate -dimsu python3 $X/driver.py $R/runtime-codex.json $X/cells.tsv`
18. After a latch the orchestrator has resolved in an amendment file, release it, then start the lane again with its command: `python3 $X/driver.py --clear-latch <amendment> $R/runtime-<lane>.json`
19. After the last cell, with no cell running, the D3 witnesses (steps 19-21 may run at once): `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all D3`
20. The D4 witnesses: `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all D4`
21. The F10 witnesses: `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all F10`
22. The malformed-JSON probe: `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py probe-all`
23. Timing reruns: `python3 $X/recheck.py $R/runtime-smoke.json`
24. The mechanical harm check: `python3 $X/harm_check.py $R/runtime-smoke.json`
25. The false-completion judges, **model**, after steps 19-21: `python3 $X/fc_judge.py run $R/runtime-smoke.json`
26. The decision; its last line is the token: `python3 $X/decide.py $R/runtime-smoke.json`
