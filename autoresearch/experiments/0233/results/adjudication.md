# 0233: severe-finding dispositions and NOT_TRIGGERED adjudications (prepared for root)

This follows the 0232 adjudication contract (`0232-live/adjudication-contract.md`) and its precedent (`0232-live/adjudication.md`, `decisions.json`). Output: `0233-live/decisions-severe.json` (`severe`, `witnesses`, `adjudicated`).

## Summary

- **Measured cells:** 84 (`judge.py cells 0233`). All have verdicts, so no trees are pending.
- **Severe findings:** 37 (`judge.py findings 0233`): 36 on I0185 (all 12 I0185 cells) and 1 on D4 (d09). No other task has a severe finding.
- **Distinct claims:** 10. All bind.
  - I0185: K2, K3, K4, K5 (reused 0232 witnesses) and K7, K8, K9, K10 (new witnesses).
  - D4: W1 (new witness).
  - K6 (the 0232 physical-alias check) runs again as a supplementary check. No disposition references it.
- **Dispositions:** 37 `reproduced`, each on its own cell's tree. 0 `not_reproduced`. (Revised after review: d35 codex:3 was `not_reproduced` in round 1; see "Review response".)
- **Witnesses:** 10, in `0233-live/witnesses/`:
  - 9 I0185 witnesses, each run on all 12 I0185 trees;
  - `d4-writer-death.py`, run on all 12 D4 trees.
- **Determinism:** every witness ran twice on every tree of its task (`0234-live/scratch/s0233/runs/*.p1*.json` and `*.p2*.json`). The two passes were identical.
- **Adjudicated rows:** 3 rows, all **FAIL**: `release` in d16-I0185-codex-C-r1, d17-I0185-codex-A-r1 and d33-I0185-codex-C-r2.
- **decide.py check** (scratch, with `audited` stubbed for all 84 cells only for this check): `audit_gaps` reports no severe gap in any cell. `complete()` raises nothing for the three ADJUDICATE cells and evaluates each as not complete.

Witness conventions are the same as in 0232:

- runs from `/work` in the cell image, with no network;
- exit 1 = the defect reproduces, 0 = the tree is correct, 2 = witness error;
- the I0185 witnesses share 0232's byte-identical fixture header (lines 1–106), which mirrors the supplied `tests/support.js`. That file is byte-identical in all 12 I0185 trees (sha256 `6218f2e9…`).

Detail runs used probes that exit 2 on purpose, so `judge.py` prints the witness's JSON. They are in `0234-live/scratch/s0233/runs/detail-*.txt`.

**Correctness sanity check.** A correct implementation must pass each witness:

- Each binding I0185 witness except K3 passes on at least one real 0233 tree. K10 passes on 8 real trees, and also on `ref-k3` on the host.
- K3 reproduces on all 12 trees. To show the requirement can be met, the corrected reference copy from 0232 (`0232-live/scratch/adj/trees/ref-k3`, copied to scratch) was run locally on the host. It passes K3, K4, K5, K7, K8, K9 and K6. It fails K2, which is the reference's known `terminal-alias` failure.
- W1 passes on 11 of 12 D4 trees, and the injection fired in every FIFO test of all 12 trees.

## Per-tree reproduction

✓ = the defect reproduces; – = the tree passes.

### I0185

| config / rep | arm | cell | K2 lock-alias | K3 release-restore | K4 stuck | K5 mkdir-before-lock | K7 tmpdir | K8 close-absence | K9 recovery-reentry | K10 temp-marker-preserve | K6 physical-alias |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude r1 | A | d14 | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – |
| claude r1 | B | d13 | – | ✓ | ✓ | ✓ | – | ✓ | ✓ | ✓ | – |
| claude r1 | C | d15 | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – |
| claude r2 | A | d35 | – | ✓ | ✓ | – | – | ✓ | ✓ | ✓ | – |
| claude r2 | B | d36 | – | ✓ | ✓ | ✓ | – | – | ✓ | – | – |
| claude r2 | C | d34 | ✓ | ✓ | ✓ | – | – | – | – | – | – |
| codex r1 | A | d17 | ✓ | ✓ | – | – | ✓ | – | – | – | – |
| codex r1 | B | d18 | ✓ | ✓ | – | – | – | – | – | – | – |
| codex r1 | C | d16 | – | ✓ | – | – | ✓ | – | – | – | – |
| codex r2 | A | d32 | – | ✓ | – | – | – | – | – | – | – |
| codex r2 | B | d31 | ✓ | ✓ | – | – | – | – | – | – | – |
| codex r2 | C | d33 | – | ✓ | – | – | ✓ | – | – | – | – |

