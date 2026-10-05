# 0232 apparatus: what differs from 0231

Stage 1 of [0232](../../iterations/0232-harness-ladder.md) §6 runs A/I/F on the 0231 apparatus. This directory is a copy of
`../0231` with only the changes below. Unlisted files are byte-identical copies, so their docstrings still say 0231:
`assess.py`, `check.py`, `calibrate.py`, `obligations.py`, `trace_usage.py`, `common.txt` and the image recipe
(`Dockerfile`, `build.sh`, `py_tools.py`, `pyright/`). The image is 0231's `devlyn-0231`, unchanged.

## Arms (`prepare.py`, `control.py`)

| Arm | Installation | Prompt |
|---|---|---|
| A | none: the task repository as supplied | native: `common.txt` + `CALLER CONTRACT` + the cell's `/harness/caller.json` (0222's A construction, 0231's paths) |
| I | the rung-1 package's own installer, offline, as 0231 installs packages | A's native prompt, no slash command |
| F | 0231's control package (4.1.0) | 0231's resolve command and committed `.task/goal.txt`, unchanged |

- `control.py` ARMS holds F at `4056ebe2` with the sha256 its 0231 build recorded (also the published 4.1.0
  tarball's), and I at the frozen rung-1 commit `5bf3dc74` with its pack's sha256. A pack that differs is refused.
- Preparing I fails unless its installer put the launcher at `$HOME/.devlyn/review.js`. Its sha256 goes into
  `baseline.json` (`review_sha256`). The 0231 arm names are refused.
- Every arm's anchor gets `origin/main` and `origin/HEAD` at the allocation commit (`git fetch origin` and
  `git remote set-head origin -a` through the harness transport), so the launcher's default base, the merge-base with
  `origin/HEAD`, is the allocation commit. The mirror's HEAD is `main`, and the transport serves the mirror beside its
  script (`/harness` in the cell), so the host runs the same script.

## Usage (`record_usage.py`, `evidence.py`)

