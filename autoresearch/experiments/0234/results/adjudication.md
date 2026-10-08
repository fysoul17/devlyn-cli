# 0234: severe-finding dispositions and NOT_TRIGGERED adjudications (prepared for root)

These follow the 0232 adjudication contract (`0232-live/adjudication-contract.md`) and its precedent (`0232-live/adjudication.md`, `decisions.json`).

## Summary

- **Findings:** 29, from `judge.py findings 0234`. All 29 are on task I0185 (cells d01–d10). No F23, F10, F11, E1 or E2 cell has a severe finding.
- **Distinct claims:** 11.
  - 10 bind: K2–K11. K2–K6 reuse the 0232 claims and witnesses; K7–K11 are new. K10 and K11 were added in response to Astra's review (see "Review response").
  - 1 does not bind: N1.
  - K5 and K6 are supplementary checks of mechanisms that findings mention only in passing or guess at. No disposition references them, and neither reproduces on any tree.
- **Dispositions:** 28 `reproduced` (each on its own cell's tree) and 1 `not_reproduced` (d02 codex:3, "not a requirement violation").
- **Witnesses:** 10 in `0234-live/witnesses/`.
  - Each was run on all 10 measured I0185 trees: d01–d05 (claude) and d06–d10 (codex), covering arms A r1/r2, B, H and P.
  - The final pass (`scratch/s0234/runs/*.final.json`) matches the earlier pass for every witness (pass1 for K2–K6, K8, K9; pass3 for K7; the per-tree detail runs `peerlock.detail.txt` and `sourcelink.detail.txt` for K10 and K11).
- **Adjudicated rows:** 1. `d06-I0185-codex-A-r1` `release` is **FAIL**.
- **decide.py check (scratch import of the apparatus `decide.py`):** `audit_gaps` reports no severe-finding gap in any measured cell. `complete()` for d06 with the adjudication gives False and raises no error.
- **Trees:**
  - d01, d02, d06 and d07 are reused from 0233 (`reused_from` d14, d35, d17, d32). `judge.py` evaluates them on `0233-live/out/<reused_from>/snapshot`.
  - `tests/support.js` is byte-identical in all 10 trees (sha256 6218f2e9…). It is also identical to the oracle's `0185/support.js` and to the 0232 trees.
  - The task request is the same I0185 request as 0232 (`0234-apparatus/.../0234/tasks.json`). Requirement quotes below are from it.

### How findings were grouped and read (same rules as 0232)

- **Grouping.** A claim is a pair: a trigger, and the requirement the finding cites as violated. Findings that share both form one claim and get one witness.
- **Findings with a concrete mechanism** are read by that mechanism.
- **Findings that only restate a failing root oracle row** are read as claiming the defect that row detects. They usually say "inferred, not confirmed".
  - These are d01 claude:0, d03 claude:0, d03 claude:1, d04 claude:0, d04 claude:1, d07 claude:0 and d08 claude:0.
  - d10 claude:0 is **not** in this list. It also names the `release` row, but it states a concrete mechanism of its own (a release that removes the lock and then reports an error, a peer that acquires in between, and a blind retry that deletes the peer's lock), so it is read by that mechanism: K10. (In round 1 it was disposed through K3; Astra's review correctly rejected that.)
  - d08 claude:0 also mentions, as a closing aside, that the blind retry "never checks ownership". Its stated mechanism (Case A: a committed install throws after a release fault whose retry succeeds; Case B: both attempts fail) is K3's, which reproduces on d08. K10 also reproduces on d08.
  - As in 0232, `release` and `heldout` map to K3, and `terminal-alias` maps to K2.
  - Some of these findings also guess a mechanism. The guesses are: lock ownership after a user deletes the lock (d03 claude:0), partial `rmSync` of recovery data and throw-on-cleanup (d04 claude:0), and a physical alias kept (d03 claude:1, d04 claude:1, tested by K6, all pass). Those guesses are not the disposition; the row's defect is.
- **The witness set covers only claims raised by a 0234 finding.** No finding raises 0232's K1 (EXDEV), so `i0185-exdev` is not part of 0234.

### Witness file header

All 10 witnesses share the 0232 I0185 fixture header byte for byte (107 lines, the text before `// Claim`).

- Each runs from `/work` in the cell image, with no network.
- Each exits 1 when the defect reproduces, 0 when the tree is correct, and 2 on a witness error.
- K2–K6 are byte-identical copies of the 0232 witnesses.
- K10 and K11 (round 2) were built from the same header (`scratch/s0234/header.js`) and checked identical to it.

## Per-tree reproduction (all 10 I0185 trees)

✓ = the defect reproduces.

| config | rep | arm | cell | K2 lock-alias | K3 release-restore | K4 stuck | K5 mkdir-before-lock | K6 physical-alias | K7 teardown-after-release | K8 lock-tmpdir | K9 after-marker-fault | K10 release-peer-lock | K11 deprecated-source-symlink |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude | r1 | A | d01 | ✓ | ✓ | ✓ | – | – | – | – | – | – | ✓ |
| claude | r2 | A | d02 | – | ✓ | ✓ | – | – | ✓ | – | – | – | ✓ |
| claude | r1 | B | d03 | ✓ | ✓ | ✓ | – | – | – | – | – | – | ✓ |
| claude | r1 | H | d04 | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – | ✓ |
| claude | r1 | P | d05 | – | ✓ | – | – | – | – | – | – | ✓ | ✓ |
| codex | r1 | A | d06 | ✓ | ✓ | – | – | – | – | ✓ | – | ✓ | ✓ |
| codex | r2 | A | d07 | – | ✓ | – | – | – | – | – | – | ✓ | ✓ |
| codex | r1 | B | d08 | – | ✓ | – | – | – | – | – | – | ✓ | ✓ |
| codex | r1 | H | d09 | – | – | – | – | – | – | – | – | ✓ | ✓ |
| codex | r1 | P | d10 | – | ✓ | – | – | – | – | – | – | ✓ | ✓ |

### Reproductions per witness, by config and arm

| witness | claude A (r1, r2) | claude B | claude H | claude P | codex A (r1, r2) | codex B | codex H | codex P | total |
|---|---|---|---|---|---|---|---|---|---|
| K2 i0185-lock-alias | 1 (r1) | 1 | 1 | 0 | 1 (r1) | 0 | 0 | 0 | 4 |
| K3 i0185-lock-release-restore | 2 | 1 | 1 | 1 | 2 | 1 | 0 | 1 | 9 |
| K4 i0185-lock-release-stuck | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 4 |
| K5 i0185-mkdir-before-lock | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| K6 i0185-physical-alias | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| K7 i0185-teardown-after-release | 1 (r2) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| K8 i0185-lock-tmpdir | 0 | 0 | 0 | 0 | 1 (r1) | 0 | 0 | 0 | 1 |
| K9 i0185-after-marker-fault | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| K10 i0185-release-peer-lock | 0 | 0 | 0 | 1 | 2 | 1 | 1 | 1 | 6 |
| K11 i0185-deprecated-source-symlink | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 10 |

### Severe-witness subsets (decide.py `quality.severe`, replicate 1; development A r2 is descriptive only)

| config | comparison | holds? | why not |
|---|---|---|---|
| claude | P ⊆ B | **no** | P (d05) has K10; B (d03) does not |
| claude | P ⊆ A | **no** | P (d05) has K10; A r1 (d01) does not |
| claude | H ⊆ B | **no** | H (d04) has K9; B (d03) does not |
| claude | P ⊆ H | **no** | P (d05) has K10; H (d04) does not |
| claude | B ⊆ A | yes | |
| codex | P ⊆ B | yes | |
| codex | P ⊆ A | yes | |
| codex | H ⊆ B | yes | |
| codex | P ⊆ H | **no** | P (d10) has K3; H (d09) does not |
| codex | B ⊆ A | yes | |

Per-tree sets (replicate 1 unless noted): d01 {K2,K3,K4,K11}; d02 (A r2) {K3,K4,K7,K11}; d03 {K2,K3,K4,K11}; d04 {K2,K3,K4,K9,K11}; d05 {K3,K10,K11}; d06 {K2,K3,K8,K10,K11}; d07 (A r2) {K3,K10,K11}; d08 {K3,K10,K11}; d09 {K10,K11}; d10 {K3,K10,K11}. Computed from `decisions-severe.json` the way `decide.py` builds `reproduced` (every witness with `true` on the tree).

These hold only if I0185 is a selected development task for that config. Selection comes from screening eligibility, which this document does not decide.

## Claims

### K2: lock-path aliasing through a symlinked skills directory (0232 witness `i0185-lock-alias.js`, reused)

**Claim.** The lock is derived from the path spelling, not the physical directory. Two configured skills directories that are one physical directory therefore take different locks, and a reentrant installation through the other spelling is admitted.

**Binds: yes, to requirement 3.** "Exclude simultaneous cooperating installations to the same destination with an exclusive filesystem lock … Another process or reentrant invocation must fail promptly with a clear busy error and leave the owner's lock/data intact." The `terminal-alias` oracle row encodes the same scenario.

**Witness and trigger.** `<root>/alias-agent/skills` is a symlink to `<root>/agent/skills`, tried in both directions. The contender reenters on the owner's first source copy. Required: the contender throws `/busy|lock|progress/i`, the installation is unchanged by it, and the owner returns 6.

**Results.**

- **Reproduces on d01, d03, d04 and d06.** These are exactly the four trees whose `terminal-alias` row is FAIL.
  - d01, d03 and d04 lock at `<parent>/.skills.devlyn-install.lock` by path spelling.
  - d06 locks at `os.tmpdir()/devlyn-skills-<sha256(path.resolve(skillsDir))>.lock` (bin/devlyn.js:675-676), which is lexical.
- **Passes on d02, d05 and d07–d10.** d05 and d07–d10 key the lock by realpath. d02 keeps it inside the physical skills directory.

### K3: post-commit lock-release failure is not recovered as requirement 2 demands (0232 witness `i0185-lock-release-restore.js`, reused)

**Claim.** After publication, one ordinary failure of the operation that removes the invocation's own lock leaves the new installation in place. The prior installation is not restored, and some trees do not report the failure at all.

**Binds: yes, to requirement 2.** "If one ordinary filesystem operation fails and subsequent recovery operations can succeed, restore all preexisting managed/deprecated paths and marker with exact bytes and file modes … Do not require rollback after successful commit if only disposal of backup data fails". Requirement 4 also applies: "Remove task-created staging/backup/lock debris after … successful recovery".

0232's literal reading is adopted unchanged: lock release is not "disposal of backup data". The 0232 notes on the opposing, lenient reading apply here too.

**Witness and trigger.** The first `rmdirSync`/`rmSync`/`unlinkSync` of a path whose name contains `lock` fails once with EIO, wherever the tree keeps its lock. Required: the call throws, `agent/` is identical to its state before the call, and the lock no longer exists.

**Results: reproduces on 9 of 10 trees** (detail: `scratch/s0234/runs/restore.detail.txt`).

| tree | result |
|---|---|
| d01, d02, d03, d04 | threw, lock left, nothing restored |
| d05, d06, d08, d10 | threw after retrying the release; lock gone, but backups already disposed and nothing restored |
| d07 | **returned 6** (silent retry) |

**Passes:** d09 (codex H). It released under rollback: "Skill installation failed …", `restored: true`, lock gone. Its `release` row is PASS. This shows the requirement is satisfiable on a real tree.

### K4: one transient fault strands the invocation's lock, so later installs are busy forever (0232 witness `i0185-lock-release-stuck.js`, reused)

**Claim.** A single failure while releasing or creating the invocation's own lock leaves the lock behind. Because an existing lock is never treated as stale, every later installation fails busy.

**Binds: yes, to requirement 3,** under requirement 2's one-failure model. "Release only the current invocation's lock on success or ordinary failure; a later invocation must work."

**Witness and trigger.** Each trigger runs in a fresh fixture and fails exactly once: the first lock removal (**remove**), the first `readFileSync` of the lock (**read**), or the first `closeSync` of a lock descriptor (**close**). Required: a second plain call returns 6.

**Results** (detail: `scratch/s0234/runs/stuck.detail.txt`):

| tree | remove | close | read | result |
|---|---|---|---|---|
| d01 | later call busy | ok | – | **reproduces** |
| d02 | later call busy | later call busy | – | **reproduces** (close is the d02 claude:0 / codex:1 trigger: `closeSync` at :781 lies outside the acquisition catch) |
| d03 | later call busy | – | – | **reproduces** |
| d04 | later call busy | – | – | **reproduces** |
| d05–d10 | ok | ok where applicable | ok where applicable | passes. A later call returned 6 in every applicable scenario. d05's detail run shows its release retry frees the lock; d06–d10 had no detail run |

"–" means the trigger did not apply to that tree.

### K5: destination created before the lock (0232 witness `i0185-mkdir-before-lock.js`, reused, supplementary)

d02 codex:2 notes in passing: "Directory creation also precedes lock acquisition at lines 817–818". The 0232 witness tests that consequence: two real processes, and the initially absent skills directory must be absent after both fail.

**Results: passes on all 10 trees.**

- d02 does create `agent/` before its lock at :818-819. However, it tracks the directories each invocation created, so the second process removes the skills directory it created.
- The finding's main claim is K7.

### K6: physical skill alias kept (0232 witness `i0185-physical-alias.js`, reused, supplementary)

This tests the guess in d03 claude:1 and d04 claude:1 ("existing physical aliases must not remain alongside their canonical replacements").

**Results: passes on all 10 trees.** Both findings are disposed through K2, the defect their cited `terminal-alias` row detects, which reproduces on both trees.

### K7 (new): recovery teardown of the destination after the lock is released (`witnesses/i0185-teardown-after-release.js`)

**Claim (d02 codex:2).** On a failed install into an initially absent destination, the tree releases its lock before it removes the skills directory it created. A reentrant installation entering at that removal is admitted and installs, while the first invocation is still recovering. The first invocation then cannot remove the now-populated directory.

**Binds: yes, to requirement 3.** It requires "an exclusive filesystem lock acquired before inspecting or mutating destination contents" and says "Another process or reentrant invocation must fail promptly with a clear busy error". Removing the destination is a destination mutation that belongs to the invocation, so it must happen inside the exclusion.

**Witness and trigger.** A fresh fixture with no `agent/`, in two scenarios with one ordinary failure each:

- **copy:** the first `copyFileSync` from the source fails once with EIO;
- **publish:** the first `renameSync` whose destination is directly inside the skills directory fails once.

At the first `rmdirSync`/`rmSync` whose target is the skills directory itself, `installSkillsForCLI('codex')` is entered again, once, with no fault. Required: the reentrant call throws a busy error. If the tree never removes the skills directory itself, that scenario cannot occur and passes.

**Scope correction made during the work.** The first version also reentered at removal of an ancestor of the skills directory, which is the created `agent/` directory.

- That fired on 7 trees, all of which keep the lock in `agent/` and remove `agent/` only after the destination is already gone and the lock released.
- Removing the directory that only hosted the lock is lock-debris removal, not destination teardown. A lock that lives in a created parent can only be removed before that parent is.
- So I restricted the trigger to the destination itself, and added the publish scenario, because most trees never create the destination before a copy failure. pass1 and pass2 are superseded; pass3 equals the final pass.

**Results** (detail: `scratch/s0234/runs/teardown.detail3.txt`):

- **Reproduces only on d02.** In the publish scenario, the reentrant call at `rmdirSync <fixture>/agent/skills` returned 6. The outer call then failed and left the skills directory present.
  - Cause: `releaseSkillInstallLock(lock)` at bin/devlyn.js:908, then `removeCreatedDirs(createdDirs)` at :910, with the lock file inside the skills directory.
- **Passes on the other 9.** In the publish scenario the reentrant call hits the held lock and gets a busy error ("…busy…" in every tree). In the copy scenario, none of the 9 creates the destination before a copy failure.

### K8 (new): lock location depends on TMPDIR (`witnesses/i0185-lock-tmpdir.js`)

**Claim (d06 codex:1).** The lock lives under `os.tmpdir()`. Two cooperating processes installing into the same destination with different `TMPDIR` values therefore take different locks, and both proceed.

**Binds: yes, to requirement 3,** with the same quote as K2. The trigger is plausible: an interactive macOS shell has a per-user `TMPDIR`, while cron, `sudo` and launchd jobs often have it unset (`/tmp`). The destination is the same `~/.codex/skills` in both cases.

**Witness and trigger.** While the owner copies its first source file, a second real process loads the same product with the same destination, `TMPDIR` set to another existing directory, and calls the install. Required: the second process fails busy, the installation is unchanged by it, and the owner returns 6.

**Results** (detail: `scratch/s0234/runs/tmpdir.detail.txt`):

- **Reproduces only on d06.** The contender saw `tmpdir=/tmp/witness-other-tmpdir-…`, returned 6, and changed the installation. The owner also returned 6.
- **Passes on the other 9.** None places its lock in `os.tmpdir()`. For example, d07's contender failed with "busy … lock exists at <fixture>/agent/.skills.devlyn-install.lock".

### K9 (new): fault right after the new marker is published (`witnesses/i0185-after-marker-fault.js`)

**Claim (d04 codex:1).**

- `writeInstallMarker` renames the new marker into place, then its `finally` `fs.rmSync(tempPath)` throws (bin/devlyn.js:410-428, called at :752).
- The catch rolls the skills back but has no undo step for the new marker.
- With an existing destination and no prior marker, the new marker is left beside the restored old skills.
- With an initially absent destination, the leftover marker makes `rmdirSync(skillsDir)` fail with ENOTEMPTY (:740). The destination, recovery data and lock remain.

**Binds: yes, to requirements 2 and 3.**

- Requirement 2: "If one ordinary filesystem operation fails and subsequent recovery operations can succeed, restore all preexisting managed/deprecated paths and marker with exact bytes and file modes; remove newly created managed paths … An initially absent skills directory must again be absent after failure."
- Requirement 3: "a later invocation must work."
- The trigger is one ordinary failure (EIO) in a filesystem operation of the install. A skills directory without a marker is a legacy installation written before the marker existed; the base's `clearInstallMarker` handles that case.
- The oracle `heldout` sweep uses only the standard fixture, which has a prior marker, so it cannot see this.

**Witness and trigger.** Two scenarios, each in a fresh fixture:

- **legacy:** a prior installation with the marker removed;
- **fresh:** no destination.

The first `rmSync`/`unlinkSync`/`rmdirSync` of a non-lock path made after a schema-1 marker exists at `<skills>/.devlyn-install.json` fails once with EIO.

**Required behaviour:**

- after the call, `agent/` is either identical to before, or holds the complete new installation (the post-commit backup-disposal exemption);
- a later plain call returns 6;
- a scenario in which no such removal happens passes.

**Results** (detail: `scratch/s0234/runs/marker.detail.txt` and the compact d04 run below):

- **Reproduces only on d04.**
  - legacy: the error says "failed; previous installation restored", but the new content is missing for all 6 skills and the new marker is present (8 problems).
  - fresh: rollback fails, the skills directory remains, and a later call is busy.
- **Passes on the other 9, with the fault firing in every one:**
  - d01 and d02 fire on the same marker temp file and restore exactly;
  - d03 and d05–d10 fire on post-commit workspace disposal and keep a complete new installation;
  - in every tree a later call returns 6.

### K10 (new, round 2): a blind release retry deletes a peer's lock (`witnesses/i0185-release-peer-lock.js`)

**Claim (d10 claude:0).** Release is a path-only `fs.rmdirSync(lockPath)` (d10 bin/devlyn.js:795), and on any error it calls `fs.rmdirSync(lockPath)` again (:801) with no ownership check. If the first call removes the directory and then reports an error, and a cooperating peer acquires the free lock before the retry, the retry deletes the peer's lock, so a third installation can enter beside the peer.

**Binds: yes, to requirement 3.** "Release only the current invocation's lock on success or ordinary failure … leave the owner's lock/data intact … An existing lock is never assumed stale or stolen." The peer is the owner at retry time; the retry assumes the lock at that path is still the invocation's own.

- **The trigger is the finding's own** (contract: "Fault injection is allowed when it realizes the finding's own trigger"): a removal that takes effect and then reports failure (the finding names an NFS retransmit or a delegating wrapper), plus a cooperating peer, which requirement 3 is about. No crash, malicious writer or source change is involved.
- **It is satisfiable together with K4.** A tree must recover from a release that fails without effect (K4) and must not delete a lock it no longer owns (K10). A local sanity variant (`scratch/s0234/sanity/k10-token`, d10's file with an owner-token release: the lock directory holds a unique owner file, release unlinks it and then removes the directory, and the retry removes only a lock that is empty or still holds its own token; diff in `k10-token.diff`) exits 0 on both K10 and K4 (`scratch/s0234/sanity/results.txt`). This was a plain local `node` run, not a measured tree.

**Witness and trigger.** Standard fixture. Armed once the owner has started copying from the source bundle. On each `rmdirSync`/`rmSync`/`unlinkSync` of a path whose name contains `lock`, the real removal runs first; then a second real process loads the same product with the same destination (same `TMPDIR`) and calls `installSkillsForCLI('codex')`. If that peer is busy, the removal returns normally (it did not free the lock). If the peer acquires the lock and reaches its first source copy, it exits there, leaving its lock exactly as a live peer holds it; the witness records every lock-named artifact that appeared or changed (under the fixture and at the top of `os.tmpdir()`), and the owner's removal then throws EIO, once. Required: every peer lock artifact is still present and unchanged after the owner returns or throws. If no removal ever frees the lock for the peer, the scenario cannot occur and passes.

**Results** (detail: `scratch/s0234/runs/peerlock.detail.txt`; the fault fired, with the peer acquiring, on all 10 trees):

| tree | faulted removal | owner outcome | peer lock |
|---|---|---|---|
| d01, d02 | `unlinkSync` of the lock file | throws (release failure reported) | **kept** |
| d03, d04 | `rmdirSync` of the lock directory | throws (release failure reported) | **kept** |
| d05 | `rmdirSync` | throws "released only on retry" | **deleted by the retry** |
| d06 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock` | throws "committed, but cleanup failed" | **deleted by the retry** |
| d07 | `rmdirSync` | **returns 6** | **deleted by the retry** |
| d08, d10 | `rmdirSync` | throws "committed/installed, but cleanup failed" | **deleted by the retry** |
| d09 | `rmdirSync` at :769 (release inside the `try`) | throws "Skill installation failed" | **deleted**: the catch rolls the destination back while the peer holds the lock, then `if (locked)` removes the lock path again at :795 |

- **Reproduces on d05–d10** (6 trees): every tree that retries the release by path.
- **Passes on d01–d04**, which do not retry. Those four strand their own lock on a release fault that has no effect, which is K4 (reproduced there); passing K10 does not make their release correct.

### K11 (new, round 2; was N2): deprecated cleanup through a symlinked `agent/commands` deletes a source file (`witnesses/i0185-deprecated-source-symlink.js`)

**Claim (d09 codex:0).** If `agent/commands` is a preexisting user symlink into `config/skills/devlyn:resolve`, and that source skill contains `devlyn.handoff.md`, the deprecated-path handling removes `agent/commands/devlyn.handoff.md` through the symlink, which deletes the real source file. d09 renames it into its backup (bin/devlyn.js:752-753) and disposes the backup after publication.

**Binds: yes, to requirement 1** ("Preserve unrelated files, user-installed skills and every source file … Preserve symlinks in unrelated user content without following or rewriting their targets") and requirement 4 ("Preserve original content outside the owned paths").

- The trigger is one preexisting symlink, with no fault, no concurrent writer and no change to the source tree by anyone but the installer. Requirement 4's "changes to selected source trees during an install are out of scope" excludes outside changes, not the installer's own deletion.
- Round 1 called this non-binding because the unmodified base does the same and the setup is unusual. That was wrong (see "Review response"): requirement 1 is an explicit, unconditional preservation requirement, "perform the same deprecated cleanup" describes which paths are cleaned, not a licence to follow a symlinked parent into the sources, and 0232 itself recorded defects that reproduce on the unmodified base tree (J1–J3 on m18).
- **Satisfiable.** A local sanity variant of the base (`scratch/s0234/sanity/k11-skip`, `cleanupDeprecated` skips a deprecated file whose parent resolves elsewhere than `<target>/commands`; 3-line diff in `k11-skip.diff`) exits 0; the unmodified base exits 1 (`scratch/s0234/sanity/results.txt`). Local `node` runs, not measured trees.

**Witness and trigger.** The standard fixture, with `<root>/agent/commands` replaced by a symlink to `<root>/config/skills/devlyn:resolve` and `config/skills/devlyn:resolve/devlyn.handoff.md` added. Required, whether the call returns or throws: the whole source bundle (`config/skills`) is byte-for-byte unchanged and the `agent/commands` symlink still exists with the same target.

**Results** (detail: `scratch/s0234/runs/sourcelink.detail.txt`): **reproduces on all 10 trees.** Every tree returned 6, and in every tree `devlyn:resolve/devlyn.handoff.md` was gone from the source bundle while the symlink itself was kept. No measured tree guards the deprecated path against a symlinked parent. Because it reproduces on every tree, it does not change any subset relation in the table above.

## Claim that does not bind (`not_reproduced`, no witness)

### N1: preexisting `.devlyn-install.json.<pid>.tmp` destroyed (d02 codex:3)

**Claim.** A preexisting file in the skills directory whose name equals the marker temp name for the current pid is deleted by `writeInstallMarker`'s `finally` and by rollback.

**Not a requirement violation.** The reason is scope, not base equivalence:

- The name is in the installer's own marker namespace: `${markerPath}.${process.pid}.tmp`, the temp name the existing `writeInstallMarker` (sources/I0185 bin/devlyn.js:410-428) has always used. A file of that name can only be left by an earlier installer run that died between creating and renaming its temp marker, with the same pid. That is a process crash, which requirement 4 puts out of scope ("Process crashes, power loss/fsync durability … are out of scope"). Leftover debris of the installer's own crashed run is not "unrelated" user content.
- Context only, not the reason: the unmodified base deletes the same file (`scratch/s0234/base/check.js`, `preexistingKept: false`). After the review of N2, base equivalence alone is not treated as an exemption anywhere in this document.

## Finding → claim → disposition

| cell | key | claim | disposition | witness |
|---|---|---|---|---|
| d01-I0185-claude-A-r1 | claude:0 | K3 (restates `release`, `terminal-alias`) | reproduced | i0185-lock-release-restore |
| d01-I0185-claude-A-r1 | codex:0 | K4 stranded lock (unlink) | reproduced | i0185-lock-release-stuck |
| d01-I0185-claude-A-r1 | codex:1 | K2 lock aliasing (terminal symlink) | reproduced | i0185-lock-alias |
| d02-I0185-claude-A-r2 | claude:0 | K4 stranded lock (closeSync in acquisition) | reproduced | i0185-lock-release-stuck |
| d02-I0185-claude-A-r2 | codex:0 | K4 stranded lock (unlink release) | reproduced | i0185-lock-release-stuck |
| d02-I0185-claude-A-r2 | codex:1 | K4 stranded lock (closeSync) | reproduced | i0185-lock-release-stuck |
| d02-I0185-claude-A-r2 | codex:2 | K7 teardown after release (K5 aside passes) | reproduced | i0185-teardown-after-release |
| d02-I0185-claude-A-r2 | codex:3 | N1 marker temp-name collision | not_reproduced | – |
| d03-I0185-claude-B-r1 | claude:0 | K3 (restates `release`; ownership guess) | reproduced | i0185-lock-release-restore |
| d03-I0185-claude-B-r1 | claude:1 | K2 (restates `terminal-alias`; K6 guess passes) | reproduced | i0185-lock-alias |
| d03-I0185-claude-B-r1 | codex:0 | K4 stranded lock (rmdir) | reproduced | i0185-lock-release-stuck |
| d03-I0185-claude-B-r1 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d04-I0185-claude-H-r1 | claude:0 | K3 (restates `release`) | reproduced | i0185-lock-release-restore |
| d04-I0185-claude-H-r1 | claude:1 | K2 (restates `terminal-alias`; K6 guess passes) | reproduced | i0185-lock-alias |
| d04-I0185-claude-H-r1 | codex:0 | K4 stranded lock (rmdir) | reproduced | i0185-lock-release-stuck |
| d04-I0185-claude-H-r1 | codex:1 | K9 fault after marker publication | reproduced | i0185-after-marker-fault |
| d04-I0185-claude-H-r1 | codex:2 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d05-I0185-claude-P-r1 | codex:0 | K3 (throws after retry, not restored) | reproduced | i0185-lock-release-restore |
| d06-I0185-codex-A-r1 | claude:0 | K2 lock aliasing (lexical sha256 key) | reproduced | i0185-lock-alias |
| d06-I0185-codex-A-r1 | codex:0 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d06-I0185-codex-A-r1 | codex:1 | K8 TMPDIR-dependent lock | reproduced | i0185-lock-tmpdir |
| d06-I0185-codex-A-r1 | codex:2 | K3 (throws after retry, not restored) | reproduced | i0185-lock-release-restore |
| d07-I0185-codex-A-r2 | claude:0 | K3 (restates `heldout`, `release`) | reproduced | i0185-lock-release-restore |
| d07-I0185-codex-A-r2 | codex:0 | K3 (silent success) | reproduced | i0185-lock-release-restore |
| d08-I0185-codex-B-r1 | claude:0 | K3 (restates `release`; Case A is K3's mechanism) | reproduced | i0185-lock-release-restore |
| d08-I0185-codex-B-r1 | codex:0 | K3 (throws after retry, not restored) | reproduced | i0185-lock-release-restore |
| d09-I0185-codex-H-r1 | codex:0 | K11 deprecated cleanup through a symlinked parent deletes a source file | reproduced | i0185-deprecated-source-symlink |
| d10-I0185-codex-P-r1 | claude:0 | K10 blind release retry deletes a peer's lock | reproduced | i0185-release-peer-lock |
| d10-I0185-codex-P-r1 | codex:0 | K3 (throws after retry, not restored) | reproduced | i0185-lock-release-restore |

## Adjudicated NOT_TRIGGERED rows (0224 rule 1)

Only one measured cell has status ADJUDICATE, and only one NOT_TRIGGERED row: `d06-I0185-codex-A-r1` `release`. No other measured 0234 verdict has a NOT_TRIGGERED row.

### d06-I0185-codex-A-r1 `release`: FAIL

**Why the row did not trigger.**

- The tree is 0233 d17 (bin/devlyn.js sha256 8eee1095…).
- It keeps its owned lock outside the fixture: `<os.tmpdir()>/devlyn-skills-<sha256(path.resolve(skillsDir))>.lock`, defined at bin/devlyn.js:675-676 and released in `finally` at :800, with a blind retry at :804. This is the same design as 0232's m33.
- `replay.js` hooks only removals under `<fixture>/agent`. 0233 d17's `checks-raw.json` records `fired: null`, `error: null`, `returned: 6`.

**Variant.** `scratch/s0234/adjudication/replay-release-d06-I0185-codex-A-r1.js` is 0232's m33 variant with only the header comment changed. Its `diff` against `control/oracle/experiments/0222/oracle/replay.js` shows exactly these differences:

- the header;
- the support `require`, pointed at the tree's byte-identical `tests/support.js`;
- fixed `product`/`kind`;
- `OWNED_LOCK`, computed as the product computes it;
- the hook predicate `|| target===OWNED_LOCK`.

Every assertion is byte-identical.

**Runs.** The variant ran twice in the cell image through `judge.py run`, using `show-release-d06-I0185-codex-A-r1.js`. Results are in `scratch/s0234/adjudication/release-variant-results.txt`.

| run | fired | error | restored | passed |
|---|---|---|---|---|
| 1 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock` (owned lock; 2 lock removals = failed attempt + retry) | `Skill installation committed, but cleanup failed …: REPLAY_LOCK_RELEASE` | false | false |
| 2 | same | same | false | false |

**Adjudication: FAIL.**

- Cause: the backups are disposed at :766, inside the `try`, before the lock is released in `finally`. The release is retried and the call throws, but the prior installation can no longer be restored.
- The K3 witness, with the fault at the real lock, independently reproduces on d06: threw, `restored: false`, `lockLeft: false`.
- The `release` PASS on d09, the only PASS among the 10, shows the requirement is satisfiable.

## Docker use

All Docker use went through `judge.py run`, with its own flags. It comprised:

- the witness passes recorded in `scratch/s0234/runs/` (pass1, pass2, pass3, final);
- detail runs, which are runners that print a witness's output and exit 2: K3 ×10, K4 ×5, K7 ×28, K8 ×2, K9 ×11, K10 ×11 (one extra d01 run, from a shell quoting slip that passed all ten cell names as one argument; the runner's exit 2 stopped it after d01), K11 ×10;
- two `release` variant runs;
- final passes of K10 and K11 (`scratch/s0234/runs/i0185-release-peer-lock.final.json`, `i0185-deprecated-source-symlink.final.json`).

Local, non-Docker runs: the two round-1 base-installer checks in `scratch/s0234/base/`, and the round-2 satisfiability sanity runs in `scratch/s0234/sanity/` (K10 and K4 on `k10-token`, K11 on `k11-skip` and on the unmodified base).

## What I could not establish

- **No external reference for K7–K11.** In its place, passing real trees show each witness can pass with its trigger firing:
  - K7: 9 trees, with the publish-scenario reentry busy in all 9;
  - K8: 9 trees;
  - K9: 9 trees, with the fault firing in all 9;
  - K10: 4 trees (d01–d04), with the peer acquiring in all 4, plus the local `k10-token` variant that also passes K4;
  - K11: no measured tree passes; the local `k11-skip` variant of the base passes.
- **K10's trigger is a removal that succeeds and then reports failure.** That is the finding's own trigger and a known network-filesystem behaviour, but it is less common than a failure without effect. The binding rests on requirement 3's ownership clauses, not on frequency.
- **K7's binding is a judgment call.** It is written down above: destination teardown belongs inside the exclusion, while removing a parent that only hosted the lock does not.
- **N1 is a not-binding judgment.** It rests on requirement 4's crash scope, not on base equivalence.

## Review response (Astra round 1, REVISE)

Source: `scratch/astra-severe-0234-r1.out.md`. Both HIGH findings were verified against the evidence and **accepted**; no finding was rebutted.

1. **HIGH: d10 claude:0 was disposed through K3, a different defect.** Accepted. The finding states its own mechanism (release removes the lock, then errors; a peer acquires; the blind retry deletes the peer's lock), and K3 faults before removal with no peer, so under the concrete-mechanism grouping rule it is not K3. Fix: new claim K10 and witness `i0185-release-peer-lock.js`, which realizes the finding's own trigger with a real peer process. Run on all 10 trees: reproduces on d05–d10, including d10, passes on d01–d04. d10 claude:0 is now `reproduced` with `i0185-release-peer-lock`. A local owner-token variant passes both K10 and K4, so the two are jointly satisfiable. K10 changes the claude subset relations: P (d05) now has a defect that B, A r1 and H lack.
2. **HIGH: N2's non-binding rationale did not meet requirement 1.** Accepted. Requirement 1 says "every source file"; the trigger is one preexisting symlink; base equivalence is not an exemption (0232 itself reproduced defects on the unmodified base, J1–J3 on m18). Fix: N2 is now binding claim K11 with witness `i0185-deprecated-source-symlink.js`. Run on all 10 trees: reproduces on all 10, including d09. d09 codex:0 is now `reproduced`. A local base variant that skips a deprecated file reached through a symlinked parent passes, so the requirement is satisfiable. Because K11 reproduces everywhere it changes no subset relation.
3. **Consequential change, not raised by Astra:** N1's write-up leaned on the same base-equivalence argument. Its disposition is unchanged, but its reason now rests only on requirement 4's crash scope, with base equivalence noted as context.

Round-1 versions are kept at `scratch/s0234/decisions-severe.r1.json` and `scratch/s0234/adjudication.r1.md`.
