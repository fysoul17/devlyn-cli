# 0232 stage 1: severe-finding dispositions and `release` adjudications (prepared for root)

State: all 36 measured cells have verdicts (the drive finished 2026-10-05T18:33Z). `.stop-` files are ignored.

- **Severe findings:** 34, from `witness.py findings`: 30 for I0185 (all 12 cells) and 4 for D3 (m18 only). No D4 cell has a severe finding (12 of 12 checked, both assessments each), so no D4 witness is needed.
- **Distinct claims:** 8, all binding: K1–K5 for I0185 and J1–J3 for D3. One supplementary check, K6, tests a mechanism one finding guessed.
- **Dispositions:** all 34 findings are `reproduced` on their own tree. The 5 findings from m31–m33 map to existing claims (K3, K2), so no new claim or witness was needed.
- **Release adjudications:** m31-I0185-codex-I-r2 and m33-I0185-codex-A-r2 had `release` NOT_TRIGGERED. Both are adjudicated **FAIL** under 0224 rule 1 (see the `release` section).
- **Pending trees:** none; `pending_trees` is cleared.
- **decide.py audit-gap check over all 36 cells:** no gap.

Witnesses are in `/Users/aipalm/.local/share/nx01/0232-live/witnesses/`:

- Each runs from `/work` in the cell image, with no network.
- Each exits 1 when the defect reproduces, 0 when the tree is correct, and 2 on a witness error.
- The I0185 witnesses share a byte-identical fixture header that mirrors the supplied `tests/support.js`. That file is byte-identical in all 12 I0185 trees.

Final recorded runs are in `scratch/adj/runs/`:

- I0185: `*.pass4.json` and `*.pass5.json`, each witness on all 12 trees, the two passes identical.
- D3: `*.pass2.json` and `*.pass3.json`.

The release variants and their results are in `adjudication/`.

## How findings were grouped and read

- **Grouping.** A claim is a pair: a trigger, and the requirement the findings cite as violated. Findings that share both form one claim and get one witness.
- **Findings with a concrete mechanism** are read by that mechanism.
- **Findings that only restate a failing root oracle row** are read as claiming the defect that row detects. These are m05 claude:0, m06 claude:0, m13 claude:0, m14 claude:0, m14 claude:1, m23 claude:0 and m24 claude:0. They typically say "root cause not independently confirmed".
  - `release` maps to K3 and `terminal-alias` maps to K2.
  - `heldout` maps to K3 as well. Its recorded failure in `out/<cell>/checks-raw.json` is `swallowed N` in the one-shot fault sweep for m13, m23 and m24, which is the lock-release failure being retried into success.
- **Locating the lock.** "Lock naming is internal", so K3 and K4 locate the lock as the first removed path whose name contains `lock`. Every tree names its lock `…lock`.
- **Witness change after m31–m33.** m31 and m33 keep their lock under the system temp directory (`/tmp/devlyn-skills-<sha256>.lock`). K3 and K4 originally looked only inside the fixture, so I widened them to match the lock wherever it lives. K3 now also requires that the lock no longer exists after recovery.
  - Both witnesses were re-run on all 12 trees. The booleans for the 9 earlier trees are unchanged.

## Per-tree reproduction (all 12 I0185 trees)

✓ = the defect reproduces.

| config / rep | arm | cell | K1 exdev | K2 lock-alias | K3 release-restore | K4 stuck | K5 mkdir-before-lock | K6 physical-alias |
|---|---|---|---|---|---|---|---|---|
| codex r1 | A | m04 | ✓ | ✓ | ✓ | – | – | – |
| codex r1 | I | m06 | – | – | ✓ | – | – | – |
| codex r1 | F | m05 | ✓ | ✓ | ✓ | ✓ | – | – |
| claude r1 | A | m15 | – | – | ✓ | ✓ | – | – |
| claude r1 | I | m13 | – | – | ✓ | – | – | – |
| claude r1 | F | m14 | ✓ | ✓ | ✓ | ✓ | – | – |
| claude r2 | A | m22 | ✓ | ✓ | ✓ | ✓ | – | – |
| claude r2 | I | m24 | – | – | ✓ | – | ✓ | – |
| claude r2 | F | m23 | ✓ | – | ✓ | – | – | – |
| codex r2 | A | m33 | ✓ | ✓ | ✓ | – | – | – |
| codex r2 | I | m31 | – | – | ✓ | – | – | – |
| codex r2 | F | m32 | ✓ | ✓ | – | – | – | – |

