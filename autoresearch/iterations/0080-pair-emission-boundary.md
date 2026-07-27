# iter-0080 — engine-neutral pair-emission boundary

**Status: REGISTERED-FROZEN 2026-07-26. Not built.** Opened because
**FS-0079-A fired** in iter-0079.

## Freeze record

Five seat rounds across two cross-vendor seats (Grok 4.5 · Codex, with Opus 5
orchestrating): R0 ×2, R1 ×2 (Codex's killed at the report stage; its
substantive deltas recovered from the log per the HANDOFF rule), R2 Codex,
confirmation ×2.

**Both seats' freeze conditions are met and were stated in advance.**

- **Codex — FREEZE.** Verified all five load-bearing sections against the text
  by line range, found no new mechanical hole, and confirmed the
  acknowledged non-recovery lazy-`EndTurn` residual is not exploitable through
  the amended recovery path. Its R2 had set the condition explicitly: *"If
  variant (iv) fails measurement, keep Grok non-certified"* — variant (iv)
  measured 3/3.
- **Grok — NOT FREEZE with a single named edit**: the build-scope B2 row still
  read `HOME="$NEUTRAL"` + "variant open", contradicting § B2 RESOLVED,
  P-0080-C, and gate part 3 — *"until that row matches the resolved recipe, the
  freeze text freezes a contradiction."* **Edit applied**, plus the superseded
  three-option comparison block marked SUPERSEDED.

**Honest sequencing note**: Codex's FREEZE was given on the 784-line text, i.e.
*before* that consistency fix (+4 lines). The fix removes a contradiction and
implements Codex's own R2 edit #1 ("replace the open B2 choice with variant
(iv)"), so it moves the document toward, not away from, the text Codex approved.
No substantive change was made after either seat's verdict.

**Orchestrator claims retracted during this iter: 5.** KS-1 (preamble locus) ·
"structurally perfect" schema PASS (the schema had in fact *failed*) · Finding
3's process-only scope · the P3 licensing read · `HOME` as a "strict improvement,
not a trade". Every one was caught by a seat, or by a control a seat demanded.
**Seat claims refuted on verification: 1** (`allocator.py` line count).
**False-PASS paths constructed by a seat that no other party saw: 1** (Codex's
welded-prose + INFO-finding + PASS bypass, built from two separately-measured
real behaviours of this engine).

**Product files changed: none.** Build is the next step, not part of this
registration.

## Why (pre-flight 0)

iter-0079 shipped the N-model pair wiring and proved grok is reachable,
isolated, probe-capable and fail-closed — but its emission dimension recorded
**VALID-NEGATIVE**. Two measured defect classes, both engine-behaviour, neither
patched inline (FS-0079-A's frozen disposition):

1. **INFO pseudo-finding on a clean PASS.** 2 of 3 clean-fixture runs emitted
   `{"id":"pair-judge-pass","severity":"INFO",…}` *alongside*
   `# SUMMARY {"verdict":"PASS"}`, violating P-0079-B's "empty findings list"
   criterion. Pipeline impact is nil — `verify-merge-findings.py:912-917`
   excludes INFO from the verdict-binding set — but the frozen criterion failed.
2. **Narration preamble welded to output line 1.** On runs where grok announced
   an action, it prepended e.g. `Running the mandatory dominance-loss probe…`
   with **no newline** before the first JSON object, so a strict parser rejects
   line 1. This is what falsified P-0079-F despite grok executing the mandatory
   probe correctly and finding the seeded CRITICAL defect. Reproduced in both
   the P-B pilot and the P-F run.

## Sequencing — knob sweep FIRST (binding)

**Arm order is not negotiable and exists because of a named prior mistake.** The
iter-0079 remedy sketch jumped straight to "prompt delta or collector rule",
which is structurally the same omission as that iter's retraction #4 ("zero-MCP
is unachievable" — asserted before searching the vendor's documented knobs, and
two documented knobs then closed it).

1. **Vendor output-format knob sweep.** Search the grok CLI's documented surface
   for an output-format / no-preamble / structured-output control before
   concluding any devlyn layer must change. A negative result here is a
   completed-search receipt, not an assumption.
2. **Only if (1) is empty**: A/B a prompt delta in `adapters/grok.md`, gated by
   `adapters/README.md:56-59` condition 3 (measured lift over the canonical body,
   not preference).
3. **Pre-committed fallback, frozen BEFORE the A/B result is seen**: a strict
   recovery rule at the collector boundary — engine-neutral, never grok-named.
   Pre-committing it is what stops step 3 from becoming a post-hoc relaxation.

## Step 1 — knob sweep (PRE-REGISTERED 2026-07-26, predictions before runs)

### KS-0 — documented-surface receipt: **step 1 is NOT empty** (answered before any run)

The grok CLI documents an output-format surface. Receipts, opened at citation time:

| Knob | Documented behaviour | Source |
|---|---|---|
| `--output-format <plain\|json\|streaming-json>` | `json` = "A single JSON object emitted after the response completes: response text, stop reason, session ID, request ID" with fields `text`, `stopReason`, `sessionId`, `requestId` | `~/.grok/docs/user-guide/14-headless-mode.md:118-160`; `01-getting-started.md:223` |
| `--json-schema <SCHEMA>` | "JSON Schema for structured output. When set, the model is constrained to produce JSON matching this schema. Implies `--output-format json`." | `grok --help` (0.2.112) — not in the user-guide corpus |
| (property) | "Update messages go to **stderr**. Stdout stays clean for `--output-format json`." | `14-headless-mode.md:561` |

This closes the sequencing obligation's step 1 as **positive**, so steps 2 and 3
are not yet licensed. The remaining question is behavioural, not documentary.

### Pre-registered predictions (stated before the first run)

- **KS-1 (preamble locus)** — the welded preamble is a CLI-rendered *update*
  line, not model assistant text; under `--output-format json` it does not
  appear in `.text`. **Falsifier**: any json-arm run whose `.text` begins with
  narration prose while grok narrated an action.
- **KS-2 (collector compatibility)** — raw `--output-format json` stdout is
  **rejected** by `collect-codex-findings.py` unchanged (the envelope object
  carries no `severity`), so a knob-only fix still needs an unwrap step
  somewhere. **Falsifier**: collector exits 0 on the raw envelope.
- **KS-3 (schema arm)** — under `--json-schema`, `.text` is a schema-conforming
  JSON document with zero narration on 2/2 runs. **Falsifier**: any
  non-conforming or narration-bearing `.text`.
- **KS-4 (control — the honesty gate)** — the plain arm **reproduces** the
  iter-0079 defect: ≥1 of 2 runs welds a preamble to line 1 and the collector
  exits non-zero. **Falsifier**: 2/2 plain runs parse clean → the defect is not
  reproducible at this n and no fix is justified until the control n grows.

Instrument: fixture reproduces the P-0079-F condition (priority ordering +
rollback ⇒ the mandatory dominance-loss probe ⇒ a forced tool action, which is
the only condition under which the preamble was ever observed). Prompt rebuilt
from `verify.md`'s pair-JUDGE contract with **no anti-preamble clause**, same
discipline as the valid P-0079-B re-measure. Isolation = the `adapters/grok.md`
measured recipe verbatim.

### MEASURED 2026-07-26 — results (raw, after the predictions above)

