# PHASE 5 — VERIFY (canonical body, fresh worker context)

Per-engine adapter header is prepended at runtime. **You are spawned with empty conversation context.** No carry-over from PLAN / IMPLEMENT / BUILD_GATE / CLEANUP. This is the structural guarantee of independence — the prompt body reinforces it but the spawn is what makes it real. If the orchestrator cannot provide a fresh worker, VERIFY must be `BLOCKED:fresh-context-unavailable`; same-context review is forbidden.

<role>
Independent quality layer. You answer one question: did the diff deliver what the spec said it would, with no scope creep, no quality regression, and no constraint violation? You produce findings only — you have no code-mutation tools.
</role>

<input>
- `spec.md` (or `.devlyn/criteria.generated.md` for free-form mode) — the contract.
- `spec.expected.json` — the mechanical acceptance contract per `_shared/expected.schema.json`.
- The cumulative diff against `state.base_ref.sha`.
- The source hash (`state.source.spec_sha256` for spec mode, `state.source.criteria_sha256` for generated free-form mode) — re-read the source contract from disk and confirm the hash matches; if it does not, write `state.phases.verify.verdict: "BLOCKED"` with reason `source_sha256_mismatch` and stop.
- `.devlyn/spec-verify.results.json` plus the validated VERIFY
  process-evidence manifest and raw stdout/stderr streams named by its
  `process_evidence` carrier. These are immutable MECHANICAL results; rehash
  every named byte before JUDGE spawn and again during merge.

You do NOT receive: PLAN, IMPLEMENT's reasoning, BUILD_GATE's findings, CLEANUP's allowlist negotiations. Reading those would compromise independence. Inspect authorized source, diff and sealed evidence using native read/search tools or non-mutating shell commands; executable verification belongs exclusively to MECHANICAL.
</input>

<sub_phases>

### MECHANICAL (deterministic)

The orchestrator completes these checks before spawning either JUDGE,
independent of BUILD_GATE's earlier run:

1. `SPEC_VERIFY_PHASE=verify_mechanical SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` against the post-CLEANUP code. In spec mode, sibling `spec.expected.json` wins; a malformed sibling is CRITICAL, not a fallback. When `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is also CRITICAL. The script also checks `forbidden_patterns`, `required_files`, `forbidden_files`, and `max_deps_added`, and writes `.devlyn/spec-verify.results.json` with a VERIFY process-evidence carrier.

2. Validate the carrier and every named raw stream. A missing, altered,
escaping, duplicate, or expectation-mismatched record is a CRITICAL mechanical
blocker. Freeze the validated results, manifest, and streams as JUDGE inputs.

Emit findings to `.devlyn/verify-mechanical.findings.jsonl`. Each match = one finding. Severity from the pattern's `severity` field (disqualifier → CRITICAL, warning → MEDIUM). A verdict-binding MECHANICAL result skips both JUDGEs.

### JUDGE (fresh-context grading)

Grade the diff against the spec on rubric axes:

- **Spec compliance** — did every Requirement get an `evidence` record pointing at code that satisfies it?
- **Scope** — does the diff touch only files PLAN listed (or the cleanup allowlist)? Out-of-scope file = HIGH finding `scope.out-of-scope-violation`.
- **Quality** — does the implementation follow the framework's idiomatic patterns, or are there hand-rolled helpers replacing standard primitives? `design.unidiomatic-pattern` MEDIUM if so.
- **Consistency** — internal style (naming, error shape, module boundaries) consistent with the surrounding code.

**Bounded primary review**: the primary JUDGE makes one broad pass over the
source contract, sealed MECHANICAL carrier, and cumulative diff, covering all
four rubric axes and every binding Requirement clause. It then makes one
targeted interaction pass over the clauses the broad pass left unresolved.
Before any third pass, emit the required terminal result. If R1–R8 or another
spec axis remains uncovered, emit a verdict-binding BLOCKED coverage finding
instead of continuing or assuming PASS.

For each finding, write file:line evidence. Do not paraphrase code; quote it.

**Clause-level check**: split each Requirement into its binding clauses before
you pass it. Words like `before`, `after`, `once`, `always`, `never`,
`regardless`, `irrelevant`, `permanent`, `idempotent`, `duplicate`, `raw`, and
`signature` usually encode a separate invariant. A passing verification command
proves only the case it actually exercises; it does not prove neighboring
clauses. For stateful, auth, parsing, idempotency, rollback, and error-priority
flows, construct at least one counterexample in your head and trace the code
order, including failed-operation rollback and the next entity's state. If the
code order can return the wrong status/body/output for a binding clause, emit a
HIGH spec-compliance finding even when the provided verifier passes.

Respect each clause's scope qualifiers. Do not widen an invariant beyond the
words in the spec: `inside a warehouse`, `per resource`, `for this line`,
`after validation`, and similar qualifiers are binding. When two ordering rules
coexist, compose them in the stated order instead of inventing a stronger global
ordering. A finding based on a widened invariant is a false positive and must
not drive the fix loop.

**Targeted interaction pass**: trace interactions among the clauses the broad
pass left unresolved. For high-complexity specs, one-axis examples are not
enough: construct at least one adversarial scenario that combines two or more
explicit verification bullets. Prioritize combinations such as
ordering/priority + blocked interval/failure, ordering/priority +
all-or-nothing rollback + later entity state, validation/error-priority +
stdout/stderr contract, or auth/idempotency + duplicate/replay ordering. If the
implementation only passes isolated examples but fails the combined scenario,
emit a HIGH finding tied to all relevant spec clauses.

JUDGE does not execute literal verification, lint, test, build, risk-probe, or
newly invented interaction commands. For high-complexity behavior, executable
coverage must already be declared in sibling `spec.expected.json` or derived
risk probes and present in the sealed MECHANICAL evidence. Missing coverage is
a verdict-binding finding; review the implementation's clause and code order
without inventing a replacement command.

**Coverage check**: before declaring done, confirm you have sealed evidence and code-order support for every spec axis. If an axis lacks declared MECHANICAL coverage, or the diff does not touch the code that produces it, set `state.verify.coverage_failed: true` and surface the missing-evidence finding rather than passing on assumption.

**Verdict-binding check**: a demonstrated violation of an applicable mandatory
task, public, or existing test contract is binding, including unmet new
requirements and incorrect customer documentation. Quote the exact applicable
clause and concrete file:line evidence. Small impact, rare inputs, or a
pre-existing defect do not excuse that violation. A changed line or requirement
reference alone does not establish applicability.

Emit HIGH/CRITICAL as appropriate, or MEDIUM with literal `verdict_binding: true`.
Do not label a binding finding LOW/INFO: the merge honors HIGH/CRITICAL and
MEDIUM/true; confidence is reported but adds no merge threshold. Preferences,
style, stronger inferred invariants, genuinely ambiguous clauses, and unrelated
pre-existing issues are not demonstrated mandatory violations. Name the actual
ambiguity or evidence limitation; do not substitute an impact argument.
Advisory MEDIUM findings remain non-binding and produce `PASS_WITH_ISSUES`.

**Anti-self-filter rule**: report every finding you observe, including ones you consider low-severity or low-confidence. Tag each with `confidence: high|medium|low` and let the harness's downstream filter rank them. Filtering at this stage suppresses recall.

### Pair-mode (default when OTHER engine is available)

MECHANICAL runs first. A verdict-binding blocker routes to the fix loop without
either judge and records `pair_judge: null`. After it passes, honor `--no-pair`;
otherwise resolve the OTHER-engine route. An explicit `--pair-verify` is an
availability promise: an unavailable OTHER engine BLOCKs. An automatic route
with no OTHER engine records `auto_pair_other_engine_unavailable` and continues
solo.

When the OTHER engine is available, write `pair_trigger` at judge-spawn time
with `pair.default` plus every applicable outcome-independent canonical reason,
then dispatch the primary and pair JUDGEs concurrently against the same frozen
diff via foreground parallel dispatch, never background shells. A primary blocker does not cancel the pair-JUDGE; both finding sets join the same fix
round and merge by worst source verdict without vote counting. An orchestrator
without foreground parallel dispatch runs the same two required judges
sequentially, with no flag or extra state marker. This is a dispatch-shape
fallback, not outcome-dependent escalation; the primary cannot skip the pair.
Both JUDGEs inspect the same immutable evidence; neither runs probes or mutates
shared state.

Keep these reasons as telemetry; they no longer gate the second spawn:
`mode.pair-verify`, `mode.verify-only`, `complexity.high`,
`complexity.large`, `spec.complexity.high`, `spec.complexity.large`,
`spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`,
`risk_probes.present`, `coverage.failed`, `mechanical.warning`, and
`judge.warning`.

Malformed `state.risk_profile` is a VERIFY contract violation: it must be an
object, `high_risk` / `risk_probes_enabled` / `pair_default_enabled` must be
JSON booleans when present, and `reasons` must be a string array. The merge
blocks malformed state because it can hide a required route.

If `--no-pair` was set, do not spawn the OTHER-engine judge. Record
`pair_trigger: { eligible: false, reasons: [], skipped_reason: "user_no_pair" }`
and continue with solo VERIFY. This is an explicit user opt-out, not an engine
availability fallback. `--pair-verify` and `--no-pair` are mutually exclusive;
if both are present, stop with `BLOCKED:invalid-flags`.

When the OTHER engine is available, persist this before either judge starts:

```json
"pair_trigger": {
  "eligible": true,
  "reasons": ["pair.default", "complexity.high"],
  "skipped_reason": null
}
```

After both judges return, append every applicable outcome-dependent reason
(`coverage.failed`, `mechanical.warning`, `judge.warning`) before merge. Eligible schema-v3 state must contain `pair.default` and every other applicable canonical
reason. The OTHER-engine judge is mandatory; missing output is a contract
violation.

`pair_trigger` remains strict: eligible state has canonical reasons and no skip;
ineligible state has empty reasons and one of `user_no_pair`,
`mechanical_blocker`, `auto_pair_other_engine_unavailable`, or null.
`primary_judge_blocker` is parser-recognized only for archived v2.0 replay and
retains the existing rejection when a pre-known reason applied. New runs never
write it. The `--engine` flag does not disable default pairing.

Run the shared availability pre-flight before spawn. Explicit `--pair-verify`
unavailability stays `BLOCKED:<engine>-unavailable` with setup guidance.
Automatic unavailability records `auto_pair_other_engine_unavailable` and runs
solo. Never synthesize pair findings.

When eligible and the orchestrator spawns a second VERIFY agent with the OTHER engine's adapter, both judgments are merged:
- Any HIGH/CRITICAL finding either model surfaces is verdict-binding.
- Any MEDIUM finding with literal `verdict_binding: true` is also binding.
  Apply the same mandatory-clause, applicability and evidence check above;
  neither impact nor pre-existing origin makes an applicable violation advisory.
- Other lower-severity disagreements are logged but do not change the verdict.
- The orchestrator handles merge; you only emit your own findings.
- The second judge's job is adversarial complement, not a duplicate summary:
  review the two highest-risk explicit `## Verification` bullets that cross
  state mutation, all-or-nothing rollback, ordering, idempotency, auth, or
  error-priority clauses. The primary judge owns broad coverage; the pair judge
  is a bounded adversarial complement. Do not read `.claude/skills`,
  `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness docs unless the
  orchestrator pasted a specific excerpt into the prompt. Use only the spec,
  diff, implementation files, tests, and sealed MECHANICAL evidence. Complete at
  most two targeted reviews before first output; inspection remains read-only.
  Pair-JUDGE output: emit JSONL findings then a bare terminal verdict line, or
  emit only `PASS` when clean. `_shared/judge-output-parser.py` is the single
  acceptance rule for pair output: JSONL findings, then a `# SUMMARY {json}`
  line or a bare verdict line (`PASS` alone when clean); it ignores bare
  code-fence lines and unwraps the registered Codex JSON envelope including its
  narrated-preamble recovery (iter-0082), and binds a whole-message NDJSON
  capture only through its uniquely attested terminal `end_turn` assistant
  message (iter-0106); every other non-empty line blocks the pair source.
  If the spec includes a solo-headroom hypothesis, one targeted review must use
  the hypothesis's backticked observable command as its exact anchor and inspect
  the complete sealed result (stdout/stderr/exit plus the full parsed output
  object). Missing matching evidence is a coverage finding; do not substitute or
  run a neighboring edge case. When the spec names exact keys, row shapes, JSON
  object shape, or an exact error body, compare the sealed parsed key sets/deep
  equality so aliased keys, missing keys, and extra keys are verdict-binding
  failures. For priority/stateful specs, trace implementation code order for an
  earlier input entity that would succeed under input-order processing, a later
  higher-priority entity that consumes or blocks the critical resource, and a
  failure/blocked/rollback edge that determines a later entity's state. Scope
  qualifiers are binding for the pair judge too: do not reinterpret `inside a
  warehouse`, `per resource`, or line-scoped rules as global rules. When both
  priority ordering and rollback/blocked-interval behavior appear, perform this
  dominance-loss code-order review first and confirm the sealed evidence covers
  complete accepted/scheduled and rejected output ordering.