D3: J1 `d3-delimiter-dropped`, J2 `d3-later-delimiter` and J3 `d3-alias-default` reproduce only on m18 (codex F r1, the unmodified base tree). They pass on the other 11 D3 trees.

## Claims

### K1: cross-filesystem rename (EXDEV)

**Claim.** The staging and backup directories live in the skills directory's parent, so backup and publish renames cross the skills-directory boundary. When the skills directory is on another filesystem (a mount point, or a symlink to another volume), every install fails with EXDEV. The pre-change in-place installer succeeded on that layout.

**Binds: yes, to the keep-existing-behavior clause.**

- The task requires: "Upgrade the real `bin/devlyn.js` function `installSkillsForCLI(cliKey)` … This function is called by the existing CLI installation flow. Keep its synchronous API, return count, …"
- The original installer copies in place. Its only rename stays inside the skills directory, so it returns 6 on this layout. A local mount-simulation run of the original shows 0 crossing renames.
- The trigger is plausible: a Docker bind-mounted `~/.codex/skills`, or a symlink to another volume. Symlinked skills directories are explicitly in scope (the `alias` and `terminal-alias` rows).
- **Judgment call.** The registrants' I0185 reference also fails the mount variant, because it renames the skills directory itself. They may not have considered this layout in scope.

**Witness:** `witnesses/i0185-exdev.js`. Two scenarios run against the standard fixture:

- **symlink:** `<root>/agent/skills` is a symlink to a directory on `/dev/shm` (tmpfs), while the fixture lives on the overlay `/tmp`. This produces a real kernel EXDEV.
- **mount:** `fs.renameSync` throws EXDEV for every rename between the inside and the outside of the skills directory.

**Required behaviour:** the install returns 6 with a complete new installation.

**Results:** reproduces on m04, m05, m14, m22, m23, m32 and m33. The docker detail runs show EXDEV on the first backup rename, for example m32 `skills/.devlyn-install.json -> agent/.devlyn-install-*/backup/0`.

- m23 fails in the symlink scenario on its deprecated-command backup, which goes to the work dir beside the real destination on `/dev/shm`.
- **Passes:** m06, m13, m15, m24 and m31.
  - m06, m13, m15 and m31 stage inside the destination or back up each path beside itself.
  - m24 copies when a rename returns EXDEV.
- **Reference (docker sanity):** reproduces (mount scenario).

### K2: lock-path aliasing through a symlinked skills directory

**Claim.** The lock is derived from the path spelling, not the physical directory. Two configured skills directories that are one physical directory, one being a symlink to the other, therefore take different locks. A reentrant installation through the other spelling proceeds instead of failing busy.

**Binds: yes, to requirement 3.** "Exclude simultaneous cooperating installations to the same destination with an exclusive filesystem lock … Another process or reentrant invocation must fail promptly with a clear busy error and leave the owner's lock/data intact." The `terminal-alias` row encodes the same scenario.

**Witness:** `witnesses/i0185-lock-alias.js`.

- **Setup:** `<root>/alias-agent/skills` is a symlink to `<root>/agent/skills`, tried in both directions (owner via the real path, then via the alias).
- **Trigger:** the contender reenters on the owner's first source copy.
- **Required behaviour:** the contender throws `/busy|lock|progress/i`, the installation is unchanged by it, and the owner returns 6.

**Results:**

- **Reproduces on m04, m05, m14, m22, m32 and m33.** In both directions the contender returned 6 and changed the installation.
  - m32's lock is `${skillsDir}.devlyn-install.lock` (bin/devlyn.js:672).
  - m33's lock is `<os.tmpdir()>/devlyn-skills-<sha256(path.resolve(skillsDir))>.lock` (bin/devlyn.js:675-676), keyed lexically.
