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

## R0 seat round + v2 FROZEN — 2026-07-27 (Codex GPT-5.6-sol + Grok 4.5, both executing)

**Status: FROZEN, NOT BUILT. Product files changed: NONE.**
Both seats executed against the live collector and merge; neither reviewed prose.

### Orchestrator withdrawals — 3, all refuted by execution I reproduced myself

1. **"A second `# SUMMARY` reject closes every dual-document shape" — WITHDRAWN.**
   Grok's counterexample, reproduced by the orchestrator against the real
   collector: `{"severity":"INFO"}` / `# SUMMARY {"verdict":"PASS"}` /
   `{"severity":"CRITICAL"}` → **ACCEPT, verdict PASS, CRITICAL in the findings
   file**. One summary, so the guard never fires. Dual-*summary* ≠ dual-*document*.
   Adjacent hole found the same way: `CRITICAL` + `# SUMMARY PASS` **ACCEPTs**
   today — there is no findings↔summary consistency check (`:65-66` only rejects
   non-PASS *without* findings).
2. **"`verify-merge-findings.py` already blocks a review the collector dropped" —
   WITHDRAWN, and it is a safety hole, not a backstop.** `detect_pair_stdout_contract_violations`
   (`verify-merge-findings.py:771-930`) line-scans `*-judge.stdout` and **never
   unwraps the envelope** — searched, no `stopReason`/`.text` extraction. The
   shipped adapter writes the whole `--output-format json` envelope to that file
   (`adapters/grok.md:47-48`). Both seats executed it: envelope-with-welded-CRITICAL
   → `pair_judge: PASS`, zero blockers; raw `.text` with the same body → `BLOCKED`.
   Codex ran it on **all six untouched iter-0081 artifacts: PASS 6/6.**