Instrument: `scratchpad/emission-sweep/` (fixture = 20-line priority allocator
with one seeded CRITICAL: input-order iteration instead of priority-first;
`probe.py` = the spec's backticked anchor). grok 0.2.112, `grok-4.5`,
effort medium unless noted. Isolation = `adapters/grok.md` recipe verbatim.

**KS-4 (control) — CONFIRMED, 2/2.** The plain arm reproduces the iter-0079
defect exactly: line 1 = `I'll statically review the spec and implementation…{"id":"V-001","severity":"CRITICAL",…`
— narration welded to the first JSON object with no separator. Collector rejects.
The defect is real and reproducible, so a fix is licensed.

**KS-1 — FALSIFIED.** The preamble is **model assistant text, not a CLI update
line**. Under `--output-format json` it survives *inside* `.text`:
`"text": "I'll statically review …without running any commands.{\"id\":\"V1-priority-order\",…"`
(`out/sjson-2`). Measured 1/2 on the static route and again in two minimal
repros (`"I'll read that file and count its lines.LINES=20"`). The doc sentence
`14-headless-mode.md:561` ("update messages go to stderr") is true and
irrelevant — this narration is not an update message. **What the knob does buy
is real but narrower than predicted**: stdout line 1 is now always `{` because
the envelope wraps everything, so the *transport* is preamble-proof; the
preamble merely relocates into a field.

**KS-2 — CONFIRMED.** Raw `--output-format json` stdout is an envelope
(`text`, `stopReason`, `sessionId`, `requestId`, `usage`, …) carrying no
`severity`, so `collect-codex-findings.py:60-62` rejects it. A knob-only fix
still needs an unwrap step.

**KS-3 — FALSIFIED, and on a dimension the emission criterion does not
measure.** `--json-schema` gives *perfect* emission (3/3 parse-clean, first
char `{`, zero welded prose) and **worthless judgments**:

| Run | turns | Outcome |
|---|---|---|
| `sschema-1` | **1** | **zero tool calls** — never read spec or implementation; hallucinated `"line":71` findings about "seats", "journal entries", `InsufficientCapacityError` in a **20-line file** with none of those |
| `sschema-2` | **1** | **zero tool calls** — same class, `"line":48`, "mutates seats and writes journal entries" |
| `sschema-3` | 2 | tool use restored, but narration **laundered into a structurally-valid INFO pseudo-finding**: `{"id":"static-review-start","severity":"INFO",…,"summary":"Starting static review…"}` — iter-0079's defect class 1, now schema-shaped |
| `schema-1` (probe route) | 1 | **stop=`Cancelled`** yet emitted `{ "findings": [], "verdict": "PASS" }` — a **structurally perfect, verdict-binding FALSE PASS on a run that did no work**, against a fixture carrying a seeded CRITICAL |

The `schema-1` row is the disqualifier. **Stated precisely, so the conditional
is not lost**: the raw envelope is rejected by `collect-codex-findings.py:60-62`
today, so this is not a false PASS *at present*. It becomes one the moment any
unwrap step is added — and every path that makes `--json-schema` usable at all
requires exactly that unwrap. `collect-codex-findings.py:64-65` accepts
empty-findings + `verdict:PASS` as a clean pass, so an unwrapped `schema-1`
lands as a verdict-binding pair PASS produced by a run with `stopReason:
Cancelled` and zero work done. Combined with the separately named
`verify-merge-findings.py:877-878` default-to-PASS residual, the arm's own
success condition is what opens the false-PASS path. **`--json-schema` is
REJECTED for the judge seat.** Structured-output constraint suppresses the
tool-use loop the pair judge exists to perform.

By contrast the `--output-format json` arm kept `turns=2` and found the **real**
seeded bug both times (`priority-order-not-applied`, `allocator.py:13`).

### Finding 1 (unpredicted, dominant) — chained-command denial destroys the review

The 6 probe-route runs all died at turn 1 with 84-90 bytes of preamble and
**exit 0**. Root cause, read off the session transcript (`grok export`), not
inferred:

```
## Tools
- Read: …/spec.md
- Read: …/allocator.py
- Execute: python3 …/probe.py; echo "EXIT:$?"   (Run mandatory dominance-loss probe)
```

grok appends `; echo "EXIT:$?"` because `verify.md:177-179` instructs the judge
to compare "stdout/stderr/**exit**". Under `--permission-mode dontAsk` that
chained command is denied — `cancellationCategory: "PermissionCancelled"` — and
the **entire turn is cancelled**. Isolated 3-cell control:

| Cell | Command shape | `--allow` coverage | Result |
|---|---|---|---|
| H | `python3 …probe.py; echo "EXIT:$?"` | **both** segments allowed | **Cancelled** |
| I | same | python3 only | **Cancelled** |
| J | `python3 …probe.py` (unchained) | python3 only | **EndTurn** — probe ran, and grok reported ``Exit code: `0` `` anyway |

So this is **not** an allowlist-scoping problem: a chained command is
unauthorizable under `dontAsk` *even when every segment carries an explicit
allow rule*. iter-0079 characterized the adjacent hazard as a template
defect (` *` vs bare form); the measured bound is stronger and the shipped
`Bash(<anchor>)` template cannot satisfy `verify.md`'s own exit-comparison
clause. Cell J also shows the capability is not lost — only the chained shape.

**This, not the preamble, is the dominant failure mode on the probe route**
(7/7 cancellations vs the preamble's 2/2 on the static route).

#### Finding 1 — completed search on the allow-rule side (cells H-N)

Grok's R0 seat cited `22-permissions-and-safety.md:325-328`, which documents the
opposite of the measurement: *"`allow` rules are checked against the whole
command string only. `Bash(git *)` therefore auto-approves `git status && rm -rf /`"*.
If that held, `Bash(python3 *)` would authorize the chained probe. It does not.
Full cell table, all under `--permission-mode dontAsk`:

| Cell | Command shape | `--allow` | Result |
|---|---|---|---|
| J | `python3 …probe.py` | prefix | **EndTurn** — probe ran; grok reported ``Exit code: `0` `` unprompted |
| H | `…probe.py; echo "EXIT:$?"` | both segments | Cancelled |
| I | `…probe.py; echo "EXIT:$?"` | python3 prefix | Cancelled |
| K | `…probe.py; echo done` (no `$?`) | python3 prefix | Cancelled |
| L | `…probe.py && echo done` | python3 prefix | Cancelled |
| M | `…probe.py; echo "EXIT:$?"` | python3 prefix | Cancelled |
| N | `…probe.py; echo done` | **exact full-string rule** + prefix | Cancelled, `cancellationCategory: "PermissionCancelled"` |

**Conclusion, now a completed search rather than an absence-of-memory claim**
(scope narrowed per R1 — a negative existence claim must not outrun its cells):
under `dontAsk`, **every allow shape tested — prefix, dual-segment, and exact
full-string for the chain itself — produced `PermissionCancelled`.** Other
permission modes are untested and unclaimed. The
`$?` expansion is not the trigger (cells K/L). This is a **vendor
doc-vs-behaviour conflict**, recorded as such: the documented footgun (whole-string
allow approving chains) does not reproduce; actual behaviour is *safer* than
documented and *silently destroys the review*. The fix therefore cannot live in
the allowlist — it must remove the chained shape from the judge's output.

### Finding 2 (unpredicted) — the json knob makes the silent failure visible

`--output-format json` reports `stopReason: "Cancelled"` and (with
`--debug-file`) `cancellationCategory: "PermissionCancelled"`. Today that same
failure reaches the pipeline as **exit 0 with a prose-only stdout**, which the
collector rejects with a misleading "invalid JSONL" error. This is the first
machine-readable signal for the review-destroyed class that `adapters/grok.md`
currently handles only in prose.

### Finding 3 (unpredicted) — the isolation receipt's MCP row is wrong at process level

Under the **full** iter-0079 recipe (`GROK_CLAUDE_MCPS_ENABLED=false` and the
rest), a headless run creates:

```
$ISO_HOME/logs/mcp/MCP_DOCKER.stderr.log   (2411 B — "Reading secrets [github.personal_access_token …]")
$ISO_HOME/logs/mcp/pencil.stderr.log       (56 B — "Starting server in stdio mode")
$ISO_HOME/logs/mcp/pyx-memory.stderr.log   (0 B)
```

Reproduced 2/2, including on a minimal `Reply with exactly: OK` prompt with
`--tools read_file,grep,list_dir` (no shell). `grok inspect` in the same home
reports all three as `[claude] [disabled]`, and the ACP initialize response
carries `"mcpServers":[]` — so **tool callability remains PASS**, unchanged.
What is false is the *process-level* reading of the isolation table's
"No MCP reachability" row: the servers are **launched**, and `MCP_DOCKER`
actively attempts to read a GitHub personal access token during a judge run.
`grok inspect` alone does **not** create these logs, so the launch is
attributable to the headless run. The 0079 receipt measured callability and
generalized to reachability; the build-phase re-certification must measure
process launch as its own invariant.

## R0 — Grok seat (2026-07-26), and what the orchestrator verified

Run under the `adapters/grok.md` recipe **plus Finding 2's `--output-format
json`**, which is how the seat's own liveness was certified rather than assumed:
`stopReason=EndTurn`, `num_turns=8` — a real tool-using read, not a truncated
review. (First live use of Finding 2 as an instrument.)

**Verdicts**: strong-agree P1 (reject schema), agree P2 (adopt json **with a
frozen fail-closed unwrap contract**), agree-with-amendment P3, agree-with-
reframing P4, agree P5-must-be-corrected.

**Three artifact corrections the seat raised. Orchestrator re-opened each; two
adopted, one refuted** — a seat correction is a claim like any other:

| Seat claim | Verified? | Disposition |
|---|---|---|
| `schema-1` also carries `structuredOutput: null` + `structuredOutputError: "model did not produce structured output"` — so the schema *failed* and free-form `.text` still carried PASS | **CONFIRMED** | **ADOPTED — strengthens the finding.** The arm can mint a pass-shaped payload *without satisfying the schema at all*. My "structurally perfect" wording was wrong and is corrected above |
| `sschema-3`'s `.text` is **two concatenated JSON documents** (`…}{…`), not one object with an extra INFO finding | **CONFIRMED** (`'}{' in text` → True; doc 1 = INFO `static-review-start` + `NEEDS_WORK`, doc 2 = the real HIGH finding) | **ADOPTED — worse than described.** Narration was laundered into a whole extra document |
| `allocator.py` is 21 lines, not 20 | **REFUTED** — `wc -l` = 20, `splitlines()` = 20 | **REJECTED.** The original claim stands; the hallucinated `line:48`/`line:71` findings remain out-of-file by the same margin |

**Substantive reframings adopted from the seat:**

1. **P4 is not the false-PASS axis.** Under this iter's own decisive criterion,
   chain-cancel lands as **BLOCKED** (collector rejects → no canonical findings
   → `verify.pair.emission-contract`), not as an unjustified PASS. It is a
   *review-destruction / seat-fitness* defect. It stays a **pin gate**, not the
   emission core. My P4 framing ("higher severity" full stop) conflated two
   failure classes; the seat's split is correct.
2. **P3's licensing was sloppy.** The STUB's sequencing licenses step 2 only if
   step 1 comes back **empty**. It came back *positive but residual*. Reading
   that as "licensed" would smuggle in exactly the jump the rule was written to
   prevent. The honest move is to **amend the sequencing rule explicitly**
   ("measured-positive knobs leaving a behavioural residual license step 2/3"),
   not to reinterpret the original text. Adopted.
3. **The A/B baseline for any prompt delta is the json arm, not plain.**
4. **P5 must not be a silent residual.** The isolation table splits into
   *callability* (PASS, unchanged) and *process-launch* (FAIL/RESIDUAL), and the
   build must sweep for a suppression knob before asserting impossibility —
   the explicit 0079 zero-MCP mistake class. The seat would not emission-certify
   while the adapter implies full isolation without naming the residual.

### Finding 3 — RESOLVED, a knob exists (`HOME` override)

The R0 seat's P5 instruction ("search for a suppression knob before asserting
impossibility — mirror the 0079 zero-MCP mistake") was executed and **found
one**. Sweep, in order:

| Attempt | MCP processes launched? |
|---|---|
| `GROK_CLAUDE_MCPS_ENABLED=false` (env form — the shipped recipe) | **YES** — 3 servers, 2/2 runs |
| `[compat.claude] mcps = false` + `skills/hooks/agents/rules = false` in the ephemeral `config.toml` (documented config form, `07-mcp-servers.md:214`, `05-configuration.md:344-348`) | **YES** — same 3 servers |
| **`HOME="$NEUTRAL"`** added to the recipe | **NO — `logs/mcp/` is never created**, 2/2 |

Root cause: the vendor knobs suppress *registration* (`grok inspect` →
`[disabled]`, ACP → `"mcpServers":[]`) but the scan of `~/.claude.json` is keyed
off `$HOME`, which `GROK_HOME` does not relocate. Pointing `HOME` at the neutral
dir removes the source file from reach, so nothing is scanned and nothing spawns.

**Functional control (the knob must not buy isolation by breaking the seat)**:
with `HOME` overridden, a read + unchained-probe run returned
`stopReason=EndTurn`, `num_turns=2`, correct file read and real probe output —
auth still resolves from `GROK_HOME`, and the neutral `HOME` received zero
writes.

> **RETRACTED**: this section first concluded "a **strict improvement**, not a
> trade." R1 named a specific untested failure mode and it **measured true** —
> the control above never exercised home-relative *product* paths. It IS a
> trade; see § B2 variant for the measurement and the third arm that avoids it.

This turns P5 from "correct the receipt and name a residual" into "close it."
The isolation table still splits into callability vs process-launch rows, but
both can now read PASS under the amended recipe.

*Second time this iter that the search-before-asserting rule paid: the knob
sweep (step 1) and this one. Both were positions the orchestrator was ready to
close as "no knob exists."*

**Incidental**: grok reports `LINES=21` for the 20-line `allocator.py` in two
independent runs — the same off-by-one behind its refuted R0 "21 lines"
correction. Mechanism identified, claim still refuted.

## R0 — Codex seat (2026-07-26), two material deltas, both upheld

Run: `codex-monitored.sh -s read-only -c model_reasoning_effort=xhigh`. The
process was killed at the report stage after ~10 min; **the substantive verdict
landed on disk** and was recovered from the log (the HANDOFF's
killed-at-report-stage rule applied, not a re-run).

### Delta 1 — my mechanism claim was confounded. Control run resolves it.

Codex: *"`--json-schema` should still be rejected, but the claimed causal
mechanism is not proven: the schema and non-schema arms used different output
prompts, and one schema run did use tools."* **Correct** — `prompt-schema-static.txt`
and `prompt-jsonl-static.txt` differ in their OUTPUT CONTRACT section, so knob
and prompt varied together. The missing cell was run:

| Arm | Prompt | Knob | turns |
|---|---|---|---|
| `sctrl-1/2/3` | schema-**shaped** | **none** (`--output-format json`) | **2, 2, 2** |
| `sschema-1/2/3` | schema-shaped | `--json-schema` | **1, 1, 2** |

**The prompt is excluded; the knob is the cause.** The honest final wording,
incorporating Grok's parallel objection: `--json-schema` **degrades** the
tool-use loop (2/3 zero-tool-call vs 0/3 matched control) rather than always
suppressing it. REJECT stands, and now stands on a deconfounded mechanism plus
the false-PASS shape, which was never confound-dependent.

### Delta 2 — the isolation defect is far worse than Finding 3 stated. **CERTIFICATION BLOCKER.**

Codex: *"the MCP residual is not process-only: the preserved session shows three
MCP servers connected, 65 tools enumerated, and their instructions injected into
the judge conversation despite `grok inspect` labeling them disabled."*

**Verified by the orchestrator in the preserved session**
(`$ISO_HOME/sessions/…/019f9d35-…/`):

- `events.jsonl` — three `mcp_server_connected` records: `pencil` (9 tools),
  `MCP_DOCKER` (**41** tools incl. `create_pull_request`, `push_files`,
  `merge_pull_request`, `create_or_update_file`), `pyx-memory` (**15** tools
  incl. `store_memory`, `delete_memory`). **65 tools connected.**
- `chat_history.jsonl` line 3 — a `<system-reminder>` injected into the judge's
  conversation: *"MCP servers connected: MCP_DOCKER (41 tools), pencil (9 tools): …,
  pyx-memory (15 tools): Use pyx-memory for durable memory across sessions,
  **proactively — do not wait to be told**…"*

My Finding 3 said "processes launch but tools are not callable." That was
**understated**: the servers *connect*, their tools are *enumerated*, and their
instructions — including a directive to proactively write memory — are *injected
into the judge's context*. My `"mcpServers":[]` evidence came from the ACP
**initialize** response, which is the state *before* MCP init completes; I
measured the wrong moment.

**This also solves an open iter-0079 mystery.** That iter recorded that "the same
recipe self-reported `MCP_NOT_CALLABLE` and `MCP_CALLABLE` on different runs;
only the behavioural attempt settled it." Both self-reports were honest: the seat
*saw* the injected announcement (→ CALLABLE) but could not invoke it because
`--disallowed-tools use_tool,search_tool` removed the invocation path (→ NOT
CALLABLE). The reminder's own tail gives it away — *"you MUST call `` first"*,
with an **empty tool name**, because the tool it names was removed.

### The fix holds at the escalated level

The `HOME` override was re-tested against Codex's stronger bar, with the session
preserved:

| Signal | Shipped recipe | `HOME="$NEUTRAL"` added |
|---|---|---|
| `mcp_server_connected` events | **3** | **0** |
| tools enumerated | **65** | **0** |
| `MCP servers connected` system-reminder in `chat_history.jsonl` | **1** | **0** |
| `$ISO_HOME/logs/mcp/` | created | never created |
| functional path | — | `EndTurn`, tool use intact, auth intact |

So Delta 2 escalates the severity and Finding 3's remedy still closes it. The
isolation row is re-stated as three separate invariants — **callability**
(already PASS), **connection/enumeration**, and **context injection** — because
the 0079 receipt collapsed all three into one and the two new ones were failing
silently.

## Three-way convergence (Opus 5 orchestrator · Grok 4.5 · Codex)

| Position | Grok | Codex | Resolved |
|---|---|---|---|
| P1 reject `--json-schema` | agree; "degrades, not suppresses" | agree; mechanism unproven | **REJECT**, mechanism deconfounded by `sctrl`, wording = *degrades* |
| P2 adopt `--output-format json` | agree **iff** frozen fail-closed unwrap contract | (not reached before kill) | ADOPT with Grok's 5 unwrap rules frozen pre-build |
| P3 step 2/3 licensing | amend the rule, don't reinterpret it | — | **AMEND** explicitly |
| P4 chain denial | separate class; BLOCKED not false-PASS; fix by prompt, not allow-widening | — | Accepted; **pin gate**, not emission core; search completed (cells H-N) |
| P5 isolation | correct the receipt; search for a knob first | **certification blocker** — 65 tools + context injection | Escalated to blocker, **then closed** by `HOME` override |

**Orchestrator claims retracted this iter: 4.** KS-1 (preamble locus);
"structurally perfect" schema PASS (schema had *failed*); Finding 3's
process-only scope; the P3 licensing read. Every one was caught by a seat or by
a control the seats demanded. One seat claim was refuted on verification
(`allocator.py` line count).

## Correction inherited from iter-0079 (do not repeat)

For defect class 1 the failing instrument is the **frozen P-B criterion**, NOT
the collector — `collect-codex-findings.py` already exits 0 on INFO+PASS. A
follow-up drafted from 0079's original remedy sketch would patch code that is not
broken. Re-freezing the clean-route criterion against the verdict-binding set is
a legitimate option **as a fresh freeze here**; it would have been a retroactive
relaxation inside 0079.

## Required controls

- claude and codex default-route behaviour unchanged (unpinned
  `pair_judge_priority` still resolves the binary complement).
- Severity preservation: no fix may drop or rewrite a real finding's severity.
- Malformed / truncated / empty stdout must still fail closed to
  `verify.pair.emission-contract`.

## Related, deliberately NOT folded in

`verify-merge-findings.py:877-878`'s default-to-PASS — iter-0079's separately
named residual, where three failure paths converge on a false PASS. It is
engine-neutral pipeline-wide scope and carries its own registration. Do not
absorb it here without a decision.

## REGISTRATION — FROZEN 2026-07-26

Grok R1 returned six named deltas (`DELTA-R1-1..6`) plus two overclaim
corrections — **all eight adopted**, three after fresh measurement. Codex R2
returned four required edits — **all four adopted**, one after fresh
measurement. Both seats then confirmed against the resulting text (see
§ Freeze record).

### Amended sequencing rule (supersedes the STUB's "only if (1) is empty")

> A measured-positive knob sweep that leaves the **named behavioural residual —
> a narration preamble welded, without a separator, to the first content bytes
> of `.text` under `--output-format json`** — licenses steps 2 and 3. Same
> anti-post-hoc discipline: the step-3 fallback is frozen before any A/B result
> is seen.

Reason for the amendment, stated so it cannot be re-read as a loophole: step 1
returned two documented knobs, one adopted and one rejected on measurement, and
the welded preamble survives both. The original text only anticipated an empty
step 1. **The residual is named, per `DELTA-R1-1`'s companion point**, so a
future iter cannot re-license a prompt delta for unrelated discomfort.

### Build scope

| # | File | Change | Closes |
|---|---|---|---|
| B1 | `adapters/grok.md` `## Invocation` | add `--output-format json`; **never** `--json-schema` + certification note recording the measured false-PASS shape | KS-2/KS-3 |
| B2 | `adapters/grok.md` `## Invocation` | **variant (iv), CLOSED**: add `HOME="$NEUTRAL" ZDOTDIR="$NEUTRAL"` to the env block **and** create `$NEUTRAL/.zshenv` containing `export HOME=<real home>`, so grok's host scans run neutral while probe shells recover the real home. No seed allowlist. Measured 3/3 — see § B2 RESOLVED | Delta 2 (65 tools + 2 context injections) + evidence fidelity |
| B3 | `collect-codex-findings.py` | engine-neutral envelope pre-pass + fail-closed `stopReason` gate (Grok's 5 rules, frozen below) | Finding 2 |
| B4 | `verify.md` pair-JUDGE contract | **scoped** (`DELTA-R1-5`): the mandatory dominance-loss **anchor** runs as one argv vector with no shell chain operators, and chains used *only to re-capture exit status* are forbidden because tool results already carry it. **Not** a general ban on compound shell or on multi-step probes issued as separate tool calls | Finding 1 |
| B5 | `adapters/grok.md` certification prose + `engine-doctor.sh` note | restate isolation as three invariants (callability / connection+enumeration / context injection) | 0079 receipt correction |

**Frozen unwrap contract (B3) — written before any code:**
1. Success allowlist for `stopReason` is the exact string `"EndTurn"` **only**,
   case-sensitive, matched as the vendor emits it (`"EndTurn"` / `"Cancelled"`
   observed in artifacts); anything else, including unknown values → non-zero
   exit, no canonical findings.
2. `text` must be a string; missing/null → reject.
3. Only `.text` is fed to the existing line collector. Never synthesize findings;
   never map a missing summary to PASS.
4. The envelope object itself must never be accepted as a finding
   (`collect-codex-findings.py:60-62` already enforces this; keep it).
5. **Frozen detection predicate** (`DELTA-R1-3` — rule 5 was previously
   untestable): stdout is treated as an envelope **iff** it parses as a *single*
   top-level JSON object whose key set includes all of
   `{text, stopReason, sessionId, requestId}` **and** has no top-level
   `severity`. Anything else takes the existing line path, unchanged.

**Acknowledged hole this does NOT close** (`DELTA-R1-3` companion): B3 blocks the
*Cancelled*-shaped false PASS. It does **not** block a **lazy `EndTurn` PASS** —
`EndTurn` + `# SUMMARY {"verdict":"PASS"}` with zero work is still a legal clean
pass at `collect-codex-findings.py:64-65`. That is the same class as the
out-of-scope `verify-merge-findings.py:877-878` residual and is named here
rather than silently inherited.

**Self-tests, TIERED** (`DELTA-R1-4` — the flat list pre-committed a
self-contradiction, since tier 1's "welded rejected" is exactly what step 3 is
frozen to recover):

- **Tier B3-strict** (ships with B3): raw envelope rejected · `Cancelled`+PASS
  text rejected · unknown `stopReason` rejected · `EndTurn`+valid JSONL accepted ·
  plain multi-line JSONL unchanged · welded-preamble `.text` rejected ·
  dual-document `.text` (the `sschema-3` `…}{…` shape) rejected · `EndTurn` +
  empty findings + PASS summary **accepted** (documents the intentional clean
  path, so a later change cannot silently close it).
- **Tier B3+recovery** (ships only with step 3): welded-preamble `.text` carrying
  a verdict-binding finding + `NEEDS_WORK` **accepted**, preamble bytes
  discarded, findings/severities identical to the un-welded control ·
  dual-document still rejected · **welded prose + INFO-only finding + PASS
  summary REJECTED** (Codex R2's constructed bypass — this is the tier's
  load-bearing negative test) · welded prose + `# SUMMARY PASS` with no findings
  rejected · everything in tier B3-strict except the welded row unchanged.

### Frozen predictions

- **P-0080-A (unwrap fail-closed)**: replaying `out/schema-1` (`Cancelled` +
  `{"findings": [], "verdict": "PASS"}`) through B3 yields a non-zero exit and
  **no** canonical findings file, 3/3. *Falsifier*: any PASS.
- **P-0080-B (no default-route regression)**: with `pair_judge_priority` unset,
  claude↔codex resolution is unchanged and **identical claude/codex stdout
  inputs produce identical canonical outputs** — *not* "the collector file is
  byte-unchanged", which B3 makes impossible (`DELTA-R1-2` gloss);
  `collect-codex-findings.py --self-test` green. *Falsifier*: any output diff on
  a replayed real codex/claude stdout.
- **P-0080-C (isolation + evidence fidelity, five invariants)**: under B2 =
  variant (iv), a judge run produces 0 `mcp_server_connected` events, 0
  enumerated MCP tools, 0 `MCP servers connected` reminders, **0 `The following
  skills are available` reminders**, no `$ISO_HOME/logs/mcp/`, and **no host
  `~/.zshenv` error in probe output**, while `Path.home()`/`.gitconfig`/`.npmrc`
  match the direct baseline and `stopReason=EndTurn` with real tool use — 3/3.
  *Falsifier*: any non-zero count, any probe-visible host-shell error, any
  home-path divergence from baseline, or a functional regression.
- **P-0080-D (unchained probe)**: under B4, the mandatory dominance-loss probe on
  the seeded fixture completes `EndTurn` with the correct CRITICAL, 3/3, with the
  allow rule scoped to the bare anchor (**no** `echo *`, no always-approve).
  *Falsifier*: any `PermissionCancelled`.
- **P-0080-E (emission residual)**: after B1-B4, the welded preamble rate is
  measured on a forced-tool route at n≥6. This prediction states **no** pass bar
  — it is the A/B baseline for step 2. Recording a bar before the step-2 delta
  exists would be the retroactive-relaxation trap 0079 fell into.
  **`DELTA-R1-2` closes the gate hole this opens**: A-D passing plus E merely
  *measured* must NOT be read as emission-certified. See the amended closing
  gate — building B1-B4 alone never lifts the `not emission-certified` note.

### Pre-committed step-3 fallback (frozen BEFORE any A/B result) — **REWRITTEN per `DELTA-R1-1`**

**The first draft was incapable of clearing the residual it was frozen to
clear.** It said "scan forward to the first *line* that is valid finding JSON or
`# SUMMARY`". The measured weld is **same-line** — `I'll read … review….{"findings":[…]}`
with no newline — so *no line* parses, recovery no-ops, and the residual stands
while the fallback could still be reported as "implemented". Grok's R1 caught
this; it is the single most consequential catch of the round.

Rewritten and frozen: after the `stopReason` success gate passes, the collector
may scan `.text` **forward by bytes** to the first offset at which either a
complete finding JSON object or a `# SUMMARY ` token begins, and discard only
the strictly-preceding bytes. Constraints, all binding:

- Recovery never synthesizes a verdict, never reorders findings, never alters
  severity.
- A recovered stream yielding no legal findings/summary contract still rejects.
- **Dual-document `.text` (`…}{…`, the `sschema-3` shape) still rejects** — the
  byte scan must not be usable to silently pick one of two documents.
- **Recovery may never produce PASS at all** (Codex R2, Q2 — strengthened from
  the weaker "no summary-only PASS" rule, which it broke). A recovered stream is
  admissible **only** if it carries at least one **verdict-binding** finding
  (CRITICAL/HIGH/MEDIUM/LOW) *and* a `NEEDS_WORK` summary consistent with it.
  Anything else — including `INFO`-only findings with a PASS summary — rejects.

  **Why the weaker rule failed, and why this is not hypothetical.** Codex
  constructed the bypass:

  ```json
  {"text": "I'll inspect…{\"id\":\"review-start\",\"severity\":\"INFO\",…}\n# SUMMARY {\"verdict\":\"PASS\"}",
   "stopReason": "EndTurn", "sessionId": "s", "requestId": "r"}
  ```

  The byte scan finds the INFO object, so the stream is not "summary-only" and
  the old rejection never fires; `collect-codex-findings.py:64-65` accepts
  INFO+PASS; `verify-merge-findings.py:912-917` excludes INFO from the
  verdict-binding set. A lazy zero-work `EndTurn` becomes a clean pair PASS.
  **Both halves of this shape are separately measured behaviours of this engine**
  — the INFO pseudo-finding is iter-0079's defect class 1
  (`{"id":"pair-judge-pass","severity":"INFO"}` + PASS) and `sschema-3`'s
  `static-review-start`; the weld is KS-4. Codex composed two real observations
  into a false-PASS path neither seat had seen. This also closes, by
  construction, the "lazy `EndTurn` PASS" hole named above — on the recovery
  path. It remains open on the non-recovery path, where it stays an
  acknowledged, named residual.

### B2 variant — `DELTA-R1-6` was right, and it is now MEASURED

Grok predicted a specific failure mode rather than a category: `HOME="$NEUTRAL"`
applies to the whole process tree, so a probe touching `Path.home()`,
`~/.gitconfig` `insteadOf`, or `~/.npmrc` auth resolves into the empty neutral
dir and can emit a **false CRITICAL** ("state did not persist") or miss a
home-path bug. It called my "strict improvement, not a trade" wording an
overclaim. **Measured — the prediction is correct:**

| Run | `Path.home()` | `~/.gitconfig` | `~/.npmrc` |
|---|---|---|---|
| direct baseline | `/Users/aipalm` | present | present |
| judge, real HOME | `/Users/aipalm` | present | present |
| judge, `HOME=$NEUTRAL` | `/private/tmp/n-…` | **absent** | **absent** |

So B2-strict **is** a trade. My claim is retracted. But the trade is avoidable —
a third arm was measured:

| Variant | MCP connections | reminder injection | probe home fidelity |
|---|---|---|---|
| shipped recipe (no HOME) | **3 / 65 tools** | **1** | full |
| **B2-strict** (`HOME=$NEUTRAL`, empty) | 0 | 0 | **broken** |
| **B2-selective** (`HOME=$NEUTRAL` seeded with `.gitconfig` + `.npmrc`, **never** `.claude.json`) | **0** | **0** | **restored** |

B2-selective gets both. Its own cost, stated so it is not smuggled in: the seed
list is an **allowlist that will attract additions** (`~/.ssh/config`, `~/.aws`,
`~/.cargo`), and each addition re-opens leak surface — the same accretion
pressure CLAUDE.md's subtractive rule exists to resist.

> **SUPERSEDED** — this section left the variant open for the freeze round.
> Codex R2 rejected all three options above on a better criterion and proposed a
> fourth, which then measured 3/3. **B2 is variant (iv)**; see § "B2 RESOLVED".
> The three rows here are kept only as the measurement trail that ruled them out.

### Two further leaks, surfaced by Codex R1's evidence dump (NEW)

Codex's R1 was killed before its verdict, but its raw reads of the preserved
session exposed two channels neither seat nor the orchestrator had measured.

**(a) Plugin skills are injected — an iter-0079 shipped fix is incomplete.**
`chat_history.jsonl` carries a `<system-reminder>`: *"The following skills are
available for use:"* followed by 11 entries with absolute paths under
`/Users/aipalm/.claude/plugins/marketplaces/{claude-plugins-official,openai-codex}`
(`codex-cli-runtime`, `gpt-5-4-prompting`, `hookify`, `frontend-design`,
`rescue`, `setup`, …). This happened **with** `GROK_CLAUDE_SKILLS_ENABLED=false`
**and** `[skills] ignore = ["~/.agents", "~/.claude", "~/.cursor"]` — the very
knob iter-0079 shipped to close its `~/.agents/skills` leak. **That fix does not
cover `~/.claude/plugins/marketplaces/`.** It also corrects a third 0079
isolation row: "No AGENTS.md/user-config injection — PASS" rested on the seat
self-reporting `INSTRUCTIONS_ABSENT`, which is about rules/instructions; skills
were a separate channel and were never measured.

**(b) The real `~/.zshenv` still executes inside probes, and B2 makes it emit
errors into the judge's evidence.** A probe tool-result under the HOME-override
recipe reads:

```
exit: 0
{"accepted": ["low-early", "mid-tail"], "rejected": ["high-late"], "remaining": 0}
/Users/aipalm/.zshenv:.:35: no such file or directory: /private/tmp/neu-p7/.cargo/env
```

The login shell sources the operator's real `.zshenv` regardless of `HOME`, and
its `. "$HOME/.cargo/env"` line then fails *because* `HOME` was overridden. A
pair judge told to compare "stdout/stderr/exit" sees that error line as part of
the probe's externally visible result — **B2 is a false-finding generator on the
stderr channel**, which is strictly worse than the missing-config mode
`DELTA-R1-6` predicted. Note this defeats **B2-selective** too: seeding
`.gitconfig`/`.npmrc` does not stop `.zshenv`, and chasing it would mean seeding
`.cargo/env` next — exactly the unbounded-allowlist accretion Grok warned about.

**Isolation scoreboard under each recipe** (mechanically checkable):

| Signal in the judge's own conversation | shipped recipe | + `HOME` override |
|---|---|---|
| `mcp_server_connected` / tools enumerated | 3 / **65** | **0 / 0** |
| `MCP servers connected` reminder | 1 | **0** |
| `The following skills are available` reminder | 1 | **0** |
| any `/Users/aipalm` string anywhere | present | **0** |
| probe stderr free of host-shell errors | yes | **NO — new failure** |

**(c) …and the evidence-integrity defect has its own knob — `ZDOTDIR`.**
Root cause of (b), measured: **`ZDOTDIR=/Users/aipalm` is exported in the ambient
environment**, so zsh reads the operator's rc files from that path no matter what
`HOME` says — which is also why overriding `HOME` alone produced the error rather
than silence. Adding `ZDOTDIR="$NEUTRAL"` to the recipe:

| Recipe | probe stderr | `/Users/aipalm` in judge-visible result |
|---|---|---|
| `HOME` override only | `/Users/aipalm/.zshenv:.:35: no such file or directory: …/.cargo/env` | present |
| **`HOME` + `ZDOTDIR` override** | **(empty)** | **none** |

*(An earlier arm of this test appeared to show `ZDOTDIR` failing; that arm was a
harness bug of mine — the `export` ran in a `bash -c` subshell that exited before
grok launched. Re-run inline, the knob works. Recorded because the broken arm's
result would otherwise have read as a negative.)*

So the leak scoreboard's only red cell closes, and the residual trade shrinks to
just home-relative *paths*. Updated option set for the freeze round:

| Option | 4 leak channels | probe stderr | home-relative paths | cost |
|---|---|---|---|---|
| shipped recipe | **open** | clean | full | 65 tools + 2 injections |
| B2-strict + `ZDOTDIR` | closed | **clean** | broken | probes must be repo-local |
| B2-selective + `ZDOTDIR` | closed | **clean** | restored (seeded) | unbounded seed allowlist |

**Third time this iter the search-before-concluding rule paid** (step-1 knobs,
`HOME`, now `ZDOTDIR`). Each was a point where "no knob exists" was the tempting
conclusion.

### B2 RESOLVED — Codex R2's variant (iv), proposed unmeasured, now MEASURED 3/3

Codex refused all three options above on a criterion better than mine:
**"isolation must not alter the evidence being judged."** None of (i)-(iii)
satisfies both context isolation and probe fidelity. It proposed a fourth —
**split the environment at the process boundary** — and correctly declined to
adopt it unmeasured.

Recipe: `HOME="$NEUTRAL" ZDOTDIR="$NEUTRAL"` for the grok process, plus a
controlled `$NEUTRAL/.zshenv` containing `export HOME=<real home>`, so **grok's
own host scans run under the neutral home while probe shells get the real one
back**. No allowlist, no seeding.

Measured, n=3, all signals Codex named:

| Run | `mcp_server_connected` | skills reminder | MCP reminder | host `.zshenv` error | `Path.home()` | `.gitconfig` | `.npmrc` | stop |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | none | `/Users/aipalm` | ✓ | ✓ | `EndTurn` |
| 2 | 0 | 0 | 0 | none | `/Users/aipalm` | ✓ | ✓ | `EndTurn` |
| 3 | 0 | 0 | 0 | none | `/Users/aipalm` | ✓ | ✓ | `EndTurn` |

Baseline for comparison: `{"expanduser": "/Users/aipalm", "gitconfig_exists": true, "home": "/Users/aipalm", "npmrc_exists": true}` — **probe fidelity is
baseline-equivalent**, and all four leak channels stay closed. **B2 := variant
(iv).** Artifacts: `out/variant-iv/run-{1,2,3}.json`.

**A first pass of this control failed 3/3 `Cancelled` and the design was nearly
discarded.** The cause was my control prompt, not the recipe: it asked the judge
to report "stderr **and exit code**", which induced exactly the chained command
Finding 1 documents. Re-run without the exit-code clause, 3/3 `EndTurn`.
Recorded because it is independent corroboration of Finding 1's mechanism from
an unrelated direction — **the orchestrator writing a control prompt fell into
the same trap `verify.md:177-179` sets for the judge**, which is the strongest
argument yet for B4.

### Overclaim corrections adopted from R1

1. **"Categorically unauthorizable by any `--allow` form"** → too strong for a
   negative existence claim. Corrected to: *under `dontAsk`, every allow shape
   tested — prefix, dual-segment, and exact full-string — produced
   `PermissionCancelled`.* Other permission modes are untested and unclaimed.
2. **"Both isolation rows can now read PASS"** → only after P-0080-C re-measures
   at build time. The R1 seat correctly refused to accept a row it could not
   open.
3. **Reproducibility defect on my side, now fixed.** The R1 seat could not verify
   cells H-N because I had run them inline without persisting artifacts. They are
   re-run and persisted at `out/cell-{J,H,I,K,L,N}/` via
   `run-chain-cells.sh` — **all six reproduce identically** (J `EndTurn`; H/I/K/L/N
   `Cancelled`), this time under the B2 recipe, so Finding 1 is independent of
   the isolation change.
4. **Do not overcorrect P4 out of the iter.** Demoting chain-cancel from "the
   emission problem" to a pin gate is right; deleting B4/P-0080-D from scope
   would be the opposite error. Both stay.

### Explicitly out of scope

`verify-merge-findings.py:877-878` default-to-PASS (own registration) ·
re-freezing the INFO+PASS clean-route criterion (a criterion change, not a
collector bug — `collect-codex-findings.py:64-65` is correct) · shipping
`Bash(echo *)` or `--always-approve`.

## BUILT + GATED 2026-07-26 — PARTIAL. Emission NOT certified (as the contract predicted).

Build delegated to Codex (`-s workspace-write`, executor pin). Files changed:
`adapters/grok.md`, `collect-codex-findings.py`, `verify.md` (+ `.claude` and
`.agents` mirrors), and one knock-on to `scripts/lint-skills.sh`. Self-test green,
`lint-skills.sh` **All checks passed**.

### Gate results

| Prediction | Result | Evidence |
|---|---|---|
| **P-0080-A** unwrap fail-closed | **PASS 3/3** | the **real** `out/schema-1` artifact (`Cancelled` + `{"findings":[],"verdict":"PASS"}`) → exit 1, **no canonical file**, 3/3. Bonus real-data checks: `sjson-2` (welded `.text`) → exit 1 fail-closed; `sjson-1` (clean) → exit 0 with the true `CRITICAL priority-order-not-applied` @ `allocator.py:13` preserved |
| **P-0080-B** no default-route regression | **PASS** | **25 real** `codex-judge.stdout` / `claude-judge.stdout` artifacts from `benchmark/auto-resolve/` and `.devlyn/runs/` replayed through old vs new collector: identical exit, identical stdout, identical canonical files. 0 mismatches |
| **P-0080-C** isolation + evidence fidelity, 5 invariants | **PASS 3/3** | against the **literal shipped recipe**: `mcp_server_connected` 0 · MCP reminder 0 · skills reminder 0 · no `logs/mcp/` · no host `.zshenv` error · `Path.home()`/`.gitconfig`/`.npmrc` baseline-equivalent · `EndTurn` |
| **P-0080-D** unchained probe | **FALSIFIED at n=6** | 5/6 `EndTurn` with the correct CRITICAL, **1 `Cancelled`**. The frozen falsifier is *"any `PermissionCancelled`"*, so this is a falsification — reporting the first 3 as "3/3" would be cherry-picking the frozen bar |
| **P-0080-E** emission residual | **5/6 welded** | baseline recorded, **no pass bar** by construction. Collector correctly rejects 3/3 on the runs checked end-to-end |

### A receipt/ship-shape divergence I caught in my own work

Every iter-0080 measurement had been taken with `--no-plan`, which the shipped
recipe does **not** contain — the same stale-receipt class that recurred three
times in iter-0079 and that Treatment-Seat Identity Fidelity (0074.2 (f))
exists to prevent. Rather than add the flag to match my receipts, P-0080-C was
re-run against the recipe **exactly as shipped**: 3/3 PASS. `--no-plan` was never
load-bearing, so nothing was added. The certified shape is now the shipped shape.

### What B4 actually bought, and what it did not

**Bought**: before B4 the probe route was **0/6** — every run died at turn 1 with
the anchor chained. After B4 the anchor executes in **6/6** runs, and run 3's own
narration reads *"Running the mandatory dominance-loss probe as a single
comman[d]"* — the instruction is being followed.

**Did not buy**: elimination. Run 5 reached `turns=3`, ran the probe
successfully, stated the correct root cause (*"the allocator walks input order
and never sorts by priority"*), and was then `Cancelled` on a **later exploratory
command** outside the bare-anchor allow rule. So the failure mode **moved and
narrowed**: from "the anchor itself is unauthorizable" to "the judge's follow-up
command is out of allow scope". That is the P-H under-scoped-allowlist hazard,
not the chain defect, and it needs its own registration — widening the allowlist
is still forbidden.

Grok's R1 predicted exactly this shape: *"B4 is prompt text. Models still emit
`; echo "EXIT:$?"`… P-0080-D is the real gate (behavioural), not the markdown
edit."* Prose reduced the rate from 6/6 to 1/6; it did not mechanize it.

### Closing-gate verdict: NOT emission-certified

Gate parts 1 (residual cleared) and 2 (probe path, no `PermissionCancelled`) both
fail. Therefore: the `not emission-certified` note **stays** in `engine-doctor.sh`,
the certification line **stays** in `adapters/grok.md`, and **no durable `pair
grok` pin is written**. This is the 4-part conjunction working as designed — the
amendment Codex forced (`DELTA-R1-2`) is precisely what stops B1-B4 landing from
being read as certification.

**Next work**: step 2 (prompt delta A/B against the json arm, `adapters/README.md:56-59`
condition 3) and/or step 3 (the frozen byte-forward recovery + its tier), plus a
separate registration for the post-anchor allow-scope residual.

## Gate for closing — AMENDED per `DELTA-R1-2`

The original one-liner let A-D pass and the residual stand while someone lifted
the note. The gate is now a conjunction, and **building B1-B4 alone never
satisfies it**:

grok is emission-certified — and only then does the `not emission-certified`
note come out of `engine-doctor.sh`, the certification line out of
`adapters/grok.md`, and a durable `pair grok` pin become available subject to
the standing seat-fitness rule — **iff all four hold**:

1. **Emission**: B1 + B3's fail-closed unwrap in place, **and** the P-0080-E
   residual rate *cleared* — either by measured step-2 lift or by step-3
   byte-recovery, against a bar frozen together with whichever of those is
   attempted. A merely *measured* residual is not a cleared one. **Recovery
   counts as clearing only if the Tier B3+recovery negative tests pass,
   INFO+PASS included** (Codex R2, Q3 hole 1: the earlier wording let step-3
   count as residual-clearing without excluding that shape).
2. **Probe path**: the mandatory dominance-loss probe completes `EndTurn` with
   the correct CRITICAL on the seeded fixture, with the allow rule scoped to the
   bare anchor — no `Bash(echo *)`, no `--always-approve` (P-0080-D).
3. **Isolation AND evidence fidelity**: P-0080-C re-measured at build time, 3/3,
   under B2 = variant (iv), on **all** of — zero MCP connections/tools, zero MCP
   reminder, **zero plugin-skills reminder**, no host `~/.zshenv` execution or
   error in probe output, and `Path.home()`/`.gitconfig`/`.npmrc`
   **baseline-equivalent**. (Codex R2, Q3 hole 2: the earlier wording only asked
   that the trade be *recorded*, which a variant could satisfy while still
   corrupting the judge's evidence. "Recorded" is not a control.)
4. **No regression**: P-0080-B green on replayed real claude/codex stdout.

`engine-doctor.sh`'s note is a **string flag, not a measurement** (`DELTA-R1-5`
companion): B5 must not be written so as to imply the doctor enforces zero MCP
connections. P-0080-C is the only thing that certifies that.

**B1 is recipe text, and B4 is prompt text — neither is mechanically enforced.**
B1 holds only if the adapter recipe is the sole spawn path; B4's real gate is
the behavioural P-0080-D, not the markdown edit. Both limits are recorded rather
than papered over.

## CONTINUATION ROUND 2026-07-27 — three pre-registered measurements, all NEGATIVE. **SHIP NOTHING.**

Three-seat round (Opus 5 orchestrator · Codex GPT-5.6-sol · Grok 4.5), R0 + R1,
both seats independent on every load-bearing citation. Artifacts are
session-scoped; every claim below is reproducible from the pre-registrations and
raw outputs named in each subsection.

### M1 — KS-5: the step-1 knob sweep was incomplete, and completing it is a NEGATIVE

`--output-format` documents **three** values (`0080-…md:91`); only `json` and
`--json-schema` were ever measured. `grep -in streaming` over this iter returns
exactly one hit — that table cell. The one artifact, `out/diag-stream.ndjson`, is
a 1-turn `Cancelled` diagnostic cited nowhere. **So the amended sequencing rule's
"survives both knobs" license (line 480+) rested on an unmeasured third value.**
Both seats confirmed this independently.

Measured under the shipped recipe verbatim, sole delta `streaming-json`, n=4:
the stream separates narration from contract via an interleaved `thought` run —
**and `stream-3` fires the pre-registered falsifier**: narration *and* the
canonical contract inside a **single** maximal `text` run, plus a ```` ```json ````
fence. 3/4 separable is **not** reported as a partial pass; the falsifier is
"any", the same discipline P-0080-D was held to at line 806.

**Path (i) streaming-json is VALID-NEGATIVE for production.** What survives is a
mechanism this iter never named: **`.text` under `--output-format json` is the
concatenation of per-turn assistant text with no separator** — that is *why* the
weld exists. Step 1 is now complete, so steps 2/3 are licensed by measurement
rather than by omission.

### M2 — Step 2 (prompt delta): FALSIFIED at n=6 per arm, matched interleaved control

Channel = `--rules` (alias `--append-system-prompt`), the vendor's documented
**system-prompt** channel, text wrapped in `<human_rules>`
(`~/.grok/docs/user-guide/12-project-rules.md:163-171`) — chosen over a judge-prompt
edit so the canonical `verify.md` body stays untouched and the delta stays
engine-scoped. Rule text kept narrow per that guide's line **177**
("shorter, specific rules are easier for Grok to follow"), naming only the two
measured defect shapes. `--system-prompt-override` was rejected: it replaces the
default system prompt and skips `--rules` (line 171) — `--json-schema`-class
capability-suppression risk.

| arm | n | collector-accepted | welded | EndTurn | turns≥2 | seeded CRITICAL | PASS |
|---|---|---|---|---|---|---|---|
| A (control) | 6 | **0/6** | **6/6** | 6/6 | 6/6 | 6/6 | 0 |
| B (+`--rules`) | 6 | **0/6** | **6/6** | 6/6 | 6/6 | 6/6 | 0 |

**Zero effect, zero degradation.** First-turn narration is near-identical across
arms. Frozen bar condition 1 fails → both seats' pre-committed flip to (iii)
fires. The control measured **6/6** welded, worse than P-0080-E's 5/6.

**Not claimed**: that no prompt delta can work. One text, one channel — a negative
existence claim must not outrun its cells.

### M3 — the frozen step-3 fallback, measured on 18 REAL artifacts BEFORE building

Faithful prototype of § "Pre-committed step-3 fallback" with no additions.

| Result | Count |
|---|---|
| `EndTurn` rows recovered, real CRITICAL + `NEEDS_WORK` preserved | **16** |
| `EndTurn` rows still rejected | **1** — the fence row |
| non-`EndTurn` correctly refused (`Cancelled`) | 1 |

The single failure is **a defect shape neither 0079 nor 0080 recorded**: the model
wraps the finding in a markdown fence. Byte-forward recovery discards the *opening*
fence with the preceding prose; the **trailing** ` ``` ` line survives and fails the
line contract. Observed independently on **both** transports (json arm and
streaming arm) — not a singleton.

**And Tier B3+recovery is NOT green.** Codex constructed, and the orchestrator
verified executable, a **tab-separated dual-contract** composition:
an INFO finding + `# SUMMARY PASS`, then a TAB-indented CRITICAL + `# SUMMARY
NEEDS_WORK`. The tab defeats a `}{` adjacency check while
`collect-codex-findings.py` strips leading whitespace per line and lets the **last**
summary overwrite the first — so two verdict documents are admitted as one. The
frozen rule's binding "dual-document `.text` still rejects" constraint is therefore
**not satisfied by a naive implementation**, which is itself the finding: the
constraint is harder to implement than the freeze text implies.

Grok added a third gap: an **opening-only** fence (no closer) would ACCEPT under the
frozen rule today — "the freeze is not a coherent fence policy."

### Seat convergence

| Decision | Codex | Grok | Resolved |
|---|---|---|---|
| D1 — is 16/17 "cleared"? | **No** — partial liveness only; no prospectively frozen bar | **No** — gate part 1 needs a co-frozen bar AND a green negative tier | **NOT CLEARED.** Even 17/17 would not clear: clause D (tier green) independently fails |
| D2 — fence handled inside recovery? | **No** as a retroactive amendment to frozen v1; **yes** only via a prospectively registered v2 | **No** under this freeze; a new freeze may license a bounded strip | **Same position.** Not in v1; a v2 needs its own freeze + negatives written first |
| D3 — what ships? | **No new prompt or collector code.** Keep B1/B3 + both warnings; register everything | Register three residuals; optional freeze-as-written build only as explicitly non-certifying | **SHIP NOTHING** — Codex's stricter reading wins on evidence: building a mechanism whose frozen negative tier is known-failing is not licensed by the step-2 flip |
| Drift? | Not yet; continuing to tweak emission would be | **Yes — strategic emission-tunnel**; hygiene excellent, allocation drifted | **Stop emission. Register. Pivot to allow-scope** — the only residual whose clearance can move a failing gate conjunct |

The step-2 flip licensed *attempting* (iii), not *claiming clearance* — and the
tab-dual bypass shows the attempt is not ready to be product code.

### Registered residuals (measured anchors, no fix shipped)

- **R-weld** — narration preamble welded to the first content bytes of `.text`.
  Named at freeze; frozen byte-forward recovery clears **16/16** pure-weld
  `EndTurn` rows on this corpus. **Mechanism-addressable, NOT bar-cleared.**
- **R-fence** — paired markdown fence around the contract. Two independent
  transports. Frozen recovery fails closed on it. **New residual; needs its own
  freeze + bar + negative tier before any code.** Note the step-2 rule text
  explicitly forbade fences and the model emitted one anyway.
- **R-dual-tab** — the dual-document constraint is defeated by whitespace that the
  collector strips but an adjacency check does not. **Blocks Tier B3+recovery.**
- **R-allow-scope** — post-anchor exploratory command outside the bare-anchor allow
  rule (§ "What B4 actually bought"). Gate part 2. **Independently failing; no
  emission work can touch it.**

### Closing-gate verdict: UNCHANGED — NOT emission-certified

The `not emission-certified` note stays in `engine-doctor.sh`, the certification
line stays in `adapters/grok.md`, no durable `pair grok` pin. **Product files
changed: none.**

### Orchestrator retractions this round: 4

1. **P-C admission rule** — Codex composed a bypass from measured components
   (prose diagnosis discarded as unparseable + INFO+PASS admitted); orchestrator
   verified it at `collect-codex-findings.py:64-65`. P-C would have *opened* a
   false-accept path the shipped `json` route already closes. Withdrawn.
2. **"~83% of clean reviews become BLOCKED"** — a category transfer of P-0080-E's
   probe-route rate onto the clean route. Grok caught it. Retracted.
3. **"Only step 2 leaves clean PASS reachable"** — true only against (iii); under
   the measured streaming morphology path (i) kills it too. Narrowed.
4. **"Both full pre-registrations executed"** — too strong: Grok's R0 falsifier
   required a paired clean route, which the step-2 pre-registration explicitly
   excluded. Codex caught it. (Does not rescue the delta: condition 1 failed 6/6.)

Also corrected on verification: the vendor quote cited as `12-project-rules.md:175`
is at line **177** (Codex).

**Seat claims verified before adoption: 2, both CONFIRMED** (the tab-dual
composition, executed; the citation line number).

### P-AUTH — FALSIFIED, and the probe itself was the finding

Two clusters of `Not signed in` failures each followed ~4 rapid isolated runs.
Hypothesis — refresh-token rotation written into `$ISO_HOME` and discarded with it
— **FALSIFIED**: before / iso-after / host-after were byte-identical. Not expiry
either: the credential in use had a 6-hour life and the same file that "failed"
worked afterwards. **Cause unknown; not asserted.**

**Codex found a security defect in the probe itself**: its redactor masked only
top-level string values, so the nested auth object — access JWT, refresh token, and
PII — was written to a plaintext artifact and echoed into the orchestrator's
transcript. Artifacts purged, the seat log redacted, three stale `$ISO_HOME`
directories holding credential copies removed, and the probe **deleted** rather
than repaired (its hypothesis is falsified, so a credential-dumping instrument has
no remaining use). **Credential ROTATED by the operator 2026-07-27 and verified
live afterwards (`grok -p` → `EndTurn`); this action item is CLOSED.** Recorded as a first-class
lesson: an instrument that reads secrets needs recursive redaction, and "it is only
a scratchpad file" is not a control.