- **Passes:** m06, m13, m15, m23, m24 and m31. Their locks are keyed by realpath, or sit inside the physical directory (m24).
- **Reference:** reproduces (local run; calibration `terminal-alias` FAIL).
- **Note on m33.** Its findings also name the parent-alias configuration, and its `alias` row is FAIL. The witness uses the terminal-symlink configuration, which both m33 findings also name and which reproduces.

### K3: post-commit lock-release failure is not recovered as requirement 2 demands

**Claim.** After publication, one ordinary failure of the operation that removes the invocation's own lock leaves the new installation in place, and the prior installation is not restored. Some trees throw after already deleting their backups (m04, m06, m31, m33). Others retry the release and report success (m13, m23, m24).

**Binds: yes, to requirement 2:**

> "If one ordinary filesystem operation fails and subsequent recovery operations can succeed, restore all preexisting managed/deprecated paths and marker with exact bytes and file modes; remove newly created managed paths. Propagate an actionable failure to the caller … Do not require rollback after successful commit if only disposal of backup data fails: report that cleanup failure and keep recovery data, instead of concealing it."

Requirement 4 also applies: "Remove task-created staging/backup/lock debris after … successful recovery".

**This is the most consequential judgment.** I adopted the literal reading:

- The only exemption from rollback after commit is "only disposal of backup data". Lock release is not that, so it falls under the general restore-and-report rule.
- This is the registrants' post-seal adjudication for 0185, the `release` replay, which 0222/0232 carry as an oracle row.
- The strongest opposing reading is the held-out fault sweep's lenient rule: any post-commit removal failure may keep the new installation if it is reported. Under that reading:
  - m04, m06 and m31 codex:0 would not bind;
  - only "report the failure" would bind, through a report-only witness that reproduces on m13, m23 and m24;
  - the severe-witness subsets would then fail claude r1 I-vs-A, and hold for codex r2 I-vs-F, instead of the reverse.
- In both affected pairings, the oracle-row counts already fail the quality condition (see the decide.py section). The reading therefore changes which severe subsets hold, not the per-task quality outcome.
- The throw-without-restore and silent-success findings are one claim because all cite the same requirement 2 recovery obligation and the same backup-disposal-exemption argument.

**Witness:** `witnesses/i0185-lock-release-restore.js`.

- **Trigger:** the first `rmdirSync`/`rmSync`/`unlinkSync` of a path whose name contains `lock` fails once with EIO, wherever the tree keeps its lock.
- **Required behaviour:** the call throws, `agent/` is byte-, mode- and symlink-identical to its state before the call, and the lock no longer exists.

**Results:** reproduces on 11 of 12 trees.

| tree | call result | other observed state |
|---|---|---|
| m04, m06, m31, m33 | threw | lock retried and released, but backups already disposed, nothing restored |
| m05, m14, m22 | threw raw EIO | lock left |
| m15 | threw `EDEVLYN_CLEANUP` | lock left |
| m13, m23, m24 | **returned 6** | release retried |

**Passes:** m32 (codex F r2).

- It releases the lock before disposing of its backups: `try { fs.rmdirSync(lock); } catch` at bin/devlyn.js:773.
- On a failed release it rolls back under the still-held lock (:774-776), retries the release (:778), and throws.
- Its `release` row is PASS.

This is a real-tree demonstration that the requirement is satisfiable. A locally run corrected copy of the reference (`scratch/adj/trees/ref-k3/bin/devlyn.js`) also passes, together with acceptance, the `release` replay and `heldout`.

### K4: one transient fault strands the invocation's lock, so later installs are busy forever

**Claim.** A single failure while releasing or creating the invocation's own lock leaves the lock behind. Because an existing lock is never treated as stale, every later installation fails busy.

**Binds: yes, to requirement 3,** under requirement 2's failure model. Requirement 3 says: "Release only the current invocation's lock on success or ordinary failure; a later invocation must work."

**Witness:** `witnesses/i0185-lock-release-stuck.js`. Each trigger runs in a fresh fixture and fails exactly once:

- **remove:** the first lock removal;
- **read:** the first `readFileSync` of the lock after copying began;
- **close:** the first `closeSync` of a descriptor on the lock.