The witnesses agree with the root oracle rows:

- K2 reproduces on exactly the six trees whose `terminal-alias` row is FAIL.
- K9 reproduces on exactly the three trees whose `absence-lock` row is FAIL (d13, d35, d36).
- K3 reproduces on every tree. Every `release` row is FAIL, and the three NOT_TRIGGERED rows are adjudicated FAIL below.

### D4

W1 `d4-writer-death` reproduces only on d09-D4-claude-B-r1. It passes on d07, d08, d10, d11, d12, d37, d38, d39, d40, d41 and d42.

### Reproductions by witness, arm and config

| witness | total | claude A | claude B | claude C | codex A | codex B | codex C |
|---|---|---|---|---|---|---|---|
| i0185-lock-alias (K2) | 6 | 1 | 0 | 2 | 1 | 2 | 0 |
| i0185-lock-release-restore (K3) | 12 | 2 | 2 | 2 | 2 | 2 | 2 |
| i0185-lock-release-stuck (K4) | 6 | 2 | 2 | 2 | 0 | 0 | 0 |
| i0185-mkdir-before-lock (K5) | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| i0185-lock-tmpdir (K7) | 3 | 0 | 0 | 0 | 1 | 0 | 2 |
| i0185-lock-close-absence (K8) | 2 | 1 | 1 | 0 | 0 | 0 | 0 |
| i0185-recovery-reentry (K9) | 3 | 1 | 2 | 0 | 0 | 0 | 0 |
| i0185-temp-marker-preserve (K10) | 4 | 2 | 1 | 1 | 0 | 0 | 0 |
| i0185-physical-alias (K6, supplementary) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| d4-writer-death (W1) | 1 | 0 | 1 | 0 | 0 | 0 | 0 |

### Effect on the severe-witness subset condition

The condition: a candidate tree's set of reproducing witnesses must be contained in the reference tree's set for the same task, config and replicate.

| task / config / rep | B/A | C/B | C/A |
|---|---|---|---|
| I0185 claude r1 | fails (B adds K5, K8, K9) | fails (C adds K2) | holds |
| I0185 claude r2 | fails (B adds K5) | fails (C adds K2) | fails (C adds K2) |
| I0185 codex r1 | holds | fails (C adds K7) | holds |
| I0185 codex r2 | fails (B adds K2) | fails (C adds K7) | fails (C adds K7) |
| D4 claude r1 | fails (B adds W1) | holds | holds |
| D4 claude r2, codex r1, codex r2 | holds | holds | holds |

Adding K10 changes no entry: it reproduces on all three claude r1 trees, and in claude r2 only on A (d35), the reference side of every claude r2 comparison.

K7 is a new claim with no 0232 precedent. It alone decides codex C/B (r1 and r2) and codex C/A r2. The binding judgment for it is set out under K7 below.

## Claims

### K2: lock-path aliasing through a symlinked skills directory (0232 K2, witness reused unchanged)

**Claim.** The lock is derived from the spelling of the destination path, not from the physical directory. When one configured skills directory is a symlink to another, the two spellings take different locks, and a reentrant installation through the other spelling proceeds.

**Binds: yes, to requirement 3.** "Exclude simultaneous cooperating installations to the same destination with an exclusive filesystem lock … Another process or reentrant invocation must fail promptly with a clear busy error and leave the owner's lock/data intact." The `terminal-alias` row encodes the same scenario.

**Witness:** `witnesses/i0185-lock-alias.js`.

- **Setup:** `<root>/alias-agent/skills` is a symlink to `<root>/agent/skills`. Both directions are run.
- **Trigger:** the contender reenters on the owner's first copy from the source bundle.
- **Required behaviour:** the contender fails busy and leaves the installation unchanged, and the owner returns 6.

**Results.**

- **Reproduces on d14, d15, d17, d18, d31 and d34.** In both directions the contender returned 6 and changed the installation.
  - On d15 the owner then also failed: ENOENT on its backup rename.
