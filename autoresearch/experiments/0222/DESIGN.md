# 0222 — comparison apparatus v2 (no budgets)

2026-09-25. **Status: APPARATUS.** Session 3 of [0221](../../iterations/0221-subtraction-direction.md) §5. This builds and checks the apparatus. It registers no comparison; the structure screen (Session 6) and confirmation (Session 7) freeze their own cells and decision rules against it. Design critique: Astra (gpt-6-astra, ultra) R0 REVISE, all four blocking items adopted. Implementation review: Astra and Grok (grok-4.7) R1 REVISE, all findings fixed before any model call (raw: `.devlyn/0221/s3-design/`).

## What it replaces

One directory replaces the 0210→0211→0214→0218→0219→0220 wrapper chain. The archives stay byte-identical and are imported where they are sound: 0207 calibration/oracles, 0208/0210 rollout accounting, 0211 packet compaction, 0185 acceptance/heldout/support.

The 0221 user decisions (§2) supersede, without editing the archives:

- 0206 PROTOCOL: :45 (no resolve in any arm; arm F now runs published 3.2.1, lifting 0201 rule 5 for this arm only), :52-56 (astra-only owner, Fable 240 s reviewer, no Grok), :58-67 (4-descendant / 2-review pool), :69-75 (no installed devlyn instructions; F installs them), :77-120 (finite budget, live observation, BUDGET_EXCEEDED stop, assessment caps), :79-81 (24 cells, D1-D4 order), :131-132 (BUDGET_EXCEEDED category), :138-171 (D1-gated advancement), :188 (no scheduler; `screen.sh` is a 15-line serial loop), :192 (unavailable accounting blocks dispatch).
- 0210 AMENDMENT: :15-21, :26-41, :47-67 (same tasks/arms/models, thresholds as stop rules, UNKNOWN or reviewer timeout stops the screen, first-breach stop-all, assessment allowances, descriptive-only results, equal Fable capability).
- 0221 §4 criterion 5 adjusts the NORTH-STAR dominance rule; the decision rules themselves belong to the Session 6/7 registrations.

Everything else in 0206 (protected files, blind assessment, truthful claims) still holds.

## Arms and routes

Routes, watchdogs and tasks are data in [tasks.json](tasks.json).

- **A (native):** only the 74-word [task frame](common.txt) plus the caller contract. Native subagents and whatever the CLI ships by default stay available, including Codex system skills such as `.system/review-agent`: that is native capability, recorded, not stripped. No review tool is advertised.
- **C:** A plus required review→repair through `python3 /control/review.py` (any number of calls, 600 s each), with a cross-engine reviewer: Claude owner → gpt-6-astra, Codex owner → claude-opus-5-5. C's treatment is *required* review and repair, not exclusive access to review.
- **F:** published devlyn-cli@3.2.1 (npm integrity sha512-SIdRp0x…, tarball sha256 17e57582…) installed offline in the cell image (`-y` for Claude, `agents codex` for Codex) and committed as the baseline. Roles are bound through the shipped `.devlyn/engines.json` mechanism, mounted read-only. Claude config: a native Claude worker (3.2.1 rejects an explicit model on a Claude worker; it inherits the owner's `--model claude-opus-5-5`), a claude-opus-5-5 primary judge and a gpt-6-astra/high pair judge. Codex config: a gpt-6-sol/high worker, a gpt-6-astra/high primary judge and a claude-opus-5-5 pair judge. Claude judges are model-only, because 3.2.1's adapter effort table covers only Fable 5.1 on Claude Code 2.1.263 and would block `high`. Prompt: `/devlyn:resolve --goal-file .devlyn/goal.txt`, local-only. The goal carries the common constraints without A's "no later repair turn" sentence, so resolve keeps its own repair loop.
- **B′:** the `/devlyn:intent` candidate package, installed by the same mechanism in Session 5. `prepare.py` refuses B′ until then.
- **Configs:** Claude owner claude-opus-5-5/high; Codex owner gpt-6-astra/high with gpt-6-sol/high native children. Grok stays a host-side static checker (0221 §4); no Linux build is sealed.
- **Assessment:** two blinded assessors, claude-opus-5-5 and gpt-6-astra, host-side, 600 s each. Root audits every cell's `final.txt` against its verdict; assessors never see it.

## Tasks

- **D3, D4** (0206, exposed): budget fields removed. D4 test paths become `tests/test_utils/**` and `tests/test_types/**`, because a file beside those packages breaks pytest collection (container control). Format gates are ordinary public checks.
- **I0185** (0185, exposed regression material, not holdout): the registered `.devlyn/0185/inputs/install` tree (hash-sealed), the request's own allowed paths, public `node --test tests/acceptance.js`. Oracle = the frozen heldout plus the four promoted post-seal replays (`oracle/`, one-line `require` change each): release, alias, terminal-alias, absence-lock. A replay whose injected fault never fires is **NOT_TRIGGERED**: the cell is ADJUDICATE, and root decides from the product's publication architecture before it counts. It is never an automatic PASS or FAIL.
- **SMOKE:** a trivial route smoke only, never a measurement task.

## Execution policy

- **Watchdogs only:** owner 5400 s, review 600 s, evaluator 600 s per container, assessor 600 s. There are no token, call or cost limits and no review caps. A timeout is a row.
- **Usage:** post-hoc per engine and model ([record_usage.py](record_usage.py)). Missing, torn or unparseable usage is PARTIAL/UNKNOWN with named gaps, never 0, and never stops a cell. Codex rollouts are validated per exec root by the 0208/0210 accounting with infinite limits. Claude records both result.modelUsage and transcripts until the smoke decides which is authoritative. F cells are PARTIAL by construction, because 3.2.1 runs isolated Codex judges with `--ephemeral`.
- **Stop the screen only for:** a container that survives teardown; a changed control manifest, sealed input or issue snapshot; model identity MISMATCH or UNVERIFIED; or an evaluator that did not run (Docker/exec startup failure, uncleaned oracle fixtures).
  - Identity is bound per role. A Codex owner session must use exactly its route model, and its native descendants the child model. A Claude owner's `system/init` model must match. Every other Codex session, Claude model (result or transcripts; Claude's internal Haiku helper excepted), F pipeline `model_requested`/`model_effective` and reviewer call must be on a routed model. A reroute is a mismatch. UNVERIFIED means models ran but the owner session could not be bound.
  - Every other outcome is recorded and the screen continues: an owner crash, a hang, a reviewer failure, or a product that crashes or hangs an oracle (a FAIL row).