**Required behaviour:** a second plain call returns 6.

**Results:**

| tree | result | observed |
|---|---|---|
| m05, m14 | **reproduces** | remove: later call busy |
| m15 | **reproduces** | remove and read: later call busy; close ok |
| m22 | **reproduces** | remove, read and close: later call busy |
| m04, m06, m13, m23, m24, m31, m32, m33 | passes | one retry releases the lock |
| I0185 reference | reproduces | local run; bare `finally` release |

### K5: destination created before the lock

**Claim.** m24 runs `mkdirSync(skillsDir, {recursive})` before taking its lock, and its lock lives inside the skills directory. The failing sequence:

1. A creates the absent skills directory and pauses.
2. B takes its lock inside that directory.
3. A fails busy and cannot remove the directory, because it is not empty.
4. B fails with an ordinary copy error and keeps the directory, since it existed when B started.

The initially absent skills directory remains although both installations failed.

**Binds: yes, to two requirements:**

- requirement 3: "lock acquired before inspecting or mutating destination contents";
- requirement 2: "An initially absent skills directory must again be absent after failure".

The trigger is two cooperating installations plus one ordinary failure, both contemplated by the requirements. The registrants' `absence-lock` row encodes the same expectation, and m24 fails it for the same root cause.

**Witness:** `witnesses/i0185-mkdir-before-lock.js`. Two real processes hand-shake through files, with no timing assumptions. If B never reaches its copy because A already held the lock, the tree passes.

**Results:**

- **Reproduces only on m24.**
- **The other 11 trees pass.** They take their lock before creating the skills directory; m31 and m33 take it before creating any directory.
- **Reference (docker sanity):** passes.

### K6 (supplementary, no disposition references it): physical skill alias kept

m14 claude:1 guessed that its `terminal-alias` failure meant "Req 1: existing physical aliases must not remain alongside their canonical replacements". `witnesses/i0185-physical-alias.js` tests that guess.

**Results:** passes on all 12 trees and on the reference (docker sanity). The finding itself is disposed through K2, the defect its cited row detects.

### J1–J3 (D3): the delimiter is dropped on executable dispatch (m18, the unmodified base tree)

m18's `checks.json` lists no changed files.

| claim and witness | obligation (quoted) | trigger | m18 | other 11 D3 trees |
|---|---|---|---|---|
| J1 `d3-delimiter-dropped.js` | "Real spawned child receives -- before --not-an-option and parses it as an operand." | `parent child -- --not-an-option` | **reproduces**: child exits 1 `unknown option '--not-an-option'` | pass |
| J2 `d3-later-delimiter.js` | "Ordinary operands before/after the first delimiter retain order; subsequent -- tokens remain literal." | `parent child before -- after -- --tail` | **reproduces**: child argv `[before, after, --, --tail]` | pass |
| J3 `d3-alias-default.js` | "Alias and default executable routes preserve the same boundary." | `parent c -- …` and `parent -- …` | **reproduces**: both routes, unknown option | pass |

## `release` adjudications (0224 rule 1): m31 FAIL, m33 FAIL

**Why the row did not trigger.**

- The `release` replay (`control/oracle/experiments/0222/oracle/replay.js`) injects `REPLAY_LOCK_RELEASE` at the first `rmdirSync`/`rmSync`/`unlinkSync` whose path is under `<fixture>/agent` and whose name contains `lock`.
- It passes only if `!!fired && !!error && restored`, where `restored` means the `agent/` snapshot equals its pre-call state.
- m31 and m33 keep their owned lock outside the fixture:
  - **m31:** `/tmp/devlyn-skills-<sha256(realpath(skillsDir))>.lock`, defined at bin/devlyn.js:717-722 and released at :837.
  - **m33:** `<os.tmpdir()>/devlyn-skills-<sha256(path.resolve(skillsDir))>.lock`, defined at bin/devlyn.js:675-676 and released at :797.
- Their `checks-raw.json` replay output shows `fired: null`, no lock among the 34 recorded removals under `agent/`, and `returned: 6`. Hence NOT_TRIGGERED.

