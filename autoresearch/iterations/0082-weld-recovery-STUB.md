# iter-0082 — R-weld: make the pair judge's review actually collectable

**Status: v2 FROZEN, BUILT, GATED, SHIPPED. 2026-07-28.**
Read § "BUILT + GATED" (last section) first, then § "v2 FROZEN" for the bar it
was scored against. v1 was frozen, built, measured, and **failed its own gate**
on an unsatisfiable conjunct; that record is preserved below and is not amended.
The v1 patch was **not** reused — v2's round measured a false PASS in it. The
shipped implementation is a different one, built against a bar frozen first.

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

## GATE — 2026-07-27. **FAILED. SHIP NOTHING. Product files at HEAD: unchanged.**

**Grok: SHIP. Codex: NOT SHIP. Codex is right on both counts, and both were
reproduced by the orchestrator before adoption.**

### Blocker 1 — a real defect: recovery laundered a frozen negative

`contract_offset()` finds the JSON object *after* a forbidden fence prefix, and
the slice discards that prefix before the fence rule ever sees it. Reproduced:

```
Narration.```json{"id":"first","severity":"HIGH",…}
{"verdict":"NEEDS_WORK"}
```

→ **plain path rejects (N6), recovery path ACCEPTS.** The two paths disagreed on
a frozen negative. My negative suite exercised N6 only as a plain stream — the
suite itself had the hole. Grok saw the same shape and ranked it non-blocking
because it is not a false PASS; **Codex's reading is the correct one**: N6 is a
frozen conjunct, and a path that accepts it fails the bar regardless of severity.

### Blocker 1b — a regression I introduced

A trailing `#` comment after the summary: **HEAD accepts, my version rejected.**
G1 terminates on a later *record*; a comment is ignorable everywhere. My terminal
check ran before the comment skip.

### Both fixed, and the suite now closes the hole

Comments are ignorable wherever they appear; a duplicate summary and a later
record reject separately; recovery refuses a fence token welded to the contract
start. Every plain negative now also runs **through recovery** (`N6r`, `N2r`).
After the fixes: negatives **13/13**, self-test green, **N8 6/6**, 106-capture
sweep **0 regressions / 65 byte-identical**, lint green.

### Blocker 2 — N9, and it is the same mistake I recorded as binding one iter ago

The frozen bar reads *"Anything less does not ship."* **N9 is unmet and
unsatisfiable** — the corpus is gone and no product change can recreate it.
Codex: *"Because the bar was frozen before measurement, corpus loss cannot
retroactively weaken it."* That is correct, and the consequence is that
**this bar can never be met.**

**That is exactly the defect iter-0081 v1 had — a clearance bar conjoined to
something no work in the iter can satisfy — and I recorded "a clearance bar must
not conjoin an independently registered open residual" as a binding lesson, then
made the same class of error in the next iter.** The lesson was too narrow: it
must also read **a bar must not conjoin an UNSATISFIABLE conjunct.**

Codex's assessment of the substitute, adopted: the 106-capture sweep is good
evidence for *plain-stream* non-regression and it caught the real `LOW` bug, but
it contains **zero newly recovered envelope welds** — the novel path whose
losslessness N9 exists to measure. N8's six recovery positives do not cover the
16-recovery / 1-fence-reject / 1-non-EndTurn-refusal spread the lost corpus had.

### Gate integrity note

Codex disclosed that its attempt to run an independent Claude seat failed (that
CLI was not logged in) and **explicitly refused to present its run as a
successful two-engine gate**. Recorded as the honest label it is.

### v2 entry conditions — to be frozen BEFORE re-measuring

1. Replace N9 with a **satisfiable** corpus requirement: a durable, in-repo set of
   real welded envelopes with known-correct expected collections. N8's six are the
   seed; the shape spread (recovery positives, fence rejects, non-`EndTurn`
   refusals) must be rebuilt from real captures, never synthesised into the bar.
2. Carry forward, already measured: negatives 13/13 incl. the through-recovery
   variants, N8 6/6, 106-capture sweep clean.
3. Keep the code as fixed here; the patch is preserved, the tree is not.

### Registered separately — NOT conjoined (three now)

- **R-merge-envelope** — merge never unwraps the envelope, so a collector reject
  leaves `pair_judge: PASS` on the shipped path.
- **R-comment-finding** — pre-existing in HEAD and unchanged here:
  `# {"severity":"CRITICAL"}` + `# SUMMARY PASS` accepts as PASS with zero
  findings, because the commented finding is skipped.