- **Passes on d13, d16, d32, d33, d35 and d36.**
  - d16 and d33 key the lock by realpath.
  - d13, d35 and d36 keep the lock inside the physical skills directory.
  - d32 keeps it beside the realpath of the destination (bin/devlyn.js:698-703).

### K3: a post-commit lock-release failure is not recovered as requirement 2 demands (0232 K3, witness reused unchanged)

**Claim.** After publication, one ordinary failure while removing the invocation's own lock leaves the new installation in place, and the prior installation is not restored. The trees fail in one of two ways:

- they throw after their backups are already gone;
- they retry the release and report success.

**Binds: yes, to requirement 2.**

> "If one ordinary filesystem operation fails and subsequent recovery operations can succeed, restore all preexisting managed/deprecated paths and marker with exact bytes and file modes … Do not require rollback after successful commit if only disposal of backup data fails"

Lock release is not disposal of backup data. Requirement 4 also applies: "Remove task-created staging/backup/lock debris after … successful recovery".

This is the same literal reading that 0232 adopted and root accepted. 0232's adjudication.md records the opposing lenient reading and its consequences. Under that reading, codex:0-style "throws after disposal" findings would not bind.

**Witness:** `witnesses/i0185-lock-release-restore.js`.

- **Trigger:** the first `rmdirSync`/`rmSync`/`unlinkSync` of a path whose name contains `lock` fails once with EIO, wherever the lock lives.
- **Required behaviour:** the call throws, `agent/` is identical to its state before the call, and the lock no longer exists.

**Results: reproduces on all 12 trees.** The detail runs confirm the injection hit each tree's own lock.

| trees | lock location | what happened |
|---|---|---|
| d13, d35, d36 | `agent/skills/.devlyn-install.lock` | threw "cleanup failed"; lock left |
| d14 | `agent/.skills.devlyn-install.lock` | threw; lock left |
| d15 | `agent/.skills.devlyn-install.lock` | threw; lock left |
| d34 | `agent/.devlyn-install.lock` | threw; lock left |
| d16, d17, d33 | `/tmp/devlyn-skills-<sha256>.lock` | threw after a successful retry; backups already disposed; nothing restored |
| d18, d31 | under `agent/` | threw after a successful retry; backups already disposed; nothing restored |
| d32 | `agent/.skills.devlyn-install.lock` | **returned 6** (silent retry) |

The corrected 0232 reference (`ref-k3`) passes.

### K4: one transient lock fault strands the lock, so later installs are busy forever (0232 K4, witness reused unchanged)

**Binds: yes, to requirement 3:** "Release only the current invocation's lock on success or ordinary failure; a later invocation must work."

**Witness:** `witnesses/i0185-lock-release-stuck.js`. Each trigger fails exactly once:

- **remove:** the first removal of the lock path;
- **read:** a read of the lock after copying has started;
- **close:** the first `closeSync` of a descriptor opened on the lock. The descriptor is closed, then EIO is reported.

**Required behaviour:** a second plain call returns 6.

**Results.**

- **Reproduces on d13, d14, d15, d34, d35 and d36.** In each, the later call was refused busy:
  - remove: all six trees;
  - close: d13 and d35 as well. d14's and d36's close scenarios recover.
- **Passes on d16, d17, d18, d31, d32 and d33.** One retry releases the lock.

### K5: destination created before the lock (0232 K5, witness reused unchanged)

**Binds: yes, to two requirements:**

- requirement 3: "lock acquired before inspecting or mutating destination contents";
- requirement 2: "An initially absent skills directory must again be absent after failure".

**Witness:** `witnesses/i0185-mkdir-before-lock.js`. Two real processes hand-shake through files.

- **Process A** (this process) installs into an absent destination and pauses right after its first `mkdir` that creates the skills directory or an ancestor.
- **Process B** then takes its lock and fails once while copying.
- **Required behaviour:** when both installations fail, the skills directory does not exist.

**Results.**

- **Reproduces on d13 and d36.** A failed busy against B's lock inside the directory that A had created. B then failed with a copy error, and the directory remained.
- **Passes on the other 10 trees.**
  - On d35, A failed with a raw `EEXIST` from its own non-recursive `mkdir`, not a busy error. The directory was absent at the end, so d35 passes this claim.
  - No d35 finding claims that unclear-error symptom.

