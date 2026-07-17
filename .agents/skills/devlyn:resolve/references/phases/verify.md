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

You do NOT receive: PLAN, IMPLEMENT's reasoning, BUILD_GATE's findings, CLEANUP's allowlist negotiations. Reading those would compromise independence.
</input>

<sub_phases>

### MECHANICAL (deterministic)

Re-run the mechanical checks fresh, independent of BUILD_GATE's earlier run:

1. `SPEC_VERIFY_PHASE=verify_mechanical SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` against the post-CLEANUP code. In spec mode, sibling `spec.expected.json` wins; a malformed sibling is CRITICAL, not a fallback. When `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is also CRITICAL. The script also checks `forbidden_patterns`, `required_files`, `forbidden_files`, and `max_deps_added`.

Emit findings to `.devlyn/verify-mechanical.findings.jsonl`. Each match = one finding. Severity from the pattern's `severity` field (disqualifier → CRITICAL, warning → MEDIUM).

### JUDGE (fresh-context grading)

Grade the diff against the spec on rubric axes:

- **Spec compliance** — in spec mode, did every Requirement get evidence? In free-form mode, grade every binding raw-Goal clause and accept the single non-authoritative `criteria.generated://goal` entry only when all pass. Verification is mechanical evidence, not scope law; anchors and assumptions are non-binding.
- **Scope** — use the spec's boundaries in spec mode and only explicit raw-Goal boundaries in free-form mode; VERIFY cannot read PLAN. An out-of-contract file is HIGH `scope.out-of-scope-violation`.
- **Quality** — does the implementation follow the framework's idiomatic patterns, or are there hand-rolled helpers replacing standard primitives? `design.unidiomatic-pattern` MEDIUM if so.
- **Consistency** — internal style (naming, error shape, module boundaries) consistent with the surrounding code.

For each finding, write file:line evidence. Do not paraphrase code; quote it.

**Clause-level check**: split each spec Requirement—or every raw-Goal clause in
free-form mode—into binding clauses before you pass it. Words like `before`, `after`, `once`, `always`, `never`,
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

**Interaction check**: for high-complexity specs, one-axis examples are not
enough. Construct at least one adversarial scenario that combines two or more
explicit verification bullets. Prioritize combinations such as
ordering/priority + blocked interval/failure, ordering/priority +
all-or-nothing rollback + later entity state, validation/error-priority +
stdout/stderr contract, or auth/idempotency + duplicate/replay ordering. If the
implementation only passes isolated examples but fails the combined scenario,
emit a HIGH finding tied to all relevant spec clauses.

For high-complexity specs, execute at least one combined adversarial check with
the repo's existing CLI/API/test runner before declaring PASS. Use a temporary
script or inline command that leaves no tracked files behind. The check must
cross two or more explicit verification bullets, not merely repeat the visible
acceptance command. If the command exposes a mismatch, emit a HIGH finding with
the command, expected output/state, and actual output/state.

**Coverage check**: before declaring done, confirm you have evidence for every spec axis. If you could not exercise an axis (the spec asks for behavior X but the diff does not touch the code that produces X), set `state.verify.coverage_failed: true` and surface the missing-evidence finding rather than passing on assumption.

**Verdict-binding severity check**: HIGH/CRITICAL findings are always
verdict-binding. A MEDIUM finding is also verdict-binding when it identifies a
concrete behavioral regression against the visible spec, an existing public
contract, or an existing test contract. Examples: a previously valid input now
errors, duplicate/idempotent handling regresses, warning/error semantics change
for a real API path, or a focused existing regression test would fail. Advisory
design/style concerns remain non-binding MEDIUM and produce `PASS_WITH_ISSUES`.

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
Prefer read-only checks and serialize probes requiring exclusive shared state.

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
- Any high-confidence MEDIUM finding either model surfaces is also
  verdict-binding when it identifies a concrete behavioral regression against
  the spec, public contract, or existing test contract. This includes
  duplicate/idempotent/order-preservation regressions and real warning/error
  behavior changes. Do not downgrade these to advisory simply because they are
  not HIGH.
