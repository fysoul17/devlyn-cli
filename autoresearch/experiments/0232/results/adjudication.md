# 0232 stage 1: severe-finding dispositions (prepared for root)

State as of 2026-10-05T15:24Z (drive still running).

- **Available measured cells** (each has a `verdict-<cell>.json`, `.stop-` files ignored): m01–m30, 30 cells.
- **Severe findings:** 29, from `witness.py findings`, in 10 cells: 25 for I0185 (9 cells) and 4 for D3 (m18 only). No available D4 cell has a severe finding.
- **Distinct claims:** 8, all binding: K1–K5 for I0185 and J1–J3 for D3. One supplementary check, K6, tests a mechanism that one finding guessed.
- **Dispositions:** all 29 findings are `reproduced` on their own tree.
- **Pending trees:**
  - I0185: m31-I0185-codex-I-r2, m32-I0185-codex-F-r2, m33-I0185-codex-A-r2
  - D4: m34–m36
  - D3: none pending (all 12 trees run)

Witnesses are in `/Users/aipalm/.local/share/nx01/0232-live/witnesses/`:

- Each runs from `/work` in the cell image, with no network.
- Each exits 1 when the defect reproduces, 0 when the tree is correct, and 2 on a witness error.
- The I0185 witnesses share a byte-identical fixture header that mirrors the supplied `tests/support.js`, so each file is self-contained. The D3 witnesses share a D3 header in the same way.

Every witness ran through `witness.py run` on every available tree of its task, three times with identical results. The recorded results are in `scratch/adj/runs/`.

## How findings were grouped and read

- **Grouping.** A claim is a pair: a trigger, and the requirement the findings cite as violated. Findings that share both form one claim and get one witness.
- **Findings with a concrete mechanism** are read by that mechanism.
- **Findings that only restate a failing root oracle row** are read as claiming the defect that row detects. These are m05 claude:0, m06 claude:0, m13 claude:0, m14 claude:0, m14 claude:1, m23 claude:0 and m24 claude:0. They typically say "root cause not independently confirmed".
  - The rows are in `control/oracle/experiments/0222/oracle/` and `0185/heldout.js`.
  - `release` maps to K3 and `terminal-alias` maps to K2.
  - `heldout` maps to K3 as well. Its recorded failure in `out/<cell>/checks-raw.json` is `swallowed N` in the one-shot fault sweep for m13, m23 and m24, which is the lock-release failure being retried into success.
- **Locating the lock.** "Lock naming is internal", so K3 and K4 identify the lock as the first removed path under the fixture whose name contains `lock`. This is the same convention as the registrants' `release` replay. Every tree's fired path confirms it: `.skills.devlyn-lock`, `skills.devlyn-install.lock`, `.skills.devlyn-install.lock` and `skills/.devlyn-install.lock`. A tree with a differently named lock makes the witness exit 2. It never silently passes.

## Claims

### K1: cross-filesystem rename (EXDEV)

**Claim.** The staging and backup directories live in the skills directory's parent. Every backup and publish step therefore renames across the skills-directory boundary. When the skills directory is on another filesystem (a mount point, or a symlink to another volume), every install fails with EXDEV. The pre-change in-place installer succeeded on that layout.

**Binds: yes, to the keep-existing-behavior clause.**

- The task requires: "Upgrade the real `bin/devlyn.js` function `installSkillsForCLI(cliKey)` … This function is called by the existing CLI installation flow. Keep its synchronous API, return count, …"
- The original installer copies in place. Its only rename is the marker temp file renamed within the skills directory, so it returns 6 on this layout. A local mount-simulation run of the original passes with 0 crossing renames.
- The trigger is plausible: a Docker bind-mounted `~/.codex/skills`, or a symlink to another volume. Symlinked skills directories are explicitly in scope (the `terminal-alias` and `alias` rows).
- **Judgment call.** The registrants' own I0185 reference also fails the mount variant, because it renames the skills directory itself into `<parent>/.devlyn-install-*/old`. They may not have considered this layout in scope.

**Witness:** `witnesses/i0185-exdev.js`. Two scenarios run against the standard fixture with a prior installation and a deprecated command:

- **symlink:** `<root>/agent/skills` is a symlink to a directory on `/dev/shm` (tmpfs), while the fixture lives on the overlay `/tmp`. This produces a real kernel EXDEV with no injection.
- **mount:** `fs.renameSync` throws EXDEV for every rename between the inside and the outside of the skills directory.

