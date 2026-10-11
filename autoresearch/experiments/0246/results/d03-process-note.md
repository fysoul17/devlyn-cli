# 0246 d03 Claude/A process and cost note

Read-only audit of retained evidence; no tests, model calls, authentication, or native runs were performed. This note preserves the recorded CHECKS_PASS / COMPLETE verdict and makes no comparative efficacy or causal performance claim.

Raw cell: `/Users/aipalm/.local/share/nx01/0246-live/out-measured/d03-f23-claude-a`. Stream references below are one-based lines of `run/stdout`. Verdict: its parent's `verdict-d03-f23-claude-a.json`.

## Native execution and recorded cost

The recorded arm is A, with native Claude Opus 5.5 at max effort, session `cd63e32d-6949-458c-8cff-c22aa7432050`. The cell has no installed devlyn guides or peer helper. Actual tool use comprises 26 Bash calls and 15 Edit calls. No observed Task/Skill call, peer invocation, child model launch, or devlyn invocation occurred. A broader native tool catalog is not evidence of tool use. The verdict reports peer policy NOT_ACTIVATED / MATCH, identity MATCH, and no accounting gaps.

Recorded wall time is **825.7604531670222 seconds**. COMPLETE emitted usage is **3,441,785 input tokens and 93,953 output tokens**: Claude input 66, cache-read input 3,315,713, cache-write input 126,006; output 93,953. These are the retained accounting totals, not independently measured provider billing. No Codex or peer usage is recorded.

Local delivery is commit `3683f82d3bb3731835071fc4b66b6fa0c064beab`, changing only `bin/cli.js` and `tests/cli.test.js`. The recorded source/delivery checks passed and cleanup is CLEAN. No archive or verdict was rewritten.

## Executed checks versus reported checks

| Retained evidence | Actual observation |
| --- | --- |
| Lines 386–387, before implementation | Existing CLI suite: 3 tests, 3 pass, 0 fail. The printed shell exit status follows a pipeline; TAP counts establish the observed result. |
| Lines 587–588 | Updated public CLI suite: 9 tests, 9 pass. |
| Lines 658–661, 835–836, 872–873, 903–904 | Four further successful public CLI suite runs, giving five successful candidate public runs in total. |
| Lines 710–711 | Server test file alone: 3 pass. |
| Lines 738–739 and 872–873 | Explicit test-file glob: 12 tests, 12 pass, twice. |
| `checks.json` | Evaluator public suite: 9 pass; recorded oracle results all PASS: priority-rollback, single-warehouse-fefo, submillisecond-order, offset-equivalence. |

The mutation evidence is more precise than either the interim “31 deliberate bugs” statement (line 791) or the final “32 ... tests caught all” statement:

| Batch | Attempts and observed output |
| --- | --- |
| Command line 612; result 615 | 22 named attempts: 19 CAUGHT, 1 SURVIVED (FEFO replaced by lot-id ordering), 2 ANCHOR NOT FOUND. Only 20 mutants reached test execution. |
| Command line 658; result 661 | 11 executed mutants, all CAUGHT, including the strengthened FEFO fixture and repaired/repeated checks. |
| Command line 837; result 840 | 32 executed mutants: explicit output `mutations caught: 31 / 32`; `root may be array` survived. |
| Command line 872; result 873, after the null-root assertion was added | The previously surviving root-object-guard removal was checked individually and caught: invalid-input test failed as expected. The unmutated public suite and both test files passed. |

Together these show **64 mutant-suite executions across the batches**, plus two failed mutation-anchor attempts. They are not 64 unique defects. The final 32-check coverage claim is supported across the consolidated batch and a later targeted recovery; there is **no retained final full-batch 32/32 output**. The final narrative's “first round found two weak spots” compresses the chronology: FEFO discrimination failed in the first batch, while the root-guard gap appeared in the later consolidated batch.

The null-root issue was a test gap exposed by deliberately removing the implementation's existing object guard, not an observed defect in the final unmutated implementation. The final assertion verifies a structured invalid-input response for null. The claimed “about 40” hand checks is an owner estimate; this note does not certify a distinct-case count.

## Timestamp behavior and recorded oracle outcome

