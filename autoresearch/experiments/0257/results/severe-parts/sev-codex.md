# 0257 Codex-owner severe findings and release adjudications

## Summary

- 69 findings: 62 reproduced by frozen witnesses and 7 by three new witnesses on their own cells; 0 pending, 0 not reproduced.
- 21 I0185 `release` NOT_TRIGGERED rows: root's cell-image replays gave 1 PASS (d011) and 20 FAIL, all twice. All 21 match the provisional judgments.
- Frozen witness results are from `results/witness-runs/witnesses.json`; new witness and replay results are from `results/witness-runs/new-witnesses.json`. `[true, true]` means both container passes reproduced the defect or failed the `release` row. The three witness file SHA-256 values match `new-witness.sha256.json`.

## Per finding

| Cell | Key | Claim | Witness | Root result on cell | Disposition |
|---|---|---|---|---|---|
| d011-I0185-codex-A-r1 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d012-I0185-codex-B-r1 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d027-I0185-codex-B-r2 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d027-I0185-codex-B-r2 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d028-I0185-codex-A-r2 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d028-I0185-codex-A-r2 | codex:1 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d043-I0185-codex-A-r3 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d043-I0185-codex-A-r3 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d044-I0185-codex-B-r3 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d044-I0185-codex-B-r3 | codex:1 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d051-D3-codex-B-r4 | claude:0 | N2: first delimiter lost before executable child | `d3-executable-delimiter` | [true, true] | reproduced |
| d051-D3-codex-B-r4 | claude:1 | N3: regression helper re-enters its --eval parent | `d3-regression-child-probe` | [true, true] | reproduced |
| d051-D3-codex-B-r4 | claude:2 | N3: regression helper re-enters its --eval parent | `d3-regression-child-probe` | [true, true] | reproduced |
| d051-D3-codex-B-r4 | codex:0 | N2: first delimiter lost before executable child | `d3-executable-delimiter` | [true, true] | reproduced |
| d051-D3-codex-B-r4 | codex:1 | N3: regression helper re-enters its --eval parent | `d3-regression-child-probe` | [true, true] | reproduced |
| d059-I0185-codex-B-r4 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d059-I0185-codex-B-r4 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d059-I0185-codex-B-r4 | codex:1 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d060-I0185-codex-A-r4 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d060-I0185-codex-A-r4 | claude:1 | X1: cross-device symlink destination rejects installation | `i0185-cross-device-stage` | [true, true] | reproduced |
| d060-I0185-codex-A-r4 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d075-I0185-codex-A-r5 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d075-I0185-codex-A-r5 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d075-I0185-codex-A-r5 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d076-I0185-codex-B-r5 | claude:0 | N1: release retry deletes a new owner’s lock | `i0185-lock-aba-ownership` | [true, true] | reproduced |
| d076-I0185-codex-B-r5 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d091-I0185-codex-B-r6 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d091-I0185-codex-B-r6 | codex:1 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d092-I0185-codex-A-r6 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d092-I0185-codex-A-r6 | claude:1 | X1: cross-device symlink destination rejects installation | `i0185-cross-device-stage` | [true, true] | reproduced |
| d092-I0185-codex-A-r6 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d107-I0185-codex-A-r7 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d107-I0185-codex-A-r7 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d108-I0185-codex-B-r7 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d108-I0185-codex-B-r7 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d123-I0185-codex-B-r8 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d124-I0185-codex-A-r8 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d124-I0185-codex-A-r8 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d139-I0185-codex-A-r9 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d139-I0185-codex-A-r9 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d139-I0185-codex-A-r9 | codex:1 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d140-I0185-codex-B-r9 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d155-I0185-codex-B-r10 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d156-I0185-codex-A-r10 | claude:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d156-I0185-codex-A-r10 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d171-I0185-codex-A-r11 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d171-I0185-codex-A-r11 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d171-I0185-codex-A-r11 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d172-I0185-codex-B-r11 | claude:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d172-I0185-codex-B-r11 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d187-I0185-codex-B-r12 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d187-I0185-codex-B-r12 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d188-I0185-codex-A-r12 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d188-I0185-codex-A-r12 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d188-I0185-codex-A-r12 | codex:1 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d203-I0185-codex-A-r13 | claude:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d203-I0185-codex-A-r13 | codex:0 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d203-I0185-codex-A-r13 | codex:1 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d219-I0185-codex-B-r14 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d219-I0185-codex-B-r14 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d220-I0185-codex-A-r14 | claude:0 | N1: release retry deletes a new owner’s lock | `i0185-lock-aba-ownership` | [true, true] | reproduced |
| d220-I0185-codex-A-r14 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d220-I0185-codex-A-r14 | codex:1 | K2: symlink aliases acquire separate locks | `i0185-lock-alias` | [true, true] | reproduced |
| d235-I0185-codex-A-r15 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d236-I0185-codex-B-r15 | claude:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d236-I0185-codex-B-r15 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d251-I0185-codex-B-r16 | codex:0 | K3: lock-release fault returns failure without restoration | `i0185-lock-release-restore` | [true, true] | reproduced |
| d251-I0185-codex-B-r16 | codex:1 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |
| d252-I0185-codex-A-r16 | codex:0 | K7: TMPDIR separates same-destination locks | `i0185-lock-tmpdir` | [true, true] | reproduced |

