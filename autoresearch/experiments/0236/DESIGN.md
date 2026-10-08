# 0236 apparatus: one resumed repair turn on sealed 0235 cells

Registration: `autoresearch/iterations/0236-review-findings-repair.md`. The 0235 apparatus is frozen; 0236 loads its
modules by path and never edits them.

| File | Role |
|---|---|
| `run_continuation.py` | One continuation: `run_continuation.py <runtime.json> <name> <unit> <F\|G>` |
| `messages.py`, `messages/` | The frozen G text and per-unit F messages (`python3 messages.py <0235 output>`) |
| `cells.tsv`, `smoke.tsv` | The 16 measured continuations in §5 order (`name unit arm replicate`); smoke `s01-r06-G` |
| `witnesses/` | `d3-parseoptions-override.js`, `d4-writer-strict.py` (§4 criterion 3; exit 1 = reproduces, 0 = does not, 2 = STOP) |
| `decide.py` | The §6 rule: `decide.py <output> <decisions.json>` |
| `test_apparatus.py` | Model-free, Docker-free tests |

**Runtime.** The 0235 runtime fields plus `source_output`, the sealed 0235 output directory. `control`, `auth`,
`account` and `image` stay 0235's.

**Continuation.** After the 0235 preflight and control check, the source cell must:
- have a verdict that is not STOP;
- have an evidence manifest that matches its files except exactly `cell/work/.git/index` (§10), with the drift
  recorded in `origin.json`;
- have been sealed on the runtime image.

The frozen message must still regenerate from the source's raw assessor output.

The new cell copies:
- `baseline.json`, `prompt.txt` and `harness/` byte-for-byte;
- `cell/` and `home/`, with symlinks kept;
- the source `tmp/`, to `tmp.seed/`.

It then writes:
- `continuation.txt` and `origin.json`;
- a `plan.json` whose argv is `claude -p --resume <session> …`;
- `seal.json`, which holds the 0236, 0235 and shared file hashes and the origin.

0235 `cell.run` launches the owner. Its `docker` helper is wrapped so the new `/tmp` volume is filled from `tmp.seed/`
right after it is created: the root directory is 1777 and owned by root, and its contents belong to 501:501. `tmp/`
therefore holds only the continuation's own `/tmp` at teardown. If `cell.run` raises before its teardown (volume
create, `/tmp` restore or container create), the cell stops with `launch failed`, and the volume is removed; a volume
that could not be removed is named in the reason.

**Environment (§5).** Environments differ between units (some source homes carry account-synced skills) but are held
identical within a unit, F and G alike:
- **Route.** The continuation's `init` model, `claude_code_version`, `permissionMode`, agents and plugins must equal its
  source's `init`.
- **Unit reference.** The unit's first measured continuation in `cells.tsv` order records its skills, MCP server names
  and non-MCP tools as `<output>/environment-<unit>.json`, write-once; every later continuation of the unit must match
  it. MCP tool names and server status are recorded, never compared. A later continuation whose unit reference is
  missing or malformed is a preflight refusal (exit 3): nothing is dispatched. The smoke's unit is not measured, so the
  smoke checks the route only.

After teardown:
- **Stops.** The cell stops before grading if the resumed session id differs from the source's, if the source
  transcript is not a strict byte prefix of the new one, if the route differs from the source's, or if the environment
  differs from the unit reference (or the first continuation cannot record it).
- **Recorded, not gating.** MCP tool names, MCP server status and account-synced skills, beside the source's.
- **0235 post-run pipeline, unchanged.** Seal, session usage, quota, diagnostics, stop gates, locate, check and grade.
  Regrade with `0235/run_cell.py --regrade <runtime> <name>`.

**Turn usage.** The turn is the final result `modelUsage` minus the source transcript's last `cost-state`, for each
model and counter. It is COMPLETE only when all of the following hold:
- it equals the sum over the source session's assistant messages appended after the source bytes, deduplicated by id;
- no source message is written again;
- source and session usage are COMPLETE;
- the cell has no usage outside the owner session.

Otherwise the turn's tokens are unknown, and §6 conditions 5–6 stay unmet. A turn that launches its own Claude or
Codex session (for example a reviewer) therefore has unknown usage: it fails closed rather than counting the
descendant. The verdict keeps:
- `session_*`, which is cumulative;
- `turn_*`, with uncached, cache-read and cache-write input listed separately;
- `turn_seconds` and `cumulative_seconds`.

`files_changed` and `tree_unchanged` compare the new snapshot with the source snapshot.

**Decision inputs.** These are root's judgments in `decisions.json`:
- `audited`, `false_completion` and `user_data_harm`, as cell lists;
- `witnesses`, as `{witness: {cell: reproduced}}`, where `reproduced` is a boolean (a witness error is a STOP to
  resolve first; any other value is refused);
- `adjudicated`.

Both witnesses run on a copy of every continuation snapshot, using the image and flags of `0234-live/judge.py`.
`decision.json` reports preservations (complete and audit-clean, witness reproduces) per arm and per cell, apart from
repairs.

**D4 witness.** `d4-writer-strict` runs every FIFO test in its own pytest process under writer death and under a 40 s
writer stall. A `sitecustomize` module installs a Python audit hook that injects on the `open` event and records
spawns and every FIFO write-open; a pytest plugin records survivors at session end. A test's result is STOP, never a
reproduction and never a pass, when it starts a child the hook cannot reach (unsupported instrumentation), when it
opened a FIFO for writing but the injection fired zero times in it (writer not injectable: only nonblocking or
main-thread write-opens, which are never injected), or when its session end was not recorded. Exit 1 when a test that
is not STOP, or the tree, demonstrates a defect; else 2 when any test is STOP or the witness fails; else 0. Its
docstring lists the conditions and the known limit (sequential 40 s stalls in one test can exceed 150 s).

Validated 2026-10-09 on copies of the 0235 snapshots, in the cell image with the `judge.py` flags:
- r03 and r08 reproduce (exit 1): under death their delayed-read tests are still running at 150 s.
- r04 reproduces (exit 1): under stall, the writer thread is alive at session end.
- r04's and r08's `test_lazy_fifo_convert_does_not_connect` tests make only a main-thread nonblocking write-open, so
  they are STOP (writer not injectable); a tree that keeps such a test and shows no defect elsewhere exits 2.
- The gate-pass r07 does not reproduce (exit 0): the injection fires in each of its eight runs, and every test
  terminates cleanly.
- On synthetic FIFO tests added to r07 copies, a child writer that connects with a nonblocking open (synA) and a
  main-thread blocking writer (synB) are each STOP, writer not injectable (exit 2). Earlier (2026-10-08): a non-Python
  child, `os.system`, an environment-stripped Python child and `python -I` are unsupported instrumentation (exit 2); an
  `io.FileIO` writer thread alive after a stall and a leftover FIFO in `/tmp` reproduce (exit 1).

**Costs.** Wall time for a `HANG_TIMEOUT` is 5400 s. The operational account charges each attempt with:
- its unit's original owner run and original assessors, both from `origin.json`;
- the turn;
- every failed assessment attempt archived as `assessment.stop-N/` (unknown usage stays unknown; a run without its
  record makes that arm's operational wall, input and output unknown);
- its final reassessment.