**Procedure** (0224 DESIGN rule 1): "root writes a variant of that replay that moves only the injection hook to the product's equivalent step (cited file:line: … the owned-lock release for `release`) and keeps every assertion byte-identical. The row is PASS only if the variant fires and passes."

The variants are `adjudication/replay-release-<cell>.js`. Each differs from `replay.js` only in:

- the hook predicate: `|| target===OWNED_LOCK`, with `OWNED_LOCK` computed exactly as the product computes it;
- the support `require`, pointed at the tree's byte-identical `tests/support.js`;
- fixed `product`/`kind` instead of argv, so `witness.py` can run it from the tree root.

The assertions are byte-identical (see `diff` against `replay.js`). Both ran twice in the cell image through `witness.py` via `adjudication/show-release-<cell>.js`. The results are in `adjudication/release-variant-results.json`.

| cell | fired | error | restored | passed | adjudication |
|---|---|---|---|---|---|
| m31-I0185-codex-I-r2 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock` (owned lock; 2 lock removals = failed attempt + retry) | `Could not release installation lock …: REPLAY_LOCK_RELEASE` | false | false | **FAIL** |
| m33-I0185-codex-A-r2 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock` (owned lock; failed attempt + retry) | `Cannot release skill installation lock …: REPLAY_LOCK_RELEASE` | false | false | **FAIL** |

**Cause.** Both trees dispose of their backups before releasing the lock, then retry the release and throw. The prior installation cannot be restored.

- m31 disposes at bin/devlyn.js:821-822 and releases at :837-842.
- m33 disposes at :766 inside the `try`, then releases in `finally` at :795-803.

The K3 witness, which tests the same requirement with the fault at the real lock, independently reproduces on both (docker: `restored:false`, `lockLeft:false`, error thrown).

**Consequence for the oracle-row counts (codex, I0185):**

- release passes: A = 0 (m04 FAIL, m33 FAIL), I = 0 (m06 FAIL, m31 FAIL), F = 1 (m32 PASS).
- A PASS for m33 would have put I below A. A PASS for m31 would have made I equal to F.

## Finding → claim → disposition