- **Complete input accounting.** Each cell records `input_tokens` (processed input, counted once) beside `output_tokens`:
  - Codex: `input_tokens` already include cached and cache-write tokens (0208's validated counter semantics).
  - Claude: uncached input + cache reads + cache writes, from the owner's result, every separate result envelope and
    each uncovered transcript's lower bound.
  - A missing Claude counter is a named gap, never zero. An empty usage map is missing too: it covers no transcript,
    whose usage then counts as a lower bound.
- **Claude result envelopes** are the `*.output.json` files under `.devlyn`. 4.1.0 saves each raw Claude result there
  (judges, SURFACE_CLOSE); a `.stdout` beside one holds extracted result text.
- **Review launcher calls** (`home/.devlyn/reviews/<UTC timestamp>-<engine>/`) are inventoried as launches:
  - A Codex call's JSON `thread.started` ids bind its traces (seat `reviewer`), so they are never unbound traces.
  - A Claude call's final stream event is a result envelope, deduplicated by session; it covers that session's
    transcript.
  - A call without its trace or its result with usage is a named gap.

## Identity, quota and snapshot

- **Identity** (`cell.py`): a review runs its engine's registered reviewer pin (`tasks.json` routes; also the
  launcher's defaults), including the rollout fallback when its trace is lost. Which engine the agent chose is
  methodology, not identity, so a same-engine review is non-compliant rather than a STOP in either config.
- **Quota** (`quota.py`): review records' raw stdout and stderr are execution evidence, so a reviewer's account limit
  STOPs the cell like any other execution fault.
- **Cell `/tmp`** (`cell.py`) is a per-cell Docker volume. After teardown it is copied into `<cell-out>/tmp`, then
  removed. Codex's Linux sandbox refuses every command when `/tmp` is a host bind mount, which would disable every
  sandboxed Codex reviewer, judge and worker. A failed copy keeps the volume and STOPs the cell.
- **Storage** (`run_cell.py`): the free-space floor before each cell is 8 GiB, not 0231's 20 GiB. It covers one cell's
  writes on this host's nearly full volume, and every verdict records `trace_bytes`.
- **Snapshot** (`locate.py`): Git's view of each tree reads the cell home, as the container does, never the host
  user's ignore files. F keeps 0231's selection exactly; a receipt-less F run is its anchor. A and I are
  native: the anchor (the session's working directory) when its product differs from the allocation, else the one
  linked worktree whose product does. Changed products in more than one worktree beside an unchanged anchor are a
  locator STOP, never a silent choice. A baseline-witness worktree beside a changed anchor keeps the anchor. A
  directory entry (an untracked nested repository) is copied as a tree with its symlinks kept; any copy failure is a
  locator STOP.

## Evidence (`run_cell.py`, `compliance.py`)

- F keeps 0231's obligation adapter as is; its result is reported.
- I gets `compliance.py`, reported as methodology apart from product quality. It is compliant when at least one review
  meets all four conditions:
  - it was made by the registered other engine (Astra D5: "one fresh review from another engine");
  - it succeeded: its `meta.json` exit code is 0 and its raw stdout holds an answer;
  - its `meta.json` `reviewed_tree` equals the final tree of the selected run location;
  - its `meta.json` `base` is the allocation commit (a later base reviewed only part of the change).
- Otherwise the record names why: no review, or per call wrong engine, failed review, tree mismatch or partial base.
- The final tree is the launcher's algorithm run on the host (`locate.final_tree`) with the cell home: HEAD read into
  a temporary index, `add -A -- .`, write-tree. The index and new objects stay in a temporary directory, so the sealed
  evidence is never written. No participant command runs: every configured filter key is blanked, and a tracked
  submodule is refused (adding it would run `git status` inside it). A nested repository the add records as a gitlink
  is refused too: the tree would hold only its commit while the snapshot copies its live files. A refusal or Git
  failure leaves no final tree; it is recorded, and no call matches.
- A has no methodology obligation. All arms get the same checks, oracle rows and blinded assessors on one snapshot.

## Decision (`decide.py`)

The record's O4 rule per configuration, over each arm's six cells:
- S = completed cells. W (a hang counts 5400 s), I and O are sums over all six; per-success cost = sum / S, compared
  exactly (fractions).
- **Quality** (both comparisons, per task): completion and every check and oracle-row pass count at least the
  reference's; no false completion, scope violation, user-data harm or reproduced HIGH/CRITICAL that the same witness
  does not reproduce on the reference tree of its replicate.
- **Admission:** I against A. Per-success W, I and O are not higher, and at least one of completion count, W, I and O
  is strictly better. If I fails, A stays admitted.
- **Replacement** of the incumbent F needs admission and the F comparison (owner O1): per-success W at most 0.70 × F's,
  I and O not higher. The result reports both outcomes (`admission`, `comparison`).
- **No claim:** a candidate with S = 0 earns none. When S_ref = 0, the reference's per-success cost is unbounded: its
  tests pass with the reason "dominance over a zero-success incumbent", never as a percentage.
- **Missing usage:**
  - candidate usage that is not COMPLETE makes its test INCONCLUSIVE;
  - a reference's PARTIAL sum is a lower bound: it can prove a test, never disprove one.
- `decisions.json` must record `user_data_harm` as well as 0231's judgments. Raw sums, per-success costs and every
  cell's methodology record are printed beside the outcomes. A token sum over any usage that is not COMPLETE prints as
  unknown, its observed amount only as a labeled lower bound.

## Cells

- `cells.tsv` holds 36 cells. Each (task, config) runs its three arms back to back.
- Per config and replicate, the arm positions form a Latin square. Replicate 2 runs the groups in reverse with each arm
  order reversed, so each config sees all six orders once.
- `smoke.tsv` holds 6 cells.

## Tests and limits

- `test_apparatus.py` runs model-free and Docker-free, except the container cases, which need the image and the 0232
  control tree.
- The obligation meter's fixtures need the 0231 bundle package, so they stay in 0231's suite.
- **Host tree.** A participant filter that changes content, Git configuration the host path does not match (an
  `includeIf gitdir:` on a container path) or replacement refs can make the host tree differ from the reviewed one, and a
  tracked submodule or a gitlinked nested repository leaves no final tree: each reads as non-compliant, never as
  compliant.
- **Reviewer children.** A Codex reviewer's traced native children would be checked against the owner's child pin,
  which would make the cell a STOP. This case is unobserved.