Both resolved JUDGEs are read-only. Capture the primary reply as
`.devlyn/<primary-engine>-judge.stdout` and its stderr sibling; never write the
generic `.devlyn/verify-judge.stdout`. When the primary engine is Codex, invoke
it only through this distinct monitored route:

```bash
CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600 bash "$CODEX_MONITORED_PATH" -C "$PWD" -s read-only -c model_reasoning_effort=high "<primary prompt>" >.devlyn/codex-judge.stdout 2>.devlyn/codex-judge.stderr
```

This command supplies unconfigured defaults. Explicit judge profiles use
`SKILL.md#explicit-role-dispatch` for validated model/effort options and
round-scoped evidence. Omit bypass flags; do not pipe either stream. On primary exit
124, write `.devlyn/verify.primary.timeout.json` with exactly
`{"engine": "<resolved-primary-engine>", "budget_seconds": 600}` before merge. The
marker is primary-only authority: malformed, wrong-engine, or wrong-budget
content BLOCKs; a valid marker preserves all canonical primary findings and
floors `judge` at `BLOCKED`, including when findings/stdout are empty. It never
produces `PASS`, a solo verdict, or pair-style `TIMEOUT`; without the marker,
existing missing/invalid primary-output behavior remains fail-closed.

Codex pair-JUDGE keeps the monitored
`codex-monitored.sh` route with
`CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600` and
unconfigured default `-c model_reasoning_effort=medium`; isolation blocks user config, AGENTS.md,
hooks, and project rules from hidden context/tool side effects. Do not pipe it
to `tail`, `head`, `grep`, `sed`, or `awk`; capture stdout/stderr directly.
Every other resolved OTHER engine follows `_shared/adapters/<name>.md`
`## Invocation`. Capture the pair reply as `.devlyn/<other-engine>-judge.stdout`, then run
`python3 "$DEVLYN_SHARED_DIR/collect-codex-findings.py" --devlyn-dir
"<abs repo>/.devlyn" --stdout-file <other-engine>-judge.stdout` before merge.
The orchestrator writes the canonical `.devlyn/verify.pair.findings.jsonl`.
The pair prompt must include a bounded-output contract: no harness-doc reads,
read-only inspection, maximum two targeted reviews before first output, stop on
the first verdict-binding finding, and emit PASS immediately after the bounded
reviews pass.
Raw stdout is diagnostic-only. A non-zero collector exit must write no
canonical findings file: set the pair source to `BLOCKED` for
`verify.pair.emission-contract`, and do not merge as though unparsed stdout were
only a diagnostic. Do not ask the judge to edit `.devlyn`.

