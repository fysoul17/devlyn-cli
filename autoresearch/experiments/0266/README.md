# 0266 — one sentence against literal scope on failure paths

[`DESIGN.md`](DESIGN.md) is the design: `design-final.md` of the review folder verbatim (four reviewer passes),
then the apparatus that implements it and what changed from 0265. It compares two packages, both launched through
`devlyn run`: B, the published `devlyn-cli@4.3.31`, and C, the same package with one added sentence in its
principles. A wording screen (18 Claude cells) picks one of three candidate sentences (K1, K2, K3); the registered run
(176 cells, two lanes) reads R1 (Claude F10: the malformed-JSON event, C more than B) and the guards G1-G5, and prints
one verdict. The apparatus is 0265's ([../0265](../0265)): modules 0266 does not change (`cell.py`, `check.py`,
`assess.py`, `quota.py`, `locate.py`), the judges' rule, prompt and witness descriptions, the image build and the nine
frozen witnesses are read from 0265 by path.

## Operator

From the root of the worktree at the registration commit, with `X=autoresearch/experiments/0266` and
`R=~/.local/share/nx01/0266-live`, one command per line, in order. **Model** marks a step that makes model calls;
every other step makes none and reads no credential unless it says so. The seal and the screen decision are written
once and refuse while their file exists: move it aside before repeating the step on another commit. The controls
(step 4) are run again on a new commit and replace `q5-controls.json`.

Before the Codex login is chosen (none of these reads a login, and naming it later changes nothing they made):

1. Unit tests, 0266's and 0265's (`test_integration.py` needs step 2's root and takes several minutes):
   `nice -n 10 python3 -m pytest -q $X` and `nice -n 10 python3 -m pytest -q autoresearch/experiments/0265`
2. Runtime root: clones, issue snapshots, the 4.3.31 tarball by npm integrity, the image (`devlyn-0265`, loaded or
   saved, never rebuilt when present), the control tree with the four packages (C-K1..K3 built by the package's own
   `buildRelease` in the image and compared with B; the files and fields that differ are printed and frozen), runtime
   files with `codex_auth` null: `python3 $X/setup_runtime.py`
3. Q2 launch probe and seal of every package (recording shims, no credential, about 7 min):
   `python3 $X/instructions.py seal $R/runtime-smoke.json`
4. Q5 witness and probe controls, 35 of them (about 25 min):
   `NX01_0266_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py controls`

Just before SMOKE:

5. Name the Codex login the run uses, by the absolute path of its `auth.json` (it rewrites `codex_auth` in the three
   runtime files and nothing else; it refuses once a cell has started or another login is named):
   `python3 $X/setup_runtime.py --codex-auth <auth.json>`
6. Q6 judge calibration, **model** (both judge seats per pair; reads the Claude and Codex logins), the gate:
   `python3 $X/fc_judge.py calibrate $R/runtime-smoke.json`
7. Q6 held-out score, **model**, never a gate: `python3 $X/fc_judge.py calibrate $R/runtime-smoke.json --held-out`
8. Q7 SMOKE, **model** (B and C-K3 per engine, their assessors, one process):
   `caffeinate -dimsu python3 $X/driver.py $R/runtime-smoke.json $X/smoke.tsv`
9. SMOKE's forms and assertions: `python3 $X/instructions.py seal-forms $R/runtime-smoke.json`
10. The harm check on SMOKE as a control (no finding expected):
    `python3 $X/harm_check.py $R/runtime-smoke.json smoke-claude-B smoke-claude-C smoke-codex-B smoke-codex-C`

The screen (Stage S; its cells never count in a reading):

11. The screen, **model**, Claude lane: `caffeinate -dimsu python3 $X/driver.py $R/runtime-claude.json $X/screen.tsv`
12. Its probe, after the lane has ended: `NX01_0266_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py probe-all screen`
13. The screen decision, once; its last line is `0266-screen:<GO|STOP|UNDECIDED>[(<candidate>)]`:
    `python3 $X/decide.py screen $R/runtime-smoke.json`. On STOP ("not screened in") or UNDECIDED the experiment ends
    here and the owner is told; there is no registered run. On GO the lanes below take C's package from
    `$R/screen-decision.json` and refuse to start unless its package sha256 is the one the seal pinned.

The registered run (Stage R):

14. Claude lane, **model**, in its own terminal: `caffeinate -dimsu python3 $X/driver.py $R/runtime-claude.json $X/cells.tsv`
15. Codex lane, **model**, at the same time in another: `caffeinate -dimsu python3 $X/driver.py $R/runtime-codex.json $X/cells.tsv`
16. After a latch the orchestrator has resolved in an amendment file, release it, then start the lane again with its
    command: `python3 $X/driver.py --clear-latch <amendment> $R/runtime-<lane>.json`. A lane that was killed inside a
    cell ran no cleanup: resolving its latch includes proving that cell's container and volume gone and removing
    `$R/scratch/credentials/<cell>` unread. After the last cell `$R/scratch/credentials` holds nothing. A screen slot's latch
    (step 11) is resolved the same way, before step 14: the screen lane, started again with its command, passes that
    slot, whose STOP then reads as an unknown of the screen (no screen cell is run again).
17. After the last cell, with no cell running, the D3 witnesses (steps 17-19 may run at once):
    `NX01_0266_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all D3`
18. The D4 witnesses: `NX01_0266_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all D4`
19. The F10 witnesses, the write-failure witness among them:
    `NX01_0266_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py run-all F10`
20. The probe (with G5's batch on F11): `NX01_0266_RUNTIME=$R/runtime-smoke.json python3 $X/results/operator/judge.py probe-all`
21. Timing reruns: `python3 $X/recheck.py $R/runtime-smoke.json`
22. The mechanical harm check: `python3 $X/harm_check.py $R/runtime-smoke.json`
23. The false-completion judges, **model**, after steps 17-19: `python3 $X/fc_judge.py run $R/runtime-smoke.json`
24. The decision; its last line is the token `0266:<verdict>;R1:…,G1:…,…,G5:…`:
    `python3 $X/decide.py $R/runtime-smoke.json`

Operator hold: while the file `$R/operator-hold` exists, no lane starts a new cell (`touch $R/operator-hold`; a cell
already running finishes and is graded; each lane logs a `hold` with reason `operator hold` every 60 s); `rm
$R/operator-hold` resumes dispatch, with every pre-dispatch check made again.

`python3 $X/power.py` prints DESIGN's chance and power figures recomputed through `decide.py` (no model).
`python3 $X/control.py compare <B package> <C package> <K>` repeats the package comparison on its own.

Not repeated from 0265 (DESIGN "Qualification"): Q3 (strict config: same image, Codex and `config.toml`) and Q8 (the
memory rehearsal: same image, same lane shape), so both lanes run at once.

Custody: per-cell reports are archived to `~/.local/share/nx01/archive/reports-0266` before `$R` is deleted, and
deletion needs the owner's approval.