**Required behaviour:** the install returns 6 and leaves a complete new installation.

**Results** (true means the defect reproduces):

| tree | arm/config/rep | result | observed (docker detail run) |
|---|---|---|---|
| m04 | A codex r1 | **true** | both scenarios: `rename skills/.devlyn-install.json -> agent/.skills.devlyn-update-*/backup/0` EXDEV |
| m05 | F codex r1 | **true** | both: `skills/devlyn:auto-resolve -> agent/skills.devlyn-install-*/backup/1` EXDEV |
| m06 | I codex r1 | false | both return 6; stages inside the destination, so no rename crosses |
| m13 | I claude r1 | false | both return 6 |
| m14 | F claude r1 | **true** | both: marker `-> agent/.skills.devlyn-work-*/backup-0` EXDEV |
| m15 | A claude r1 | false | both return 6 |
| m22 | A claude r2 | **true** | both: marker `-> agent/.skills.devlyn-install-*/backup/0` EXDEV |
| m23 | F claude r2 | **true** | symlink: deprecated `commands/devlyn.handoff.md` moved to the work dir beside the real destination on `/dev/shm`, EXDEV. mount: marker `-> agent/.skills.devlyn-install-*/...`, EXDEV |
| m24 | I claude r2 | false | both return 6; the mount scenario's single crossing is handled by its EXDEV copy fallback |
| I0185 reference | sanity (docker) | true | mount scenario fails (renames the skills dir itself); the reference does not meet K1 |

### K2: lock-path aliasing through a symlinked skills directory

**Claim.** The lock is derived from the lexical path. Two configured skills directories that are one physical directory, one being a symlink to the other, therefore take different locks. A reentrant installation through the other spelling proceeds and mutates the same installation instead of failing busy.

**Binds: yes, to requirement 3.** "Exclude simultaneous cooperating installations to the same destination with an exclusive filesystem lock … Another process or reentrant invocation must fail promptly with a clear busy error and leave the owner's lock/data intact." The registrants' `terminal-alias` row encodes the same scenario.

**Witness:** `witnesses/i0185-lock-alias.js`.

- **Setup:** `<root>/alias-agent/skills` is a symlink to `<root>/agent/skills`. The codex and omp targets get the two spellings, tried in both directions: owner via the real path with contender via the alias, then the reverse.
- **Trigger:** on the owner's first copy from the source bundle, the contender reenters.
- **Required behaviour:** the contender throws `/busy|lock|progress/i`, the physical directory is unchanged by it, and the owner returns 6.

**Results:**

| tree | result | observed |
|---|---|---|
| m04 (A codex r1), m05 (F codex r1), m14 (F claude r1), m22 (A claude r2) | **true** | in both directions the contender returned 6 and changed the installation |
| m06 (I codex r1), m13 (I claude r1), m15 (A claude r1), m23 (F claude r2) | false | contender refused busy (realpath-keyed lock), data unchanged, owner 6 |
| m24 (I claude r2) | false | the lock sits inside the physical directory, so the contender is refused busy |
| I0185 reference | true | local run only; consistent with calibration `terminal-alias` FAIL |

A correct implementation passes this witness (m06, m13, m15, m23, m24).

### K3: post-commit lock-release failure is not recovered as requirement 2 demands

**Claim.** After publication, one ordinary failure of the operation that removes the invocation's own lock leaves the new installation in place, and the prior installation is not restored. Some trees throw after already deleting their backups (m04, m06). Others retry the release and report success (m13, m23, m24).

**Binds: yes, to requirement 2:**

> "If one ordinary filesystem operation fails and subsequent recovery operations can succeed, restore all preexisting managed/deprecated paths and marker with exact bytes and file modes; remove newly created managed paths. Propagate an actionable failure to the caller … Do not require rollback after successful commit if only disposal of backup data fails: report that cleanup failure and keep recovery data, instead of concealing it."

Requirement 4 also applies: "Remove task-created staging/backup/lock debris after … successful recovery".

**This is the most consequential judgment.** I adopted the literal reading:

- The only exemption from rollback after commit is "only disposal of backup data". Lock release is not that, so it falls under the general restore-and-report rule.
- This is exactly the registrants' post-seal adjudication for 0185, the `release` replay ("Post-seal source-adjudication replay"), which 0222/0232 carry as an oracle row.
- The strongest opposing reading is the held-out fault sweep's lenient rule: any post-commit removal failure may keep the new installation if it is reported.
  - Under that reading, m04 codex:0 and m06 codex:0 would not bind.
  - The silent-success findings (m13 codex:0, m23 codex:0, m24 codex:1) would bind only to "report the failure".
  - A separate report-only witness would then reproduce on m13, m23 and m24 but not on m15 or m22. That would turn the claude I-vs-A severe-witness condition from pass to fail in replicate 1 as well.
