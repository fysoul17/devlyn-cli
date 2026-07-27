# iter-0081 — R-allow-scope: the judge's probe capability contradicts its permitted scope

**Status: REGISTERED, NOT FROZEN, NOT BUILT. 2026-07-27.**
Opened because iter-0080's closing gate **part 2** fails independently of emission
(DECISIONS 0080.3), and both seats' R1 named this the only residual whose
clearance can move a failing gate conjunct.

## Why this iter exists (pre-flight 0)

**User-visible failure**: 1 in 6 grok pair-judge runs produces **no review at all**.
The judge reads the spec, runs the mandatory dominance-loss anchor, correctly
identifies the seeded CRITICAL, and is then cancelled on its next tool call —
`stopReason=Cancelled`, exit 0, prose-only stdout. Measured 1/6 in P-0080-D and
reproduced **1/6 again** in this iter's capture (n=6, shipped recipe verbatim).

**Mission gate**: Mission 1. It is gate part 2 of the iter-0080 closing
conjunction; no emission work can touch it.

## The measurement that changed the diagnosis

iter-0080 characterised this as *"the judge's second command falls outside the
bare-anchor rule"* and filed it as a post-anchor **exploratory** command. Sessions
were not preserved then, so that reading came from narration. This iter preserved
the transcripts. **The characterisation was imprecise and is corrected here.**

n=6 under the shipped recipe. Every run has the **same information need** — read
`probe.py` to learn the probe's inputs. The runs differ only in *which granted
tool they use to satisfy it*:

| Runs | Route taken for the identical read | Outcome |
|---|---|---|
| 1, 2, 3, 5, 6 | `read_file` | `EndTurn`, correct CRITICAL |
| **4** | `run_terminal_command` with `python3 -c "…p.read_text()…"` | **`Cancelled`** — review destroyed |

Run 4's denied call, verbatim from `chat_history.jsonl`:

```json
{"name":"run_terminal_command",
 "arguments":{"command":"python3 -c \"import json; from pathlib import Path; p=Path('…/probe.py'); print(p.read_text())\"",
              "description":"Read probe inputs for expected ordering"}}
```
→ `{"type":"tool_result","content":"User cancelled the execution for tool `run_terminal_command`"}`

**It was not exploration.** It was a *file read* — a job the granted `read_file`
tool does, and which the same run had already used successfully twice (on the spec
and the implementation). The allow rule (`Bash(python3 …/probe.py)`,
prefix-matching per the vendor doc) correctly refuses `python3 -c …`:
**the allowlist behaved exactly as designed.**

> **Precision correction (Grok R0, adopted).** Run 4 had **not** already read
> `probe.py` with `read_file` and then re-read it through the shell. It used
> `read_file` for the spec and the implementation, then chose the shell as its
> *first* route to `probe.py`. So the defect is a **substitutable tool class**,
> not a re-read of already-loaded content. Run 3 is the control twin: same
> post-anchor need, same sequencing, `read_file` instead of shell → lives.

## Why-chain — stopped at the invariant, not at a fixed count

1. Why did the review die? → A shell call fell outside the allow rule, and grok's
   deny semantics truncate the review silently at exit 0.
2. Why was there a second shell call? → The judge needed `probe.py`'s **inputs**.
3. Why did it need them? → The spec's `## Verification` bullet describes the probe
   input in prose (`spec.md:16`) while the exact inputs live in the probe source
   (`probe.py:12`), and the probe prints only the **actual** object — yet the judge
   must "compare the full externally visible result … including accepted rows,
   rejected rows, and remaining state." **The judge has no complete, source-bound
   comparison packet.**

   > **Correction (Codex R0, adopted).** "The product supplies no expected side" is
   > too broad: canonical VERIFY input includes `spec.expected.json`
   > (`verify.md:9`), which can carry exit and output-substring expectations
   > (`expected.schema.json:22`) — just not the full parsed object. The defensible
   > claim is the packet one, above.
4. Why did that read go through the shell in 1 of 6 runs? → Two granted routes
   serve one information need, and route choice is nondeterministic.
5. **Violated invariant**: *the judge is granted two routes to the same
   information, one of which fails silently — for an information need the harness
   itself created by not supplying the expected side of the comparison it demands.*

## Two contradictions in SHIPPED files (this is the product-level part)

The above could be dismissed as an instrument artifact — the fixture spec is ours.
It is not. Both contradictions are in shipped product text, opened at citation time:

1. **`config/skills/devlyn:resolve/references/phases/verify.md`** instructs the pair
   judge to use the backticked observable command "as its command anchor **before
   adding bounded input variations**." A bounded input variation is *by definition*
   a command other than the bare anchor. **`config/skills/_shared/adapters/grok.md`**
   scopes the allow rule to "that bare anchor." So the judge is instructed to issue
   commands the recipe is instructed to deny — and denial destroys the review.
