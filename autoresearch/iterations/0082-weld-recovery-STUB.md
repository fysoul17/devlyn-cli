# iter-0082 — R-weld: make the pair judge's review actually collectable

**Status: REGISTERED, NOT FROZEN, NOT BUILT. 2026-07-27.**

Opened because iter-0081 cleared gate part 2 and **R-weld is now the only thing
between the grok pair seat and a usable review**. Every one of the six admissible
iter-0081 runs produced a correct CRITICAL and `NEEDS_WORK` — and the collector
rejected all six.

## Why this iter exists (pre-flight 0)

**User-visible failure**: the pair judge finds the right defect and the harness
throws it away. Measured 6/6 in iter-0081's v2 cell (`0081.5`), 16/16 in
iter-0080's corpus.

**Mechanism, already established — do not re-derive** (`0080.3`): `.text` under
`--output-format json` is the concatenation of per-turn assistant text with **no
separator**, so narration lands on the *same line* as the first finding JSON.
No line parses; the collector rejects.

## What iter-0080 already froze, measured, and refused to ship

A **byte-forward recovery** rule (`0080-…md:576-620`): after the `stopReason`
gate, scan `.text` forward by bytes to the first offset where a complete finding
JSON object or a `# SUMMARY ` token begins, discard only the strictly-preceding
bytes. Binding constraints: never synthesize a verdict, never reorder, never
alter severity; a recovered stream with no legal contract still rejects;
**dual-document `.text` still rejects**; and **recovery may never produce PASS at
all** — admissible only with a verdict-binding finding *and* a consistent
`NEEDS_WORK`.

Measured on 18 real artifacts (`0080-…md:943-968`): **16 recovered, 1 rejected, 1
correctly refused**. It was **not shipped**, for two reasons that are this iter's
actual work:

- **R-dual-tab** — the binding "dual-document still rejects" constraint is
  **not satisfiable by a naive implementation**. Codex built a TAB-separated
  dual-contract (INFO + `# SUMMARY PASS`, then a TAB-indented CRITICAL +
  `# SUMMARY NEEDS_WORK`); the tab defeats a `}{` adjacency check while the
  collector strips leading whitespace per line and lets the **last** summary
  overwrite the first. Two verdict documents pass as one.
- **R-fence** — the 1 rejected row is a markdown fence around the finding.
  Byte-forward recovery discards the *opening* fence with the prose; the
  **trailing** ` ``` ` survives and fails the line contract. Observed on **both**
  transports. Grok added that an **opening-only** fence would ACCEPT under the
  frozen rule — so "the freeze is not a coherent fence policy."

`0080.3` shipped nothing on exactly this ground: putting a mechanism into product
code that is known to break its own negative tier is not licensed.

## Orchestrator's opening position (to be attacked, not ratified)

**R-dual-tab's root cause is not whitespace and not adjacency. It is that the
collector silently accepts a second summary and overwrites the first** —
`collect-codex-findings.py:51`, `summary = item`, unguarded.

Candidate root fix, subtractive: **a second `# SUMMARY` line is a hard reject.**
Then any dual-*verdict* document carries two summaries and rejects by
construction — no adjacency check, no whitespace normalization, no parser. One
assignment becomes a guarded assignment. A single document with many findings and
one summary is unaffected, which is the legitimate shape.

For **R-fence**, the incoherence Grok named argues for a uniform rule rather than
a special case: fence lines become **ignorable**, the same shape as the existing
`raw.startswith("#")` comment skip (`:53-54`). Opening-only, closing-only, and
paired then behave identically, and the 17th row clears.

**Both are unverified opinions until the seats attack them and the negatives are
written first.** `0080.3`'s condition is binding: a v2 needs **its own freeze with
its negative tests written before any code**, never a retroactive amendment to
the v1 rule.

## Not yet frozen

No bar, no predictions, no build scope. Those come after the seat round and
before any measurement.

## Binding process corrections carried from iter-0081

1. **Never handicap a gate seat.** Both seats get execution from the first round.
2. **Score the frozen conjunct, never a proxy.** "Collector exit 0" means run the
   collector.
3. **A clearance bar must not conjoin an independently registered open residual.**