- **Provider or auth failure:** an auth/account preflight failure is a shared cause, so the screen stops before dispatch. The cell gets no verdict and runs when the screen resumes. That is not a requeue, because nothing ran. A provider failure after dispatch is the cell's recorded row. There is no automatic requeue: a comparison bundle is rerun only after its common cause is fixed, with the original rows preserved.
- **Verdict:** COMPLETE only if every public check and oracle row passes, no path is outside scope, and both assessors say complete with no HIGH/CRITICAL finding. NOT_TRIGGERED gives ADJUDICATE. Anything else is PRODUCT_INCOMPLETE. Assessor disagreement is recorded, never averaged away.
- **Scope:** every product path, symlink target and file mode is compared with the post-install baseline. `.git` and `.devlyn` are harness state.
- **Harness setup, identical for every arm:** image v2 ([build.sh](build.sh): Codex 0.156.1, Claude 2.1.281, Node 22.23.2, less, pytest 9.0.3, CLIs on the login PATH, `PYTEST_ADDOPTS=-p no:cacheprovider`). Also: branch `main` with a GitHub `origin` (no push credentials in the cell), `.devlyn/` in `.git/info/exclude`, Codex `danger-full-access`, `--network bridge`, pids 256 / 4 GiB / 2 CPU, read-only root, all capabilities dropped. The nested Codex `workspace-write` sandbox works inside this container: the probe wrote the workspace, and a write to home was refused as read-only.
- **Control tree:** [control.py](control.py) builds it from tracked files plus pinned downloads and writes a sha256 manifest. `run_cell.py` refuses to dispatch if the manifest no longer matches.

## Structure-screen shape (frozen for Session 6)

{I0185, D4} × {A, B′, C, F} × {claude, codex} = 16 cells, interleaved. Session 6 fixes the order and decision rules before dispatch, and binds B′ to the Session 5 package.

## Model-free evidence

- `python3 -B -m unittest discover -s autoresearch/experiments/0222 -p 'test_*.py'`: 16 pass with `APPARATUS_IMAGE`/`APPARATUS_CONTROL` set. This covers routes, prompts and hash bindings, the base-diff packet with untracked files, usage above the old caps across exec roots, a truncated rollout recorded as PARTIAL, replay of the archived 0219 native usage (203,245 / 3,406), per-role identity, verdict mapping, and reviewer argument handling. Container cases: a hang-wall kill of a TERM-ignoring setsid child, a nonzero exit recorded, a teardown failure reported, a reviewer exit 124 recorded with a second call still allowed, and the D4 path-collision control.
- Calibration through the same `check.evaluate` used for cells: see [CALIBRATION.md](CALIBRATION.md).

## Limitations

- The Codex reviewer and assessor run in a read-only sandbox and are told not to use tools. The Claude ones run with `--tools ''`.
- Native provider retries are no longer suppressed. Usage of failed attempts may be under-reported, and that is recorded rather than prevented.
- Tasks D3, D4 and 0185 are exposed. Nothing here is holdout evidence.