2. **Inside `adapters/grok.md` alone**: "The `--allow` rule must cover the full
   probe-command family the judge may need" and "the allow rule scoped to that bare
   anchor" are the same file's two answers to the same question.

Our fixture's judge only tried to *read*; the product contract additionally asks it
to *vary the input*, and that class is **unmeasured**.

> **Correction (Codex R0, adopted).** 1/6 is **not** a product-wide lower bound —
> it is a conditional rate on one forced-probe fixture. What the shipped
> contradiction establishes is **reachability** of the defect, not its incidence
> across specs. The earlier "lower bound" wording is withdrawn.

## Reframing — reliability, not safety

Per Grok's iter-0080 R0 split, which stands: a cancelled review lands as
**BLOCKED** (`stopReason=Cancelled` → collector rejects → `verify.pair.emission-contract`),
never an unjustified PASS. This is a **seat-fitness / review-destruction** defect.
The cost is that ~1/6 of pair judgments yield nothing, not that a bad diff passes.
Any proposal that trades safety for liveness here is out of scope.

## Candidate fix classes — deepest (most subtractive) first

Ranked by the mandatory pre-edit question, not by ease.

- **C1 — delete the NEED.** *(Superseded by C1\* — Codex R0 showed C1 as first
  written conflates two non-equivalent things: supplying the **expected** side
  leaves actual execution outstanding, while pre-running the anchor supplies the
  **actual** side but neither the exact input nor the expected result.)*
  **C1\***: supply a single source-bound packet — exact anchor command, exact
  input, spec-derived expected full result, actual `stdout`/`stderr`/`exit`, the
  parsed actual object, and hashes binding all of it to the frozen snapshot.
  Only the bound tuple deletes step 3 of the why-chain.
- **C2 — delete the CAPABILITY.** Drop `run_terminal_cmd` from the judge's
  `--tools` and pre-execute the anchor harness-side. The silent-deny class becomes
  structurally impossible. **Named cost**: the judge loses adaptive probing —
  exactly the "path A" capability iter-0079 validated. C1 and C2 compose; C2 alone
  removes the failure mode but also removes `verify.md`'s "bounded input variations".
- **C3 — resolve the contradiction in one direction and delete the other text.**
  Either `verify.md` stops asking for variations, or the recipe stops scoping to
  the bare anchor. The second direction is **forbidden** (allowlist widening).
- **C4 — prose only** ("use `read_file` for reads; shell only for the anchor").
  Recorded for completeness and **expected to be partial**: B4 is the precedent —
  prose took the chain defect 6/6 → 1/6 without mechanising it.

**Explicitly forbidden**: widening the `--allow` rule, `Bash(echo *)`,
`--always-approve`, and any retry-on-Cancelled loop (a workaround that hides a
broken contract).

## Open questions for the seat round (R0)

1. Is C1 sufficient alone? If the expected side is supplied, does any legitimate
   second command remain — and if so, C2 or C3?
2. Does C2's loss of adaptive probing regress the iter-0079 path-A result, or was
   that result about *the anchor* running, which pre-execution preserves?
3. Which direction does C3 resolve in, given `verify.md` is engine-neutral and the
   allow rule is grok-specific? Does an engine-neutral contract get narrowed by one
   engine's permission semantics — and if not, what is the alternative?
4. Is the 1/6 rate the right bar, or is the relevant bar 0 denials of any kind?
5. What falsifier would each candidate accept?

## R0 seat round — 2026-07-27 (Codex GPT-5.6-sol · Grok 4.5)

**Both seats: the invariant above stops one level early.** The parent class is
not "two routes to one fact" but:

- **Grok** — *judge-chosen non-anchor shell is lethal under silent deny, and the
  contract still induces non-anchor shell.* Missing expected data is the currently
  measured inducer, not the root. Run 4's own narration said the finding was
  verdict-binding and it was "stopping here" — **and it issued another tool call
  anyway**, so residual post-verdict tooling is itself a kill switch.
- **Codex** — *role eligibility must cover the canonical task's entire mandatory
  operation set, not one command that happened to be allowed.* `pair_judge` is a
  Boolean (`engine-preflight.md:18,23`) and cannot express "pre-executed evidence
  only" vs "adaptive probe capable."

Same insight at two altitudes; both adopted.

### Converged

