# 0257 Claude-owner severe-finding dispositions

## Summary

- Scope: 100 severe rows, 34 cells: 98 I0185 findings and 2 D4 findings.
- Final dispositions: 98 reproduced, 2 not reproduced, 0 pending. The two not reproduced are the external lock-replacement claims excluded by the adopted 0233/0256 reading; their diagnostic witness returned true / true on their own cells.
- No Claude-owner cell has a NOT_TRIGGERED row. `adjudicated` was provisionally empty and remains empty after root's replay results; the 21 `show-release-*` replays belong to codex-owner cells.
- Root ran every new witness twice on every tree of its task through `judge.py run`. All active new-witness passes agree. The frozen binding family and comparative denominators are unchanged (0257 DESIGN, Grading).

## Per finding

| # | cell | key | claim | witness | root on cell | disposition |
|---:|---|---|---|---|---|---|
| 0 | d009-I0185-claude-A-r1 | claude:0 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 1 | d009-I0185-claude-A-r1 | claude:1 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 2 | d009-I0185-claude-A-r1 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 3 | d009-I0185-claude-A-r1 | codex:1 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 4 | d010-I0185-claude-B-r1 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 5 | d010-I0185-claude-B-r1 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 6 | d010-I0185-claude-B-r1 | codex:1 | M1: marker temp cleanup failure leaves an unjournaled marker | `i0185-marker-cleanup-restore` | true / true | reproduced |
| 7 | d022-D4-claude-A-r2 | codex:0 | D1: writer startup can block outside bounded cleanup | `d4-writer-startup` | true / true | reproduced |
| 8 | d025-I0185-claude-B-r2 | claude:0 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 9 | d025-I0185-claude-B-r2 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 10 | d025-I0185-claude-B-r2 | codex:1 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 11 | d026-I0185-claude-A-r2 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 12 | d026-I0185-claude-A-r2 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 13 | d026-I0185-claude-A-r2 | codex:1 | K10: pre-existing temporary marker is deleted | `i0185-temp-marker-preserve` | true / true | reproduced |
| 14 | d037-D4-claude-A-r3 | codex:0 | W1: FIFO read-open escapes the timeout guard | `d4-writer-death` | true / true | reproduced |
| 15 | d041-I0185-claude-A-r3 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 16 | d041-I0185-claude-A-r3 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 17 | d041-I0185-claude-A-r3 | codex:1 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 18 | d041-I0185-claude-A-r3 | codex:2 | K10: pre-existing temporary marker is deleted | `i0185-temp-marker-preserve` | true / true | reproduced |
| 19 | d042-I0185-claude-B-r3 | claude:0 | M3: replaced lock is deleted without owner-token proof | `i0185-replaced-lock-owner` | true / true (diagnostic; withdrawn) | not_reproduced |
| 20 | d042-I0185-claude-B-r3 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 21 | d057-I0185-claude-B-r4 | claude:0 | K3: post-commit lock-release fault prevents restoration | `i0185-lock-release-restore` | true / true | reproduced |
| 22 | d057-I0185-claude-B-r4 | codex:0 | M2: realpath EIO changes lock identity for the same destination | `i0185-realpath-fault-alias` | true / true | reproduced |
| 23 | d058-I0185-claude-A-r4 | claude:0 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 24 | d058-I0185-claude-A-r4 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 25 | d058-I0185-claude-A-r4 | codex:1 | K10: pre-existing temporary marker is deleted | `i0185-temp-marker-preserve` | true / true | reproduced |
| 26 | d073-I0185-claude-A-r5 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 27 | d073-I0185-claude-A-r5 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 28 | d074-I0185-claude-B-r5 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 29 | d074-I0185-claude-B-r5 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 30 | d089-I0185-claude-B-r6 | claude:0 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 31 | d089-I0185-claude-B-r6 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 32 | d089-I0185-claude-B-r6 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 33 | d089-I0185-claude-B-r6 | codex:2 | K10: pre-existing temporary marker is deleted | `i0185-temp-marker-preserve` | true / true | reproduced |
| 34 | d090-I0185-claude-A-r6 | claude:0 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 35 | d090-I0185-claude-A-r6 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 36 | d090-I0185-claude-A-r6 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 37 | d105-I0185-claude-A-r7 | claude:0 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 38 | d105-I0185-claude-A-r7 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 39 | d105-I0185-claude-A-r7 | codex:1 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 40 | d106-I0185-claude-B-r7 | claude:0 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 41 | d106-I0185-claude-B-r7 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 42 | d106-I0185-claude-B-r7 | codex:1 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 43 | d121-I0185-claude-B-r8 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 44 | d121-I0185-claude-B-r8 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 45 | d122-I0185-claude-A-r8 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 46 | d122-I0185-claude-A-r8 | claude:1 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 47 | d122-I0185-claude-A-r8 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 48 | d122-I0185-claude-A-r8 | codex:1 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 49 | d137-I0185-claude-A-r9 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 50 | d137-I0185-claude-A-r9 | claude:1 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 51 | d137-I0185-claude-A-r9 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 52 | d137-I0185-claude-A-r9 | codex:1 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 53 | d138-I0185-claude-B-r9 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 54 | d138-I0185-claude-B-r9 | codex:0 | M1: marker temp cleanup failure leaves an unjournaled marker | `i0185-marker-cleanup-restore` | true / true | reproduced |
| 55 | d138-I0185-claude-B-r9 | codex:1 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 56 | d138-I0185-claude-B-r9 | codex:2 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 57 | d153-I0185-claude-B-r10 | claude:0 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 58 | d153-I0185-claude-B-r10 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 59 | d153-I0185-claude-B-r10 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 60 | d154-I0185-claude-A-r10 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 61 | d154-I0185-claude-A-r10 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 62 | d154-I0185-claude-A-r10 | codex:1 | K5: destination created before lock loses initial absence | `i0185-mkdir-before-lock` | true / true | reproduced |
| 63 | d169-I0185-claude-A-r11 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 64 | d169-I0185-claude-A-r11 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 65 | d169-I0185-claude-A-r11 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 66 | d169-I0185-claude-A-r11 | codex:2 | K10: pre-existing temporary marker is deleted | `i0185-temp-marker-preserve` | true / true | reproduced |
| 67 | d170-I0185-claude-B-r11 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 68 | d170-I0185-claude-B-r11 | claude:1 | K6 physical alias alleged; `terminal-alias` failure is K2 | `i0185-lock-alias` | true / true | reproduced |
| 69 | d170-I0185-claude-B-r11 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 70 | d170-I0185-claude-B-r11 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 71 | d185-I0185-claude-B-r12 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 72 | d185-I0185-claude-B-r12 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 73 | d186-I0185-claude-A-r12 | claude:0 | K3: post-commit lock-release fault prevents restoration | `i0185-lock-release-restore` | true / true | reproduced |
| 74 | d186-I0185-claude-A-r12 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 75 | d201-I0185-claude-A-r13 | claude:0 | M4: reentrant install enters after destination mkdir, before lock | `i0185-prelock-reentry` | true / true | reproduced |
| 76 | d201-I0185-claude-A-r13 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 77 | d201-I0185-claude-A-r13 | codex:1 | M4: reentrant install enters after destination mkdir, before lock | `i0185-prelock-reentry` | true / true | reproduced |
| 78 | d202-I0185-claude-B-r13 | claude:0 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 79 | d202-I0185-claude-B-r13 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 80 | d202-I0185-claude-B-r13 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 81 | d217-I0185-claude-B-r14 | claude:0 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 82 | d217-I0185-claude-B-r14 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 83 | d217-I0185-claude-B-r14 | codex:1 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 84 | d217-I0185-claude-B-r14 | codex:2 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 85 | d218-I0185-claude-A-r14 | claude:0 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 86 | d218-I0185-claude-A-r14 | claude:1 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 87 | d218-I0185-claude-A-r14 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 88 | d233-I0185-claude-A-r15 | claude:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 89 | d233-I0185-claude-A-r15 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 90 | d234-I0185-claude-B-r15 | claude:0 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 91 | d234-I0185-claude-B-r15 | claude:1 | K8: lock-descriptor close failure loses initial absence | `i0185-lock-close-absence` | true / true | reproduced |
| 92 | d234-I0185-claude-B-r15 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 93 | d234-I0185-claude-B-r15 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 94 | d249-I0185-claude-B-r16 | claude:0 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 95 | d249-I0185-claude-B-r16 | codex:0 | K4: one transient own-lock fault strands later installations | `i0185-lock-release-stuck` | true / true | reproduced |
| 96 | d249-I0185-claude-B-r16 | codex:1 | K2: same physical destination gets separate alias locks | `i0185-lock-alias` | true / true | reproduced |
| 97 | d250-I0185-claude-A-r16 | claude:0 | K3: post-commit lock-release fault prevents restoration | `i0185-lock-release-restore` | true / true | reproduced |
| 98 | d250-I0185-claude-A-r16 | claude:1 | M3: replaced lock is deleted without owner-token proof | `i0185-replaced-lock-owner` | true / true (diagnostic; withdrawn) | not_reproduced |
| 99 | d250-I0185-claude-A-r16 | codex:0 | K10: pre-existing temporary marker is deleted | `i0185-temp-marker-preserve` | true / true | reproduced |