- **R-verdict-default** — `verify-merge-findings.py:94` is
  `VERDICT_RANK.get(verdict, 0)` and **0 is PASS**, so any unrecognised verdict
  string ranks as PASS. The orchestrator first reasoned this was fail-closed and
  **that reasoning was wrong**; the default is what makes it a real vector,
  bounded today only because the findings themselves still rank.

**Orchestrator retractions this round: 2** (the "non-exact verdict is fail-closed"
reasoning; and the claim that the frozen bar was satisfiable).
**Seat claims verified before adoption: 4, all CONFIRMED.**

## v2 FROZEN — 2026-07-27 (R0 + R1; Codex GPT-5.6-sol + Grok 4.5, both executing)

**Status: FROZEN, NOT BUILT. Product files changed: NONE.** Both seats executed
against the live collector and the real merge; neither reviewed prose. Both were
forbidden from touching tracked files, and the tree was verified unchanged after
each round — the operator lesson from v1's R0 held.

### The v1 patch does not survive this round — three measured defects

All four rows reproduced by the orchestrator before adoption. Patched =
the preserved v1 patch (`052bddf..c1506c1`), applied to a throwaway worktree.

| | input (envelope, `EndTurn` unless noted) | HEAD | v1 patch |
|---|---|---|---|
| **A** | fence line, `#` comment, one `INFO`, `{"verdict":"UNKNOWN"}` | REJECT | **ACCEPT** → merge `pair_judge=PASS`, `overall=PASS` |
| **B** | `Narration.```json trailing {…CRITICAL…}` + `NEEDS_WORK` | REJECT | **ACCEPT** |
| **C** | same, fence token with trailing bytes on its own line | REJECT | **ACCEPT** |
| **D** | `Narration.` ⏎ `# example {…CRITICAL…}` ⏎ real `HIGH` + `NEEDS_WORK` | REJECT | **ACCEPT**, findings `['commented','real']` |

The leading narration line in **D** is load-bearing: without it the stream parses
plainly and collects `['real']` only. The promotion requires recovery to fire.

**A is a false PASS the patch introduces and HEAD does not have.** B and C are
frozen negative **N6**'s own shape ("fence token with trailing bytes … must not
become 'ignore arbitrary suffixes'"). D promotes a commented-out example into the
findings record.

**Two distinct mechanisms, not one:**

- **A is the plain path**, not recovery — measured by collecting the bare stream
  with no envelope at all. The exact-fence skip and the `#` skip drop those lines,
  then G3 promotes any severity-less `{"verdict": …}` to a summary, which widens
  the accepted verdict vocabulary past HEAD. Merge then ranks the lone `INFO`
  finding at 0 → `pair_judge: PASS` (`verify-merge-findings.py:117-125`,
  `:165-170`). **The summary verdict is never consulted for `pair_judge`**;
  `rank()`'s unknown→0 default (`:93-94`) is a latent twin, not this mechanism.
- **B/C/D are `contract_offset()`**, which slices at the first parseable object and
  discards the preceding bytes on that line — including a fence token with
  trailing bytes and a `#` that had commented the object out. The v1 fix only
  handled an *exact* fence token immediately adjacent to `{`.

### Seat disagreement, resolved with a named delta

Grok R0 classified B/C/D as a registered residual, on the ground that they push
toward `NEEDS_WORK` and never PASS. Codex ruled that inadmissible: N6 freezes an
input class as rejected, the bar requires N1-N7 conjunctively, and severity cannot
convert a forbidden acceptance into a residual — the same adjudication already
recorded at `0082:246`.