The implementation validates calendar fields and normalizes explicit timezone offsets into UTC whole-second milliseconds. It retains arbitrary fractional-second digits separately, stripping trailing zeros, and compares the milliseconds followed by normalized fractional digits. This avoids losing submillisecond ordering through Date truncation. Missing offsets are deliberately treated as UTC.

The timestamp handling was present in the first implementation edit (line 415), before the later manual precision probes. The retained manual output at line 505 includes `0.0001 vs 0.00005 -> 1` and `0.0001 vs 0.000100 -> 0`. Persistent processing-order tests exercise offsets and equivalent instants; this note does not claim a dedicated persisted submillisecond assertion. The four recorded oracle PASS results, including submillisecond-order and offset-equivalence, are reported as existing evaluator evidence. No hidden oracle was inspected or replayed.

## Directory-mode test failure and baseline provenance

The owner directly ran `node --test tests/` after implementation, twice (lines 684–685 and 710–711). It failed with `MODULE_NOT_FOUND: /cell/work/tests` under Node v22.23.2. These commands execute the package script's underlying command; the retained transcript does not show a literal `npm test` invocation. Explicit test files passed, as recorded above.

Read-only inspection of baseline commit `d868dbfccde0b51a1b6d592add8e91998c6b1e8c` shows the same `package.json` bytes as the delivered checkout, SHA-256 `127f48d4ddeb3adf1c574371024938e5d220823d293a58306f1e8affa64d064c`, with `scripts.test = "node --test tests/"`. Both test files already existed, and the same Node version was reported before implementation (line 10). This supports an existing command/runtime incompatibility as the explanation, but **a before-change directory-mode failure is not independently verified by an actual baseline execution in this cell**. The baseline execution covered only the CLI file. The final owner's stronger “already broken before this change” claim is therefore qualified here. Package configuration was outside the allowed change scope and remained unchanged.

## Process observations and limits

The caller required the public check and at least two new cases; it did not request mutation testing or peer review. The owner spontaneously established a baseline, probed date parsing and precision, exercised allocation/error paths, wrote six additional public tests, and used deliberate mutations to assess its own tests. The mutation runs exposed two test discrimination gaps that it then repaired, without a peer.

There is also observable overlapping verification: FEFO/rollback mutations recur across batches, the consolidated 32-mutant batch followed formatting work, and the public suite ran again after a clean local commit without another source edit. Some repeats followed substantive test changes and have a concrete purpose. These observations identify executed work, not a measured avoidable-token amount. No isolated per-check cost or counterfactual run exists here, so this single cell cannot establish that A is generally faster, slower, better, or worse than another arm.

## Evidence preservation

The following nine protected evidence/source files were SHA-256 captured before this audit and checked unchanged immediately before writing this note. Keys below are relative to the raw cell except the sibling verdict.

| File | SHA-256 before = after |
| --- | --- |
| `../verdict-d03-f23-claude-a.json` | `6f1f0b98a4d84a6a009a634bd1a49576b7ce14358324f85fbc0f08082feb69af` |
| `final.txt` | `b97478a44013aee5d79a59d743509aef7508fe659e5b9c744611524ea1a1a83d` |
| `run/stdout` | `abe3f074618802d5493ace1b4a899d6bd1a35ec4034da2ad0fb1614d5d18ad45` |
| `run/stderr` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run/result.json` | `c73fc247512ca01b2994c2308401305b657215e0a4219fcf5cbfa757ef5e5116` |
| `harness/caller.json` | `9f7a4d621eb8f249a6b0847859c100d755d30f879100b3fedde44fb25a965451` |
| `baseline.json` | `9314fe43d2d5bb1ae62018bc23f338e4cc9403760380225392197f4c28321ba5` |
| `cell/work/bin/cli.js` | `4300a07a3928cc92704880f16f94410a5bb0cf3db6705970fd97da6ea87b551d` |
| `cell/work/tests/cli.test.js` | `9639eedad14d01ec53659cd8b7b0006e247fa25b120fe97c8f7894156e74d2c3` |

Only this process note was written. The original outcome, costs, raw files, and frozen study inputs remain untouched.