## New claims, requirements, and binding

- **M1 — marker cleanup after publication** (`i0185-marker-cleanup-restore`): a single EIO in `rmSync(tempPath)` after the marker rename must not leave a reported failed install with no restored prior tree. This is an ordinary failure under I0185 requirement 2; the stated post-commit exception concerns *backup-data disposal*, not marker cleanup. Root reproduced it on d010 codex:1 and d138 codex:0, both twice.
- **M2 — failed realpath changes lock identity** (`i0185-realpath-fault-alias`): a contender resolving a symlink to the owner's physical destination encounters one EIO. It may propagate EIO or fail busy, but may not publish concurrently. This binds to I0185 requirement 3. Root reproduced it on d057 codex:0 twice.
- **M4 — prelock reentry** (`i0185-prelock-reentry`): after a fresh destination `mkdir`, a reentrant call enters before the outer lock. Requirement 3 requires ownership before inspecting or mutating destination contents. Root reproduced it on d201 claude:0 and codex:1, both twice. K5's separate timing did not reproduce on d201.
- **D1 — writer startup stall** (`d4-writer-startup`): a test-owned FIFO writer stalls before consuming stdin or reporting ready. D4 obligation 6 requires the tests to bound the probe and terminate owned processes. Root reproduced it on d022 codex:0 twice.
- **K6 physical skill alias allegation** (`i0185-physical-alias`, existing supplementary witness): root got false / false on d170. At d170 `bin/devlyn.js` retires each `skillAliases(skillName)` path before publication (around line 829). Its cited `terminal-alias` oracle failure concerns destination alias locking: binding K2 (`i0185-lock-alias`) got true / true on that same cell. The disposition uses K2, following 0233's d15 physical-alias-guess precedent; the distinct K6 allegation was not reproduced.
- **M3 — external lock replacement** (`i0185-replaced-lock-owner`) is **withdrawn**. It removes and recreates the owner's lock while the owner copies, which requires a noncooperating third party. I0185 requirement 4 says “malicious noncooperating writers ... are out of scope.” The adopted 0256 ruling on d11 claude:0 part (a) says its trigger “needs a third party that removes and recreates the owner's lock, which no cooperating installation does” and “does not bind.” This is exactly d042 claude:0 and d250 claude:1's isolated mechanism. Both are `not_reproduced` as binding findings despite diagnostic true / true; neither asserts a separate K3 mechanism. The script is retained only to make root's saved results auditable and is removed from `new_witnesses` and `root_to_run`.

