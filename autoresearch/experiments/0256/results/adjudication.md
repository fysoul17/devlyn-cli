# 0256: severe-finding dispositions and NOT_TRIGGERED adjudications (prepared for root)

This follows 0233's method (`experiments/0233/results/adjudication.md`, `decisions.json`): its claims K2–K10 and W1, its adopted literal readings (K3; K7 binding, which decided 0233's codex development result), and 0224 rule 1. Output: `results/decisions-severe.json` (`severe`, `witnesses`, `adjudicated`). Root decides; Astra verifies.

## Summary

- **Measured cells:** 56, all with verdicts (`judge.py cells`).
- **Severe findings:** 27 (`judge.py findings`): 25 on I0185 (all 8 I0185 cells) and 2 on D4 (d28). No other task has one.
- **Distinct claims:** 13.
  - Reused unchanged from 0233: K2, K3, K4, K5, K7, K8, K10 (I0185) and W1 (D4). K6 and K9 also run again as supplementary checks; no disposition references them.
  - New: X1 cross-device staging (d10 claude:1), X2 deprecated cleanup through a symlinked skills directory (d21 claude:0), W2 a FIFO writer that connects and then stalls (d28 codex:1).
- **Dispositions:** 27 `reproduced`, each on its own cell's tree. 0 `not_reproduced`.
- **Witnesses:** 13 in `results/witnesses/`: the 10 from 0233, byte-identical (checked with `cmp`), and 3 new ones: `i0185-cross-device-stage.js`, `i0185-deprecated-terminal-link.js` and `d4-writer-stall.py`.
  - Each I0185 witness ran on all 8 I0185 trees; each D4 witness ran on all 8 D4 trees.
  - Every witness ran twice through `judge.py`, and the two passes were identical: `scratchpad/0256/witness-runs/<witness>.p1.json` and `.p2.json`.
  - The 0233 witnesses were run by root. The 3 new witnesses and the replay variants were run by me.
- **Adjudicated rows:** 2, both **FAIL**: `release` in d12-I0185-codex-A-r1 and in d22-I0185-codex-B-r2. They did not trigger for the same reason as 0233's d16, d17 and d33.
- **decide.py check:** run in scratch, with `audited` stubbed for all 56 cells and `false_completion`/`user_data_harm` left empty, only for this check. It shows no severe, witness, paired-witness or adjudication gap in any panel. No panel reads NOT_FINISHED, and `complete()` raises nothing for the two ADJUDICATE cells.

Witness conventions, as in 0233:

- each witness runs from `/work` in the cell image, with no network, all capabilities dropped and uid 501;
- exit 1 means the defect reproduces, 0 means the tree is correct, 2 means a witness error;
- the I0185 witnesses share 0233's fixture header (lines 1–106, sha256 `4efdba98…`), identical in all 11 I0185 witnesses;
- the supplied `tests/support.js` is byte-identical in all 8 I0185 trees and in the control oracle (sha256 `6218f2e9…`).

Detail output came from `scratchpad/0256/sev/detail.py`. It runs the same `docker run` as `judge.py` (no network, cap-drop ALL, no-new-privileges, uid 501) but prints the witness's JSON. The output is in `scratchpad/0256/sev/detail-*.txt`.

## Per-tree reproduction

✓ = the defect reproduces; – = the tree passes.

### I0185

| config / rep | arm | cell | K2 lock-alias | K3 release-restore | K4 stuck | K5 mkdir-before-lock | K7 tmpdir | K8 close-absence | K10 temp-marker | X1 cross-device | X2 deprecated-link | K9 recovery-reentry (suppl.) | K6 physical-alias (suppl.) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude r1 | A | d09 | – | ✓ | ✓ | – | – | ✓ | ✓ | – | – | – | – |
| claude r1 | B | d10 | ✓ | ✓ | ✓ | – | – | ✓ | ✓ | ✓ | – | – | – |
| claude r2 | A | d24 | – | ✓ | ✓ | ✓ | – | ✓ | ✓ | – | – | ✓ | – |
| claude r2 | B | d23 | – | ✓ | ✓ | ✓ | – | ✓ | – | – | – | ✓ | – |
| codex r1 | A | d12 | ✓ | ✓ | – | – | ✓ | – | – | ✓ | – | – | – |
| codex r1 | B | d11 | – | ✓ | – | – | – | – | – | ✓ | – | – | – |
| codex r2 | A | d21 | ✓ | ✓ | – | – | – | – | – | ✓ | ✓ | – | – |
| codex r2 | B | d22 | – | ✓ | – | – | ✓ | – | – | ✓ | – | – | – |