| Point | Both seats |
|---|---|
| **C4 (prose) is not a clearance path** | B4 is the *prior*, not an anecdote: this defect class does not die by instruction. Run 4's "stopping here" + simultaneous shell call is the strongest warning available |
| **Bar** | **Zero denials of the silent-destroy class**, matching P-0080-D's "any `PermissionCancelled`". 1/6 is diagnostic, never a threshold |
| **Canonical `verify.md` ends stay engine-neutral** | Do not delete a comparison obligation because one vendor's `dontAsk` is harsher. Fix the **means**, or re-home the obligation harness-side |
| **Allowlist widening / `--always-approve` / retry-on-Cancelled** | Forbidden, unchanged |
| **Reliability, not safety** | Upheld — `Cancelled` → collector rejection → BLOCKED, never PASS |

### Contested: does C2 regress iter-0079 path A?

**Grok: no** (harness pre-execution preserves the certified result).
**Codex: yes** (P-0079-F required grok *itself* to execute the probe).

**Adjudicated on the frozen text, not on who spoke last — Codex is right.**
`0079-…md:517-520` strengthens P-F to *"The run passes only if grok **executes**
that probe"*, and `0079-…md:962-964` concludes *"the scoped shell makes it able to
discharge a mandatory-probe spec. **Path A is validated.**"* That is a capability
claim about the judge process, not only an outcome claim. Grok's reading
substitutes outcome-preservation for the capability that was actually certified.

**C2 therefore requires an explicit supersession of path A, with the named delta
Codex supplied**: path A proved the bare anchor *executable*; iter-0081 proves that
capability is **not total** for the canonical role, because a legitimate
post-anchor operation silently terminates the seat. C2 stays available — as a
recorded supersession, never as a gloss.

### Divergent primaries — for R1

- **Grok**: **C1\* + C3-narrow** primary (delete the harness-created gap *and* the
  neutral text that licenses shell the recipe cannot honour); **C2 as fallback**
  only if residual `Cancelled` survives. Criterion: **Permission-Contract Closure**
  — every shell argv the contract *licenses* is either the bare anchor or already
  fulfilled by the harness.
- **Codex**: **capability-aware routing** — keep `verify.md` neutral, express the
  judge-capability distinction, route variation-requiring tasks to a capable OTHER
  engine, fail an explicit grok pin closed as capability-incompatible. Criterion:
  **Obligation–Capability Totality**. And, because the Boolean cannot express
  conditional eligibility, its honest interim is **`pair_judge: no`** for grok.

The open R1 question is whether `pair_judge: no` is the honest state or an
over-correction that discards a seat which found the correct CRITICAL in 6/6 runs
and completed in 5/6.

## Not yet frozen

No predictions, no bar, no build scope. Those are frozen **after** the seat round
and **before** any measurement — the discipline iter-0080 held throughout.

## R1 + Opus×Fable decision round — 2026-07-27

### R1 converged further

Grok **conceded the path-A dispute with a named delta**: *"I cannot quote a line
that makes path A outcome-only. Codex's reading is the text."* C2 therefore stays
available only as an explicit supersession. Both seats also froze the same bar
(zero silent-destroy denials), and Codex refuted Grok's C3-narrow: deleting
"bounded input variations" from `verify.md:171-176` would remove a capability
claude/codex **can** honour, which the R0-converged row already forbade.

### The contested product change: `pair_judge: yes` → `no`?

**DECISION: NO. Keep `pair_judge: yes`.** Decided by the Opus 5 orchestrator with
a Fable 5 seat at the user's direction. **Caveat recorded per iter-0079's binding
lesson: both are Anthropic, so this convergence is weaker evidence than the
Codex↔Grok rounds above.** It is adopted anyway because it rests on git
provenance and shipped-file behaviour the orchestrator verified independently,
not on agreement.

**The orchestrator's own adjudication was WRONG and is retracted.** It had judged
Codex "textually right" that `adapters/README.md:49`'s disjunction
("structurally unable **or not certified**") forbids grok's `yes`. Fable inverted
it on provenance, and `git log -L 49,49:config/skills/_shared/adapters/README.md`
confirms:

- Commit **`155fc8b` — the iter-0079 ship commit itself** — changed "structurally
  unable **to fill** a role" → "structurally unable **or not certified for** a role".
- Its cause is finding **F5** (`0079-…md:752`): *"`README.md:49` says
  Role-eligibility is for structurally unable backends; grok is **uncertified, not
  unable** … Widen README semantics before the precedent ships."*
- The **same commit** shipped `adapters/grok.md` with `pair_judge: yes` **and** the
  "not emission-certified" line.

So the clause Codex reads as forbidding `yes`+uncertified was written, in a frozen
three-seat round, **specifically to license it**. The "self-contradiction in one
file" dissolves — both texts were co-authored as one reviewed state.

Three further verified reasons, each opened at citation time:

1. **Silence would outrank disclosure.** An absent `## Role eligibility` section
   grants full dual-role eligibility with **zero** certification
   (`adapters/README.md:49`, first sentence). Under Codex's reading a
   silent future adapter is pair-eligible for free while grok — the only adapter
   that *discloses* its status — becomes unselectable. Wrong reading of a
   fail-closed contract.
2. **Bootstrap contradiction.** P-0079-F required `pair_judge_priority: ["grok"]`
   **pinned** (`0079-…md:505-507`). Re-certification therefore requires `yes`
   while gates are red — which Codex's semantics would itself call dishonest.
   Config-validity is the only reading consistent across the lifecycle.
3. **The flip is not a deletion.** `engine-doctor.sh:72` computes `pin_eligible`
   from binary+adapter presence alone, independent of `role` at `:68` — verified.
   A bit-only flip prints the incoherent row `role=none pin_eligible=yes`, which
   is why Codex's own minimum is three surfaces, one of which reverses a rendering
   gated green by P-0079-A.

**On the 2026-07-25 directive** (grok/Kimi K3/Qwen must be pinnable as pair
judges): `no` is not a per-se violation — the directive is a program demand, not a
promise that a measured-broken seat stays pinnable. But it **mechanically
reinstates the exact user-visible symptom the directive was issued against**:
`pair grok` → `BLOCKED:invalid-engine-config`. A refusal for a true reason beats
one for a false reason, but re-instituting that behaviour is not a call to make
when an honest alternative exists.

**What survives from Codex's position, and it is real**: the widened sentence is
ambiguous enough that two frontier models *and the orchestrator* independently
read it his way. That is a genuine doc defect. The subtractive repair is to delete
the ambiguity — state in `adapters/README.md` that the **field value** is
structural role capability while **certification status** rides the adapter prose
line plus the doctor note — not to flip the bit the ambiguity made look wrong.

### The one real gap the flip was reaching for

`/devlyn:engines`' `executor <name>` warns and writes when the CLI is unavailable
("pins are promises"); `pair <name>` has **no** equivalent clause
(`devlyn:engines/SKILL.md:43-44`, verified). So `pair grok` writes silently today.
Uncertified belongs at the *transient* pole (warn, write, fail closed at run), not
the *structural* pole (refuse) — it is evidence-based and has a registered
clearing path, namely this iter.

**Nothing ships from this decision round.** iter-0081 remains NOT FROZEN; the
doc-fix and the pin-warn parity are candidates for its freeze, alongside the
destroy-defect fix, and are subject to the same pre-registration discipline.

**Orchestrator retractions this round: 1** (the `README.md:49` adjudication).
**Seat claims verified before adoption: 4, all CONFIRMED** (git provenance;
`pin_eligible` independence from `role`; the pin-time warn asymmetry; the doctor's
hardcoded grok note).

## Reproduction (scratchpad artifacts are session-scoped; this is the durable recipe)

The n=6 capture above ran the `adapters/grok.md ## Invocation` recipe **verbatim**
with exactly one change — `$ISO_HOME` is preserved instead of `rm -rf`'d, so
`$ISO_HOME/sessions/*/*/chat_history.jsonl` can be read for the actual tool calls.
**Shred `$ISO_HOME/auth.json` before archiving anything** (binding lesson,
DECISIONS 0080.3: the credential is a nested object, so a top-level-only redactor
leaks the access JWT, the refresh token, and PII).

- Prompt: the P-0080-D/E probe-route prompt — pair-JUDGE contract + the mandatory
  dominance-loss clause + B4's unchained-anchor sentence. Reconstruct from
  `verify.md`'s pair-JUDGE section; it carries no anti-preamble clause.
- Fixture: a ~20-line priority allocator with one seeded CRITICAL (input-order
  iteration instead of priority-first), a `spec.md` whose `## Verification` bullet
  backticks the probe command, and a `probe.py` that prints only the **actual**
  parsed object. The under-specification is load-bearing — it is why-chain step 3.
- Flags: `--permission-mode dontAsk --no-memory --tools
  "read_file,grep,list_dir,run_terminal_cmd" --disallowed-tools
  "Agent,use_tool,search_tool" --allow "Bash(python3 <abs>/probe.py)"
  --reasoning-effort medium --output-format json`. **No `--no-plan`** — the
  shipped recipe does not carry it (0080's receipt/ship-shape correction).
- Read per run: envelope `stopReason`/`num_turns`, and every `tool_calls` entry in
  `chat_history.jsonl` plus any `tool_result` containing "User cancelled".

Expect roughly 1 in 6 to die `Cancelled`. The rate is **diagnostic only** — the
frozen bar is zero, per P-0080-D's "any" discipline.