| cell | key | claim | disposition | witness |
|---|---|---|---|---|
| m04-I0185-codex-A-r1 | claude:0 | K1 EXDEV | reproduced | i0185-exdev |
| m04-I0185-codex-A-r1 | codex:0 | K3 lock-release restore | reproduced | i0185-lock-release-restore |
| m04-I0185-codex-A-r1 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| m05-I0185-codex-F-r1 | claude:0 | K3 (restates `release` and `terminal-alias` rows) | reproduced | i0185-lock-release-restore |
| m05-I0185-codex-F-r1 | codex:0 | K4 stranded lock | reproduced | i0185-lock-release-stuck |
| m05-I0185-codex-F-r1 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| m06-I0185-codex-I-r1 | claude:0 | K3 (restates `release`) | reproduced | i0185-lock-release-restore |
| m06-I0185-codex-I-r1 | codex:0 | K3 lock-release restore | reproduced | i0185-lock-release-restore |
| m13-I0185-claude-I-r1 | claude:0 | K3 (restates `heldout`, `release`) | reproduced | i0185-lock-release-restore |
| m13-I0185-claude-I-r1 | codex:0 | K3 (silent success) | reproduced | i0185-lock-release-restore |
| m14-I0185-claude-F-r1 | claude:0 | K3 (restates `release`) | reproduced | i0185-lock-release-restore |
| m14-I0185-claude-F-r1 | claude:1 | K2 (restates `terminal-alias`; its physical-alias guess is not reproduced, see K6) | reproduced | i0185-lock-alias |
| m14-I0185-claude-F-r1 | codex:0 | K4 stranded lock | reproduced | i0185-lock-release-stuck |
| m14-I0185-claude-F-r1 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| m15-I0185-claude-A-r1 | claude:0 | K4 stranded lock (read/unlink) | reproduced | i0185-lock-release-stuck |
| m15-I0185-claude-A-r1 | codex:0 | K4 stranded lock | reproduced | i0185-lock-release-stuck |
| m18-D3-codex-F-r1 | claude:0 | J1 delimiter dropped | reproduced | d3-delimiter-dropped |
| m18-D3-codex-F-r1 | claude:1 | J2 order / later delimiter | reproduced | d3-later-delimiter |
| m18-D3-codex-F-r1 | claude:2 | J3 alias and default routes | reproduced | d3-alias-default |
| m18-D3-codex-F-r1 | codex:0 | J1 delimiter dropped (also names J2/J3) | reproduced | d3-delimiter-dropped |
| m22-I0185-claude-A-r2 | claude:0 | K4 stranded lock (read; close) | reproduced | i0185-lock-release-stuck |
| m22-I0185-claude-A-r2 | claude:1 | K2 lock aliasing (also names K1, which reproduces too) | reproduced | i0185-lock-alias |
| m22-I0185-claude-A-r2 | codex:0 | K4 stranded lock | reproduced | i0185-lock-release-stuck |
| m22-I0185-claude-A-r2 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| m23-I0185-claude-F-r2 | claude:0 | K3 (restates `heldout`, `release`) | reproduced | i0185-lock-release-restore |
| m23-I0185-claude-F-r2 | codex:0 | K3 (silent success) | reproduced | i0185-lock-release-restore |
| m24-I0185-claude-I-r2 | claude:0 | K3 (restates `heldout`, `release`, `absence-lock`) | reproduced | i0185-lock-release-restore |
| m24-I0185-claude-I-r2 | codex:0 | K5 mkdir before lock | reproduced | i0185-mkdir-before-lock |
| m24-I0185-claude-I-r2 | codex:1 | K3 (silent success) | reproduced | i0185-lock-release-restore |
| m31-I0185-codex-I-r2 | codex:0 | K3 lock-release restore (throws after disposing backups) | reproduced | i0185-lock-release-restore |
| m32-I0185-codex-F-r2 | claude:0 | K2 lock aliasing (`${skillsDir}.devlyn-install.lock`) | reproduced | i0185-lock-alias |
| m32-I0185-codex-F-r2 | codex:0 | K2 lock aliasing | reproduced | i0185-lock-alias |
| m33-I0185-codex-A-r2 | claude:0 | K2 lock aliasing (lexical sha256 key; parent and terminal alias) | reproduced | i0185-lock-alias |
| m33-I0185-codex-A-r2 | codex:0 | K2 lock aliasing | reproduced | i0185-lock-alias |

## decide.py checks (scratch copy, all 36 cells)

- **`audit_gaps`, severe part:** no gap in any of the 36 cells.
- **`load()`:** with root's other judgments (`audited`, `false_completion`, `user_data_harm`) stubbed only for this check, it raises no error. In particular, no NOT_TRIGGERED row lacks an adjudication.

Severe-witness subset condition (an I tree's witness set must be contained in its A and F counterparts'):

- **Holds:** codex r1 vs A and F; claude r1 vs A and F; codex r2 vs A; D3 everywhere.
- **Fails:**
  - claude r2, m24 vs m22 (A) and m23 (F): `i0185-mkdir-before-lock`.
  - codex r2, m31 vs m32 (F): `i0185-lock-release-restore`.
- In both failing pairings, the I0185 oracle-row counts already fail:
  - claude: heldout I = 0 vs A = 2 and F = 1; absence-lock I = 1 vs A = 2 and F = 2.
  - codex I-vs-F: release I = 0 vs F = 1.

## What I could not establish

- **Reference sanity for K1–K4:** the reference does not meet those requirements. In its place, the following show the witnesses can pass:
  - passing trees: K1 m06, m13, m15, m24, m31; K2 m06, m13, m15, m23, m24, m31; K3 m32; K4 m04, m06, m13, m23, m24, m31, m32, m33;
  - the locally run corrected reference for K3;
  - the locally run original installer for K1's mount scenario.
- **The original installer's K1 symlink scenario was not run,** because the host has no second filesystem. Code inspection shows it has no crossing rename.

**Docker use beyond the witness runs.** All went through `witness.py`'s own runner, with the same flags:

- one environment probe;
- fifteen detail runs (probe scripts that exit 2 to print output);
- four `release` variant runs;
- three reference sanity runs (K1, K5, K6), via `run()` pointed at a copy of the reference tree.