## New claims and binding

**N1 — lock ownership after release/reacquire (`i0185-lock-aba-ownership.js`).** Requirement 3 says "Release only the current invocation's lock" and requires exclusion among "simultaneous cooperating installations". The witness uses the shared 0256 I0185 fixture header. A's own release removes its empty lock, a second cooperating invocation can acquire the now-free path, and A observes EIO from its release before retrying. It reproduces only if A's retry removes B's lock. This is distinct from 0256's excluded d11 part (a): that scenario "needs a third party that removes and recreates the owner's lock, which no cooperating installation does" (`0256/results/adjudication.md`, "What I could not establish"). Here A removes its own lock; B merely acquires a free one. No noncooperating writer removes an owned lock. The ambiguous remove-then-error condition is synthetic, and the result is a new reported and safety-adjudicated mechanism, outside 0257's frozen binding witness family. Root obtained [true, true] on d076 and d220; a host scratch control without the blind retry passed.

**N2 — executable delimiter (`d3-executable-delimiter.js`).** D3 requires the first `--` to reach a real spawned child before an option-like operand, including alias, default, nested, and later-literal-delimiter routes. The witness creates a temporary parent and child importing the snapshot's `index.js`, invokes them as real processes, and compares the child's raw argv and parsed operands. Root obtained [true, true] on d051 and [false, false] on the other 63 D3 trees. This new D3 mechanism is outside the frozen 11 binding-witness family, per 0257 DESIGN.

**N3 — regression check actually runs its child (`d3-regression-child-probe.py`).** A regression test for the executable help route must complete by running the intended child. The witness runs only that named test if it exists, with an 18-second process-group bound and cleanup. It exits 1 when the targeted test fails and 0 when it passes or is absent. d051's helper launches its parent with `--eval`; `lib/command.js:1284,1298` forwards `process.execArgv`, causing repeated eval rather than `pm-literal.js`. Root obtained [true, true] on d051 and [false, false] on the other 63 D3 trees. The assessor's possible orphan descendants are a risk claim, not separately established by this witness.

### New witness reproduction by config and arm

Each listed tree returned [true, true]; all unlisted trees for that witness returned [false, false]. `dNNN` abbreviates the full cell ID with the task, config, and arm supplied by the row. There were no inconsistent results for these three witnesses.