**Grok R1 reversed and named the delta**: its own criterion ("only
`NEEDS_WORK`-ward, therefore residual") was falsified by case A, a false PASS out
of the same lenient package. Adopted: Codex's ruling. This is the v1 gate's own
precedent applied to its successor, not a new rule.

### Decisive criterion for v2 — **path-invariant, support-bounded conservation**

- **Path-invariant** (Codex): every frozen exclusion must hold through *every*
  ingress path — plain stream, envelope-plain, envelope-recovery. A negative is
  not a payload; it is a payload **×** all paths.
- **Support-bounded** (this round): every claim is bounded by the real captures
  that support it. A shape with no surviving real capture is reported
  **uncovered** and never counted as covered.

### Frozen negatives — written before any code

Carried unchanged: **N1-N7**. v1's `N6r`/`N2r` stop being separate cases; the
path-invariance rule below makes them instances, which is why they are deleted
rather than restated.

| ID | payload | required |
|---|---|---|
| **N10** | fence line + `#` comment + a non-verdict-binding finding + severity-less `{"verdict":"<string absent from VERDICT_RANK>"}` | **reject at collect** — scored on the collector's exit and artifacts, never on the shipped run (see the scope note below) |
| **N11** | fence token with trailing bytes — same line as the contract, and on its own line | reject |
| **N12** | a `#`-commented finding | never appears in the collected findings |

**Path-invariance conjunct**: the runner applies **every** negative through all
three ingress paths. A negative that rejects plainly and accepts through recovery
fails the bar — that is exactly how v1 died.

**N10 scope note — this conjunct was repaired before any build, on a verifier
finding, and the repair is itself the third instance of the class this iter
exists to stop.** N10 first read *"…and the run must not report `pair_judge:
PASS`."* **That is unsatisfiable by any in-scope work.** Measured in four
configurations: when the collector rejects it writes no canonical artifact, and
merge then defaults `pair_judge` from `None` to `PASS` on mere stdout presence
(`verify-merge-findings.py:877-878`), while its line-scan sees neither the `INFO`
finding nor a bare `{"verdict": …}` (`:912-917`). Result: `pair_judge=PASS,
overall=PASS` in **4/4** — plain and envelope, bare and full-trigger state. The
only configuration that avoids PASS is stdout-removed-under-reset, which is
verbatim **R-merge-envelope**'s deferred invariant (`0082:157-161`) — a residual
this bar registers as NOT conjoined. So the clause silently conjoined it.

The false PASS is the *motivation* for N10, not a conjunct of it. **Within R-weld's
scope the collector rejecting is the whole of the available fix**, and the
run-level PASS closes only when R-merge-envelope lands. Recorded as an honest
bound, not quietly dropped.

**Positive controls** (each must accept): the legitimate single-contract shape; a
welded preamble recovered; a `#` comment after the summary (HEAD parity — v1
regressed this one).

### Corpus — replaces N9, every row named by a path that exists today

All 11 real captures are vaulted outside session storage at
`~/.local/share/nx01/iter0082-corpus/` with `SHA256SUMS`, because losing the
corpus is what killed N9 and this is the third round of that loss class.

| ID | conjunct | satisfied by |
|---|---|---|
| **C1** | commit the **exact raw bytes** of the real captures + a manifest carrying provenance, shape class, sha256, and the hand-verified expected collection | the 11 vaulted files |
| **C2** | the collector reproduces every expected collection exactly — no finding, severity, or verdict lost, reordered, or changed | run after C1 |
| **C2b** | the real-corpus losslessness claim is **bounded to shape class W1** (grok `--output-format json` envelope, `EndTurn`, narration welded to one `CRITICAL`, terminal severity-less `NEEDS_WORK`). No claim of multi-shape recovery losslessness | honest label |
| **C3** | **uncovered by real data: the fence-wrapped *finding*.** Reported, never synthesised into the corpus, never counted as covered | search scope below |
| **C4** | the corpus must contain the recovery-positive class — without real bytes on the novel path the bar does not clear | 8 welded envelopes |
| **C5** | the **61 git-tracked** plain-stream judge captures: **0 regressions** against HEAD | already in-repo |

**C3's search scope, recorded** — because this is the same claim shape this round
just refuted a seat on. Swept: all 125 on-disk `*judge*.stdout` plus the
non-judge `.stdout` files under `benchmark/` and `.devlyn/`. No fence-wrapped
*finding* found. One tracked capture **does** carry a paired-fence-wrapped
severity-less **verdict** —
`benchmark/ceiling/results/nodeg-20260719g/DR-shape-compound-rules-f25-cart/A1/devlyn-snapshot/runs/rs-20260719T103916Z-60b9f2c446f0/claude-judge.stdout`
— a real, complete, correct judge review that **both HEAD and the v1 patch throw
away** (prose lines precede the fence, so no line parses). It joins the corpus as
a real **reject** row with its reason recorded; this bar does not require
accepting it. C3 therefore holds on the finding-vs-verdict distinction only, and
says so.

**C5's denominator is `git ls-files`, not the disk.** 61 captures are tracked;
125 exist on disk, so **64 are untracked** and cannot be part of a bar that must
stay reproducible from a clean clone — the corpus section's own loss-class rule
applied to itself. The 64 are swept and reported, never scored.

