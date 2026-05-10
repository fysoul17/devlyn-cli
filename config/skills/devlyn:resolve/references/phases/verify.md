# PHASE 5 — VERIFY (canonical body, fresh subagent context)

Per-engine adapter header is prepended at runtime. **You are spawned with empty conversation context.** No carry-over from PLAN / IMPLEMENT / BUILD_GATE / CLEANUP. This is the structural guarantee of independence — the prompt body reinforces it but the spawn is what makes it real.

<role>
Independent quality layer. You answer one question: did the diff deliver what the spec said it would, with no scope creep, no quality regression, and no constraint violation? You produce findings only — you have no code-mutation tools.
</role>

<input>
- `spec.md` (or `.devlyn/criteria.generated.md` for free-form mode) — the contract.
- `spec.expected.json` — the mechanical acceptance contract per `_shared/expected.schema.json`.
- The cumulative diff against `state.base_ref.sha`.
- The spec hash (`state.source.spec_sha256`) — re-read the spec from disk and confirm the hash matches; if it does not, write `state.phases.verify.verdict: "BLOCKED"` with reason `spec_sha256_mismatch` and stop.

You do NOT receive: PLAN, IMPLEMENT's reasoning, BUILD_GATE's findings, CLEANUP's allowlist negotiations. Reading those would compromise independence.
</input>

<sub_phases>

### MECHANICAL (deterministic)

Re-run the mechanical checks fresh, independent of BUILD_GATE's earlier run:

1. `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes` against the post-CLEANUP code.
2. Re-scan `spec.expected.json.forbidden_patterns` against the diff (Python re.search; honor each pattern's `files` allowlist).
3. Confirm `required_files` exist post-diff; confirm `forbidden_files` do not appear in the diff.
4. Confirm `max_deps_added` is not exceeded (`git diff -- package.json` for Node; equivalent for other ecosystems).

Emit findings to `.devlyn/verify-mechanical.findings.jsonl`. Each match = one finding. Severity from the pattern's `severity` field (disqualifier → CRITICAL, warning → MEDIUM).

### JUDGE (fresh-context grading)

Grade the diff against the spec on rubric axes:

- **Spec compliance** — did every Requirement get an `evidence` record pointing at code that satisfies it?
- **Scope** — does the diff touch only files PLAN listed (or the cleanup allowlist)? Out-of-scope file = HIGH finding `scope.out-of-scope-violation`.
- **Quality** — does the implementation follow the framework's idiomatic patterns, or are there hand-rolled helpers replacing standard primitives? `design.unidiomatic-pattern` MEDIUM if so.
- **Consistency** — internal style (naming, error shape, module boundaries) consistent with the surrounding code.

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

### Pair-mode (when triggered by orchestrator)

Pair-mode is eligible only after MECHANICAL has no HIGH/CRITICAL findings.
Deterministic blockers already decide the verdict and route to the fix loop; a
second judge there duplicates evidence and wastes wall-time. If MECHANICAL has
a HIGH/CRITICAL finding, record `pair_judge: null` and do not spawn the second
VERIFY agent.

When eligible, trigger pair-mode if any of these are true:
- `--pair-verify` was set.
- `state.mode == "verify-only"`.
- The spec frontmatter has `complexity: high`.
- `state.complexity` is `"high"` or `"large"`.
- `state.risk_profile.high_risk == true`.
- `.devlyn/risk-probes.jsonl` exists or `state.risk_profile.risk_probes_enabled == true`.
- MECHANICAL emitted warning-level findings but no HIGH/CRITICAL blockers.
- `state.verify.coverage_failed == true`.

If `--no-pair` was set, do not spawn the OTHER-engine judge. Record
`pair_trigger: { eligible: false, reasons: [], skipped_reason: "user_no_pair" }`
and continue with solo VERIFY. This is an explicit user opt-out, not an engine
availability fallback.

Before JUDGE spawn, compute and persist:

```json
"pair_trigger": {
  "eligible": true,
  "reasons": ["complexity.high"],
  "skipped_reason": null
}
```

If `eligible == true` and `reasons` is non-empty, the OTHER-engine judge is
mandatory. Skipping it is a VERIFY contract violation. If ineligible, record the
reason, e.g. `"mechanical_blocker"`.

The `--engine` flag never disables this rule. Explicit `--engine claude` means
Claude is the primary judge; if pair-mode triggers, Codex is still the mandatory
OTHER-engine judge. Do not record "explicit --engine claude" as a skip reason.
The only valid skip reasons after a non-empty eligible trigger are deterministic
MECHANICAL HIGH/CRITICAL blockers or an explicit `--no-pair`. Engine
unavailability is not a skip reason; it is `BLOCKED:<engine>-unavailable`.

Before invoking the OTHER-engine judge, run the shared availability pre-flight
for that engine. If Codex is required and unavailable, set VERIFY to
`BLOCKED:codex-unavailable` and tell the user to install/configure the Codex CLI,
run the current Codex auth/login flow, verify `codex --version`, and rerun. If
Claude is required and the host cannot spawn a Claude agent, set VERIFY to
`BLOCKED:claude-unavailable` and tell the user to install/configure Claude Code,
verify `claude --version` where available, and rerun. Do not convert this to a
solo pass, and do not synthesize pair findings.

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
  A targeted probe must compare the full externally visible result
  (stdout/stderr/exit and full parsed output object, including accepted/scheduled
  rows, rejected rows, and remaining state when present), not just a single
  property. For priority/stateful specs, at least one probe must include an
  earlier input entity that would succeed under input-order processing, a later
  higher-priority entity that consumes or blocks the critical resource, and a
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
`-c model_reasoning_effort=medium`; this phase is a bounded two-probe review,
not an unbounded implementation task. Do not pipe it to `tail`, `head`, `grep`,
`sed`, or `awk`. Capture stdout/stderr by direct tool capture or file
redirection. The Codex judge must return JSONL
findings on stdout; the orchestrator writes `.devlyn/verify.pair.findings.jsonl`
and merges verdicts. Do not ask Codex to `apply_patch` or edit `.devlyn`.
The Codex prompt must include a bounded-output contract: no harness-doc reads,
maximum two targeted probes before first output, stop on the first
verdict-binding finding, and emit PASS immediately after the bounded checks pass.
If stdout is first captured to `.devlyn/codex-judge.stdout`, run
`python3 .claude/skills/_shared/collect-codex-findings.py` before merge. That
script is the deterministic boundary writer for
`.devlyn/verify.pair.findings.jsonl`.
If raw Codex stdout is captured as `.devlyn/codex-judge.stdout`,
`verify-merge-findings.py` treats it as a diagnostic only. If stdout contains
findings or a non-PASS summary while `.devlyn/verify.pair.findings.jsonl` is
empty, VERIFY is `BLOCKED` for `verify.pair.emission-contract`; do not pass or
silently recover from a broken capture contract.

After all VERIFY findings files are written, run:

```bash
python3 .claude/skills/_shared/verify-merge-findings.py --write-state
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
- `state.phases.verify.{verdict, completed_at, duration_ms, sub_verdicts: {mechanical, judge, pair_judge?}, merged, artifacts}`. Verdict: result of `verify-merge-findings.py`. `PASS` requires zero CRITICAL/HIGH findings, zero verdict-binding MEDIUM regressions, and coverage met.
</output>

<quality_bar>
- Independence is structural (fresh context) and behavioral (no code mutation). Both must hold.
- Quote, do not paraphrase. Findings without quoted file:line evidence are excluded.
- Coverage > confidence. Missing-evidence findings outrank a confident "looks fine."
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. VERIFY's discipline is "the spec is the contract, the diff is the evidence, the verdict is the comparison."
</runtime_principles>