## Reproduction across task trees

Each d-number below identifies a tree; the column groups them by configuration and arm. Only agreeing true / true runs count as reproductions. Root's hash manifest matches the files for all five witnesses created by this part; the K6 file is the existing 0256 witness and its hash also matches.

| witness | trees reproducing by config and arm | inconsistent |
|---|---|---|
| `d4-writer-startup` | claude B (8): d006, d053, d085, d117, d134, d181, d198, d245; claude A (6): d022, d037, d054, d133, d214, d229 | none |
| `i0185-marker-cleanup-restore` | claude B (2): d010, d138 | none |
| `i0185-prelock-reentry` | claude A (6): d009, d058, d105, d137, d154, d201; claude B (2): d025, d106 | none |
| `i0185-realpath-fault-alias` | claude B (1): d057 | none |
| `i0185-replaced-lock-owner` | codex A (16): d011, d028, d043, d060, d075, d092, d107, d124, d139, d156, d171, d188, d203, d220, d235, d252; codex B (16): d012, d027, d044, d059, d076, d091, d108, d123, d140, d155, d172, d187, d204, d219, d236, d251; claude B (2): d042, d057; claude A (3): d058, d201, d250 | d137-I0185-claude-A-r9 [true, false] |
| `i0185-physical-alias` | none | none |

Under **No guesswork**, the withdrawn M3 diagnostic has one observed inconsistency, d137-I0185-claude-A-r9 [true, false]. Its hook substitutes the original inode only when `fs.lstatSync(lockPath, { bigint: true })` is called. The d137 tree's `releaseSkillInstallLock` calls `fs.lstatSync(lock.path)` **without** the bigint option (snapshot `bin/devlyn.js`, around lines 711–719), so the hook never substitutes an inode there. It compares the real inode of the recreated lock with the original `fstatSync` identity; filesystem inode reuse can make that comparison equal or unequal. Root's two passes show both outcomes. Because M3 is outside the adopted scope, this diagnostic is withdrawn rather than changed and rerun. The inconsistent diagnostic is not interpreted as a negative result or used for grading.

## Other mixed findings

- d057 claude:0 and d250 claude:0 cite hidden `heldout` failure without a mechanism. Their same-cell `release` row fails and K3 reproduces; the table uses K3 for the actionable part. The hidden `heldout` failure remains a separate check result and is not inferred to have K3 as its cause.
- d090 claude:0 and d249 claude:0 cite both `release` and `terminal-alias`; K2 reproduces on each, so the table maps the alias claim to K2. K3 also reproduces. d234 claude:0 cites K2 and X1; both official witnesses reproduce, and K2 is the selected disposition.
- d186 claude:0 says a deliberately retained lock after a failed rollback blocks retries. As in 0256's d23 ruling, that variant requires an initial fault plus a rollback fault and does not bind the single-fault requirement. Its cited `release` failure is represented by K3, which reproduces on d186.
- d170 claude:0 additionally speculates that release after incomplete rollback admits another installer; the concrete unretried release fault is K4 and reproduces. The incomplete-rollback aside has no separate disposition.

## Handoff

`new_witnesses` lists the four active witnesses M1, M2, M4 and D1. `root_to_run` is empty; root's twice-per-tree runs and all binding dispositions are recorded. This part ran no Docker, models or network and made no 0257 denominator change.