Hand-verified expected collection for all 8 welded envelopes, read off the raw
bytes: exactly one `CRITICAL` finding and `{"verdict":"NEEDS_WORK"}`. The 2
`Cancelled` envelopes must refuse. The raw-stream weld must refuse (see residuals).

**Carried from v1's N8, restated rather than dropped**: the real merge over the
collected artifacts must return `NEEDS_WORK` for all six iter-0081 captures. C2
plus `finding_rank` determinism implies it, but an implied conjunct is a narrowed
conjunct, so it is written down.

**Redaction decided: commit exact bytes, unmodified.** A pattern scan over every
capture returned only field *names* (`inputTokens`, `output_tokens`) — no
credential. `sessionId`/`requestId` are opaque ephemeral ids; `total_cost_usd` and
`modelUsage` are inert to a collector that reads only `text` and `stopReason`.
Grok's proposal to placeholder the ids and drop the metadata was considered and
**rejected**: the corpus's entire value is that it is real, and any rewrite makes
"this is a genuine capture" uncheckable against the vault hashes.

### Root-cause direction — binding on the build, per no-workaround

- The recovery prefix rule must be defined by what the discarded preamble may
  **contain** — narrative bytes only: no fence token, no `#`, no `{` — **not** by
  enumerating forbidden tokens to skip. A token denylist is rejected in advance:
  it is a parser by accretion, and it is what produced B and C.
  **The cut may fall mid-line.** An earlier draft of this directive said "cut at a
  line boundary"; that is measurably wrong and would have made C2/C4 unsatisfiable
  — all 8 real welds have their contract offset mid-line (run1 at byte 173,
  preceded by `…the mandatory anchor command.` with no newline), so a
  line-boundary-only rule recovers **0/8**. Measured before the build, not after.
  The containment rule alone separates the corpus from B/C/D: all 8 real preambles
  are pure narration (no `#`, no fence, no `{`), while B and C carry a fence token
  and D carries a `#`.
- G3 must not widen the summary verdict vocabulary past the verdicts merge knows.
- **Not licensed**: making `INFO` verdict-binding, or changing merge's rank
  default (registered separately, below).

### Placement — subtractive, both seats converged

`benchmark/ceiling/probes/r-weld-0082/` (**not** npm-packed): the corpus, its
manifest, and **one** runner holding every synthetic negative. `lint-skills.sh`
invokes that runner beside the existing collector self-test (`:384`).

`config/skills/_shared/test-collector-negatives.py` is **not created**. `config/**`
is packed (`package.json` `files`), so it would ship to npm users while lint never
runs it and the mirror parity list (`lint-skills.sh:59-88`) never covers it — a
shipped file enforced by nothing.

### Bar

Every negative rejects **on every ingress path**; every positive control accepts;
C1-C5 hold; lint green. Anything less does not ship.

**Satisfiability check — asserted, then FALSIFIED by a verifier, then repaired.**
The first draft claimed this check had been run; N10 proved it had not been run by
execution. After the three repairs above, every conjunct has been satisfied or
shown satisfiable by a command, not by reading. No conjunct depends on an artifact
that does not exist today, and none depends on a future nondeterministic capture.
There is deliberately **no fresh-capture conjunct**: yield cannot be frozen, and
"a fence will appear" is how v1 died. Attempting fresh captures post-freeze is
permitted and adds rows under C1; the bar does not fail if none appear.

### Registered separately — NOT conjoined (four)

- **R-merge-envelope** — merge never unwraps the envelope, so a collector reject
  leaves `pair_judge: PASS` on the shipped path.
- **R-comment-finding** — pre-existing in HEAD: `# {…CRITICAL…}` + `# SUMMARY PASS`
  accepts as PASS with zero findings. **Distinct from N12**, which forbids the
  *promotion* of a commented finding into the findings; this one is a comment-only
  stream yielding PASS with none.
- **R-verdict-default** — `verify-merge-findings.py:93-94` ranks an unrecognised
  verdict as PASS. Latent twin of A's mechanism, not A's mechanism.
- **R-rawstream-weld** — NEW. A real non-enveloped welded capture
  (`.devlyn/grok-judge.stdout`) is still thrown away; the shipped capture path is
  always enveloped (`adapters/grok.md:41-48`), so it is out of this bar's scope.

### Fable 5 verification of the freeze — FREEZE DEFECTIVE, three repairs made