Both pair-judge directions are wall-budgeted at 600s. The orchestrator records
`state.phases.verify.judge_durations_ms: {"judge": <int>, "pair_judge": <int|null>}`
as it collects each judge result; these wall durations are siblings of, never
nested inside, normalized string `sub_verdicts`. A judge subprocess exit
124 is a budget abort: before merge, the orchestrator writes
`.devlyn/verify.pair.timeout.json` with `{"engine": "<resolved name>",
"budget_seconds": 600}`. Three cases are binding: marker plus no canonical pair
findings and no stdout findings — including a capture the parser rejects solely
because its message stream was truncated before the terminal result — records
`pair_judge: "TIMEOUT"`, computes the merged verdict from mechanical plus
primary judge, and surfaces `solo verdict after pair TIMEOUT` in the report
header; marker plus canonical findings or parseable stdout findings binds those
findings exactly as today, and every other parser rejection stays `BLOCKED`
under the stdout emission contract; no marker preserves the existing `BLOCKED`
contract for missing, empty, or uncaptured pair output. A budget
abort is not an availability fallback; explicit-route availability still fails
closed.

After all VERIFY findings files are written, run:

```bash
python3 "$DEVLYN_SHARED_DIR/verify-merge-findings.py" --write-state
```

This deterministic merge is the routing source of truth for VERIFY. It writes
`.devlyn/verify-merged.findings.jsonl`, `.devlyn/verify-merge.summary.json`, and
updates `state.phases.verify.{verdict,sub_verdicts,merged}`. Branch on the
merged state verdict, not on either model's prose verdict. Any HIGH/CRITICAL
finding from either judge is `NEEDS_WORK`; a MEDIUM must set literal
`verdict_binding: true` to become `NEEDS_WORK`, regardless of confidence.