### K7 (new): the lock location depends on each process's TMPDIR

**Claim** (d16 codex:0, d17 codex:1, d33 codex:1). The lock is `path.join(os.tmpdir(), 'devlyn-skills-<sha256>.lock')`. `os.tmpdir()` follows each process's `TMPDIR`. Two cooperating processes that install into the same destination with different existing `TMPDIR` values therefore take different locks, and both proceed.

The lock is defined at:

- d16: bin/devlyn.js:683-684;
- d17: :675-676;
- d33: :682-684.

**Binds: yes, to requirement 3:** "Exclude simultaneous cooperating installations to the same destination with an exclusive filesystem lock … Another process … must fail promptly with a clear busy error and leave the owner's lock/data intact."

- The requirement puts no condition on the processes' environment.
- `TMPDIR` routinely differs between processes of one user: a `sudo -E` or launchd context, a sandboxed terminal, a CI step, or a user-exported `TMPDIR`.
- The lock is the only mechanism protecting the destination, and it lives outside the destination in a location chosen per process.

**Judgment call.** This is a new claim with no 0232 precedent. The opposing reading is that "cooperating" installations share one environment, which would make the trigger implausible. Under that reading K7 does not bind, and its three findings would be `not_reproduced`.

The reading matters for the subset condition. K7 is the only witness that reproduces on a codex C tree and not on its reference. Without K7, every codex C tree's set would be {K3}. So codex C/B r1, C/B r2 and C/A r2 would hold instead of fail. Codex C/A r1 holds either way.

**Witness:** `witnesses/i0185-lock-tmpdir.js`. Two real processes, with no timing assumptions:

- **Owner:** this process, with `TMPDIR=<tmpA>`. On its first copy from the source bundle, while it holds its lock, it synchronously runs a second Node process.
- **Contender:** that second process, with `TMPDIR=<tmpB>`, the same product and the same destination.
- **Required behaviour:** the contender fails busy and leaves the installation unchanged, and the owner returns 6.

**Results.**

- **Reproduces on d16, d17 and d33.** The contender returned 6 and changed the installation while the owner held its lock.
- **Passes on the other 9 trees.** Each contender failed busy on a lock beside or inside the destination.
- `ref-k3` passes.

### K8 (new): the initial absence is lost after a lock-descriptor failure

**Claim** (d13 claude:0 part b, d13 codex:1, d35 claude:0, d35 codex:1). With no prior installation, `openSync(lock, 'wx')` succeeds and then `closeSync` fails once. The lock file is never removed. Because the lock lives inside the skills directory, the recovery `rmdir` of that directory fails with ENOTEMPTY. The initially absent directory, and the lock, remain.

**Binds: yes, to two requirements:**

- requirement 2: "An initially absent skills directory must again be absent after failure";
- requirement 4: "Remove task-created staging/backup/lock debris after … successful recovery".

The stranded-busy half of these findings is K4's close scenario. K8 tests the absence half, which is a distinct claim: the same trigger, against a different requirement.

**Witness:** `witnesses/i0185-lock-close-absence.js`.

- **Fixture:** fresh, with no `agent/` at all.
- **Trigger:** the first `closeSync` of a descriptor opened on a path whose name contains `lock` closes the descriptor, then throws EIO. A tree that never closes a lock descriptor is "not applicable" and passes.
- **Required behaviour:** if the call fails, the skills directory and the lock no longer exist. If the call succeeds, it returns 6.

**Results.**

- **Reproduces on d13 and d35.** `agent/skills/.devlyn-install.lock` remains, and so does the skills directory.
  - d13 reported "previous installation was restored … cleanup also failed: ENOTEMPTY".
  - d35 threw the raw EIO.
- **Passes on d14 and d36.** The trigger fired, and the directory and lock were gone afterwards.
- **Not applicable on the other 8 trees.** They use `mkdir` locks with no descriptor.

### K9 (new): destination teardown happens outside the exclusion period

**Claim** (d35 codex:2). A fresh installation fails during staging. Its recovery releases the lock before it removes the skills directory it created. A reentrant installation admitted at that moment succeeds, and the failed installation then cannot restore the initial absence.

