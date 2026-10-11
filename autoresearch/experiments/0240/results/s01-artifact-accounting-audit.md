# s01-h-codex artifact/accounting audit

2026-10-10 UTC / 2026-10-11 KST. Read-only inspection of
`/Users/aipalm/.local/share/nx01/0240-live/staged-v1/out-smoke/s01-h-codex`
and its sibling verdict. **Confirmed collector false positive:** an owner-written
check record is mistaken for a Claude result because of its filename. No source
regrade, accounting rerun, test, authentication, model call or frozen-file change
was performed. The saved STOP/PARTIAL and reported lower bound of 1,175,250 input /
17,382 output remain unchanged; this diagnosis is not a replacement cost verdict.

## Exact producer and artifact

`run/stdout:59`, completed owner command `item_30` (exit 0), writes
`cell/work/.devlyn/pair/peer-check.json` after running a Python assertion proposed
by the Codex peer. Its exact JSON value is:

```json
{
  "command": "python -c <verbatim code in .devlyn/pair/peer-check.py>",
  "exit_code": 0
}
```

The code checks `calculate_total(9, 50, 10) == 6`; the retained
`peer-check.raw.log` reports that assertion passed. This is provenance of the
artifact, not a new evaluation. The owner subsequently includes `.devlyn/pair`
in acceptance evidence (`run/stdout:80`, `item_41`), producing the byte-identical
copy at `cell/work/.git/devlyn-completion/0bb15e599fb544c2e07a9eee/custody/.devlyn/pair/peer-check.json`.
Both files have SHA256
`603c605d11a97e27cc983ddd3cd5da0fe787efd48368b68d70f48b63158c29f2`.

Actual helper receipts declare **Codex** captures:
`cell/work/.devlyn/pair/fresh/attempt.json` names
`peer1791644607812460421.jsonl`, and `resume/attempt.json` names
`peer1791644694801217919.jsonl`. Neither declares `peer-check.json` or a Claude
launch. Saved policy reports only Codex owner/peer roots, no descendants, and
MATCH without gaps or violations. No Claude transcript files exist in the cell;
saved Claude accounting has no sessions, terminal messages, API errors or retries.
The configuration-capability question is root's separate audit.

## Causal path in the frozen collector

- `0234/evidence.py:125–139` scans every `.devlyn`, plus `tmp` and `cell`.
  `peer[\w-]*\.json` and `*.output.json` filenames alone make invalid JSON or
  valid non-envelope JSON an `unreadable` Claude result. `peer-check.json` matches
  this expression but lacks `type=result` and `session_id`, so line 139 adds it.
- Each physical file is encountered both through its `.devlyn` root and the
  enclosing `cell` root. Thus the original and custody paths each appear twice
  in inherited usage gaps; the duplicates do not indicate four model attempts.
- `0234/evidence.py:261,279` passes this list through inventory.
  `0234/record_usage.py:227` converts every entry to an unreadable-Claude gap;
  lines 301–308 consequently record PARTIAL despite no separate Codex gap.
- `0238/claude-accounting-v1.py:21–22` consumes the same list independently.
  Its final set removes duplicate strings but still yields UNKNOWN. The inherited
  Runner adds those two gaps and stops at `0238/runner.py:145–172`, before product
  evaluation. The v5 guard is behaving consistently with the erroneous discovery.

## Smallest prospective correction

Correct capture discovery in a **new versioned module**, without changing any
0234/0238/0240 frozen bytes or rewriting this verdict. A filename is not evidence
that a model call produced a file.

1. Identify expected Claude capture paths from `devlyn-peer-v1` receipts whose
   engine is `claude` and whose `capture` field names the sibling file; retain
   each fresh/resumed attempt and custody copy. Also preserve legacy dispatched
   Claude captures from `attempted()` and actual observed Claude CLI redirects
   using the existing launch/redirect recognition. Match paths/producer bindings,
   not an arbitrary basename. Missing, malformed or counter-incomplete **expected**
   captures remain explicit gaps. Conflicting copies remain gaps.
2. Continue discovering valid native result envelopes by content, including
   arbitrary names and unregistered sessions. Continue native transcript/trace
   inventory, unmatched-launch and unbound-session checks. Do not skip Claude
   accounting because the owner is Codex; cross-engine peers are legitimate.
3. Remove basename-only promotion of ordinary JSON into an expected model
   capture. Do not special-case `peer-check.json`, rename the owner's evidence,
   discard gap strings after collection, or infer zero cost from absent usage.

The narrow wiring is a prospective Runner subclass which, after inherited
initialization, replaces `self.frame.cell_run.evidence.claude_envelopes` on that
private imported evidence module. `self.frame.usage.evidence` already refers to
that same object. Native `inventory()`, policy's supplied evidence, and v5
`accounting.audit(..., evidence, receipts)` then share the corrected discovery.
Retain the inherited run/STOP, identity, ancestry, accounting and delivery code;
seal the new module plus imported dependencies. No new orchestration layer or
fork of the full runner is necessary.

Before a new native attempt, targeted synthetic controls should cover ordinary
`peer*.json`/`*.output.json` owner records plus custody; valid unregistered Claude
envelopes; receipt-bound and observed-redirect captures with missing files,
invalid JSON, missing session/usage counters; legacy dispatch failures; and
unregistered native sessions/interrupted requests. These distinguish safe capture
classification from a suppression of genuine missing-usage evidence. Arbitrary
malformed files with no launch/native provenance cannot establish that a model
ran merely from their name; observable unbound launches/sessions must still stop.