A third seat verified the frozen text itself, adversarially, with execution, and
**found the bar defective**. All three findings were reproduced by the
orchestrator before repair; all three are fixed above, **before any build or
measurement against v2** — this is not a post-hoc amendment of a scored bar.

1. **N10's second conjunct was unsatisfiable and secretly conjoined
   R-merge-envelope** — `pair_judge=PASS` measured in 4/4 configurations. The
   class this iter exists to stop, committed a third time, in the very freeze
   written to stop it. Caught only because the bar was verified before it was
   built against.
2. **"cut at a line boundary" contradicted the corpus** — 0/8 real welds recover
   under it, so C2/C4 would have been unsatisfiable.
3. **"125 tracked" was false** — 61 are tracked, 64 of the 125 on disk are not.

Non-blocking, also repaired: row D's payload needed its narration prefix to
reproduce; C3's search scope is now recorded with the one real fence-adjacent
capture named; v1's N8 merge half is restated instead of implied.

Verified clean and load-bearing: vault 11/11 by hash; A/B/C/D reproduce; A-is-plain-path
confirmed independently; C2/C4 satisfiable against the real bytes (8/8 collect one
`CRITICAL` + `NEEDS_WORK`, 2 `Cancelled` refuse, raw weld refuses); **no frozen
negative requires rejecting any corpus row** — N10-N12 and C2/C4 are jointly
satisfiable; every cited `file:line` checked; N9 still reported UNMET and the v1
record unamended.

### Orchestrator retractions this round — 2

**I attributed case A to `contract_offset` recovery in the R1 packet. That was
wrong** — A is the plain path, measured by collecting the bare stream with no
envelope. Grok caught it by executing; **Codex inherited my framing** and cited the
verdict-rank default for A. The conclusion (A blocks reuse of the patch) is
unchanged; the mechanism is not. **A wrong claim in the seat packet propagates
into a seat's answer** — the packet is evidence and gets the same verification bar
as a finding.

**2. I froze an unsatisfiable conjunct — again.** N10's "the run must not report
`pair_judge: PASS`" clause conjoined R-merge-envelope, which this same document
registers as NOT conjoined, two sections apart. v1 died on an unsatisfiable
conjunct; the lesson was recorded as binding; **I then wrote another one into the
replacement bar.** Two prior seats read the freeze and did not catch it — it took
a verifier pointed specifically at satisfiability. **Binding: a freeze is not
frozen until a seat has tried to satisfy every conjunct by execution.** Writing
"satisfiability checked" is not checking it.

### Seat claims verified before adoption — 7 (6 confirmed, 1 refuted)

Confirmed: B/C accepted through recovery (both seats) · A's false PASS through the
real merge (Codex) · D's commented-finding promotion (both) · A is the plain path
(Grok) · the negatives script prints "13 cases" while asserting 14 (Grok) ·
`test-collector-negatives.py` ships unenforced (Codex).

**Refuted: Grok's "no surviving `Cancelled` capture exists."** Its search used
`*stdout*.json`; the files are `*.json`. Two real `Cancelled` envelopes exist and
are vaulted. A negative existence claim failed to a single counter-example, again.

### Gate integrity note

Codex's R0 run executed a full measurement set and then **the vendor stream
terminated on a content filter before its synthesis was emitted** (`exited code=1`).
Its measurements were kept — they are reproducible and I reproduced them — and its
design position was obtained in a rephrased R1. Recorded as the honest label:
R0 produced data, not a verdict.

## BUILT + GATED — 2026-07-27/28. **SHIP.** Three seats, all executing.

**Grok: SHIP. Codex: NOT SHIP → SHIP with a named delta. Fable: SHIP, no blockers.**
The tracked tree was verified unchanged after every seat round.

### Result against the frozen bar

`test-collector-contract.py` **✓ 110 checks** — 9 negatives across ingress paths,
N12 conservation ×3, 3 fence shapes uniform, 6 positive controls, 12 real captures
(W1 rows also replayed through the real merge), 61 tracked captures byte-identical
to a baseline taken from the pre-change collector. Collector self-test ✓. Lint
**All checks passed**, now including the contract runner. All three mirrors
byte-identical. One product file: **+89/-41**.

**The measured failure this closes**: HEAD rejects all 8 real welded captures;
v2 collects each as one `CRITICAL` + `NEEDS_WORK`, and the real merge returns
`NEEDS_WORK` 8/8. The pair judge's review survives the harness.

### The root-cause shape held