**Binds: yes, to two requirements:**

- requirement 3: "Another process or reentrant invocation must fail promptly with a clear busy error and leave the owner's lock/data intact";
- requirement 2: "An initially absent skills directory must again be absent after failure".

The root `absence-lock` row tests the same scenario. The only difference is its trigger: a second-publication rename failure.

**Witness:** `witnesses/i0185-recovery-reentry.js`.

- **Fixture:** fresh.
- **Trigger:** the first `copyFileSync` from the source bundle fails once with EIO. During recovery, the first `rmdirSync`/`rmSync` of the skills directory itself reenters the same installation.
- **Required behaviour:** the reentrant call fails busy, the outer call fails, and the skills directory does not exist afterwards. A tree that never removes the skills directory with `rmdirSync`/`rmSync` is judged on absence alone.

**Results.**

- **Reproduces on d13, d35 and d36.** The reentrant call returned 6, and the outer call reported ENOTEMPTY with the directory left behind.
- **Passes on the other 9 trees:**
  - d15 and d34 reentered and got busy, and the directory was absent;
  - the other trees never `rmdir` the skills directory and leave it absent.

### K6 (supplementary; no disposition references it): physical skill alias kept

d15 claude:0 cites requirement 1, "Existing physical aliases must not remain alongside their canonical replacements", as a guess for its `terminal-alias` failure.

`witnesses/i0185-physical-alias.js` (0232 K6, unchanged) passes on all 12 trees and on `ref-k3`. The finding is disposed through K2, the defect its cited row detects; K2 reproduces on d15.

### K10 (new): a pre-existing `.devlyn-install.json.<pid>.tmp` in the skills directory is destroyed (d35 codex:3)

**Claim.** Suppose the skills directory already holds a file the invocation did not create, named `.devlyn-install.json.<current pid>.tmp`. The marker write's exclusive create fails with EEXIST, and its `finally` deletes that file; d35's recovery journal also lists the path as newly created (`bin/devlyn.js:893`) and removes it. The prior installation is restored, but the file's bytes and mode are lost.

**Binds: yes**, to requirement 1, "Preserve unrelated files, user-installed skills and every source file", and requirement 4, "Remove task-created staging/backup/lock debris ... Preserve original content outside the owned paths."

- The file is outside every owned path. Requirement 1 defines the recoverable update as the "selected skill directories, existing installation marker, and deprecated paths". The temporary marker name is none of these.
- The compatibility sentence ("Keep its synchronous API, return count, ... complete-bundle check and marker schema") does not list temporary-file naming or its cleanup, so it does not exempt deleting a file the invocation did not create.
- Requirement 4 puts process crashes out of scope as a failure to recover from. It does not allow destroying a pre-existing file. A file of that name need not come from a crash: pids are reused (in the cell image the installer runs as pid 1), and a failed exclusive create proves only that the file exists, not that this invocation owns it.

**Witness:** `witnesses/i0185-temp-marker-preserve.js` (shared fixture header, lines 1–106).

- **Fixture:** the prior installation, plus an unrelated file `agent/skills/.devlyn-install.json.<process.pid>.tmp` (fixed bytes, mode 0640). The product runs in the witness process, so `process.pid` is the product's pid.
- **Trigger:** one ordinary `installSkillsForCLI('codex')` call.
- **Required behaviour:** afterwards the file exists with its original bytes and mode, whether the call succeeds or fails. The call's own outcome is recorded but not judged here; the other witnesses cover restoration.

**Results.** Both passes are identical (`0234-live/scratch/s0233/runs/i0185-temp-marker-preserve.js.p1.json` and `.p2.json`). Detail is in `runs/detail-temp-marker.txt`.

- **Reproduces on d13, d14, d15 and d35.** Each threw `EEXIST ... .devlyn-install.json.1.tmp` and reported the previous installation restored, and the file was gone (ENOENT). These four trees write the marker into the live skills directory through the original `writeInstallMarker`.
- **Passes on the other 8 trees** (d16, d17, d18, d31, d32, d33, d34, d36). Each returned 6, and the file was intact with mode 0640. For example, d16 writes the marker into its staging directory (`writeInstallMarker(stage)`, `bin/devlyn.js:744`).
- **Sanity check:** the corrected reference `ref-k3` also preserves the file when run on the host (it fails the install with EEXIST inside its staging directory, which this claim does not judge).

