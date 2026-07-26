# iter-0079 — N-model pair: grok as the first non-binary pair judge (REGISTERED-FROZEN 2026-07-26, three-seat)

**FREEZE RECORD — three-seat convergence, two vendors independent of the
orchestrator.** Six review rounds. Final round verdicts, all on the same revised
text: **Codex GO-WITH-EDITS / stands-with-amendments** (moved from
freeze-BROKEN once path A landed), **Grok GO-WITH-EDITS /
stands-with-amendments**, **Fable 5 GO-WITH-EDITS / stands-with-amendments**.
No seat objected to the mechanism in the final round. Every seat's items were
applied and the two blocking conditions the seats named (P-C's stale "5 runs"
vs P-B's 6; the retraction ledger counting 5 while listing 4) are fixed. Fable
recorded "no unresolved disagreement with any seat to escalate."

**What makes this freeze different from the 07-25 one that broke in a day**:
that freeze had ONE cross-vendor seat and its own caveat named the risk;
this one has two (Grok/xAI, Codex/OpenAI) plus Fable, and the Codex seat that
broke the previous freeze is the one now endorsing it. The Grok seat additionally
ran **under this iter's own measured isolation recipe** — the shipping shape
reviewing its own registration.

**Subtractive close-out**: the document was cut 955 → 936 lines in the final
pass (superseded static-only block, stale "Open for R1" questions), per Fable's
Q4 — the Saint-Exupéry test applied to the registration itself.

**STATUS 2026-07-26, after the first genuine three-seat round.** Codex, Grok
(run under the measured isolation recipe — its own shipping shape), and Fable 5
all reviewed the amended text. Verdicts: **Codex GO-WITH-EDITS / freeze broken;
Grok GO-WITH-EDITS / stands-with-amendments; Fable GO-WITH-EDITS /
stands-with-amendments.** No seat objected to the mechanism; all three
objected to registration text. Every item from all three has been applied
(Codex: receipt mismatch, anchor-derivation, mandatory-probe fixture, P-B
coherence; Grok: P-F empty-PASS wording, absolute `--devlyn-dir` into the generic
rule, deny-semantics non-parity residual, P-H into the build gate, retraction
count; Fable: 6/6 arithmetic honesty, doctor's four arrays, merge-side
default decision, risk-probe sub-role scope, README:50 widening, allowlist
obligation into adapter prose). **Freeze is NOT declared** — the seats have not
seen this revision. Path A (scoped shell) resolved Codex's structural
freeze-breaker; what remains is confirmation, not mechanism.

**FREEZE BROKEN by the Codex seat, 2026-07-26.** The Codex quota reset; the
third seat ran against the frozen text and returned **OBJECT**. Two of its
findings are mechanical and were re-verified by the orchestrator at the bytes —
both are holes that **all three prior parties missed**, which is exactly the
shared-blind-spot risk the two-seat freeze record flagged:

1. **HIGH — unenforceable eligibility (the freeze-breaking named delta).** The
   frozen text handles grok's missing shell with a prose "static-analysis-only"
   residual plus a seat-fitness gate on the durable pin. But role resolution
   understands only a Boolean `pair_judge: yes|no` (`engine-preflight.md:19,23`;
   `devlyn:engines/SKILL.md:44`) — there is **no spec-capability dimension**, so
   nothing stops the harness selecting grok for a spec whose dominance-loss probe
   is mandatory (`SKILL.md:291`; `verify.md:193-199`). The carve-out cannot be
   enforced by the mechanism it relies on; the incompatibility would be
   discovered post-spawn. Violates #1 no-workaround and #7 production-ready.
2. **HIGH — zero-exit silent pair PASS.** The frozen F2 remedy covers only a
   **non-zero** collector exit. Verified at `collect-codex-findings.py:64-68`:
   the guards reject only `summary is None` with no findings, and only exact
   uppercase `NEEDS_WORK|FAIL|BLOCKED` with no findings. So `{}` or
   `{"verdict":"pass"}` (lowercase, or any unknown verdict) **exits 0**, writes
   an empty canonical file (`:109-114,133-135`), and
   `verify-merge-findings.py:877-878` defaults the pair source to PASS.
3. **MEDIUM — P-0079-C's four-file enumeration is wrong as worded.** Verified at
   `collect-codex-findings.py:25-32`: `atomic_write` writes a randomly-named
   `NamedTemporaryFile` in the target directory and then renames, and
   `path.parent.mkdir(parents=True, exist_ok=True)` may create the directory. The
   four names are a correct **final-state delta**, not a write-event allowlist —
   and P-C is worded as "permitted writes".
4. **MEDIUM — P-B/P-F are not a production gate.** 4/5 admits a 20% format-failure
   rate; P-F exercises only the finding-producing route, never the legitimate
   clean-diff `# SUMMARY {"verdict":"PASS"}` route that P-B admits. (Named
   disagreement with the R1 seat, which said keep 4/5 — Codex's delta is
   production-threshold vs measurement-threshold.)
5. **MEDIUM — scope honesty.** This iter cannot close the stated grok/Kimi/Qwen
   goal; it is the **grok-first generic-invocation foundation**. Kimi K3 and Qwen
   remain separate unresolved adapter/backend registrations.
6. **LOW — stale one-file claims** still live in the Principles check.

Codex's Q7 verdict on the shared blind spot: all three parties handled only
collector *non-zero exits* and cited only the final `write_outputs()` call,
missing both the zero-exit semantic hole and the atomic-write temporaries; and
all three noticed the static-only residual but none noticed that the Boolean
role mechanism cannot enforce the proposed carve-out.

**This vindicates running the third seat.** The two-seat freeze record's own
caveat — "only ONE cross-vendor seat; shared-lineage blind spots are not
excluded" — turned out to be the operative risk, not a formality.

**Superseded FREEZE RECORD (kept for the trail) — read the scope honestly before citing this.**
Frozen after 4 review rounds: Grok R0 (GO-WITH-EDITS, 7 findings) + Fable 5
R1/R2/R3 (GO-WITH-EDITS, 11 findings, then 3 successive freeze checks). Freeze
is declared on the R3 seat's explicit pre-commitment — "once the carve-out edit
lands, I have no further findings and no deletion candidates" — with that exact
edit applied and its citation (`collect-codex-findings.py:134`)
orchestrator-verified. **This is a TWO-SEAT freeze, not the three-way the
protocol prefers**: the Codex seat was quota-dead all session (until 2026-07-29)
and is still owed. The R0 question set is durable below and can go to Codex
unchanged; the document it would review is now the corrected text, per the R1
seat's own sequencing request.

**Convergence caveat (do not overstate)**: after the Codex→Fable substitution
the round had exactly ONE cross-vendor seat (Grok/xAI); Fable 5 and the Opus 5
orchestrator share a vendor. Additionally the R0 seat ran WITHOUT isolation and
read the contracts it was judging against (retroactive disclosure below), so R0
was not context-independent. What carries the freeze is not seat agreement — it
is that every load-bearing finding was re-verified mechanically at file:line by
at least two parties.

**Orchestrator claims retracted during this iter (5 — do not resurrect)**:
(1) "grok is structurally ineligible for the pair role" — false, missing adapter
file; (2) "one file, zero skill-body changes closes the goal" — false, spawn
recipes were binary-hardcoded; (3) the memory-sourced grok recipe (non-existent
tool IDs + `--always-approve`); (4) "zero-MCP is unachievable" — false, two
documented knobs were untried and both work; (5) "a prose static-analysis-only
residual plus a durable-pin gate is sufficient handling for grok's missing
shell" — false, role resolution is a Boolean with no spec-capability dimension,
so the carve-out was unenforceable (Codex; resolved by path A's scoped shell).
Each was caught by a seat, not by the orchestrator. *(Enumeration completed
07-26 per Grok G5 — the count had been corrected to 5 while the list still
stopped at 4.)*

**Build gate**: the frozen predictions are P-0079-A (+F6a), B, C (final-state
delta), D, E, F, G, **and H** — **plus the standing obligation to re-run the
five-invariant isolation table against the final shell-bearing recipe** (the
07-25 receipt certified the pre-shell recipe only; Codex 07-26). Build routes
through the `.devlyn/engines.json`
`executor` pin — **which is `codex` and quota-dead until 2026-07-29**, so the
build itself is blocked on either that window or an explicit pin change.

**Why (pre-flight 0)**: user directive 2026-07-25 — "grok이든 Kimi K3든 Qwen이든
여러 모델들을 pair로 할 수 있게 해야하는데?". The orchestrator had reported
`BLOCKED:invalid-engine-config` as if grok were structurally ineligible for the
pair-judge role. That report was wrong: the harness has no engine whitelist.
`invalid-engine-config` is the fail-closed response to a **missing adapter
file**, and the ordered `pair_judge_priority` plug-in point already exists and is
already implemented end-to-end. The only thing that has never existed is
`_shared/adapters/grok.md`. This iter closes the gap for one engine and, in
doing so, measures whether the declared plug-in point actually holds for a
third-party engine — which is the real open question for Kimi K3 / Qwen later.

**Round record**: R0 run 2026-07-25 as a **two-seat round, not three** — the
Codex seat was unavailable (quota exhausted until 2026-07-29; receipt below).
Reported as a skip, not silently downgraded. **Grok R0: GO-WITH-EDITS**, 7
findings (3 HIGH / 2 MEDIUM / 2 LOW), log `scratchpad/r0-grok.log`.
Orchestrator re-opened every HIGH at the cited lines and **confirms all three**
(verification record below). NOT FROZEN: R1 convergence is still owed, and the
freeze path (Grok-only + orchestrator citation-verification vs. wait for the
Codex seat) is a pending user decision.

**Orchestrator named deltas vs its own R0 packet** (both are retractions of
orchestrator claims, not Grok concessions):
1. WITHDRAW "one file, nothing else closes the goal". Confirmed at
   `engine-preflight.md:51` (only two named directions: Claude→Codex via
   `codex-config.md`, non-Claude→Claude via `adapters/claude.md`) and
   `verify.md:211` ("When the OTHER engine is **Claude**" — conditional, not
   generic). Searched `config/skills/devlyn:resolve/` and
   `_shared/engine-preflight.md` for a generic "OTHER engine E →
   `adapters/<E>.md` `## Invocation`" rule: **none exists**. The plug-in point
   at `engine-preflight.md:21` grants name *validity* only; spawn recipes are
   binary-hardcoded. `grok.md` alone therefore yields a valid name and an
   unwired seat — the same overclaim class as this session's opening misreport.
2. WITHDRAW the memory-sourced grok recipe. Live
   `~/.grok/docs/user-guide/14-headless-mode.md:52` — "the shell tool is
   `run_terminal_cmd`, not `bash`"; `:65-75` — subagent blocking uses special
   `Agent` entries. The draft's `run_terminal_command` and `spawn_subagent` are
   **both non-existent tool IDs**, so they deny nothing. Worse, `:436` —
   `--always-approve` equals `--yolo`/`bypassPermissions` and "auto-approv[es]
   tool executions (**file writes**, command execution, etc.)". The drafted
   recipe was therefore a live P-0079-C (read-only) violation, not a cosmetic
   naming slip. Root cause: a 14-day-old memory recipe was carried into the
   registration without re-measuring against the installed CLI, which the
   memory's own staleness warning called for.

## Receipts (all orchestrator-opened live at citation time, 2026-07-25)

- Adapter set today: `config/skills/_shared/adapters/` = `README.md`,
  `claude.md`, `codex.md`, `omp.md`. **No `grok.md`** → the name is invalid
  config, not an unavailable engine.
- Plug-in point already declared: `_shared/engine-preflight.md:21` — "This is
  the plug-in point for new engines — ship an adapter file and the name becomes
  valid with zero skill-body changes."
- Ordered N-entry pair resolution already specified:
  `_shared/engine-preflight.md:19` — pair judge = first entry of `engines.json`
  `pair_judge_priority` that is adapter-valid ∧ pair-judge-eligible ∧
  non-primary ∧ available; binary claude↔codex complement only when the key is
  absent.
- Config front-end already implemented: `devlyn:engines/SKILL.md:44` — `pair
  <name>[,<name>...]` writes `pair_judge_priority`, refusing names with no
  adapter or with `pair_judge: no`.
- Role-eligibility + API-backend extension points already specified:
  `adapters/README.md:49-50` (`## Role eligibility` fixed ASCII fields;
  `## Invocation` for API-called backends with an adapter-declared probe).
- Emission contract is already multi-engine, not codex-shaped:
  `devlyn:resolve/SKILL.md:300` — "When the OTHER engine is Claude (codex/omp
  orchestrator) ... stdout captured as `.devlyn/claude-judge.stdout`, and **the
  same emission contract applied** to that file."
- Collector is already engine-neutral in logic: `collect-codex-findings.py`
  (140 lines) — "Codex" occurs only in the docstring (:2), one error string
  (:65), self-test assertion text (:92, :99), and the default filenames
  (:74, :76, :120, :122); both paths are `--stdout-file` / `--summary-out`
  parameters.
- grok CLI present on this machine: `command -v grok` → `/Users/aipalm/.grok/bin/grok`.
- grok has **never** been wired into the pipeline: `grep -rn grok` over
  `config/`, `.agents/`, `AGENTS.md`, `CLAUDE.md`, `NORTH-STAR.md` returns zero
  matches. Its live history is orchestrator-invoked R0/R1 registration review
  (DECISIONS 0068.1, 0078.1) — prose review rounds, not `verify.pair.findings.jsonl`
  emission. **The emission behaviour is therefore UNMEASURED, and it is the one
  thing this iter can fail on.**
- Adapter ship conditions: `adapters/README.md:56-59` — prompt-delta content
  requires an empirical A/B showing lift (condition 3), and "If a model performs
  well on the canonical body without delta, ship without one."
- No cohort in flight at registration time (`ps` sweep for cohort/nodeg/ceiling/
  benchmark → empty), so the build window is open.
- **LIVE FAILURE MODE OBSERVED DURING THIS REGISTRATION (2026-07-25)**: the R0
  Codex seat died on invocation — `codex --version` → `codex-cli 0.145.0`
  (probe PASSES), but the actual spawn returned exit 1 in 6s with
  `ERROR: You've hit your usage limit ... try again at Jul 29th, 2026`
  (`scratchpad/r0-codex.stderr`, `[codex-monitored] codex exited: code=1
  elapsed=6s`). Two consequences, both directly on this iter's goal:
  1. With only the binary claude↔codex complement reachable
     (`engine-preflight.md:19`), **the harness has no pair judge at all right
     now** — every automatic VERIFY pair route degrades to solo-with-reported-
     skip (`engine-preflight.md:12`), and the machine-local `executor: codex`
     pin hard-halts `BLOCKED:codex-unavailable` (`engine-preflight.md:21`).
     A second adapter-backed pair engine is the direct remedy. This is an
     **observed** failure mode, so the pure-addition citation required by
     CLAUDE.md's subtractive-first rule is now evidential, not only the user
     request.
  2. It re-confirms the `adapters/claude.md` `## Invocation` rule that
     `command -v` is *necessary, not sufficient* — a quota-exhausted engine
     passes the default probe. `grok.md`'s probe must therefore be specified as
     probe + spawn-failure-is-same-class, not `command -v grok` alone.

## Mechanism (proposed; frozen only after R0+R1)

**R0-amended scope: one generic rule + one adapter file.** The original
"one file, nothing else" shape is withdrawn (delta 1 above) — it makes the name
valid without making the seat reachable.

0. **Generic OTHER-engine spawn rule** (NOT a grok special-case) in
   `resolve/SKILL.md` (~:300), `references/phases/verify.md` (~:201-217), and
   `engine-preflight.md:49-51`: *Codex keeps `codex-monitored.sh`; every other
   OTHER engine follows `_shared/adapters/<name>.md` `## Invocation`; capture
   `.devlyn/<name>-judge.stdout`; normalize with `collect-codex-findings.py
   --devlyn-dir "<abs repo>/.devlyn" --stdout-file <name>-judge.stdout`; the
   timeout marker's `engine` field is the resolved name, not `<codex|claude>`.*
   **The absolute `--devlyn-dir` belongs in this generic rule, not in a
   per-adapter footnote** (Grok 07-26): any adapter whose `## Invocation` spawns
   from a non-repo cwd — which grok's isolation *requires* — would otherwise have
   the collector resolve `.devlyn/` against that cwd
   (`collect-codex-findings.py:128`). Precise failure (Fable 07-26, traced):
   `stdout_path.is_file()` fails first, so the realistic symptom is exit 1 and a
   spurious BLOCKED — an out-of-repo *write* needs a pre-existing
   `$NEUTRAL/.devlyn/`. Same fix, honest mechanism. This is the one-time fix that stops
   Kimi K3 / Qwen from re-opening the identical gap — a per-engine branch in the
   skill body would be the wrong shape. Emission/merge need no change: the paths
   are already `*-judge.stdout`-globbed and engine-neutral (Q3 confirmed).
   **Edits are REPLACEMENTS of the binary wording, not additions** (R1 Q1) —
   `engine-preflight.md:51` and `verify.md:210-217` become false-by-omission
   otherwise; net line count ~flat. Item 0 carries three more corrections in the
   same sweep:
   - **(F2 + Codex finding 2) Collector fail-closed — BOTH exit paths.**
     (a) *A non-zero `collect-codex-findings.py` exit means NO canonical findings
     file may be written and the pair source is BLOCKED
     (`verify.pair.emission-contract`) — never proceed to merge treating
     unparsed stdout as diagnostic-only.*
     (b) **Zero-exit hole — missed by all three prior parties, verified at
     `collect-codex-findings.py:64-68`.** The guards reject only `summary is
     None` with no findings, and only exact uppercase `NEEDS_WORK|FAIL|BLOCKED`
     with no findings. So `{}`, `{"verdict":"pass"}` (lowercase), or any unknown
     verdict **exits 0**, writes an empty canonical file (`:109-114,133-135`),
     and `verify-merge-findings.py:877-878` then defaults the pair source to
     PASS. Required hardening, in the collector itself: with zero findings, only
     an exact `PASS` verdict may succeed; `{}`, missing verdict, lowercase, and
     unknown verdicts must exit non-zero into path (a). Ship self-tests for the
     four DISTINCT shapes (Codex 07-26: the earlier list double-counted `{}` and
     "missing verdict"): **no SUMMARY line at all**, **empty SUMMARY object**,
     **lowercase `pass`**, **unknown verdict string** (the script already carries
     a `--self-test` harness).
     **(c) Merge-side default — DECIDED, not left silent (Fable E5).**
     `verify-merge-findings.py:877-878` defaults an otherwise-empty pair source
     to `PASS`; that is the root enabler of both the zero-exit and the
     truncation holes. This iter does **NOT** change it: the default is
     engine-neutral, pre-existing, and shared by the codex and claude judges, so
     altering it is pipeline-wide scope this registration is not authorized to
     take (Goal-locked). The accepted guard is the collector hardening in (b)
     plus the (a) ordering rule plus **P-0079-H**, and the merge-side default is
     recorded here as a **named residual with its own follow-up registration**.
     Whoever takes it should note it is the single point where three separate
     failure paths converge on a false PASS.
     Verified gap: `verify-merge-findings.py:877-878` sets
     `source_verdicts["pair_judge"] = "PASS"` when no finding parsed and no
     timeout marker exists, and `:909-911` silently `continue`s past unparseable
     lines — so prose output, the likeliest failure shape of an unmeasured
     emitter, yields a silent pair PASS. Engine-neutral debt; this iter is where
     it becomes live.
   - **(F7) Risk-probe string genericization.** `resolve/SKILL.md:120` hardcodes
     "`BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable`" (verified).
     `engine-preflight.md:19` routes risk-probe derivation through the SAME pair
     resolution item 0 changes, so with `pair grok` pinned that string becomes a
     false user-visible verdict on ship. Replace with the already-generic
     `BLOCKED:<engine>-unavailable` form of `engine-preflight.md:11`. Subtractive.
     (Named-delta reversal of R0 finding 6's follow-up disposition.)
   - **(F9) `resolve/SKILL.md:59` qualification.** Verified text: "when a new
     model adapter ships in `_shared/adapters/`, that engine becomes selectable
     via `--engine <model>` without further skill changes" — false once the first
     `executor: no` adapter ships. Behaviour stays safe via
     `engine-preflight.md:23`, but the sentence could steer the orchestrating
     model at runtime. One clause: selectable *for the roles its adapter declares
     eligible*.

1. `## Role eligibility` — `executor: no`, `pair_judge: yes`. grok has only ever
   run as a read-only independent seat; declaring `executor: no` makes an
   `executor grok` pin fail as invalid config (`engine-preflight.md:23`) rather
   than silently routing implementation to an unmeasured engine.
2. `## Invocation` — **the single ship-recipe is the measured block in
   "R1-F1 DISCHARGED" below; it is the only recipe in this document.** The
   pre-measurement draft that stood here has been deleted rather than kept
   alongside it (R2 finding 1: two divergent recipes in a frozen registration
   invite the build phase to grab the wrong one; item 0's own
   replacements-not-additions discipline applies to this document too).
   Non-recipe facts that still belong in the adapter prose:
   `--permission-mode plan` stays forbidden headless (silently blocks all tools,
   returns an empty review); `--always-approve` is **banned in this adapter**
   (`14-headless-mode.md:436` — equivalent to `--yolo`/`bypassPermissions`,
   auto-approves file writes); `--tools`/`--disallowed-tools` are headless-only —
   in the TUI, :46 "a warning is printed and the flag is ignored" (quoted
   exactly; an earlier draft misquoted this as "silently ignored"); when both are
   present
   `--disallowed-tools` wins (:81), and it removes tools **entirely** whereas
   permission rules only gate execution (:85).
   **Binding allowlist obligation (Fable E2)**: the adapter prose must state that
   the `--allow` rule covers the *full* probe command family the judge may need
   AND that the judge prompt names the exact permitted command(s). An
   under-scoped allowlist is not a mild defect here — per the 07-26 measurement
   it destroys the entire review at exit 0. Enforced by the frozen
   anchor-derivation rule under P-0079-F.
   Then `collect-codex-findings.py --stdout-file grok-judge.stdout
   --summary-out grok-judge.summary.json`. Exit 124 → orchestrator writes
   `.devlyn/verify.pair.timeout.json` with `engine: "grok"`, same as the
   codex/claude directions.

3. **`engine-doctor.sh` catalog row** (R0 finding 5) — `engine-doctor.sh:20-23`
   hardcodes `TARGETS=(claude codex omp pi)` / `BINARIES` / `INSTALL_HINTS`, and
   `devlyn:engines/SKILL.md:28` drives its status table from the doctor. Without
   a grok row the user-facing front-end for this very feature never lists grok,
   even though the pin path works (pin validation reads the adapter file, not
   the doctor). **Four parallel arrays, not three** (Fable E4): `TARGETS`,
   `KINDS`, `BINARIES`, `INSTALL_HINTS` (`engine-doctor.sh:20-23`) — a row added
   to three of four leaves the arrays misaligned. Same sweep:
   `devlyn:engines/SKILL.md:28` carries its own engine enumeration; prefer
   de-enumerating it over adding another hardcoded list. In scope because the user's goal is that
   these engines are *usable as pair*, and discoverability in `/devlyn:engines`
   is part of that.
   **(F4) Second hardcoded catalog, same class:** `scripts/lint-skills.sh`
   `critical_path_files` enumerates adapter files by name — verified list
   includes `_shared/adapters/README.md`, `claude.md`, `codex.md`, `omp.md` and
   nothing else. Without a `grok.md` row the installed-mirror parity check
   silently excludes the new adapter — precisely the drift class iter-0078's
   byte-identity work exists to prevent. One line. R0 found the doctor catalog
   and stopped searching the class; R1 found the second instance.

4. **(F5) Widen `adapters/README.md:49` before the precedent ships.** Verified
   Same edit widens `README.md:50`'s `## Invocation` definition (Fable E7),
   which today describes it as being for "backends called over an API instead of
   a CLI" — grok is a CLI backend that nonetheless needs a full `## Invocation`
   block (isolation env, neutral cwd, allowlist), so the section's stated purpose
   must cover CLI backends with non-default invocation contracts too. Verified
   text: the `## Role eligibility` section is "Present only when a backend is
   **structurally unable** to fill a role". grok is structurally *able* (it ships
   `run_terminal_cmd`, `search_replace`); its executor exclusion is
   **certification-based**, which the section as written cannot express. And
   `grok.md` would be the FIRST live instance of this section (claude/codex/omp
   all lack it), so shipping under false semantics sets the precedent wrong.
   Edit: "structurally unable **or not certified for**". A few words, and it makes
   the F3 decision below coherent.

**Lint constraint on the shipped `grok.md`** (repo gotcha, check 10a1 at
`lint-skills.sh:1603-1609`): the literal string `.claude/skills/_shared` is
banned anywhere under `config/skills`, comments included. The measured recipe
uses `$DEVLYN_SHARED_DIR` and is compliant; the ban is on that specific path
literal, not on `.claude` generally, so documenting the vendor MCP scan source is
fine.

**Explicitly NOT in this iter** (subtractive-first):
- No prompt-delta sections (Identity / Output discipline / Anti-patterns) —
  `README.md:56-59` condition 3 is unmet; no A/B has been run.
- No new collector. If the neutral collector suffices, the only honest cleanup
  is a later rename, and a rename is not required to close this goal.
- No `engines.json` default change. Unset `pair_judge_priority` must keep
  behaving as the binary claude↔codex complement, byte-identically.
- **Risk-probe sub-role — named scope line (Fable E6)**: `engine-preflight.md:19`
  routes *both* VERIFY pair-JUDGE and risk-probe derivation through the same
  pair-judge resolution, so pinning `pair grok` makes grok eligible for
  risk-probe work too. This iter's predictions measure only the VERIFY pair path;
  **the risk-probe sub-role is untested for grok and rides the same
  durable-pin seat-fitness gate.** Named, not silently inherited.
- No Kimi K3 / Qwen adapters — neither CLI resolves on this machine
  (`command -v` empty); they need a backend decision (endpoint/key) first, and
  ride the API-form `## Invocation` path in a later registration.

## Frozen predictions (stated BEFORE any measurement)

- **P-0079-A (name validity, mechanical — scope narrowed by R0)**: with
  `grok.md` present, `/devlyn:engines pair grok` writes
  `pair_judge_priority: ["grok"]` and role resolution returns grok as pair judge
  with **zero edits to any skill body or shared script**. Falsified if any file
  outside `adapters/grok.md` must change to make the name *valid*.
  **Scope caveat (R0 finding 1)**: this predicts validity ONLY. It says nothing
  about reachability, and passing it while the seat is never spawned is exactly
  the overclaim this iter withdrew — P-0079-F is the reachability test, and the
  generic rule of mechanism item 0 is deliberately outside P-A's "zero edits"
  claim.
  **(F6a) Added mechanical check**: `/devlyn:engines executor grok` must REFUSE
  with `BLOCKED:invalid-engine-config`, not `BLOCKED:grok-unavailable`. This
  exercises the eligibility-refusal path, which has never fired live — no adapter
  shipped before this one carries a `## Role eligibility` section at all. The
  registration argues item 1 is justified *because* this path works; until now
  nothing tested that.
- **P-0079-B (emission contract, the real risk — REWRITTEN 07-26; the previous
  version contradicted itself after a partial threshold edit, caught by Codex)**:
  grok is invoked with the codex-direction pair-JUDGE prompt verbatim; its stdout
  is normalized by `collect-codex-findings.py`.
  - **Run allocation**: 6 runs total — **3 on fixture (i)**, **3 on fixture
    (ii)**. All 6 must succeed. (Previously "5 of 5 across two fixtures" left the
    split unspecified.)
  - **Fixture (i) seeded-finding diff** → success = collector exit 0 AND ≥1
    severity-valid JSONL finding object in the canonical file.
  - **Fixture (ii) clean diff** → success = collector exit 0 AND a
    `# SUMMARY {"verdict":"PASS"}` object with an **empty** findings list. Note
    this is deliberately an *empty* canonical file — the earlier wording
    "non-empty canonical findings file" was wrong for this route and is deleted.
  - **Free-text `PASS` is a FAILURE** on either fixture:
    `collect-codex-findings.py:64-65` admits an empty finding list only when a
    `# SUMMARY` object parsed; a bare `PASS\n` exits 1 (R0 finding 4, live-probed).
  - **Falsified by any run failing its fixture's criterion (i.e. below 6/6).**
  - **Threshold provenance**: raised from the original 4/5 on Codex finding 4's
    named delta — 4/5 admits a 20% format-failure rate into a *production* route,
    while the earlier "keep 4/5" endorsement from the R1 seat was reasoning about
    a *measurement* threshold. This reverses that endorsement on the
    production-vs-measurement distinction, not on a new measurement. Still true
    and still worth stating: **no measured claude/codex emission baseline exists**,
    so neither 4/5 nor 6/6 is empirically derived. **Arithmetic honesty (Fable
    E1)**: an all-must-pass gate compounds — at a per-run emission reliability of
    0.95 a 6/6 gate passes ~74% of the time, at 0.90 ~53%. A failed gate is
    therefore weaker evidence of an unfit engine than it looks. If 6/6 proves
    unreachable, that is FS-0079-A firing and the recorded outcome is
    VALID-NEGATIVE — **not** a licence to relax the bar after seeing the result
    (principle #3).
- **P-0079-C (read-only, in-tree AND out-of-tree)**: across **all 6 P-B runs** (corrected from a stale "5" that contradicted P-B, Codex 07-26) the repo
  tree is byte-identical before and after (tree-neutral control, same shape as
  0078's clean controls). Any mutation falsifies. **Out-of-tree clause (R2
  finding F1b — the half of R1-F1 the first discharge silently dropped)**: side
  effects must be confined to the ephemeral `GROK_HOME`, which is discarded.
  Measured baseline: after one run that dir gains `sessions/`, `logs/`,
  `active_sessions.json`, `models_cache.json`, `worktrees.db`, `bundled/`,
  `docs/`, `relocations/`, `.metadata_version` and lock files — so "auth.json
  only" is FALSE and is not the bar. The bar is **confinement**: zero writes
  outside `$GROK_HOME` and `$NEUTRAL`, and zero delta to the real `~/.grok` and
  to any memory store.
  **Permitted-write carve-out (R2-final, blocking defect in the first draft)**:
  the recipe itself writes `$REPO/.devlyn/grok-judge.stdout` and
  `.../grok-judge.stderr`, so an unqualified "repo tree byte-identical / zero
  writes outside `$GROK_HOME`" would be falsified by the recipe's own output
  capture. **Stated as a FINAL-STATE delta, not a write-event allowlist (Codex
  finding 3, verified at `collect-codex-findings.py:25-32`)**: `atomic_write`
  creates a randomly-named `NamedTemporaryFile` in the target directory then
  renames it, and `path.parent.mkdir(parents=True, exist_ok=True)` may create the
  directory — transient paths necessarily exist mid-run, so an enumeration of
  "permitted writes" was false as worded. The prediction is therefore: **after a
  completed run the final byte delta in the repo tree is confined to exactly
  these four recipe-authored files**, and same-directory atomic-write
  temporaries are permitted transiently but must be absent at the end:
  `grok-judge.stdout`, `grok-judge.stderr`, `verify.pair.findings.jsonl`
  (written **unconditionally** by the collector — `collect-codex-findings.py:134`
  `write_outputs(...)`, `--out` default — including on an empty-findings PASS),
  and `grok-judge.summary.json` (written when a `# SUMMARY` object parses).
  **Seat-authored writes remain zero.** Every other byte in the repo tree must be
  identical. The first draft named only the two captures and was therefore still
  self-falsifying: P-B's success criterion runs the collector on the same 6 runs,
  and this iter's own `--devlyn-dir "$REPO/.devlyn"` fix is what aims those
  writes into the tree. Rejected alternative: snapshotting the tree
  post-spawn/pre-collect — it leaves the collector's writes unaudited and splits
  one control into two regimes. Written into the prediction NOW, before
  measurement — amending it after a failing run would be the retroactive
  prediction edit principle #3 forbids. (`.gitignore` does not rescue the
  unqualified form: the 0078 control precedent treated a gitignored
  `__pycache__` write as a real defect.)
- **P-0079-D (fail-closed)**: with `pair grok` pinned and grok masked off PATH,
  the run halts `BLOCKED:grok-unavailable` — never a silent solo downgrade.
  A silent downgrade falsifies (principle #1).
- **P-0079-E (zero regression — concretized per Codex finding 4)**: with
  `pair_judge_priority` unset, a VERIFY run resolves **pair engine = the binary
  claude↔codex complement** (named explicitly, not "unchanged"), records the same
  pair trigger reason it recorded pre-iter, and produces the same artifact set
  (`verify.pair.findings.jsonl` + the engine's `*-judge.stdout`, no
  `grok-judge.*`). Falsified by any delta in resolved engine, trigger reason, or
  artifact set.
- **P-0079-H (out-of-allowlist containment — added 07-26 from the scoped-shell
  measurement)**: a judge run whose prompt induces a command outside the
  `--allow` rule must end with the pair source **BLOCKED**, never PASS.
  Measured basis: such an attempt silently truncates the review and **exits 0**
  with the canary unwritten — so containment holds but the review is lost, and
  only the F2 collector rule turns that into a BLOCKED verdict. This prediction
  exists because the failure is invisible at the process level: exit 0, empty
  stderr, partial stdout. Also satisfies Codex finding 4's failure-injection ask.
- **P-0079-F (end-to-end pair fire — added by R0 finding 3)**: with
  `pair_judge_priority: ["grok"]` pinned, a real `/devlyn:resolve --verify-only`
  run reaches VERIFY, spawns grok **through the generic rule of mechanism item 0**
  (no grok-named branch anywhere in a skill body), and produces
  `.devlyn/grok-judge.stdout` → a canonical `.devlyn/verify.pair.findings.jsonl`
  that is **present and mergeable — its content may legitimately be empty on a
  clean PASS** (Grok 07-26: the earlier "non-empty" wording was the same defect
  as P-B's and would mis-score a valid clean pair PASS)
  → merged state with `sub_verdicts.pair_judge != null`. Falsified if the
  orchestrator never spawns grok, or if making it spawn requires a per-engine
  branch. **This is the prediction P-A..E could not catch**: every one of them
  can pass while the seat is still never invoked (R0 Q4 gap list).
  **Strengthened 07-26 (Codex Q2): the P-F fixture MUST be a mandatory-probe
  spec** — one combining priority ordering with rollback/blocked-interval
  behaviour, so the dominance-loss probe is mandatory (`SKILL.md:291`;
  `verify.md:193-199`). The run passes only if grok **executes** that probe
  through the `--allow` rule and the full probe result appears before its valid
  JSONL/PASS output. **The fixture spec's `## Verification` must itself contain
  the backticked probe command the allow rule derives from** (Fable Q5.3) —
  otherwise the anchor-derivation rule has no source for this fixture class and
  the two requirements do not compose. Rationale: path A claims `pair_judge: yes` is now truthful
  for the whole role; a fixture that never requires a probe would leave that
  claim untested, and P-H proves only rejection safety, not role performance.
- **Frozen derivation rule for the allow-list (Codex Q2 — enforceability moved
  from role selection to invocation construction, so the construction must be
  mechanical, not a placeholder)**: `Bash(<repo probe command family> *)` in the
  recipe is a slot, and the slot is filled by ONE rule — **the command anchor
  placed in the judge prompt and the string inside `--allow` are derived from the
  same source and must be identical**. **The source, stated completely (Codex
  07-26 — the earlier text cited only the solo-headroom clause, which
  `SKILL.md:291` supplies *only when such a hypothesis exists*; a mandatory
  dominance-loss spec need not contain one, leaving the generic case
  unspecified)**, in precedence order:
  1. the spec's solo-headroom hypothesis backticked observable command, when the
     spec has one (`SKILL.md:291`);
  2. otherwise, the backticked commands in the spec's `## Verification` bullets —
     the same bullets pair-JUDGE is required to target;
  3. otherwise, the repo's existing test/CLI runner, which `SKILL.md:291` already
     admits as permitted pair-JUDGE material ("the repo's existing CLI/API/test
     runner").
  If a spec yields no command under any of the three, it has no executable
  verification and the probe obligation does not arise — running static for
  *that* spec is correct, and is not the withdrawn static-only claim, which
  failed because it asserted static sufficiency for specs where probes ARE
  mandatory. `adapters/claude.md` fills its `Bash(<repo test command> *)` slot the
  same dynamic way. An invocation whose
  prompt anchor and allow rule diverge is a construction defect, and — per the
  07-26 measurement — it manifests as a silently truncated review, so it must be
  caught at construction time, not runtime.

- **P-0079-G (spawn-failure fail-closed — added by R1 finding 6b)**: with
  `pair grok` pinned and the binary present but the spawn failing (auth broken or
  wrapper-simulated non-zero exit), the run halts `BLOCKED:grok-unavailable` —
  never a silent solo downgrade. P-0079-D covers only the *masked-binary* path;
  **the failure class actually observed this session was the other one** — codex
  passed `command -v` and died on spawn. The registration mandates
  "probe + spawn-failure-is-same-class" in `grok.md`; this is the prediction that
  tests it.

## Seat-fitness decision (R1 finding 3 — silence was the one disallowed option)

CLAUDE.md's Evolution loop binds: "On any model/version change, re-certify engine
seats with the seat-fitness instrument before re-pinning `.devlyn/engines.json`
(NORTH-STAR ceiling contract; iter-0064)." Seating a brand-new engine is a
stronger case of the same class.

**Decision — scope the contract to the commitment, not the capability.** This
iter ships the *capability* (adapter + generic spawn rule + doctor/lint rows) and
does NOT write a durable `pair_judge_priority: ["grok"]` pin. The contract gates
**re-pinning `engines.json`**, so:
- Capability + the frozen predictions here (P-B emission, P-F reachability, and a
  **re-run of the five-invariant isolation table against the final shell-bearing
  recipe** — NOT the 07-25 receipt, which certified the pre-shell recipe; Codex
  07-26) = the ship gate for this iter. No new instrument needed — subtractive.
- A **durable `pair grok` pin requires a seat-fitness run first**, unchanged from
  the standing contract. FS-0079-B's version-drift⇒re-gate rule carries the
  ongoing obligation.

**RESOLVED 2026-07-26 by path A — the static-only residual below is superseded.**
Codex showed the prose carve-out was unenforceable (role resolution is a Boolean
`pair_judge: yes|no` with no spec-capability dimension), so the fix is capability
parity, not a narrower promise: grok now ships with a measured scoped probe
channel (`--permission-mode dontAsk` + `run_terminal_cmd` + `--allow
'Bash(<probe family> *)'`), matching what `adapters/claude.md` already grants its
judge. **Residual, explicitly NOT claude-parity (Grok 07-26)**: claude's
`dontAsk` surfaces a denied tool call as a failed call the model can report;
grok's denial path instead **silently truncates the review at exit 0**
(measured). So the scoped shell reaches capability parity but not *deny-semantics*
parity — P-0079-H is the guard, and the frozen anchor-derivation rule below is
what keeps the seat inside its allowlist in the first place.
`pair_judge: yes` is therefore truthful for the whole role, and the
P-B/P-F "non-mandatory-probe target diff" constraint below is **withdrawn** —
the fixtures may and should include a mandatory-probe spec shape.
*(The superseded static-only residual text was DELETED 07-26 per Fable Q4.1 —
every operative claim in it is withdrawn, the paragraph above states what it
said, and git history carries the bytes.)*

**Named residual, not hidden**: P-B and P-F measure emission *format* and
*reachability* — neither measures grok's **judgment quality**. Because
`verify-merge-findings.py` takes the max severity across judges, a
low-quality pair judge can inject false HIGH findings and flip a run to
NEEDS_WORK. That risk is real and is exactly what the seat-fitness gate on the
durable pin exists to hold. Do not treat a passing P-B/P-F as quality evidence.

## Falsifiers

- **FS-0079-A**: grok cannot hold the emission contract (P-B below 6/6). Then a
  bare adapter is NOT sufficient for a third-party engine. *(Attribution to the
  "ship one file, zero skill changes" claim at `engine-preflight.md:21` DELETED
  per Codex 07-26: that claim is about **name validity**, which an emission
  failure does not bear on. This falsifier is about grok's emission fitness and
  nothing else.)* Record it; the fix (prompt
  delta or per-engine collector) is a SEPARATE registration, not an inline
  patch — No Unregistered Survival.
- **FS-0079-B**: the grok CLI's tool/flag surface drifts by version, so the
  probe and `--disallowed-tools` list are version-bound. If so the adapter must
  record the measured CLI version as cohort identity, same as 0068.1's
  drift⇒re-gate rule.
- **FS-0079-C**: adding a third adapter perturbs the default (unset) route.
  P-0079-E is the guard; any delta means the plug-in point is not additive.
  R0 Q5 searched for an automatic perturbation path and found none (no
  adapter-directory scan in default pair selection; the doctor never auto-writes
  `engines.json`), so this is expected to hold — it stays a guard, not a bet.
- **FS-0079-D (attribution rule, from R0 synthesis)**: if P-0079-B passes on
  manual smoke runs but P-0079-F fails — grok emits correctly, yet
  `/devlyn:resolve` never spawns it — the defect is a **harness plug-in
  overclaim**, NOT a grok capability failure. Fix mechanism item 0; do not
  record it as an engine deficiency and do not add a per-engine branch to pad
  around it. This falsifier exists because misattributing it would wrongly
  discourage the whole N-model direction.

## R0 record (durable — review packets are ephemeral, per 0068.1 convention)

**Seat status**: Grok GO-WITH-EDITS (log `scratchpad/r0-grok.log`, session-scoped).
Codex seat NOT RUN — quota exhausted until 2026-07-29. **R1 seat substituted to
Fable 5 by user directive 2026-07-25** ("codex cli gpt 5.6-sol 대신 fable 5 로
해보자") rather than waiting for the Codex quota window. Consistent with the
standing engine-tiering directive (fable = orchestrator/verifier only, never a
test arm): a review seat is a verifier.

**Two caveats that must not be glossed when reading the convergence:**
1. **Independence is weaker than a Codex round.** Fable 5 and the orchestrator
   (Opus 5) are both Anthropic Claude-family models; Codex would have supplied a
   third vendor. After this substitution the round has exactly ONE cross-vendor
   seat (Grok/xAI). Agreement between the Fable seat and the orchestrator is
   therefore weaker evidence than Grok↔Codex agreement was in 0068.1/0078.1 —
   shared-lineage blind spots are not excluded. The R1 packet compensates by
   making "what did both previous seats miss?" an explicit question (Q7), but a
   compensating prompt is not the same as an independent vendor.
2. **This is R1-shaped, not a clean second R0.** Grok's edits were already folded
   into the document the Fable seat reads, so the two seats did NOT see identical
   inputs. Do not report this as "independent convergence" the way 0078.1 could.

**NAMED DEVIATION**: `adapters/claude.md` `## Invocation` mandates omitting
`--model` (zero-touch flagship). This seat deliberately passes
`--model claude-fable-5` because the seat identity IS the variable under user
direction. Deviation is scoped to out-of-pipeline review rounds; the adapter's
rule for pipeline pair-JUDGE calls is unchanged.

**R1 owed→running; iter is NOT frozen.**

**The six R0 questions — reuse verbatim for the Codex seat so convergence is
comparable** (each answer must cite file:line; negative existence claims require
an active search at write time):
1. Mechanism minimality — what must be DELETED from scope, what EXCLUDED item
   must be included for the goal to actually close?
2. Role eligibility — is `executor: no` / `pair_judge: yes` right for grok, and
   does an `executor grok` pin fail as invalid-config (not unavailable)?
3. Collector reuse — is `collect-codex-findings.py` engine-neutral, or is there
   codex-specific coupling anywhere in the emission/merge path?
4. Predictions — falsifiable? correctly thresholded? what failure mode does
   NONE of them catch?
5. Default-route regression — where could a third adapter perturb an unpinned
   user's behaviour?
6. Strongest counter AGAINST shipping, strongest form of the registration's OWN
   position, then synthesis. Refute-only output is rejected.

**Grok R0 findings ledger** (1-5 already folded into Mechanism/Predictions above):
| # | Sev | Claim | Disposition |
|---|---|---|---|
| 1 | HIGH | Spawn recipes binary-hardcoded; "one file" ≠ usable seat | ACCEPTED → mechanism item 0 |
| 2 | HIGH | Recipe tool IDs wrong; `--always-approve` unsafe | ACCEPTED → recipe rewritten |
| 3 | HIGH | No prediction catches "orchestrator never spawns grok" | ACCEPTED → P-0079-F |
| 4 | MED | P-B "PASS line" imprecise vs collector | ACCEPTED → P-B rewritten |
| 5 | MED | `engine-doctor.sh:20` catalog hides grok | ACCEPTED → mechanism item 3 |
| 6 | LOW | Residual binary wording (`resolve/SKILL.md:120` risk-probe strings, `state-schema.md:53`) | Widen timeout wording with item 0; risk-probe strings = follow-up |
| 7 | LOW | Subtractive exclusions all correct; add no prompt deltas | ACCEPTED, no change |

## R1 record — Fable 5 seat (2026-07-25): GO-WITH-EDITS, **FREEZE-READY: NO**

11 findings. Endorses R0 findings 1-5 and 7 with independent re-verification at
live lines; one named-delta disagreement (F7 below). Two HIGH findings that
**both prior seats and the orchestrator missed**, both orchestrator-verified:

- **R1-F1 (HIGH) — the grok recipe has no isolation contract, and grok's
  defaults breach the harness's own pair-judge isolation bar.** The bar is
  explicit: codex gets `--ignore-user-config --ignore-rules --ephemeral
  --disable hooks` (`codex-monitored.sh:105-114`), rationale at
  `verify.md:204-206` ("Isolation blocks user config, AGENTS.md, hooks, and
  project rules"); claude gets the hermetic trio (`adapters/claude.md:39-43`).
  The drafted grok recipe has **no analogue of any of them**.
  **Orchestrator verification — `grok inspect` run live in this repo, 2026-07-25**
  (grok 0.2.112), measuring what a bare `grok -p` seat actually loads:
  - **MCP Servers (6)**, auto-scanned from `~/.claude.json` per
    `07-mcp-servers.md:214` ("The Claude and Cursor MCP sources are scanned by
    default"): `pyx-memory`, `MCP_DOCKER`, `codex-cli`, `pencil`, plus plugin
    servers. **`pyx-memory` writes persistent memory; `MCP_DOCKER` carries
    GitHub write tools.** A "read-only judge" with those in reach is not
    read-only.
  - **Project Instructions (3), ~10.5k tokens** — `~/.claude/CLAUDE.md`
    (global/private), repo `AGENTS.md`, repo `CLAUDE.md`. Exactly the injection
    the pair-judge contract forbids.
  - **Hooks (33)**, **Skills (99)**, **Agents (5)**, permissions loaded from
    `~/.claude/settings.json`.
- **R1-F2 (HIGH) — no fail-closed rule binds the collector's exit code; prose
  output yields a silent pair PASS.** Verified: `verify-merge-findings.py:877-878`
  — `if source_verdicts["pair_judge"] is None and timeout_marker is None:
  source_verdicts["pair_judge"] = "PASS"`; the per-line scan `continue`s past
  unparseable lines (`:909-911`). `collect-codex-findings.py:64-65` rejects prose,
  but no skill text branches on that exit code. **Prose is the most likely failure
  shape for an unmeasured emitter**, so this engine-neutral debt becomes live
  exactly here.

**RETROACTIVE DISCLOSURE — the R0 grok round was run without isolation.**
The orchestrator invoked the R0 seat as `grok -p ... --always-approve
--disallowed-tools "<partly non-existent IDs>"`. Per the measurement above that
seat had, with auto-approval active: 6 MCP servers including a writing memory
server and GitHub write tools, 33 hooks, and ~10.5k tokens of injected
harness/global instructions. Consequences, stated plainly:
1. **Repo integrity verified clean** — `git status` shows only the two
   orchestrator-authored files; HEAD unmoved at 9a7c359. No observed mutation.
   Non-repo side effects (memory writes, network egress) cannot be excluded by
   inspection, only bounded by the fact that the seat returned a normal review.
2. **The round's independence claim does not hold.** The R0 seat read
   `CLAUDE.md` and `AGENTS.md` — the very contracts it was asked to judge the
   registration against. Its findings survive because every one was
   re-verified mechanically at file:line by the orchestrator and again by the
   Fable seat; the *independence property* does not. Do not cite the R0 round as
   context-independent.
3. This is itself the strongest available evidence for R1-F1: the isolation gap
   is not theoretical, it was exercised.

**R1 findings ledger** (F1/F2 above; remainder condensed):
| # | Sev | Claim | Disposition |
|---|---|---|---|
| F3 | MED | Seat-fitness re-cert contract (CLAUDE.md Evolution loop, iter-0064) unmentioned | Must decide: gate or reasoned carve-out. Silence disallowed |
| F4 | MED | Second hardcoded catalog: `lint-skills.sh:58-93` `critical_path_files` enumerates adapters by name | → mechanism item 3 gains a lint row |
| F5 | MED | `README.md:49` says Role-eligibility is for *structurally unable* backends; grok is *uncertified*, not unable — and grok.md would be the FIRST live instance | Widen README semantics before the precedent ships |
| F6 | MED | No prediction exercises (a) `executor grok` refusal, (b) spawn-failure fail-closed — the exact class observed with codex this session | Extend P-A; add or explicitly name-as-untested the spawn-failure path |
| F7 | MED | **Named-delta disagreement with R0 finding 6**: risk-probe `BLOCKED:codex-unavailable` strings are not a separate surface — `engine-preflight.md:19` routes risk-probe derivation through the same pair resolution item 0 changes, so a pinned `pair grok` makes that string a false user-visible verdict on ship | Accept: fold into item 0's sweep, not follow-up |
| F8 | LOW | `--reasoning-effort high` deviates from both judges' `medium` | RESOLVED — measured recipe ships `medium` |
| F9 | LOW | `resolve/SKILL.md:59` becomes false for `executor: no` adapters | ACCEPTED → folded into item 0's sweep |
| F10 | LOW | allowlist+denylist may be a redundant dual layer | **DISPOSITION SUPERSEDED.** First answer ("not redundant — `--deny` is the only layer that contains MCP") was true only of the deny-only recipe. After the removal knobs were measured, deny became a genuine second layer on one bug and was **deleted**; F10's original suspicion was correct. Surviving layers: `--tools` allowlist, `--disallowed-tools` removal (`Agent` + MCP meta-tools), plugin knob — each closes a distinct surface |
| F11 | LOW | R0 receipts unauditable from the seat's sandbox | **Partly a false alarm**: the logs exist at an absolute scratchpad path outside the repo, which the seat's cwd-scoped Glob could not see. The underlying suggestion (attach quota-class receipts durably) is accepted |

**Q7 (what both prior seats missed)** — the structural diagnosis is worth
keeping: both seats treated "read-only" as a *tool-filtering* problem and never
audited grok's *default context and side-effect assembly*; both anchored on the
one guide file the packet named (`14-headless-mode.md`) and never swept sibling
guides, where the decisive facts sat one grep away. Plus: **the R0 seat was grok
reviewing grok's own wiring-in** — the two converging parties were the proposer
and the subject.

**Q8 (overreach audit)** — no folded edit should be reverted; each has a
concrete failure mode. The honest verdict runs the other way: the folded scope
was *incomplete* for its own catalog class (F4) and isolation class (F1).
"Growth from one file to three surfaces was not accretion; it was the
registration discovering the true size of the goal."

**Q9 (premature generalization?)** — no. Item 0's shape is copied from the
already-shipped, already-measured claude direction, and every layer below skill
prose was engine-neutralized in prior iters; item 0 completes an existing
trajectory whose last hardcoded layer is prose. Boundary held: codex stays a
named exception this iter (collapsing `codex-monitored.sh` into the generic rule
would be unregistered scope).

**Remaining blockers to freeze (R1)**: F1 isolation invariants + measured flag
set written into `grok.md` with `grok inspect` zero-MCP evidence required, and
P-C extended to cover out-of-tree side effects; F2 collector-exit fail-closed
sentence into item 0; F3 seat-fitness decision; F4 lint row; F5 README semantics;
F6 predictions; F7 risk-probe genericization into item 0's sweep.

**Synthesis adopted**: register and build, but the isolation set moves from
unstated assumption to a **frozen falsifiable gate** — six invariants (no
mutating built-ins, no MCP reachability, no permission hang, no
AGENTS.md/user-config injection, no cross-session memory, spawn-failure
fail-closed). Any invariant unsatisfiable by measured flags ⇒ FS-0079-A fires on
the isolation dimension and the iter records a **VALID-NEGATIVE for the grok
seat rather than shipping a leaky judge**.

## SCOPED-SHELL MEASUREMENT — 2026-07-26 (user chose path A over the Codex freeze-break)

Codex's freeze-breaking finding 1 offered two exits: give grok a measured scoped
probe channel, or add a capability dimension to role resolution. **User chose the
scoped shell** (path A) — it puts grok at parity with the claude judge's
`Bash(<repo test command> *)` rather than inventing a new selection mechanism.
Measured live, grok 0.2.112, same isolation harness as the 07-25 run:

| Result | Receipt |
|---|---|
| **Scoped shell WORKS** | `--permission-mode dontAsk` + `--tools "…,run_terminal_cmd"` + `--allow 'Bash(echo *)'` → command executed, `ISOLATION_SHELL_OK` returned |
| **Deny HOLDS** | two separate runs attempted `touch <canary>` outside the allowlist; canary absent both times — no unauthorized write |
| **NEW FAILURE MODE (registered)** | attempting a non-allowlisted command **silently truncates the review and exits 0** — stdout stops at the model's preamble, stderr is empty, no denial text is surfaced to the model or the caller |
| Tool-ID discrepancy | docs say the ID is `run_terminal_cmd` (`14-headless-mode.md:52`) and that is what `--tools` matches; the model self-reports it as `run_terminal_command`. Flag matching is authoritative — the display name is not |
| Auth caveat CONFIRMED | the ephemeral `GROK_HOME` lost auth between sessions (`Not signed in`); `auth.json` must be re-copied per run, exactly the caveat the R1 seat flagged |

`grok` permission mode `dontAsk` is documented as "Only pre-approved tools and
built-in read-only handling / Strict CI allowlists"
(`22-permissions-and-safety.md:39`) — the same posture as
`adapters/claude.md`'s. Rules use `Bash(cmd *)` prefix form, deny beats allow,
and chained commands are split on `&&`/`||`/`;`/pipes and matched per segment
(`:156,:224-226`).

**Consequence for the design — this is not a free win.** A shell-bearing judge
that steps outside its allowlist loses its entire review, silently, with a
success exit code. Downstream it is still fail-closed (partial prose → collector
rejects → the F2 rule BLOCKs the pair source), so it cannot become a false PASS,
but the seat is wasted. Two obligations follow, both to be frozen before build:
1. The allow rule must cover the full probe command family a judge legitimately
   needs, and the judge prompt must state the exact permitted command — an
   under-scoped allowlist is now a review-destroying defect, not a mild one.
2. A prediction must inject an out-of-allowlist command attempt and prove the
   run ends BLOCKED rather than PASS (this also satisfies Codex finding 4's
   request for failure-injection coverage).

## R1-F1 DISCHARGED — isolation measured live 2026-07-25 (grok 0.2.112)

Fable's synthesis made the isolation set a frozen gate whose failure would have
recorded a VALID-NEGATIVE for the grok seat. **Measured: all five in-scope
invariants satisfiable.** The seat is fit; the iter is not moot.

**Measured recipe — the single ship-recipe for `grok.md` `## Invocation`:**

```bash
# $ISO_HOME = ephemeral dir seeded with a copied auth.json + agent_id, and a
#   config.toml containing:  [plugins]\ndisabled = ["telegram", "vercel"]\nenabled = []
# $NEUTRAL  = empty dir outside any git repo
# $REPO     = absolute repo root (redirects MUST be absolute — cwd is $NEUTRAL)
cd "$NEUTRAL"
GROK_HOME="$ISO_HOME" \
GROK_CLAUDE_MCPS_ENABLED=false GROK_CURSOR_MCPS_ENABLED=false \
GROK_CLAUDE_SKILLS_ENABLED=false GROK_CURSOR_SKILLS_ENABLED=false \
GROK_CLAUDE_HOOKS_ENABLED=false GROK_CURSOR_HOOKS_ENABLED=false \
GROK_CLAUDE_AGENTS_ENABLED=false GROK_CLAUDE_RULES_ENABLED=false \
GROK_MEMORY=0 \
python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 -- grok -p "<judge prompt>" \
  --permission-mode dontAsk --no-memory \
  --tools "read_file,grep,list_dir,run_terminal_cmd" \
  --disallowed-tools "Agent,use_tool,search_tool" \
  --allow 'Bash(<repo probe command family> *)' \
  --reasoning-effort medium \
  > "$REPO/.devlyn/grok-judge.stdout" 2> "$REPO/.devlyn/grok-judge.stderr"
```

`auth.json` must be re-copied into `$ISO_HOME` **per run** — the ephemeral home
loses authentication between sessions (measured 07-26).

The collector call that follows must not inherit `$NEUTRAL` as cwd —
`collect-codex-findings.py` resolves `--devlyn-dir` (default `.devlyn`) against
cwd, so pass it explicitly: `--devlyn-dir "$REPO/.devlyn" --stdout-file
grok-judge.stdout --summary-out grok-judge.summary.json`.

**RECEIPT SCOPE WARNING (Codex, 07-26)** — this table certifies the **pre-shell**
recipe. The shipping recipe now includes `run_terminal_cmd`, so the row "no
mutating built-ins" below describes an inventory the ship recipe no longer has.
The 07-26 scoped-shell measurement covers the shell path separately (allow works,
deny holds, truncation-on-overstep), but **the shell-bearing recipe has not been
certified against all five invariants in one run**. Re-running this table against
the final recipe is a frozen build-phase obligation, not an optional check —
this is the same stale-receipt class that has recurred three times in this iter.

| Invariant | Result | Receipt |
|---|---|---|
| No mutating built-ins | PASS | live tool inventory = `read_file, list_dir, grep, search_tool, use_tool` only |
| No MCP reachability | **PASS — removed, single layer** | plugin knob → 0 enabled servers in `grok inspect`; `--disallowed-tools use_tool,search_tool` → callable set is `read_file, list_dir, grep`, seat self-reports `MCP_NOT_CALLABLE` **with `--deny` absent** (the measurement that justified deleting the second layer). Superseded receipt from the earlier deny-only recipe, kept for the record: `Tool use_tool was not executed: Denied by permission policy: deny rule on mcp` |
| No permission hang | PASS | ran to exit 0 **without** `--always-approve` |
| No AGENTS.md/user-config injection | PASS | seat self-reported `INSTRUCTIONS_ABSENT`; `grok inspect` Project Instructions 3→1, remaining one `[disabled]` |
| No cross-session memory | PASS | `--no-memory` + `GROK_MEMORY=0` + ephemeral `GROK_HOME` |

**The decisive question, resolved**: isolation requires a neutral cwd (repo-root
`CLAUDE.md`/`AGENTS.md` cannot be disabled by any knob — `05-configuration.md:358`
explicitly exempts "generic top-level `Claude.md`, `CLAUDE.md`, `CLAUDE.local.md`"
from the `agents` cell). A neutral cwd would be useless if it also blocked repo
reads — **it does not**: the seat read
`config/skills/_shared/adapters/README.md` by absolute path and quoted line 17
verbatim (orchestrator-checked against the file). **Isolation and function are
compatible.**

**RETRACTED — the orchestrator's "zero-MCP is unachievable" claim was wrong.**
The first discharge asserted that plugin-sourced servers (`telegram`, `vercel`)
could not be removed, and proposed execution-denial as a NAMED DEVIATION from
R1-F1's bar. **R2 refused it**, correctly: that was a negative existence claim
made without completing the search, and it named two documented knobs the
orchestrator had never tried. Both were then measured and **both work**:
- `[plugins] disabled = ["telegram","vercel"]` in the ephemeral `GROK_HOME`
  `config.toml` (`09-plugins.md:127-138`) → `grok inspect` MCP Servers 5 → 3,
  (baseline note: the bare seat measured in R1-F1 showed **6** servers; the 5 is
  the already-partially-isolated seat — ephemeral `GROK_HOME` had already dropped
  one before this knob was applied. Both figures are real, at different stages.)
  and all 3 remaining carry `[disabled]` from the vendor knob. **Zero enabled
  servers.**
- `--disallowed-tools "Agent,use_tool,search_tool"` (`14-headless-mode.md:85` —
  removes tools entirely, unlike permission rules) → live seat self-report:
  available tools are **`read_file`, `list_dir`, `grep` only**; no
  `search_tool`/`use_tool` and no individual MCP tools callable.
No deviation is needed; R1-F1's original bar is met.

**`--deny "MCPTool(*)"` DELETED (R2-final).** Once removal works, keeping deny is
two layers catching one bug — which CLAUDE.md rejects outright at the harness
layer ("defense-in-depth is **not** a justification"), and the retention wording
first drafted here ("cheap, and it is the documented containment path") is
exactly the anti-rationalization phrase class that rule names. Rather than argue
it, it was measured: the same recipe **without** `--deny` returns callable tools
`read_file, list_dir, grep` and `MCP_NOT_CALLABLE`. Removal alone is sufficient,
so the deny layer is gone. FS-0079-B (version-drift ⇒ re-gate) carries the
residual risk that the removal flags move in a future CLI.

**Honest residual (measured, smaller than before, not zero)**: the system-reminder
text in the seat's prompt still *names* the three disabled claude-sourced servers
and their tool counts, even though none is callable. Context noise and attention
cost, not reachable capability.

**Invariant count**: the table measures **five** invariants. The sixth from the
R1 synthesis — spawn-failure fail-closed — is orchestrator-side, not
recipe-side, and is carried by **P-0079-G**, not by this measurement.

**Consequence for the record**: the retroactive disclosure above stands
unchanged — the R0 round WAS run without any of this.

## Principles check

- **#1 no workaround** — fail-closed semantics unchanged; `executor: no` is an
  honest capability declaration, not a bypass. P-0079-D is its test.
- **#2 no overengineering / subtractive-first** — the shipped surface is: one
  generic OTHER-engine spawn rule (replacing binary wording, ~flat line count),
  `adapters/grok.md`, one `engine-doctor.sh` row, one `lint-skills.sh` row, a
  clause widening `adapters/README.md:49`, generic `BLOCKED:<engine>-unavailable`
  wording, and collector summary-validation hardening. Everything else stays
  deleted from scope: no prompt delta, no new collector, no rename, no default
  route change, no capability dimension in role resolution (path A made it
  unnecessary). Pure-addition citations: **explicit user request** for
  user-visible behaviour, plus two **observed** failure modes — codex quota-death
  leaving the harness with zero pair judges (07-25), and the collector's
  zero-exit silent-PASS hole (Codex finding 2).
- **Scope honesty (Codex finding 5)** — this iter is the **grok-first generic
  invocation foundation**; it does NOT close the stated grok/Kimi/Qwen goal.
  Kimi K3 and Qwen have no CLI on this machine and no resolved backend, so each
  remains a separate adapter + backend registration riding the generic rule this
  iter ships. Do not report iter-0079 as closing the three-engine request.
- **#3 no guesswork** — predictions frozen above before any smoke run; the
  UNMEASURED item (grok emission) is named as such rather than assumed.
- **#7 production ready** — a pinned-but-broken pair engine must surface, not
  degrade silently; P-0079-B/-D are the visible-failure tests.