- I treated the throw-without-restore and silent-success findings as one claim because all five cite the same requirement 2 recovery obligation and the same backup-disposal-exemption argument.

**Witness:** `witnesses/i0185-lock-release-restore.js`.

- **Trigger:** the first `rmdirSync`/`rmSync`/`unlinkSync` of a path under the fixture whose name contains `lock` fails once with EIO.
- **Required behaviour:** the call throws, and `agent/` is byte-, mode- and symlink-identical to its state before the call.

The requirement is satisfiable. A minimally corrected copy of the reference (`scratch/adj/trees/ref-k3/bin/devlyn.js`) passes this witness and K4, plus 5/5 acceptance, the registrants' `release` replay and `heldout` 4/4 (all run locally). The correction releases the lock before disposing of the backups, and on a release failure rolls back under the still-held lock, retries the release, and throws.

**Results:** true on all 9 trees. Observed:

| tree | call result | other observed state |
|---|---|---|
| m04 | threw "committed, but cleanup failed" | lock retried and released |
| m05 | threw raw EIO | lock left |
| m06 | threw "Could not release installation lock" | lock retried and released |
| m13 | **returned 6** | release retried |
| m14 | threw raw EIO | lock left |
| m15 | threw `EDEVLYN_CLEANUP` | lock left |
| m22 | threw raw EIO | lock left |
| m23 | **returned 6** | — |
| m24 | **returned 6** | — |

In every case the prior installation was gone. The I0185 reference also reproduces (local run; calibration `release` FAIL). Because the witness reproduces on every tree, it does not discriminate between arms.

### K4: one transient fault strands the invocation's lock, so later installs are busy forever

**Claim.** A single failure while releasing or creating the invocation's own lock leaves the lock behind. Because an existing lock is never treated as stale, every later installation fails busy.

**Binds: yes, to requirement 3,** under requirement 2's failure model ("one ordinary filesystem operation fails and subsequent recovery operations can succeed"). Requirement 3 says: "Release only the current invocation's lock on success or ordinary failure; a later invocation must work."

**Witness:** `witnesses/i0185-lock-release-stuck.js`. Each trigger runs in a fresh fixture and fails exactly once with EIO:

- **remove:** the first lock removal;
- **read:** the first `readFileSync` of the lock after copying began, which is the ownership check at release;
- **close:** the first `closeSync` of a descriptor opened on the lock.

A trigger that never fires is not applicable. **Required behaviour:** a second plain call returns 6.

**Results:**

| tree | result | observed |
|---|---|---|
| m05 (F codex r1), m14 (F claude r1) | **true** | remove scenario: later call busy |
| m15 (A claude r1) | **true** | remove and read scenarios: later call busy; close scenario ok |
| m22 (A claude r2) | **true** | remove, read and close scenarios: later call busy |
| m04 (A codex r1), m06 (I codex r1) | false | one retry releases the lock |
| m13 (I claude r1), m23 (F claude r2), m24 (I claude r2) | false | retry releases the lock; read and close scenarios also ok where applicable |
| I0185 reference | true | local run; bare `rmdirSync` in `finally` |

### K5: destination created before the lock

**Claim.** m24 runs `mkdirSync(skillsDir, {recursive})` before acquiring its lock, and the lock lives inside the skills directory. The failing sequence:

1. A creates the absent skills directory and pauses before taking its lock.
2. B takes its lock inside that directory.
3. A fails busy and cannot remove the directory, because it is not empty.
4. B fails with an ordinary copy error and keeps the directory, since it existed when B started.

The initially absent skills directory remains although both installations failed.

**Binds: yes, to two requirements:**

- requirement 3: "an exclusive filesystem lock acquired before inspecting or mutating destination contents";
- requirement 2: "An initially absent skills directory must again be absent after failure".

The trigger is two cooperating installations, which requirement 3 contemplates, plus one ordinary failure, which requirement 2 contemplates. The registrants' `absence-lock` row encodes the same expectation that the destination directory's lifecycle is protected by the lock. m24 fails that row for the same root cause.

**Witness:** `witnesses/i0185-mkdir-before-lock.js`. Two real processes hand-shake through files, with no timing assumptions:

- A runs in-process and pauses right after its first mkdir that creates the skills directory or an ancestor, until B is copying or has finished.
- B runs as a child process. It starts after A's mkdir, and its first source copy waits for A to finish, then fails once.

**Required behaviour:** when both fail, the skills directory does not exist. If B never reaches its copy, because A already held the lock, the tree passes.

**Results:**

- **m24 (I claude r2): true.** A failed busy, B failed with the injected copy error, and the skills directory was left present.
- **All other 8 trees: false.** Each takes its lock beside the skills directory before creating it. The parent A created may remain, which the requirement does not cover.
- **I0185 reference (docker sanity): false (exit 0).**

### K6 (supplementary, no disposition references it): physical skill alias kept

m14 claude:1 guessed that its `terminal-alias` failure meant "Req 1: existing physical aliases must not remain alongside their canonical replacements". The assessor itself states the alias path "looks correct" and the root cause is unconfirmed.

`witnesses/i0185-physical-alias.js` tests that guess. A prior `devlynresolve` must be replaced by `devlyn:resolve`, both directly and through a terminal symlink.

**Results:** false on all 9 trees and on the reference (docker sanity, exit 0). The finding itself is disposed through K2, the defect its cited row detects. K2 reproduces on m14.

### J1–J3 (D3): the delimiter is dropped on executable dispatch (m18, the unmodified base tree)

m18's `checks.json` lists no changed files. All three claims bind verbatim to the D3 obligations.

The shared harness:

- the parent is real Commander from `/work/index.js`, with executable subcommand `child` (`isDefault`, alias `c`);
- the child is real Commander with `--child` and `[values...]`, and prints its raw argv and what it parsed.

| claim and witness | obligation (quoted) | trigger | m18 | other 11 D3 trees |
|---|---|---|---|---|
| J1 `d3-delimiter-dropped.js` | "Real spawned child receives -- before --not-an-option and parses it as an operand." | `parent child -- --not-an-option` | **true**: child exits 1 `error: unknown option '--not-an-option'` | false |
| J2 `d3-later-delimiter.js` | "Ordinary operands before/after the first delimiter retain order; subsequent -- tokens remain literal." | `parent child before -- after -- --tail` | **true**: child argv `[before, after, --, --tail]`, operands `[before, after, --tail]` | false |
| J3 `d3-alias-default.js` | "Alias and default executable routes preserve the same boundary." | `parent c -- --not-an-option` and `parent -- --not-an-option` | **true**: both routes, child exits 1 unknown option | false |

The other 11 trees are m07, m08, m09, m16, m17, m19, m20, m21, m28, m29 and m30.

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

## Effect on the severe-witness quality condition

Checked with a scratch copy of decide.py's `audit_gaps` and subset logic:

- The 30 available cells have no audit gaps.
- In every I0185 r1 and D3 pairing, the I tree's witness set is a subset of A's and of F's.
- **The one exception is claude r2 I0185:** m24 has `i0185-mkdir-before-lock`, which m22 (A) and m23 (F) lack.
- codex r2 I0185 cannot be evaluated until m31–m33 exist.

## Pending work and what I could not establish

**To finish the pending trees:**

1. When m31–m33 have verdicts, run each of the six I0185 witnesses with `python3 witness.py run witnesses/<id>.js m31-I0185-codex-I-r2 m32-I0185-codex-F-r2 m33-I0185-codex-A-r2`.
2. Merge the results into `"witnesses"`, then dispose their findings. A new claim needs a new witness, run on all 12 I0185 trees.
3. If D4 cells m34–m36 bring severe findings, they need Python witnesses run on all D4 trees.

**Not established:**

- No reference sanity exists for K1–K4, because the reference does not meet those requirements:
  - K1: mount scenario, docker.
  - K2 and K3: also its calibration failures.
  - K4: bare `finally` release.
- In their place, the following show the witnesses can pass:
  - passing trees for K1, K2 and K4;
  - the locally run corrected reference for K3;
  - the locally run original installer for K1's mount scenario.
- The original installer's K1 symlink scenario was not run, because the host has no second filesystem. Code inspection shows it has no crossing rename.

**Docker use beyond the witness runs:**

- one environment probe and nine K1 detail runs, through `witness.py run` with probe scripts that exit 2 to print their output;
- three reference sanity runs (K1, K5, K6), through `witness.py`'s own `run()` pointed at a copy of the reference tree.