- Other lower-severity disagreements are logged but do not change the verdict.
- The orchestrator handles merge; you only emit your own findings.
- The second judge's job is adversarial complement, not a duplicate summary:
  prioritize the two highest-risk explicit `## Verification` bullets that cross
  state mutation, all-or-nothing rollback, ordering, idempotency, auth, or
  error-priority clauses. The primary judge owns broad coverage; the pair judge
  is a bounded adversarial complement. Do not read `.claude/skills`,
  `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness docs unless the
  orchestrator pasted a specific excerpt into the prompt. Use only the spec,
  diff, implementation files, tests, and the repo's CLI/API/test runner.
  Execute at most two targeted probes before first output. Stop immediately
  after the first verdict-binding finding and emit JSONL. If both probes pass
  and static scope/dependency checks show no blocker, emit PASS; do not continue
  exhaustive exploration.
  If the spec includes a solo-headroom hypothesis, one of the two targeted
  probes must exercise that hypothesis with the visible command/input shape and
  compare the full externally visible result. The probe must use the
  hypothesis's backticked observable command as its command anchor before adding
  bounded input variations. Do not substitute a neighboring easier edge case;
  the pair judge exists to test the stated expected solo miss.
  A targeted probe must compare the full externally visible result
  (stdout/stderr/exit and full parsed output object, including accepted/scheduled
  rows, rejected rows, and remaining state when present), not just a single
  property. When the spec names exact keys, row shapes, JSON object shape, or an
  exact error body, compare parsed key sets/deep equality so aliased keys,
  missing keys, and extra keys are verdict-binding failures. Use the spec's
  visible input key names literally when constructing the probe input. For
  priority/stateful specs, at least one probe must include an earlier input
  entity that would succeed under input-order processing, a later higher-priority
  entity that consumes or blocks the critical resource, and a
  failure/blocked/rollback edge that determines a later entity's state. This is
  the minimum compound shape for priority + failure/state-mutation bugs.
  Scope qualifiers are binding for the pair judge too: do not reinterpret
  `inside a warehouse`, `per resource`, or line-scoped rules as global rules.
  If a candidate finding depends on that widening, emit PASS for that probe and
  use the second bounded probe for a different explicit clause.
  When both priority ordering and rollback/blocked-interval behavior appear in
  the spec, this dominance-loss probe is mandatory and comes before any other
  probe: an earlier lower-priority entity that would succeed alone or under
  input-order processing must lose because a later higher-priority entity is
  processed first; a failed/blocked middle entity must not corrupt later state;
  and the assertion must cover the complete output ordering for both accepted
  (or scheduled) and rejected rows.

Codex pair-JUDGE is read-only. Invoke `codex-monitored.sh` directly with
`CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600` and
`-c model_reasoning_effort=medium`; this is a
bounded two-probe review, not implementation. Isolation blocks user config,
AGENTS.md, hooks, and project rules from hidden context/tool
side effects. Do not pipe it to `tail`, `head`, `grep`, `sed`, or `awk`.
Capture stdout/stderr directly. The Codex judge must return JSONL findings on
stdout; the orchestrator writes `.devlyn/verify.pair.findings.jsonl` and merges
verdicts. Do not ask Codex to `apply_patch` or edit `.devlyn`.
When the OTHER engine is Claude (codex/omp orchestrator), the judge call
follows `_shared/adapters/claude.md` `## Invocation`: wrap headless `claude -p`
as `python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 -- claude -p ...` with
`--permission-mode dontAsk`, an allowlist of `Read,Grep,Glob` plus the repo test
command, hermetic settings, stdout captured to
`.devlyn/claude-judge.stdout`. The same bounded-output contract and emission
rule apply to that stdout file, and the orchestrator writes the same
canonical `.devlyn/verify.pair.findings.jsonl`.
The Codex prompt must include a bounded-output contract: no harness-doc reads,
maximum two targeted probes before first output, stop on the first
verdict-binding finding, and emit PASS immediately after the bounded checks pass.
If stdout is first captured to `.devlyn/codex-judge.stdout`, run
`python3 "$DEVLYN_SHARED_DIR/collect-codex-findings.py"` before merge. That
script is the deterministic boundary writer for
`.devlyn/verify.pair.findings.jsonl`.
If raw Codex stdout is captured as `.devlyn/codex-judge.stdout`,
`verify-merge-findings.py` treats it as a diagnostic only. If stdout contains
findings or a non-PASS summary while `.devlyn/verify.pair.findings.jsonl` is
empty, VERIFY is `BLOCKED` for `verify.pair.emission-contract`; do not pass or
silently recover from a broken capture contract.

Both pair-judge directions are wall-budgeted at 600s. The orchestrator records
`state.phases.verify.judge_durations_ms: {"judge": <int>, "pair_judge": <int|null>}`
as it collects each judge result; these wall durations are siblings of, never
nested inside, normalized string `sub_verdicts`. A judge subprocess exit
124 is a budget abort: before merge, the orchestrator writes
`.devlyn/verify.pair.timeout.json` with `{"engine": "<codex|claude>",
"budget_seconds": 600}`. Three cases are binding: marker plus no canonical pair
findings and no parseable stdout findings records `pair_judge: "TIMEOUT"`,
computes the merged verdict from mechanical plus primary judge, and surfaces
`solo verdict after pair TIMEOUT` in the report header; marker plus canonical
findings or parseable stdout findings binds those findings exactly as today,
including the stdout emission contract; no marker preserves the existing
`BLOCKED` contract for missing, empty, or uncaptured pair output. A budget
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
finding from either judge is `NEEDS_WORK`; a high-confidence MEDIUM must set
`verdict_binding: true` to become `NEEDS_WORK`.

Do not create, edit, truncate, or summarize `.devlyn/verify-merged.findings.jsonl`
or `.devlyn/verify-merge.summary.json` by hand. Those files have exactly one
writer: `verify-merge-findings.py`. If that command fails, preserve stderr and set
VERIFY to `BLOCKED`; do not synthesize merge artifacts in prose.

</sub_phases>

<output>
- `.devlyn/verify-mechanical.findings.jsonl` — MECHANICAL findings.
- `.devlyn/verify.findings.jsonl` — JUDGE findings.
- `.devlyn/verify-merged.findings.jsonl` and `.devlyn/verify-merge.summary.json` — deterministic merge artifacts.
- `phases.verify.{verdict, sub_verdicts, merged}` are written by `verify-merge-findings.py --write-state`, never by you (VERIFY agents have no code-mutation tools). `completed_at`/`duration_ms`/`artifacts` are recorded by the orchestrator via `state-phase-write.py` after this phase returns. `PASS` requires zero CRITICAL/HIGH findings, zero verdict-binding MEDIUM regressions, and coverage met.
</output>

<quality_bar>
- Independence is structural (fresh context) and behavioral (no code mutation). Both must hold.
- Quote, do not paraphrase. Findings without quoted file:line evidence are excluded.
- Coverage > confidence. Missing-evidence findings outrank a confident "looks fine."
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. VERIFY's discipline is "the spec is the contract, the diff is the evidence, the verdict is the comparison."
</runtime_principles>