| Witness | Config | Arm | Reproducing trees |
|---|---|---|---|
| `i0185-lock-aba-ownership` | claude | A | d201, d250 |
| `i0185-lock-aba-ownership` | claude | B | none |
| `i0185-lock-aba-ownership` | codex | A | d011, d028, d043, d060, d075, d092, d107, d124, d139, d156, d171, d188, d203, d220, d235, d252 |
| `i0185-lock-aba-ownership` | codex | B | d012, d027, d044, d059, d076, d091, d108, d123, d140, d155, d172, d187, d204, d219, d236, d251 |
| `d3-executable-delimiter` | claude | A | none |
| `d3-executable-delimiter` | claude | B | none |
| `d3-executable-delimiter` | codex | A | none |
| `d3-executable-delimiter` | codex | B | d051 |
| `d3-regression-child-probe` | claude | A | none |
| `d3-regression-child-probe` | claude | B | none |
| `d3-regression-child-probe` | codex | A | none |
| `d3-regression-child-probe` | codex | B | d051 |

## NOT_TRIGGERED `release` rows — 0224 rule 1

The original replay only hooks removals under `<fixture>/agent`; these trees keep their lock under `os.tmpdir()`. Each copied replay in `results/adjudication/` changes only the support path, fixed product/kind, the hook predicate (`||target===OWNED_LOCK`), and the owned-lock expression; its assertions match 0256's variant byte for byte after those substitutions. The expression uses the product's SHA-256 identity as cited in each script, with an existing fixture target. Host scratch replays fired on all 21 cells. d011 keeps backups until unlock (`bin/devlyn.js:794-800`) and restored its exact prior snapshot, so PASS. The other 20 disposed backups before unlock and retained the new installation after the injected failure, so FAIL. Root's cell-image double runs matched each of these provisional judgments.

| Cell | Host fired / restored | Root result | Adjudicated | Matches provisional |
|---|---|---|---|---|
| d011-I0185-codex-A-r1 | yes / yes | [false, false] | PASS | yes |
| d012-I0185-codex-B-r1 | yes / no | [true, true] | FAIL | yes |
| d027-I0185-codex-B-r2 | yes / no | [true, true] | FAIL | yes |
| d028-I0185-codex-A-r2 | yes / no | [true, true] | FAIL | yes |
| d043-I0185-codex-A-r3 | yes / no | [true, true] | FAIL | yes |
| d044-I0185-codex-B-r3 | yes / no | [true, true] | FAIL | yes |
| d060-I0185-codex-A-r4 | yes / no | [true, true] | FAIL | yes |
| d075-I0185-codex-A-r5 | yes / no | [true, true] | FAIL | yes |
| d092-I0185-codex-A-r6 | yes / no | [true, true] | FAIL | yes |
| d107-I0185-codex-A-r7 | yes / no | [true, true] | FAIL | yes |
| d123-I0185-codex-B-r8 | yes / no | [true, true] | FAIL | yes |
| d124-I0185-codex-A-r8 | yes / no | [true, true] | FAIL | yes |
| d140-I0185-codex-B-r9 | yes / no | [true, true] | FAIL | yes |
| d155-I0185-codex-B-r10 | yes / no | [true, true] | FAIL | yes |
| d171-I0185-codex-A-r11 | yes / no | [true, true] | FAIL | yes |
| d187-I0185-codex-B-r12 | yes / no | [true, true] | FAIL | yes |
| d203-I0185-codex-A-r13 | yes / no | [true, true] | FAIL | yes |
| d219-I0185-codex-B-r14 | yes / no | [true, true] | FAIL | yes |
| d235-I0185-codex-A-r15 | yes / no | [true, true] | FAIL | yes |
| d251-I0185-codex-B-r16 | yes / no | [true, true] | FAIL | yes |
| d252-I0185-codex-A-r16 | yes / no | [true, true] | FAIL | yes |

## Remaining work

`root_to_run` is empty for this part. The d137 [true, false] result for `i0185-replaced-lock-owner` was withdrawn as a noncooperating-writer trigger, as recorded in `sev-claude.md` under M3. It is absent from the binding `witnesses` map in `decisions.json` and creates no unresolved panel gap; two `not_reproduced` severe entries retain its name for provenance. This part's three new witnesses and 21 replays are consistent.
