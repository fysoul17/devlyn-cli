# 0225 replay — result

Registered in [0225](../../iterations/0225-resolve-cost-cuts.md) ("Replay (after step 2)" and "Replay mechanics"). The driver is [`replay.py`](replay.py) and the frozen manifest is [`replay-manifest.json`](replay-manifest.json) (commit `50fed13d`, pushed before the first call). Raw outputs are in `~/.local/share/nx01/0225-replay/`.

## Adjudication criteria (committed while round s6-04-r0 was running, before any result was read)

A binding HIGH counts as retained when an authenticated seat's HIGH/CRITICAL in that round (`score.json` `binding`: parsed from the output of a seat whose role evidence the merge retained) names the **same mechanism**, whatever its wording, id or file:line. The mechanism is the code path plus the failure, taken from the archived finding:

1. **s6-04 r1** (archived `spec-compliance.unbounded-writer-readiness`, `tests/test_types/test_File.py:98`): the FIFO test's wait for the writer to become ready (the readiness handshake, a wait, join or open) has no timeout, so the probe can hang forever. A finding about some other unbounded wait (for example the reader side only) does not count.
2. **s6-04 r2** (archived `spec.timeout-cleanup`, `test_File.py:76`): timeout or error cleanup cannot terminate a reader thread blocked on the FIFO open/read, so the thread survives cleanup.
3. **s6-16 r0** (archived `spec.rollback-marker-restoration`, `bin/devlyn.js:754`): the install marker is published (`writeInstallMarker` / rename to `markerPath`) before a later failure, and rollback neither removes nor restores it.
4. **s6-16 r1** (archived `spec.preserve-preexisting-content`, `writeInstallMarker`): a pre-existing file at the marker's temporary path makes the exclusive write fail with EEXIST, and cleanup then deletes that pre-existing file.
5. **s6-07 r0** (archived `spec-compliance.lock-release`, `bin/devlyn.js:782`): lock release is attempted once (`rmdirSync(lock)`), so one transient failure leaves the owned lock behind and blocks later installs.

A finding that names the right code but a different failure, or the right failure at a different path, does not count.