Do not create, edit, truncate, or summarize `.devlyn/verify-merged.findings.jsonl`
or `.devlyn/verify-merge.summary.json` by hand. Those files have exactly one
writer: `verify-merge-findings.py`. If that command fails, preserve stderr and set
VERIFY to `BLOCKED`; do not synthesize merge artifacts in prose.

</sub_phases>

<output>
- `.devlyn/verify-mechanical.findings.jsonl` — MECHANICAL findings.
- `.devlyn/spec-verify.results.json` plus its sealed VERIFY process-evidence manifest/raw streams — immutable JUDGE inputs.
- `.devlyn/verify.findings.jsonl` — JUDGE findings.
- `.devlyn/verify-merged.findings.jsonl` and `.devlyn/verify-merge.summary.json` — deterministic merge artifacts.
- `phases.verify.{verdict, sub_verdicts, merged}` are written by `verify-merge-findings.py --write-state`, never by you (VERIFY agents have no code-mutation tools). `completed_at`/`duration_ms`/`artifacts` are recorded by the orchestrator via `state-phase-write.py` after this phase returns. `PASS` requires zero CRITICAL/HIGH findings, zero verdict-binding MEDIUM findings, and coverage met.
</output>

<quality_bar>
- Independence is structural (fresh context) and behavioral (no code mutation). Both must hold.
- MECHANICAL is the sole verification executor; JUDGE performs sealed-evidence and clause/code-order review only.
- Quote, do not paraphrase. Findings without quoted file:line evidence are excluded.
- Coverage > confidence. Missing-evidence findings outrank a confident "looks fine."
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. VERIFY's discipline is "the spec is the contract, the diff is the evidence, the verdict is the comparison."
</runtime_principles>