The witnesses agree with the root oracle rows:

- **K2** reproduces on exactly the three trees whose `alias` or `terminal-alias` row is FAIL: d10, d12 and d21.
- **K9** reproduces on exactly the two trees whose `absence-lock` row is FAIL: d23 and d24.
- **K3** reproduces on all 8 trees. Every `release` row is FAIL, and the two NOT_TRIGGERED rows are adjudicated FAIL below.

### D4

- **W1** `d4-writer-death` reproduces only on d28-D4-claude-B-r2.
- **W2** `d4-writer-stall` reproduces only on d28.
- Both pass on d05, d06, d07, d08, d25, d26 and d27.

### Reproductions by witness, arm and config

| witness | total | claude A | claude B | codex A | codex B |
|---|---|---|---|---|---|
| i0185-lock-alias (K2) | 3 | 0 | 1 | 2 | 0 |
| i0185-lock-release-restore (K3) | 8 | 2 | 2 | 2 | 2 |
| i0185-lock-release-stuck (K4) | 4 | 2 | 2 | 0 | 0 |
| i0185-mkdir-before-lock (K5) | 2 | 1 | 1 | 0 | 0 |
| i0185-lock-tmpdir (K7) | 2 | 0 | 0 | 1 | 1 |
| i0185-lock-close-absence (K8) | 4 | 2 | 2 | 0 | 0 |
| i0185-temp-marker-preserve (K10) | 3 | 2 | 1 | 0 | 0 |
| i0185-cross-device-stage (X1, new) | 5 | 0 | 1 | 2 | 2 |
| i0185-deprecated-terminal-link (X2, new) | 1 | 0 | 0 | 1 | 0 |
| i0185-recovery-reentry (K9, suppl.) | 2 | 1 | 1 | 0 | 0 |
| i0185-physical-alias (K6, suppl.) | 0 | 0 | 0 | 0 | 0 |
| d4-writer-death (W1) | 1 | 0 | 1 | 0 | 0 |
| d4-writer-stall (W2, new) | 1 | 0 | 1 | 0 | 0 |

### Effect on the severe-witness subset condition (B/A)

The condition: the B tree's set of reproducing witnesses must be contained in the A tree's set for the same task, config and replicate. decide.py counts every witness in `witnesses`, so the supplementary witnesses count too, as in 0233.

| task / config / rep | B/A |
|---|---|
| I0185 claude r1 | **fails**: B (d10) adds K2 and X1 |
| I0185 claude r2 | holds: B (d23) {K3, K4, K5, K8, K9} ⊆ A (d24) {K3, K4, K5, K8, K9, K10} |
| I0185 codex r1 | holds: B (d11) {K3, X1} ⊆ A (d12) {K2, K3, K7, X1} |
| I0185 codex r2 | **fails**: B (d22) adds K7 |
| D4 claude r1 | holds (neither tree reproduces) |
| D4 claude r2 | **fails**: B (d28) adds W1 and W2 |
| D4 codex r1, codex r2 | holds (neither tree reproduces) |

What the new claims and readings change:

- **X1** changes no entry. It is the second addition in claude r1, where K2 already fails the condition. In codex it reproduces on both arms of each replicate.
- **X2** changes no entry. It reproduces only on d21, an A tree.
- **W2** changes no entry. It reproduces only on d28, where W1 already fails D4 claude r2.
- **K7 alone decides I0185 codex r2.** The scratch decide.py check gives codex development `PACKAGE_LOWERS_QUALITY[I0185.severe]`; I0185.severe is its only failed clause. Without K7 the same check reads `DEVELOPMENT_PASS` (see "Root's rulings").

