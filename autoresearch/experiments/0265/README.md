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

From the research worktree's root, with `X=autoresearch/experiments/0265` and `R=~/.local/share/nx01/0265-live`, in
order. Each step says whether it makes model calls.

1. Q1, no model: `python3 -m pytest -q $X`.
2. Runtime root, no model (clones, issue snapshots, the 4.3.30 tarball, the image, control trees, runtime files):
   `python3 $X/setup_runtime.py`.
3. Q2 launch probe and seal, no model (the image with recording shims, no credential):
   `python3 $X/instructions.py seal $R/runtime-smoke.json`.
4. Q3 strict config, one Codex model call (the allowed run): `python3 $X/strict_config_check.py --run-exec $R/runtime-smoke.json`.
5. Q5 witness and probe controls, no model: `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py controls`.
6. Q6 calibration, model calls (both judge seats per pair): `python3 $X/fc_judge.py calibrate $R/runtime-smoke.json`;
   then the held-out score, model calls, never a gate: `python3 $X/fc_judge.py calibrate --held-out $R/runtime-smoke.json`.
7. Q7 SMOKE, model calls (four owners and their assessors), one process:
   `caffeinate -dimsu python3 $X/driver.py $R/runtime-smoke.json $X/smoke.tsv`.
8. SMOKE's forms and assertions, no model: `python3 $X/instructions.py seal-forms $R/runtime-smoke.json`.
9. The harm check on SMOKE as a control (no finding expected), no model:
   `python3 $X/harm_check.py $R/runtime-smoke.json smoke-claude-A smoke-claude-B smoke-codex-A smoke-codex-B`.
10. Q8 (a), no model: `python3 $X/rehearse_memory.py checks`.
11. Q8 (b), model calls (the four rehearsal cells): start the sampler,
    `python3 $X/rehearse_memory.py sample --out $R/q8-sample.json --until-file $R/q8-done &`; run both lanes at once,
    `caffeinate -dimsu python3 $X/driver.py $R/runtime-claude.json $X/rehearsal.tsv &` and
    `caffeinate -dimsu python3 $X/driver.py $R/runtime-codex.json $X/rehearsal.tsv`; when both have ended,
    `touch $R/q8-done`. Below 1 GiB by DESIGN Q8's rule (q8-sample.json's smallest available memory less what
    q8-checks.json's owners used above the rehearsal owners), step 12 runs its two commands one after the other.
12. The two lanes, model calls, at once:
    `caffeinate -dimsu python3 $X/driver.py $R/runtime-claude.json $X/cells.tsv` and
    `caffeinate -dimsu python3 $X/driver.py $R/runtime-codex.json $X/cells.tsv`. A lane that stops on a latch is
    resolved by the orchestrator, recorded in an amendment file, released with
    `python3 $X/driver.py --clear-latch <amendment> $R/runtime-<lane>.json`, and started again with its command.
13. Grading after the last cell, with no cell running:
    - witnesses, no model, one process per task (the three may run at once):
      `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all D3` (then `D4`, `F10`);
    - the malformed-JSON probe, no model: `NX01_0265_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py probe-all`;
    - timing reruns, no model: `python3 $X/recheck.py $R/runtime-smoke.json`;
    - the mechanical harm check, no model: `python3 $X/harm_check.py $R/runtime-smoke.json`;
    - the false-completion judges, model calls, after the witnesses: `python3 $X/fc_judge.py run $R/runtime-smoke.json`.
14. Decision, no model; its last line is the token: `python3 $X/decide.py $R/runtime-smoke.json`.