**Disposition:** d35 codex:3 is `reproduced` (`i0185-temp-marker-preserve`).

### W1 (D4, new): a FIFO probe in d09's tests cannot bound a writer failure

**Claim** (d09 codex:0). In `tests/test_types/test_File.py:133`, `_call_bounded(lf.read, …)` evaluates `lf.read` before entering the bounded helper. `LazyFile.__getattr__` opens the file, so the blocking FIFO open runs unbounded on the test's main thread. If the writer prints `ready` and exits before opening the FIFO, the test hangs and never reaches its cleanup.

**Binds: yes, to D4 obligation 6:** "Timeout/error probes terminate owned writer/readers and remove only their fixture paths; no sleeps-as-proof race test." A test-owned writer that fails is exactly the error case those probes must bound.

**Witness:** `witnesses/d4-writer-death.py`. It realises the finding's own trigger without editing the tree:

- A `sitecustomize` module is put on `PYTHONPATH` for the test process and every child.
- It makes any blocking write-open of a FIFO end the writer: `open`/`io.open` in a write mode, or `os.open` with `O_WRONLY`/`O_RDWR` and without `O_NONBLOCK`.
  - In a child process, the writer exits with status 1.
  - In a non-main thread of the test process, it raises EIO.
- Nonblocking release opens and the reader's opens are untouched.
- Each collected FIFO test (test ids containing `fifo`, from test files that call `mkfifo`) runs in its own pytest process, all concurrently. pytest's faulthandler is set to 140 s.

**Required behaviour:** every FIFO test finishes within 150 s. Those tests are expected to fail, since their writer died.

**Results.**

- **Reproduces only on d09.** All 4 of its FIFO tests hung. The faulthandler stack shows the main thread blocked in the FIFO read-open:

  ```
  click/utils.py:163 open ← utils.py:148 __getattr__ ← tests/test_types/test_File.py:133
  ```

- **The 11 other trees pass.** Every FIFO test terminated (exit 1), and the injection fired in each:
  - the claude trees use subprocess writers with bounded reads;
  - the codex trees use spawned reader and writer processes with `poll` timeouts, then kill.

## Finding → claim → disposition