## Claims

The reused claims, their binding and their witnesses are as in 0233's adjudication.md. Only the 0256 results are recorded below.

### K2: lock-path aliasing (witness reused unchanged)

**Binds: yes, to requirement 3** (as in 0232 and 0233).

- **Reproduces on d10, d12 and d21.** In both directions the contender returned 6 and changed the installation.
  - d10's owner then failed: ENOENT while renaming `devlyn:auto-resolve` into its backup.
  - d12 and d21 hash `path.resolve(skillsDir)` (d12 bin/devlyn.js:671-675).
- **Passes on d09, d11, d22, d23 and d24.**
  - d09 and d11 keep a lock beside the physical directory.
  - d22 keys its lock by `realpathSync` (`lockIdentity`, :677-685).
  - d23 and d24 keep the lock inside the skills directory.

### K3: a post-commit lock-release failure is not recovered (witness reused unchanged; 0232/0233 literal reading)

**Binds: yes, to requirement 2**, under the literal reading root adopted in 0232 and 0233. Lock release is not "disposal of backup data".

**Reproduces on all 8 trees.** The injection hit each tree's own lock.

| trees | lock location | what happened |
|---|---|---|
| d09, d10 | `agent/.skills.devlyn-install.lock` (unlink) | threw; lock left; not restored |
| d23, d24 | `agent/skills/.devlyn-install.lock` (unlink) | threw "installed … but cleanup failed"; lock left; not restored |
| d11 | `agent/.skills.devlyn-install.lock` (rmdir) | threw after a successful retry; backups already disposed; not restored |
| d21 | `agent/.skills.devlyn-lock` (rmdir) | threw after a successful retry; backups already disposed; not restored |
| d12, d22 | `/tmp/devlyn-skills-<sha256>.lock` (rmdir) | threw after a successful retry; backups already disposed; not restored |

### K4: one transient lock fault strands the lock (witness reused unchanged)

**Binds: yes, to requirement 3.**

- **Reproduces on d09, d10, d23 and d24.** Scenarios in which the later call was busy:
  - d09: remove, read and close;
  - d10: remove, read and close;
  - d23: remove (read is not applicable; its close scenario recovers);
  - d24: remove, read and close.
- **Passes on the four codex trees.** One retry releases the lock, and the read and close triggers are not applicable.

### K5: destination created before the lock (witness reused unchanged)

**Binds: yes, to requirements 3 and 2.**

- **Reproduces on d23 and d24.** A failed busy against B's lock inside the directory A had created. B reached its copy, holding the lock while A was in progress, then failed. The directory remained.
- **Passes on the other 6 trees.**
  - d12 and d22 (locks under `/tmp`): A returned 6 and B was busy.

### K7: the lock location depends on each process's TMPDIR (witness reused unchanged; 0233 binding adopted)

**Binds: yes, to requirement 3**, as adopted in 0233. 0233's K7 section records the opposing reading ("cooperating installations share one environment").

- **Reproduces on d12 and d22.** The contender, with a different `TMPDIR`, returned 6 and changed the installation while the owner held its lock.
  - d12: `path.join(os.tmpdir(), …)`, bin/devlyn.js:675.
  - d22: :685.
- **Passes on the other 6 trees.** Each contender failed busy.

### K8: the initial absence or lock debris remains after a lock-descriptor close failure (witness reused unchanged)

**Binds: yes, to requirements 2 and 4.**

**Reproduces on d09, d10, d23 and d24.**

| tree | lock location | after the call |
|---|---|---|
| d09, d10 | parent (`agent/`) | skills directory absent; `agent/.skills.devlyn-install.lock` and the created `agent/` remain |
| d24 | `agent/skills/.devlyn-install.lock` | raw EIO; created skills directory and lock remain |
| d23 | inside the skills directory | committed the fresh install, then threw "cleanup failed" on the close; the directory remained (lock released) |

