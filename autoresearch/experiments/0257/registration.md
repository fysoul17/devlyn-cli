# 0257 registration — bare vs the current package, powered replay

Registered after SMOKE qualification; nothing measured has run. [DESIGN.md](DESIGN.md)
is frozen (r5) and authoritative; this file adds the frozen identities.

## Prediction (copied unchanged from DESIGN.md)

1. **claude development headline** is PACKAGE_UNSAFE, PACKAGE_LOWERS_QUALITY
   or INCONCLUSIVE.
2. **claude D** is below zero.
3. **codex development:** B completes at least as many of its 64 cells as A.
4. **codex D** is above zero.
5. **I0185:** zero completions in every engine and arm.
6. **Malformed JSON (outside the token):** over the 16 claude F10/F11 cells
   per arm, B has fewer JSON-error-400 results than A. Scored only when all
   32 cells have verdicts and a JSON-error-400, HTML-400 or other probe
   result; otherwise unscored, with unassessable results reported.

## Identities

| Item | Value |
|---|---|
| Image | `devlyn-0256`, ID `sha256:25d47afd9a3a34752ae396f2701caff046d1201cd990a0b5b21d67697423bc88` (Claude Code 2.1.281, Codex 0.156.1, Node 22.23.2); tarball kept in the runtime root |
| Package B | `devlyn-cli@4.2.24`, as in [0256](../0256/registration.md) (sha256 `d024f9b48252f943bc537e2c8e7db36715dea0b6baa285a111e43bffe2114fee`) |
| Control manifest | sha256 `54f619b9d9fe002a1b67145d43b38830991e8d9099aad44c7d8cdc59ba324a47`, byte-identical to 0256's |
| Codex models cache | sha256 `f23ab454fab598ad2f8a650a51ea61931bfc191df7ca7920041e436f8a5efe8c` (0256's) |
| Task override | sha256 `58712612f0d3d2fcb20b20bf8ae4e040abe25379d94549ba5c54889ab7c5ccc1`, byte-identical to 0256's (same D3/D4 issue snapshots) |
| Calibration | 29 references, `calibration.json` byte-identical to 0256's (sha256 `6226da58…`) |
| Instruction seal | `instructions.seal.json` sha256 `6cafc1808c82298b1701ee65c41aec68edead18fd20519cb579e5604b91f0179`: installer files (claude `CLAUDE.md` `336cc4fb…`, `AGENTS.md` `11a85ab7…`), the forms each engine received in SMOKE B, and qualification PASS over all four SMOKE cells |
| Endpoints | `endpoints.json` sha256 `1b997b40274ab4ef06d72495ea430acb599d721e01745fa12f4a19e01b8cf7ef` (43-test development and 11-test confirmation families per engine) |
| Caps | seven-day 85%, five-hour 70% (owner, 2026-10-22, before SMOKE) |
| Deadline | 2026-11-12T02:30:14Z: 21 days after the first SMOKE dispatch (2026-10-22T02:30:14Z, round 1), persisted in `driver-status.json` |
| Venue | Claude account `02b266ea50d2`, organization `531f8e153d6b` |
| Apparatus | `autoresearch/experiments/0257/` at the registration commit |

## SMOKE

Evidence is kept in the runtime root: round 1 under `smoke-r1/`, round 2
under `smoke-r2/`, the refused attempt under `smoke-r3-disk-refused/`, and
round 3 in `output/`. Rounds 1 and 2 ran before this registration. They
qualify nothing and are not data. DESIGN records the account at freeze, and
this file is the freeze, so the registered venue is round 3's account.

**Round 1 (account `02b266ea50d2`).** smoke-claude-A, smoke-claude-B and
smoke-codex-A met every criterion. smoke-codex-B's owner ran and exited 0,
but the host Claude account had switched to `cc43a4e02ede` / `2905f4abf05b`
before its Claude assessment. The verdict is STOP ("assessment held:
account/organization mismatch"), and the driver stopped, as designed. The owner chose to continue on that account.

**Round 2 (account `cc43a4e02ede`).** smoke-claude-A and smoke-claude-B met
every criterion. The usage endpoint then returned HTTP 429 for about two
hours, and the driver held. At 05:00Z the host account switched back to
`02b266ea50d2`, and the driver stopped again. The owner left the choice of
account to the operator, who registered the account that was logged in.

**Refused attempt.** The first cell was not dispatched: the output volume had
6.8 GB free, below the 8 GB floor. That refusal also cleared the persisted
first-dispatch time. The round-1 time was restored before relaunch, so the
deadline is not extended. The owner chose to delete only the Docker build
cache, after which 13 GB was free (16 GB after round 3). SMOKE cells used
4–13 MB each and 0256's cells about 17 MB on average, so 328 cells need
about 1.3–5.6 GB.

**Round 3 (registration apparatus and account).** All four cells were rerun.

| Cell | Owner | Seconds | Teardown | Identity | Usage | Public + oracle | Scope | Snapshot | Seven-day / five-hour change |
|---|---|---|---|---|---|---|---|---|---|
| smoke-claude-A | EXITED_0 | 47 | CLEAN | MATCH | COMPLETE | pass | none | anchor | 0 / 1 |
| smoke-claude-B | EXITED_0 | 64 | CLEAN | MATCH | COMPLETE | pass | none | receipt (helper) | 1 / 1 |
| smoke-codex-A | EXITED_0 | 34 | CLEAN | MATCH | COMPLETE | pass | none | anchor | 0 / 1 |
| smoke-codex-B | EXITED_0 | 67 | CLEAN | MATCH | COMPLETE | pass | none | anchor | 1 / 3 |

- **Verdicts.** Every verdict is PRODUCT_INCOMPLETE, as in 0256's SMOKE. SMOKE
  is outside every sum.
- **Window changes.** Codex cells also move the Claude windows, because
  their assessors run on Claude.
- **Instruction load.** `instructions.py seal-forms` sealed claude's
  `CLAUDE.md` (`@AGENTS.md`) and imported `AGENTS.md` forms, plus codex's
  `AGENTS.md` form, from the SMOKE B sessions. The assertions then passed on
  all four cells: no sealed form in either A cell, and the sealed form in
  both B cells.
- **Probe.** `judge.py qualify-probe` on 0256 trees classified c01 and c06
  (A) as `json_error_400` and c02 and c12 (B) as `html_400`. The store was
  preserved in all four ([record](results/probe-qualification.json)). These
  trees qualify the probe only and are not data.

## Installer checks on the real trees

`instructions.py seal` ran the B installer on an empty Git tree. The unit
test covers the I0185, F10 and SMOKE trees with a fake installer. Before
registration, `prepare.prepare` also ran the real B installer for both
engines on every task's real tree (`qual-install/` in the runtime root; no
participant ran):

- **I0185:** the skip line is present, both skills are present, and
  `CLAUDE.md` and `AGENTS.md` are absent before and after the install.
- **D3, D4, B5, F10, F11, E1, E2:** the installed `CLAUDE.md` (claude only)
  and `AGENTS.md` match the seal, and the skills are present.

The first I0185 attempt failed: `.devlyn/0185/inputs/install` is untracked
and was missing from the run worktree. It was restored with 0256's
[`restore_i0185.py`](../0256/restore_i0185.py), which checks all seven files
against 0233's sealed `source_sha256`. Every run worktree needs this step.

## What runs

`driver.py <runtime.json> cells.tsv` under `caffeinate -dimsu`, from a
detached worktree at the registration merge commit, after
`python3 autoresearch/experiments/0256/restore_i0185.py .` in it: 328
measured cells in `cells.tsv` order. A host account switch stops the run; another account is a
new registration (DESIGN, Operations).