| cell | key | claim | disposition | witness |
|---|---|---|---|---|
| d09-D4-claude-B-r1 | codex:0 | W1 unbounded FIFO open in test probe | reproduced | d4-writer-death |
| d13-I0185-claude-B-r1 | claude:0 | K4 stranded lock (close); its absence half is K8, which also reproduces | reproduced | i0185-lock-release-stuck |
| d13-I0185-claude-B-r1 | codex:0 | K4 stranded lock (unlink, no retry) | reproduced | i0185-lock-release-stuck |
| d13-I0185-claude-B-r1 | codex:1 | K8 close failure, absence lost (K4 also reproduces) | reproduced | i0185-lock-close-absence |
| d14-I0185-claude-A-r1 | claude:0 | K3 (restates `release`; its `terminal-alias` part is K2, which also reproduces) | reproduced | i0185-lock-release-restore |
| d14-I0185-claude-A-r1 | codex:0 | K4 stranded lock (unlink) | reproduced | i0185-lock-release-stuck |
| d14-I0185-claude-A-r1 | codex:1 | K2 lock aliasing (terminal symlink) | reproduced | i0185-lock-alias |
| d15-I0185-claude-C-r1 | claude:0 | K2 (restates `terminal-alias`; its physical-alias guess is not reproduced, see K6) | reproduced | i0185-lock-alias |
| d15-I0185-claude-C-r1 | codex:0 | K4 stranded lock (rmdir) | reproduced | i0185-lock-release-stuck |
| d15-I0185-claude-C-r1 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d16-I0185-codex-C-r1 | codex:0 | K7 TMPDIR-dependent lock | reproduced | i0185-lock-tmpdir |
| d16-I0185-codex-C-r1 | codex:1 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d17-I0185-codex-A-r1 | claude:0 | K2 lexical sha256 lock key (parent and terminal alias) | reproduced | i0185-lock-alias |
| d17-I0185-codex-A-r1 | codex:0 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d17-I0185-codex-A-r1 | codex:1 | K7 TMPDIR-dependent lock | reproduced | i0185-lock-tmpdir |
| d17-I0185-codex-A-r1 | codex:2 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d18-I0185-codex-B-r1 | claude:0 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d18-I0185-codex-B-r1 | codex:0 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d18-I0185-codex-B-r1 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d31-I0185-codex-B-r2 | claude:0 | K3 (restates `release`; its `terminal-alias` part is K2, which also reproduces) | reproduced | i0185-lock-release-restore |
| d31-I0185-codex-B-r2 | codex:0 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d31-I0185-codex-B-r2 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d32-I0185-codex-A-r2 | claude:0 | K3 (restates `heldout` and `release`; `heldout` failed with "swallowed 64" in the one-shot sweep) | reproduced | i0185-lock-release-restore |
| d32-I0185-codex-A-r2 | codex:0 | K3 silent success after retried release | reproduced | i0185-lock-release-restore |
| d33-I0185-codex-C-r2 | codex:0 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d33-I0185-codex-C-r2 | codex:1 | K7 TMPDIR-dependent lock | reproduced | i0185-lock-tmpdir |
| d34-I0185-claude-C-r2 | claude:0 | K3 (restates `release`; its `terminal-alias` part is K2, which also reproduces) | reproduced | i0185-lock-release-restore |
| d34-I0185-claude-C-r2 | codex:0 | K4 stranded lock (rmdir) | reproduced | i0185-lock-release-stuck |
| d34-I0185-claude-C-r2 | codex:1 | K2 lock aliasing | reproduced | i0185-lock-alias |
| d35-I0185-claude-A-r2 | claude:0 | K8 close failure, absence lost (K4 close also reproduces) | reproduced | i0185-lock-close-absence |
| d35-I0185-claude-A-r2 | codex:0 | K4 stranded lock (unlink) | reproduced | i0185-lock-release-stuck |
| d35-I0185-claude-A-r2 | codex:1 | K8 close failure, absence lost (K4 also reproduces) | reproduced | i0185-lock-close-absence |
| d35-I0185-claude-A-r2 | codex:2 | K9 teardown after lock release (its mkdir-before-lock aside, K5, does not reproduce on d35) | reproduced | i0185-recovery-reentry |
| d35-I0185-claude-A-r2 | codex:3 | K10 pre-existing file at the temp-marker path destroyed | reproduced | i0185-temp-marker-preserve |
| d36-I0185-claude-B-r2 | claude:0 | K4 stranded lock (unlink) | reproduced | i0185-lock-release-stuck |
| d36-I0185-claude-B-r2 | claude:1 | K5 mkdir before lock | reproduced | i0185-mkdir-before-lock |
| d36-I0185-claude-B-r2 | codex:0 | K4 stranded lock (unlink); its additional fresh-destination and invalid-bundle variant was not separately realised | reproduced | i0185-lock-release-stuck |

## Adjudicated NOT_TRIGGERED rows (0224 rule 1): `release` in d16, d17 and d33, all FAIL

**Why the row did not trigger.**