`NARRATIVE_PREAMBLE_BYTES` is an allowlist of what the discarded preamble may
contain, exactly as frozen — Fable computed it as
`{\t,\n,\r} ∪ (0x20-0x7E minus {#, backtick, {}) ∪ 0x80-0xFF`, byte-exact, nothing
extra, nothing missing. High bytes admit UTF-8 narration (Korean preamble recovery
measured). Because recovery can never slice past the first `{`, `#`, or backtick,
mid-JSON slicing and comment consumption are **structurally impossible** rather
than defended against. `VERDICT_RANK`/`finding_rank` are single-sourced from merge
instead of redefined — v1 invented a second definition and broke 4 real captures.

### Codex's NOT SHIP, and why it was overturned

Codex reported a "new false-PASS path": fenced + `#` comment + two `INFO` + bare
`{"verdict":"NEEDS_WORK"}` → collector ACCEPT → merge PASS, where HEAD rejects.
Two measurements retired it:

1. **The behaviour is pre-existing.** HEAD accepts the same shape in its
   `# SUMMARY` spelling and merge reports PASS. The diff adds spellings, not the hole.
2. **On the full shipped path HEAD's REJECT lands on PASS too** — collector writes
   nothing, merge defaults `pair_judge` None→PASS (`verify-merge-findings.py:877-878`).

```
HEAD      collector=REJECT   -> merge pair_judge=PASS  overall=PASS  findings_in_record=0
WORKTREE  collector=ACCEPT   -> merge pair_judge=PASS  overall=PASS  findings_in_record=2
```

Identical verdict; the change **preserves two findings HEAD silently drops**.
Refusing the shape would also have required rejecting frozen **G3**, making the
bar unsatisfiable — a fourth instance of the class that killed 0081 v1, 0082 v1,
and nearly this freeze.

**Codex's named delta, in its words**: *"my prior criterion was collector-local
ACCEPT versus REJECT. The shipped-path measurement falsified my claim that this
created a new false-PASS outcome."*

### Two frozen items Codex found missing — both closed before ship

Lint did not invoke the contract runner, and the runner never invoked merge
(v1's N8 merge half). Both wired; bar and lint re-run green.

### NEW residual — R-summary-verdict-not-merged

The collector writes the judge's verdict to `pair-judge.summary.json`
(`collect-codex-findings.py:315`) and **merge never reads it** — verified by
search: merge touches only `verify.pair*.findings.jsonl`, `*-judge.stdout`, and
its own output `verify-merge.summary.json`. `pair_judge` derives solely from
finding severity (`:165-170`). **A judge that says `NEEDS_WORK` with only
`LOW`/`INFO` findings is reported `PASS`** — the same "harness discards the
judge's conclusion" failure this iter fixes, one layer up. Codex's invariant,
recorded for its own freeze: `pair_judge = worse(summary verdict,
finding-derived verdict)`.

### Also registered, NOT conjoined

- **R-envelope-severity-bypass** — a top-level `"severity"` in the envelope makes
  it parse as a *finding*, bypassing the `EndTurn` gate. HEAD and v2 alike.
- **R-backtick-preamble** — the byte allowlist excludes every backtick, stricter
  than the frozen "no fence token". Measured: 0/8 real welded preambles contain
  one, so the corpus is unaffected, but 25/61 tracked captures contain a backtick
  somewhere, so a future judge narrating with inline code loses its review. Fails
  closed. Both seats: residual, do not relax inside this ship.

### Verifier findings, non-blocking, recorded not fixed

Tier-2 reject rows are checked by exit code only, not reject reason (audited
manually this round). Manifest sha256 is provenance, not a run-time check. Tier 2
compares severity-sequence + verdict, while Tier 3 is byte-exact. Verdict
vocabulary is case-sensitive while severity is case-insensitive — sanctioned by N10.

### What could have gone wrong and didn't

`tracked-baseline.json` could have been generated from the **new** collector,
which would have made the entire 61-capture non-regression tier decorative — the
same class as v1's false "125 tracked". Fable regenerated it from the pre-change
collector and got 0/61 mismatches; the orchestrator reproduced that independently.

### Seat accounting

Orchestrator retractions this round: **0**. Seat claims verified before adoption:
**9** — 8 confirmed (Codex's two missing frozen items, its envelope-severity
bypass, its summary-not-merged invariant; Fable's byte-set computation, baseline
honesty, four claim confirmations), 1 overturned by measurement (Codex's NOT SHIP
blocker). Grok found no defect that survived.