3. **"Ignore fence lines, same shape as the `#` comment skip" — WITHDRAWN as
   written; it produces a FALSE PASS.** Reproduced: a fence *prefix* with the
   finding on the same line (```` ```{"severity":"CRITICAL"…} ````) is discarded
   by a `startswith` rule, leaving a bare `# SUMMARY PASS`. Only **exact trimmed**
   fence tokens may be ignorable.

### Converged — the terminal-record grammar (both seats, same shape)

| # | Rule |
|---|---|
| **G1** | **The summary is terminal.** Any later non-ignorable record rejects. This subsumes duplicate-summary rejection *and* prevents the output-file record reordering Codex measured |
| **G2** | Ignorable fence tokens are **exactly** the trimmed strings ` ``` `, ` ```json `, ` ```jsonl `. **Never a prefix with trailing bytes** (withdrawal 3) |
| **G3** | Recognise the measured grok summary form — a severity-less object containing exactly `verdict` — in addition to `# SUMMARY {…}` |
| **G4** | Byte-forward recovery only after the `EndTurn` gate, retaining every 0080 constraint: no synthesized verdict, no reorder, no severity change, **recovery may never produce PASS**, admissible only with a verdict-binding finding **and** a consistent `NEEDS_WORK` |

**Explicitly rejected**: banning a top-level `verdict` key inside findings.
Codex measured 27 existing severity-bearing findings that legitimately carry one;
the orchestrator reproduced the count independently. That rule would invalidate
existing evidence.

**Also rejected**: prompt engineering (measured dead, `--rules` 0/6) and a
session/ACP parser — Codex searched the vendor surface and found response-text
chunks, not a verdict channel, so it adds vendor machinery without removing byte
scanning.

### Negatives — written BEFORE any code, per 0080.3's binding condition

| ID | Payload | Required |
|---|---|---|
| N1 | TAB-separated `INFO`+`SUMMARY PASS`, then `CRITICAL`+`SUMMARY NEEDS_WORK` | reject |
| N2 | one summary: `INFO` / `SUMMARY PASS` / trailing `CRITICAL` | reject (G1) |
| N3 | `CRITICAL` + `SUMMARY PASS` | reject (consistency) |
| N4 | recovered preamble + `INFO` + `PASS` | reject (never recovered PASS) |
| N5 | paired, opening-only, closing-only exact fences around one `CRITICAL`+`NEEDS_WORK` | **identical** result across all three |
| N6 | fence token with trailing bytes on the same line | reject — "ignore fences" must not become "ignore arbitrary suffixes" |
| N7 | fenced decoy `PASS` contract followed by a real `NEEDS_WORK` contract | reject, never silently select one |
| N8 | the six untouched iter-0081 v2 stdouts | **accept 6/6**, and the real merge must then return `NEEDS_WORK` 6/6 |
| N9 | the 18 settled 0080 artifacts | no finding, severity, or verdict lost, reordered, or changed |

**Bar**: N1-N7 reject, N5 uniform, N8 accept 6/6 with merge `NEEDS_WORK` 6/6,
N9 lossless. Anything less does not ship.

### Registered separately — NOT conjoined to this bar

**R-merge-envelope**: the merge safety hole in withdrawal 2. It is a *safety*
fix, not R-weld clearance, and conjoining it here would repeat exactly the
coupling error that made iter-0081 v1 unachievable. Codex's proposed invariant,
recorded for its own freeze: *after round-artifact reset, a completed non-timeout
stdout with no canonical collector output must be `BLOCKED`*.

### Binding operator lesson — NEW, and it is the orchestrator's fault

**Both seats wrote directly into this tracked iteration file.** Grok added 46
lines; Codex added its results and cited them as `0082 R0:124/182/199/222`, and
also created `.devlyn/iter0082-probes/`. The orchestrator's earlier gate prompts
forbade modifying tracked files; **this round's prompt did not**, and both seats
were spawned with write-capable shells. Both writes were preserved to the
scratchpad and **reverted**.

A seat writing into the record bypasses the orchestrator verification step that
exists precisely to keep unverified claims out of it — the failure mode this
whole loop is built to prevent. **Every seat prompt that grants a shell must
forbid modifying tracked files.**

Everything adopted above was re-executed by the orchestrator first: the Break-A
counterexample, the `CRITICAL`+`PASS` hole, the absence of envelope unwrapping in
merge, the fence-prefix false PASS, and the 27-row `verdict` count.

## BUILT + MEASURED — 2026-07-27. Gate NOT yet run; product held uncommitted.

| Frozen item | Result |
|---|---|
| N1 dual-tab (two full contracts, tab-indented second) | **reject** |
| N2 one summary, trailing `CRITICAL` after it | **reject** |
| N3 `CRITICAL` + `SUMMARY PASS` | **reject** |
| N4 recovered preamble + `INFO` + `PASS` | **reject** |
| N5 paired / opening-only / closing-only fences | **uniform — all three accept** |
| N6 fence token with trailing bytes | **reject** |
| N7 fenced decoy `PASS`, then real `NEEDS_WORK` | **reject** |
| N8 the six untouched iter-0081 v2 stdouts | **accept 6/6**, each `NEEDS_WORK` + 1 `CRITICAL` |
| **N9 the 18 settled 0080 artifacts** | **UNSATISFIABLE — the artifacts do not exist** |

Plus the collector's own self-test (updated to the new contract) and an 11-case
negative suite, both green; lint green.

### N9 is unsatisfiable, and the bar is NOT quietly amended

The 0080 corpus lived in `scratchpad/emission-sweep/` — session-scoped, gone.
**This is the exact failure that made iter-0081's fixture durable**, recurring.
N9 is reported **unmet**, not rewritten.

**Substitute regression check, explicitly labelled as NOT N9**: every
`*-judge.stdout` still in the repo — **106 real captures** — collected under both
the HEAD collector and the new one, comparing exit status and canonical bytes.

**The substitute earned its keep on the first run: 4 REGRESSIONS.** A real
historical shape — a `LOW`-severity `VJP-PASS` advisory finding alongside a
`PASS` summary — was newly rejected, because the orchestrator's new consistency
rule counted `LOW` as verdict-binding. **It is not**: `verify-merge-findings.py:117-121`
binds only `CRITICAL`/`HIGH`, plus `MEDIUM` when the finding sets
`verdict_binding: true`. The collector now calls the same predicate instead of
inventing a second one.

After that fix: **65 accepted by both, byte-identical, 0 regressions, 0 newly
accepted** (recovery only reaches envelope-wrapped welds, which the historical
corpus does not contain).

### What changed in the product

`collect-codex-findings.py`: summary is terminal; exact-token fences ignorable;
the severity-less `{"verdict": …}` summary form recognised; a `PASS` summary with
a verdict-binding finding rejects; byte-forward recovery after the `EndTurn` gate,
admissible only with a verdict-binding finding **and** a `NEEDS_WORK` summary.
New `test-collector-negatives.py` holds the frozen negatives.

**Held uncommitted until the two-seat gate runs.** Both seats must EXECUTE, and —
new this iter — **the gate prompt must forbid modifying tracked files.**