**Input BLOCKED.** An input BLOCKED is any harness row or early refusal whose cause is the judges' input (`score.json` `harness_rows`, `stops`, `input_flags`), or an authenticated seat's BLOCKED/coverage finding whose stated cause is a missing, unreadable or mismatched input. A seat BLOCKED that states a genuine product evidence gap (per the rubric's coverage rule) is not an input BLOCKED. An infra failure (limit, network, CLI crash) is recorded as such and counts against the pass: the only repeat is the registration's whole-replay repeat.

Each decision records the candidate row verbatim, and Astra verifies it.

**Timing correction.** The criteria were written at 12:58:51Z, while round s6-04-r0 (started 12:58:26Z) was running. They were committed at 12:59:08Z (`e477e9a0`, pushed immediately), after that round had exited. Root's own account, which no artifact can independently confirm: no output had been read before the commit, and the first round's exit line reached root after it.

## Attempt 1 (2026-09-27, 12:58–13:04Z)

The run ended normally (`run exit=0`). All 7 rounds ran once, in the frozen order. The archive inventory was unchanged (17,784 files; `integrity.json` `unchanged: true`, and `score` re-inventoried it itself). In every round the snapshot, resolution and both argv hashes matched the manifest, and the pair-trigger reasons were as frozen.

| round | wall s | Claude s | Codex s | overlap | verdict (primary / pair) | Claude out tok | Codex total tok |
|---|---|---|---|---|---|---|---|
| s6-04-r0 | 40.7 | 25.8 | 39.8 | yes | PASS_WITH_ISSUES / NEEDS_WORK | 2318 | 11696 |
| s6-04-r1 | 26.2 | 25.3 | 19.5 | yes | PASS_WITH_ISSUES / NEEDS_WORK | 2191 | 11850 |
| s6-04-r2 | 30.3 | 20.0 | 29.4 | yes | PASS_WITH_ISSUES / NEEDS_WORK | 1784 | 15076 |
| s6-16-r0 | 66.0 | 65.1 | 31.4 | yes | **BLOCKED** / NEEDS_WORK | 6148 | 19630 |
| s6-16-r1 | 81.0 | 80.2 | 30.4 | yes | PASS_WITH_ISSUES / NEEDS_WORK | 7776 | 22220 |
| s6-07-r0 | 60.1 | 59.3 | 44.7 | yes | NEEDS_WORK / PASS_WITH_ISSUES | 5509 | 31781 |
| s6-07-r1 | 62.4 | 61.7 | 55.3 | yes | NEEDS_WORK / PASS_WITH_ISSUES | 6034 | 28563 |

- Claude usage is COMPLETE for every seat; the output column is the envelope's `output_tokens`.
- Codex usage is PARTIAL: the total only, with OUTPUT UNKNOWN.
- Observed identities: `claude-opus-5-5` (effort unobserved) and `gpt-6-astra` at `high`. The s6-07 Claude pair was dispatched at `--effort medium` (step 2's dispatch; the archived owner passed none), and equal effective Claude effort is not established.

### Binding HIGHs (pre-committed criteria)

| # | round | archived | replay candidate (authenticated seat) | decision |
|---|---|---|---|---|
| 1 | s6-04 r1 | HIGH `spec-compliance.unbounded-writer-readiness`, `test_File.py:98` (Codex pair) | Codex pair **MEDIUM, `verdict_binding: true`** `spec.timeout-cleanup`, `test_File.py:98`: "`assert writer.stdout.readline() == b"ready\n"` without a timeout. If the writer stalls before emitting readiness, the test blocks indefinitely and never reaches `writer.kill()`" | same defect and same line, verdict-binding, but **not HIGH/CRITICAL** → not retained under the registered rule |
| 2 | s6-04 r2 | HIGH `spec.timeout-cleanup`, `test_File.py:76` (Codex pair) | Codex pair HIGH `spec.timeout-cleanup`, `test_File.py:77`: "the reader then blocks without a writer and survives the second join" | retained |
| 3 | s6-16 r0 | HIGH `spec.rollback-marker-restoration`, `bin/devlyn.js:754` (Codex pair) | Codex pair HIGH `spec.rollback-incomplete`, `bin/devlyn.js:426`: "`fs.renameSync(tempPath, markerPath)` … before … `fs.rmSync(tempPath …)`. If this cleanup operation throws after marker publication … the newly published marker has no undo action" | retained |
| 4 | s6-16 r1 | HIGH `spec.preserve-preexisting-content` (Codex pair) | Codex pair HIGH `spec.recovery-preservation`, `bin/devlyn.js:426`: "A preexisting file … named `.devlyn-install.json.<current-pid>.tmp` is deleted … `flag: 'wx'`, so publication throws EEXIST. Nevertheless … `fs.rmSync(tempPath …)`" | retained |
| 5 | s6-07 r0 | HIGH `spec-compliance.lock-release`, `bin/devlyn.js:782` (Codex primary) | Codex primary HIGH `spec.lock-release`, `bin/devlyn.js:782`: "`try { fs.rmdirSync(lock); }` attempts release once … permanently blocking installation" | retained |

The binding-MEDIUM channel is not new in step 2. Pre-step-2 `verify.md` (`6996a126^:…/verify.md:104`) and the archived s6-04 r1 Codex prompt (`codex-judge.r1.prompt:135`) carry the same sentence, "Emit HIGH/CRITICAL as appropriate, or MEDIUM with literal `verdict_binding: true`". The merge ranks both binding forms alike (`judge-output-parser.py finding_rank`). Replay attempt 1 therefore had the same defect found, at the same line and bound to the verdict, with a lower severity label than the archive.

### BLOCKEDs

- **Input BLOCKEDs: 0.** There was no harness input row and no early refusal: `input_flags` is empty in all 7 rounds, and s6-16-r0's `stops` holds only its final merge summary line. No authenticated seat stated a missing, unreadable or mismatched input. By contrast, the archived s6-04 r0 Codex seat and s6-07 r1 Codex primary were input BLOCKEDs; both replayed as real verdicts (NEEDS_WORK).
- **One non-input BLOCKED, caused by step 2.** In s6-16-r0 the Claude primary emitted a prose first line, "I found no blocking issues, only two low-severity ones.", then valid JSONL and `PASS_WITH_ISSUES`. The merge blocked that seat with `verify-judge-emission-contract-violated` (`claude-judge.r0.stdout:1: Expecting value`), so the round verdict became BLOCKED, although the pair had found binding HIGH #3.
  - Before step 2, this strict contract applied to the pair seat only: pre-step-2 `verify.md:194-201` (`6996a126^`) says "every other non-empty line blocks the pair source".
  - Step 2 extended it to both seats (`verify.md:130`, "Both seats emit only JSONL … the harness rejects any other non-empty line"). `recover_envelope_text` recovers a narrative preamble only for NEEDS_WORK with findings.
  - Under step 1, a VERIFY BLOCKED goes to the report without repair. In a live run this round would have ended BLOCKED instead of repairing the marker defect (the archived run went NEEDS_WORK → repair).

### Apparatus divergence found after the run (Claude seats only)

All 7 Claude judges received the user's global `~/.claude/CLAUDE.md` (4,623 characters, loaded as a "Project" instruction file) in addition to the copy's own `CLAUDE.md`. The replay copies sit under `$HOME`, and Claude Code loads `<ancestor>/.claude/CLAUDE.md` for every ancestor of the cwd. `$HOME` is an ancestor, so the user's global file matched. Root's pre-run probe used a cwd outside `$HOME` and missed this. It is shown by each retained transcript's `instructions` attachment (`~/.local/share/nx01/0225-replay/transcripts/*.jsonl`).
- The archived judges loaded only `/work/CLAUDE.md` (their transcripts' attachments).
- The Codex seats were isolated as designed: their own HOME, no `~/.agents` skills, no global `AGENTS.md`.
- Every binding-HIGH candidate above came from a Codex seat. The one non-input BLOCKED came from a contaminated Claude seat.
- The textual scan of judge-authored text (Codex log and output, Claude result and transcript) found no path to another round's copy, the archive or the registration. `outside_paths` shows only the injected CLAUDE.md path and the Claude CLI's own auto-memory path. Reads outside the scan's coverage are not excluded by it, but the seal made the replay root unreadable except for the round's own copy.
- A second effect of the same cause: the archived s6-07 Claude seats loaded `/work/AGENTS.md` (Claude Code falls back to it when no CLAUDE.md applies), while the replay s6-07 seats loaded only the host CLAUDE.md, because the ancestor file suppressed that fallback.

### Registered outcome of attempt 1

**FAIL by the registered letter.** Pass condition 1 ("the five binding HIGHs are retained" as authenticated binding HIGH/CRITICAL) holds for 4 of 5. Conditions 2–4 hold: 0 input BLOCKEDs, overlap in every round, and archive integrity unchanged.

### Adjudication review and decision

Astra (gpt-6-astra, ultra, read-only) re-checked every decision above against the raw files (`.devlyn/0225/replay-a1-astra.out.md`) and confirmed:
- all five retention decisions;
- the non-input classification of the s6-16-r0 BLOCKED;
- conditions 2–4 and the 17,784-entry inventory.

Its synthesis: **registered FAIL; recall of the fifth defect preserved.** Neither cancels the other, and counting the MEDIUM as retained now would retroactively change the explicit rule.

The registration's failure branch is "step 2 may be revised once, and the replay is repeated on the same 7 rounds". Root takes it, and Astra concurred with these choices:
- **The one step-2 revision fixes the regression this replay exposed.** A primary seat's non-JSONL line now blocks the whole round, even when the other seat found a binding defect. It is general: no exception for this particular sentence, with negative cases alongside.
- **Rejected:** removing the binding-MEDIUM channel. It predates step 2, repair already treats it as binding, and changing labels to fit the replay metric would not show better recall.
- **The apparatus is repaired before the repeat:**
  - the replay root moves outside `$HOME`, with clean ancestors;
  - the actual Claude instruction attachments are verified before any call, which also restores s6-07's `AGENTS.md` fallback;
  - the scanner coverage is updated.
- **Attempt 1 is retained as recorded.** The repeat scores with the same rules and criteria.