- The `release` replay (`control/oracle/experiments/0222/oracle/replay.js`, byte-identical to 0232's) injects `REPLAY_LOCK_RELEASE` only at removals under `<fixture>/agent`.
- These three trees keep their owned lock under the system temp directory.
- Their `checks-raw.json` replay output shows `fired: null` and `returned: 6`, hence NOT_TRIGGERED.

| cell | lock definition | lock release |
|---|---|---|
| d16 | `<os.tmpdir()>/devlyn-skills-<sha256(realpath(skillsDir))>.lock`, bin/devlyn.js:683-684 | :798, retry :803 |
| d17 | `<os.tmpdir()>/devlyn-skills-<sha256(path.resolve(skillsDir))>.lock`, :675-676 | :800, retry :804 |
| d33 | `<os.tmpdir()>/devlyn-skills-<sha256(realpath(path.resolve(skillsDir)))>.lock`, :682-684 | :801, retry :806 |

**Procedure.** This follows 0224 DESIGN rule 1, exactly as in 0232 for m31 and m33. The variants are in `0234-live/scratch/s0233/adj/replay-release-<cell>.js`. Each differs from `replay.js` only in:

- the hook predicate, which gains `|| target===OWNED_LOCK`, with `OWNED_LOCK` computed exactly as the product computes it;
- the support `require`, pointed at the tree's byte-identical `tests/support.js`;
- fixed `product`/`kind` instead of argv.

The assertions are byte-identical (verified with `diff`). Each variant ran twice in the cell image through `judge.py`, via `adj/show-release-<cell>.js`.

| cell | fired | error | restored | passed | adjudication |
|---|---|---|---|---|---|
| d16-I0185-codex-C-r1 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock`; 2 lock removals = failed attempt + retry | `AggregateError: Skill installation committed but cleanup failed … Could not release installation lock …` | false | false | **FAIL** |
| d17-I0185-codex-A-r1 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock`; failed attempt + retry | `Skill installation committed, but cleanup failed …: REPLAY_LOCK_RELEASE` | false | false | **FAIL** |
| d33-I0185-codex-C-r2 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock`; failed attempt + retry | `AggregateError: Skill installation committed with cleanup errors … Cannot release installation lock …` | false | false | **FAIL** |

Both runs of each cell agree on every field shown.

**Cause.** All three trees dispose of their backup workspace before releasing the lock, so after the failed release the prior installation cannot be restored:

- d16 disposes at :789 and releases at :798;
- d17 disposes at :761 and releases in `finally` at :800;
- d33 disposes at :791 and releases at :801.

The K3 witness, which tests the same requirement with the fault at the real lock, independently reproduces on all three (`restored: false`, lock released by the retry, error thrown).

Recorded in `decisions-severe.json`:

```json
"adjudicated": {"d16-I0185-codex-C-r1": {"release": "FAIL"}, "d17-I0185-codex-A-r1": {"release": "FAIL"}, "d33-I0185-codex-C-r2": {"release": "FAIL"}}
```

## What I could not establish

- **d36 codex:0 additional_witness.** The variant is: a fresh destination, an invalid source bundle, and a lock `unlinkSync` failure during recovery. It was not realised as a separate witness. The finding is disposed through its primary claim, K4, which reproduces on d36.
- **d13 claude:0 and d35 claude:0 restate the `release` row.** Their concrete mechanisms (K4 and K8) were used instead of K3. K3 also reproduces on both trees, so the choice does not change any boolean.
- **Sanity checks against a correct implementation:**
  - For the I0185 claims, they were run on the host (Node v20.19.0), not in the cell image, using the corrected reference copy `ref-k3`. K10 needs no such check beyond it, because 8 real trees pass it in the cell image.
  - For W1, no independently corrected D4 tree was built. The 11 passing real trees, in each of which the injection fired, serve instead.

## Review response (Astra round 1, REVISE)

**MEDIUM: K10's non-binding rationale is unsupported. Accepted and fixed.**

- Round 1 treated a pre-existing `.devlyn-install.json.<pid>.tmp` as the product's own debris. Its reasons were that the original `writeInstallMarker` has the same name and the same `finally` cleanup, and that only a crashed devlyn process could leave such a file.
- Neither reason holds against the spec.
  - The compatibility sentence lists what to keep, and temporary-file cleanup is not on that list.
  - Requirements 1 and 4 require preserving content outside the owned paths.
  - A file at that path need not come from a crash: pids are reused, and the cell image runs the installer as pid 1.
  - A failed exclusive create does not show that the invocation owns the file.
- **Fix.** I wrote the preservation witness `witnesses/i0185-temp-marker-preserve.js` and ran it twice through `judge.py` on all 12 I0185 trees, with identical results both times.
  - It reproduces on d13, d14, d15 and d35, and passes on the other 8.
  - d35 codex:3 is now `reproduced`. The witness's results are recorded under `witnesses` in `decisions-severe.json`.
  - The severe-witness subset table is unchanged (see that section).

**Verification gap (not graded).** Astra could not re-run witnesses under its read-only sandbox. Every witness in this revision ran in the cell image through `judge.py`. The K10 runs are new. All other witness results are unchanged from round 1, whose two passes Astra checked against the saved results.

**Revised counts.**

| | count |
|---|---|
| findings | 37 |
| distinct claims | 10 |
| reproduced | 37 |
| not_reproduced | 0 |
| witnesses | 10 |
| adjudicated rows | 3 |