d23's outcome fails K8 under the same literal reading as K3: one ordinary lock-close failure after commit, and no restore.

The four codex trees are not applicable: they use `mkdir` locks with no descriptor.

### K10: a pre-existing `.devlyn-install.json.<pid>.tmp` is destroyed (witness reused unchanged)

**Binds: yes, to requirements 1 and 4** (0233's revised reading).

- **Reproduces on d09, d10 and d24.** Each threw EEXIST on `.devlyn-install.json.1.tmp`, and the file was gone.
- **Passes on the other 5 trees**, with the file intact (mode 0640).

### X1 (new): staging beside a symlinked skills directory cannot publish across filesystems (d10 claude:1)

**Claim.** Staging and backups live in `path.dirname(skillsDir)`, while publication renames into the skills directory itself. When the configured skills directory is a symlink to a directory on another filesystem, the renames cross devices (EXDEV) and every installation fails. The original copy-in-place implementation installed there: `.devlyn/0185/inputs/install/bin/devlyn.js:666-701`.

**Binds: yes (root's ruling, 2026-10-22; see "Root's rulings").** The opening paragraph says the function "is called by the existing CLI installation flow". Requirement 1 says: "On success fully replace selected skills". Preserving the existing installation flow includes the destination layouts the baseline supported, and the baseline installs into this layout.

- The trees fail safely: they restore and raise an actionable error.
- No requirement sentence literally requires success in a given filesystem layout.
- The reading changes no subset entry.

**Witness:** `witnesses/i0185-cross-device-stage.js` (shared header).

- **Fixture:** the prior installation, with `agent/skills` a symlink to a fresh directory under `/work`, which is a bind mount. The fixture root is under `/tmp`, the container filesystem. The witness errors (exit 2) if the two are on one device.
- **Control:** the same layout with the target on `/tmp`.
- **Reproduces when** the cross-device call fails while the control returns 6.

**Results.**

- **Reproduces on d10, d11, d12, d21 and d22.** Each failed on its first backup rename, for example:

  ```
  EXDEV: cross-device link not permitted, rename '…/agent/skills/.devlyn-install.json' -> '…/agent/<staging>/backup/…'
  ```

  The same-device control returned 6 on all five.
- **Passes on d09, d23 and d24**, which returned 6 in both layouts. A correct implementation is therefore shown on 3 real trees.

### X2 (new): deprecated skill directories are skipped when the skills directory is a symlink (d21 claude:0)

**Claim.** d21's `deprecatedParentIsLink` (bin/devlyn.js:698, used at :725 and :729) checks the destination itself. When `agent/skills` is a symlink, every deprecated directory is skipped, while the selected skills are still published through the link and the marker is committed. The original `cleanupDeprecated(path.dirname(cli.skillsDir))` removes `<skills>/devlyn:auto-resolve` through the link with `existsSync`/`rmSync` (inputs bin/devlyn.js:341-361).

**Binds: yes, to requirement 1:** "On success … perform the same deprecated cleanup". The destination link is not "unrelated user content": the function publishes through it. Configured symlinked destinations are within scope (the `terminal-alias` row).

**Witness:** `witnesses/i0185-deprecated-terminal-link.js` (shared header).

- **Fixture:** `agent/skills` is a symlink to `<real>/skills`, which holds `devlyn:auto-resolve`.
- **Reproduces when** the call succeeds and `<real>/skills/devlyn:auto-resolve` remains. A failed call is not judged.
- The plain layout is reported as a control.

**Results.**

- **Reproduces only on d21:** it returned 6 and kept the deprecated directory. In the plain layout d21 removes it.
- **Passes on the other 7 trees**, each returning 6 with the directory removed.

### W1: unbounded FIFO open in the test probe, writer dies (witness reused unchanged)

**Binds: yes, to D4 obligation 6** (as in 0233).

- **Reproduces only on d28.** d28 codex:0 is the same claim as 0233 d09 codex:0. At `tests/test_types/test_File.py:143`, `_call_unblocked(fifo, lf.read)` evaluates `lf.read`, and so opens the FIFO, on the main thread.
- **Passes on the 7 other trees.**

### W2 (new): a writer that connects and then stalls hangs the probe (d28 codex:1)

**Claim.** In d28 the read runs in a pool thread that is abandoned on timeout: `pool.shutdown(wait=False)`, test_File.py:79. Leaving `with ctx` then closes the buffered stream. That close waits for the buffer lock held by the blocked reader, so it blocks before the `start_writer` fixture can kill the writer.

**Binds: yes, to D4 obligation 6:** "Timeout/error probes terminate owned writer/readers". A connected but stalled writer is the case the timeout probe exists to bound.

**Witness:** `witnesses/d4-writer-stall.py`. It is W1's harness, unchanged except for the injected behaviour:

- In a child process, a blocking write-open of a FIFO performs the real open and then sleeps forever, holding the descriptor and writing nothing.
- Writes from the test process itself are not injected. A writer thread in the test process would be logged; none was.
- **Required behaviour:** every FIFO test finishes within 150 s.

**Results.**

- **Reproduces only on d28.** All 4 FIFO tests hung, and the injection fired in each. The faulthandler stack shows the main thread blocked in the context-exit close:

  ```
  click/utils.py:177 close ← :184 close_intelligently ← contextlib _exit_wrapper
  ```

  The worker thread is blocked in its read.
- **Passes on the 7 other trees.** Each FIFO writer test failed in 10–30 s, with the injection firing in every one.
  - d27's 4 `convert_does_not_connect` tests start no writer. They passed and were not injected.

### K9, K6 (supplementary; no disposition references them)

- K9 `recovery-reentry` reproduces on d23 and d24. That matches their `absence-lock` FAIL rows.
- K6 `physical-alias` passes on all 8 trees.

## Finding → claim → disposition

| cell | key | claim | disposition | witness |
|---|---|---|---|---|
| d09-I0185-claude-A-r1 | claude:0 | K4 stranded lock (close in acquire; the writeSync+close variant is not separately realised) | reproduced | i0185-lock-release-stuck |
| d09-I0185-claude-A-r1 | codex:0 | K4 stranded lock (unlink, no retry) | reproduced | i0185-lock-release-stuck |
| d09-I0185-claude-A-r1 | codex:1 | K4 stranded lock (close) | reproduced | i0185-lock-release-stuck |
| d09-I0185-claude-A-r1 | codex:2 | K10 pre-existing temp-marker file destroyed | reproduced | i0185-temp-marker-preserve |
| d10-I0185-claude-B-r1 | claude:0 | K4 stranded lock (close) | reproduced | i0185-lock-release-stuck |
| d10-I0185-claude-B-r1 | claude:1 | X1 cross-device staging (symlink variant; mount-point variant not realised) | reproduced | i0185-cross-device-stage |
| d10-I0185-claude-B-r1 | codex:0 | K4 stranded lock (unlink; close aside also reproduces) | reproduced | i0185-lock-release-stuck |
| d10-I0185-claude-B-r1 | codex:1 | K2 terminal-symlink lock aliasing | reproduced | i0185-lock-alias |
| d11-I0185-codex-B-r1 | claude:0 | K3 (restates `release`; part (b), throws after a successful retry with backups disposed; part (a) does not bind, see below) | reproduced | i0185-lock-release-restore |
| d11-I0185-codex-B-r1 | codex:0 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d12-I0185-codex-A-r1 | claude:0 | K2 lexical sha256 lock key | reproduced | i0185-lock-alias |
| d12-I0185-codex-A-r1 | claude:1 | K7 TMPDIR-dependent lock (tmp-cleaner aside not realised) | reproduced | i0185-lock-tmpdir |
| d12-I0185-codex-A-r1 | codex:0 | K2 lock aliasing (parent and terminal) | reproduced | i0185-lock-alias |
| d21-I0185-codex-A-r2 | claude:0 | X2 deprecated cleanup skipped through a symlinked skills dir | reproduced | i0185-deprecated-terminal-link |
| d21-I0185-codex-A-r2 | codex:0 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d21-I0185-codex-A-r2 | codex:1 | K2 terminal alias | reproduced | i0185-lock-alias |
| d22-I0185-codex-B-r2 | codex:0 | K3 throws after backups disposed | reproduced | i0185-lock-release-restore |
| d22-I0185-codex-B-r2 | codex:1 | K7 TMPDIR-dependent lock | reproduced | i0185-lock-tmpdir |
| d23-I0185-claude-B-r2 | claude:0 | K3 (restates `release`; its rollback-failure mechanism is not realised, see below) | reproduced | i0185-lock-release-restore |
| d23-I0185-claude-B-r2 | claude:1 | K5 mkdir before lock, absence lost (cites `absence-lock`; K9 also reproduces) | reproduced | i0185-mkdir-before-lock |
| d23-I0185-claude-B-r2 | codex:0 | K4 stranded lock (unlink; the lstat variant is not applicable to K4's read trigger) | reproduced | i0185-lock-release-stuck |
| d23-I0185-claude-B-r2 | codex:1 | K5 mkdir before lock (witness realises the lock taken by another invocation after the outer mkdir) | reproduced | i0185-mkdir-before-lock |
| d24-I0185-claude-A-r2 | claude:0 | K8 close failure, absence lost (K4 close also reproduces) | reproduced | i0185-lock-close-absence |
| d24-I0185-claude-A-r2 | codex:0 | K8 close failure, absence lost (K4 also reproduces) | reproduced | i0185-lock-close-absence |
| d24-I0185-claude-A-r2 | codex:1 | K4 stranded lock (unlink and read both reproduce) | reproduced | i0185-lock-release-stuck |
| d28-D4-claude-B-r2 | codex:0 | W1 unbounded FIFO open in the test probe | reproduced | d4-writer-death |
| d28-D4-claude-B-r2 | codex:1 | W2 stalled writer, context-exit close blocks | reproduced | d4-writer-stall |

## Adjudicated NOT_TRIGGERED rows (0224 rule 1): `release` in d12 and d22, both FAIL

**Why the rows did not trigger.**

- The `release` replay (`control/oracle/experiments/0222/oracle/replay.js`, sha256 `679ea403…`) injects `REPLAY_LOCK_RELEASE` only at removals under `<fixture>/agent`.
- Both trees keep their lock under the system temp directory.
- `checks-raw.json` shows `fired: null`, `returned: 6`.

This is the same reason as 0233's d16, d17 and d33, so nothing needed adapting.

| cell | lock definition | lock release |
|---|---|---|
| d12 | `<os.tmpdir()>/devlyn-skills-<sha256(path.resolve(skillsDir))>.lock`, bin/devlyn.js:671-675 | :795, retry :798 |
| d22 | `<os.tmpdir()>/devlyn-skills-<sha256(realpathSync(skillsDir))>.lock`, :670-685 (`lockIdentity`) | :813, retry :817 |

**Procedure.** The variants are in `results/adjudication/replay-release-<cell>.js`. Each differs from `replay.js` only in:

- the hook predicate, which gains `||target===OWNED_LOCK`;
- one added line defining `OWNED_LOCK` exactly as the product computes it;
- the support `require`, pointed at the tree's byte-identical `/work/tests/support`;
- fixed `product`/`kind` instead of argv.

The assertions are byte-identical (verified with `diff`). Each variant ran twice in the cell image through `judge.py`, via `adjudication/show-release-<cell>.js` (exit 1 = row FAIL):

- `judge.py` returned `true` on both passes for both cells (`witness-runs/adj-release-<cell>.p1.json` and `.p2.json`);
- the detail passes agree on every field shown (`adj-release-<cell>.detail.p1.txt` and `.p2.txt`).

| cell | fired | lock removals | error | restored | passed | adjudication |
|---|---|---|---|---|---|---|
| d12-I0185-codex-A-r1 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock` | failed attempt + retry | `AggregateError: Failed to release skill installation lock … REPLAY_LOCK_RELEASE` | false | false | **FAIL** |
| d22-I0185-codex-B-r2 | `rmdirSync /tmp/devlyn-skills-<sha256>.lock` | failed attempt + retry | `AggregateError: Could not release installation lock … REPLAY_LOCK_RELEASE` | false | false | **FAIL** |

**Cause.** Both trees dispose of their backup workspace before releasing the lock, so after the failed release the prior installation cannot be restored:

- d12 disposes at :757 and releases at :795;
- d22 disposes at :795 and releases at :813.

K3, which injects at each tree's real lock, independently reproduces on both.

**Effect.** Neither cell can complete either way:

- d12 also has `alias` and `terminal-alias` FAIL, and severe assessor findings;
- d22 has severe codex findings.

Recorded:

```json
"adjudicated": {"d12-I0185-codex-A-r1": {"release": "FAIL"}, "d22-I0185-codex-B-r2": {"release": "FAIL"}}
```

## Root's rulings (2026-10-22)

Root adopted both readings below as prepared: K7 binds (0233's adopted reading, unchanged) and X1 binds (reading A). Astra and Grok verified these judgments in one read-only round, and both returned SHIP. Their only finding was LOW: X1's binding was left unsettled. It is settled here and changes no reading.

The analysis as prepared:


1. **K7 binding decides codex development.** K7 is 0233's adopted reading, which I applied.
   - Under the opposing reading ("cooperating" installations share one environment), K7 would not bind and d12 claude:1 and d22 codex:1 would leave the decision. In the scratch check, `I0185.severe` was then codex development's only failed clause: codex r2 B (d22) would be {K3, X1}, which is contained in A (d21).
   - With `i0185-lock-tmpdir` also removed from `witnesses`, that clause holds. A scratch decide.py run of that variant (`scratch/judge/decide-sanity/decisions-noK7.json`, with the same stubs: all audited, no false completion or harm) gives codex `dev:DEVELOPMENT_PASS[]`.
   - So, pending the audits, the K7 reading is the difference between PACKAGE_LOWERS_QUALITY and DEVELOPMENT_PASS for codex development. Claude's readings do not depend on it.
2. **X1 binding.**
   - Reading A (binds): the upgrade must not make success impossible in a layout the existing CLI flow supported, a symlinked skills directory on another volume.
   - Reading B (does not bind): no requirement sentence requires success in a given filesystem layout, and the trees fail safely, restored and reported.
   - The witness reproduces on d10 either way, so d10 claude:1 stays `reproduced`. The open question is only whether `i0185-cross-device-stage` belongs in `witnesses`. Removing it changes no B/A entry (see the subset section).

## What I could not establish

- **d11 claude:0 part (a)** (release by pathname with no owner identity, so a lock replaced by another holder is deleted) was not realised. Its trigger needs a third party that removes and recreates the owner's lock, which no cooperating installation does. That falls under "malicious noncooperating writers … are out of scope" (requirement 4), so I judge that it does not bind. The finding is disposed through part (b), K3.
- **d23 claude:0's rollback-failure mechanism** (the lock is deliberately kept when rollback fails) was not realised. It needs two faults, the original failure plus a rollback failure, which is outside requirement 2's "one ordinary filesystem operation fails and subsequent recovery operations can succeed". The finding restates the `release` row, which K3 encodes and reproduces.
- **Variants not realised separately:**
  - d09 claude:0's writeSync-plus-close variant;
  - d10 claude:1's mount-point variant (a container cannot create mounts without capabilities);
  - d12 claude:1's tmp-cleaner aside (a noncooperating actor);
  - d23 codex:0's `lstatSync` variant.

  Each finding is disposed through its primary claim, which reproduces.
- **Correct-implementation sanity checks** used passing real trees only, because the 0232 corrected reference `ref-k3` no longer exists. K3 reproduces on all 8 trees, so for K3 no correct tree was exhibited in 0256. 0233 showed `ref-k3` passing it with this same witness.
  - X1 passes on d09, d23 and d24.
  - X2 passes on 7 trees.
  - W2 passes on 7 trees, with the injection firing in every FIFO writer test.
- The 0233 witness passes were run by root. I added only their detail runs, through `detail.py`.
