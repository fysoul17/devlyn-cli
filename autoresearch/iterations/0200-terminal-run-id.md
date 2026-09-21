# 0200 — reject path components in terminal run IDs

2026-09-21 KST. Root direct; no resolve invocation or npm release. This follows
0195's unverified dot-dot candidate, not a new comparison or exposed fixture draw.

## Reproduction and minimum repair

An active state with completed VERIFY/final-report, `run_id: ".."` and an empty
`.devlyn/runs` directory returned CLI success without an archive. The path
`runs/../pipeline.state.json` named the active file itself. A normal ID under the
same conditions returned79 / INCOMPLETE:archive. The character whitelist admitted
`.` and `..`, although neither names a child archive directory.

`terminal-claim-check.py:152` now rejects those exact components before path
construction. One production-line replacement; the tracked agent mirror matches.
Valid dotted IDs retain missing-archive refusal and archived completion.
**No workaround / No overengineering:** correct the input predicate, not archive
lookup with another wrapper. **No guesswork:** the packaged CLI regression fails
for both special IDs before repair; restoring the original predicate in an isolated
copy fails both again. The original deep-JSON candidate at depth2000 returned
MALFORMED in this host's diagnostic and was not included in the repair.

## Verification and limits

The final package suite has26 passing tests. The new test exercises five IDs,
including `.valid`, `valid.name` and `valid..name`, with unchanged input bytes.
The initial `...` valid control was replaced before final checks because trailing
dots are unsuitable for a portable Windows directory fixture.

Opus5 source review PASS with two LOW observations. Eight supplementary before/after
controls confirm the shared active-state API's `.` alias is now MALFORMED, and
show the hook's observable change: same-session open phases using these invalid
IDs move from block to allow under the existing MALFORMED policy. A normal ID's
open phase still blocks. This is not a change to that hook policy or a promise
that malformed states block Stop. The CLI `.` test alone only proves rejection,
not a false-CLEAN repair; the direct active-state control supplies the latter.
Grok4.6 source review also PASS; no HIGH/CRITICAL finding in either review.
Full lint PASS (467.457s); diff/mirror checks PASS. Delivery authority: `.devlyn/0200/FINAL.md`.

Archive writer validation, symlink aliases, archive content binding and Windows
trailing-dot normalization are outside this lexical repair. No general archive
integrity, security completeness, model-performance or resolve-utility claim.
0198/0199 results, original checkout WIP, A16 and existing routing stay preserved.
Mission1, unrelated confirmation and field gate15 remain OPEN.
