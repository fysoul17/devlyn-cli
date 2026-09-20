# 0194 — preserve invalid global Claude settings

2026-09-20. Root direct; no resolve or npm release. Status: SOURCE_VERIFIED; delivery in `.devlyn/0194/FINAL.md`.

## Why this iteration exists

Preflight0: prevent Claude installation from silently erasing existing global
settings. Mission1 gate4: visible failure and preservation on the shipped installer
path. This maintainer-selected defect does not close independent field gate15 or
establish harness/model superiority. Open GitHub issues returned none at selection.

## Hypothesis and mechanism

Prediction before reproduction: malformed global JSON is replaced with defaults
and installation reports success. Actual isolated-home reproduction confirmed
exit0, success message, and loss of the original bytes (`.devlyn/0194/REPRODUCTION.json`).
Why were bytes lost? The global reader caught every error and substituted `{}`.
Why could invalid shapes also fail silently? Root/env ownership and object shape
were unchecked. Only missing settings may start empty; unreadable or malformed
existing settings must stop before installation mutates project files.

## Minimal change and verification plan

Delete the silent fallback; validate global settings before installation writes.
Validate the root and present env as JSON objects using the project's existing
style. Preserve valid merge/default behavior and unrelated settings. No new flags,
schema or rollback system. Scope: `bin/devlyn.js`, native package
regressions, and this report/handoff. Predict invalid JSON/root/env/read cases fail
visibly without writes, valid merges and exact reinstall remain successful.

Use the actual npm package regression suite, full required lint, native Windows
and Linux CI, and independent review. Preserve baseline failures. No comparative
arm is run: there is no new measured intervention justifying another saturated
native/minimal comparison; 0193 remains frozen and NON_DISCRIMINATING.

## Actual result and decision

The original three regressions failed12 subcases; the first correction passed all
three and23 packed tests. Fable's first review had no blockers but identified
possible JSON-snippet disclosure in the new error. SyntaxError now reports only
`invalid JSON`; invalid-input regression uses the real `-y` CLI and includes a
secret sentinel. Read failures retain the path, underlying error and retry guidance.

A fresh Fable review found a MEDIUM regression in that correction: when project
and global settings alias, the early snapshot overwrites later project additions.
The new same-home/project test failed before repair (`alias-before.log`). A local
reader now performs both initial validation and fresh final read/validation. This
small extraction prevents a demonstrated stale-read failure without alias-detection
branches or transactional machinery. Four focused tests now pass. Prior reviews,
failures and checks remain preserved; superseded runs are not final acceptance.

Corrected source passes24 npm-packed PackageTests, four focused regressions and
full required lint254.740s. Fresh Fable5.1 and Grok4.6 final reviews report no C/H/M;
root reviewed the full diff and adjudicated the earlier findings. All reviewer
transcripts show zero tool calls. Grok advertised tools/MCP/skills despite flags,
so this is supplied-packet advice, not proof of context isolation. The two earlier
lint runs overlapped source edits and are diagnostics only; corrected-lint.log
binds the final unchanged source. Source/test hashes match both final packets.

Decision: accept the scoped repair subject to actual native CI before merge.
No comparative arms or npm release. Native Windows/Linux evidence, exact accepted
source, PR/merge and owned cleanup live in `.devlyn/0194/FINAL.md`.

## Principles and limits

Preflight0 / Mission-bound: removes reproduced installer data loss on the current
single-task surface; broader Mission1 and field gate15 remain open. No workaround:
invalid initial input stops before writes instead of being replaced with defaults.
No overengineering / Optimized: one local reader is reused twice; no alias
detection, new settings or transaction machinery. No guesswork: retain the
original12 failures and the introduced alias failure, with before/after evidence.
Worldclass / Production ready: final source needs independent review and native
package CI; delivery is separate from local checks. Best practice: standard fs and
JSON primitives, existing own-property/object validation style. Subtractive-first:
deleting the initial validation reopens data loss; deleting the fresh read restores
the observed alias regression. Valid symlinks remain supported; dangling links are
unreadable and stop with the link preserved (actual POSIX probe, not Windows proof).
Existing write-permission failures and concurrent edits are outside this repair's
preflight guarantee; no installation-wide atomicity claim is made.
