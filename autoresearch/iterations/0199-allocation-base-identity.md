# 0199 — exact allocation base identity

2026-09-21 KST. Root direct; no resolve, including controls. This closes a
reproduced defect in shipped `task-complete.py`, following the branch witnesses
from [0198](0198-receipt-admission-comparison.md). No R1 receipt-binding feature,
routing/policy change, new model comparison or npm release.

## Why this iter exists

Allocation requires the current checkout to be the requested retained base. The
shipped helper instead compared a lossy short name. A valid same-named tag or
Unicode whitespace could reject the correct base or admit a different branch.
Unlike0198's unshipped receipt-bypass cases, these are actual current allocator
failures. They do not establish downstream data loss or remote publication harm.

## Prediction and actual result

`.devlyn/0199/PREDICTIONS.md` preceded source edits and actual isolated Git CLI
replays. `baseline.json` and `repaired.json` retain raw full/short HEAD output,
CLI JSON, exit status, post-call HEAD and receipt-container existence.

| Current branch / requested base | Baseline | Repaired |
| --- | --- | --- |
| main / main, with tag main | wrongly BLOCKED | ALLOCATED |
| main+U+00A0 / exact same name | wrongly BLOCKED | ALLOCATED |
| main+U+00A0 / main | wrongly ALLOCATED | BLOCKED, unchanged HEAD, no receipt |
| main / heads/main, with tag main and branch heads/main | wrongly ALLOCATED | BLOCKED, unchanged HEAD, no receipt |

## Root cause and minimal change

Why did the base guard fail? `git symbolic-ref --short` disambiguates against
other refs, and `command()` used Unicode `strip()`. Why is that wrong? Display
shortening and whitespace trimming do not preserve Git ref identity.
`config/skills/_shared/task-complete.py:193` now compares the full symbolic ref
with `refs/heads/` plus the requested base. Line39 removes only the output record
newline. `text=True` already normalizes CRLF. The tracked `.agents` mirror matches.

**No workaround / No overengineering:** two production-line replacements remove
lossy transformations; no wrapper, flag or schema. Four isolated CLI regressions
cover correct admission and false aliases, including linked allocation and
mutation-free refusal. **No guesswork:** all four final tests fail against the
original production lines; restoring only `strip()` or only `--short` causes
two failures each. `baseline-final-tests.log`, `restore-strip.log` and
`restore-short.log` prove both replacements are necessary.

## Verification and independent review

Focused final regressions:4/4 PASS. Fable5.1 native static review found no
CRITICAL/HIGH/MEDIUM issue, with two LOW coverage suggestions. Follow-up actual
Git checks cover same-tag in-place allocation, acceptance, completion and resume
with ignored-data preservation, plus exact NUL-delimited leading-space filenames
(`consumer-controls.log`). Root also searched sibling shared Python modules for
`task-complete` callers; none outside the helper's own self-test was found.

The first new alias test created its tag before its second branch, causing Git
fixture setup itself to fail. The corrected order creates the branch first.
Both failed attempts remain recorded; final red results use the corrected tests.
The initial full lint also caught the stale tracked `.agents` mirror; it was
byte-compared to baseline before synchronization. These failures are not PASSes.
Fable final review PASS and Grok4.6 native source review PASS with limits (444.878s;
header grok-4.6, final modelUsage grok-4.6-build). No HIGH/CRITICAL finding. The final
source/mirror hash in `SOURCE-CHECK.json` binds the corrected fixture order that
Fable received as a textual delta. Existing universal-newline translation remains;
prepatch receipts with unusual whitespace-edged Gitdir paths were not tested.
Full `bash scripts/lint-skills.sh` PASS (332.664s), including37 helper tests;
`git diff --check` and source/mirror byte parity PASS. PR CI/delivery is recorded
separately in0199 FINAL.

## Boundaries and continuation

0198's frozen inputs/results and lack of observed fresh-review lift are unchanged.
This is known-defect repair, not untouched confirmation or comparative quality
proof. Mission1, unrelated confirmation and field gate15 remain OPEN;0187 NO-GO
and existing routing stand. Preserve original checkout WIP, source/Git, frozen
runs and A16. Delivery/cleanup authority will be `.devlyn/0199/FINAL.md` in the
retained research checkout; receipt `8dfa055579058029c9a71f78`.
