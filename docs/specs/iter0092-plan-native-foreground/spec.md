---
complexity: high
---

# iter-0092 — native foreground PLAN without authority escalation

Registration evidence is frozen under
`~/.local/share/nx01/iter0092-reg/`. Fable 5 session
`23d11bb2-c794-4007-abae-7bb4dbe61b9f` and Grok 4.5 session
`019fcada-39e4-7272-bb0a-60fc06b32e03` returned `FREEZE` before this spec was
implemented. Terra session `019fcac6-7737-7313-90d8-7ad81f5e995c` proved the
external PLAN-stop watcher with synthetic process-group tests.

Outer-loop amendment 2026-08-05 (recorded per the spec-amendment path; spec
stays read-only inside a run): the lint verification entry gained
`"timeout_sec": 300` after the adjudicated instrument finding from run
`rs-20260804T113416Z` (BUILD_GATE killed the 127.55s lint at the then-hardcoded
60s budget; lint itself exits 0). The authorable budget shipped as iter-0093
(DECISIONS 0093.1). No other byte of this spec changed; requirements and the
R5 gate are untouched.

## Requirements

### R1 — PLAN-only native Claude call shape

- In Claude Code only, every PLAN dispatch (initial and corrective round) sends
  the already-rendered `.devlyn/plan.prompt` in the native `Agent.prompt`
  field, explicitly sets `run_in_background: false`, and omits `mode`.
- Do not add or change model, subtype, tool allowlist, reasoning, exploration,
  context, output, adapter, renderer, state, digest, or PLAN-content controls.
- Do not retry an Agent call rejected for native input validation with a
  different `mode` or background shape. Surface the native failure and fail
  PLAN closed through the existing fresh-worker failure path.
- Every non-PLAN Claude phase retains its existing explicit
  `mode: "bypassPermissions"` behavior. Codex and oh-my-pi phase routes are
  unchanged.
- State the authority boundary explicitly: a PLAN worker inherits the parent
  permission context. The measured hands-free parent uses native
  bypassPermissions; a non-bypass parent's permission prompt remains the
  user's native boundary and is never silently escalated.

### R2 — schema-3 Agent acceptance oracle

Edit `benchmark/ceiling/scripts/plan-dispatch-oracle.py` without adding a new
runtime dependency or wrapper.

- Collect top-level parent Agent `tool_use` and top-level tool-result evidence
  separately. Match them by retained source path plus `tool_use_id` across the
  whole source, never adjacency. Sidechain Agent uses remain excluded; PLAN
  writer corroboration remains visible.
- A unique use with one result is `REJECTED` only when `is_error` is the Boolean
  `true`; Boolean `false`, explicit `null`, or an absent key is `ACCEPTED`.
  Other present types are INCOMPLETE. Missing results are INCOMPLETE. Duplicate
  use ids and multiple matching results are CONTRACT-VIOLATION.
- Receipt windows stay inclusive `[started_at, completed_at]`, bound by the
  Agent tool-use timestamp. CONTRACT-VIOLATION-class attempts take precedence
  over INCOMPLETE-class attempts, which take precedence over COMPLETE.
  COMPLETE requires exactly one in-window attempt and requires that attempt to
  be ACCEPTED and shape-valid.
- Every in-window REJECTED attempt is independently a product violation. Every
  in-window attempt, accepted or rejected, must have prompt digest equal to the
  receipt, no `mode` key, and a present Boolean
  `run_in_background: false`; absence, `null`, numeric zero, or strings fail the
  shape gate.
- Preserve the iter-0091 one-way outside-window rule: a top-level Agent prompt
  with the canonical PLAN heading outside every receipt window is conclusive
  CONTRACT-VIOLATION regardless of result disposition. Heading absence never
  exculpates in-window evidence; ordinary outside-window calls remain
  diagnostic.
- Bump only this oracle output to schema version 3. Keep exit codes COMPLETE=0,
  CONTRACT-VIOLATION=1, INCOMPLETE=2.

### R3 — conservation and total self-tests

Extend the oracle's in-file self-test with type-strict, deterministic fixtures
for:

- delayed result matching with `is_error` absent, false, and null;
- missing result, duplicate tool-use id, multiple matching results, and
  malformed `is_error`;
- one ACCEPTED plus one missing-result attempt in the same window → INCOMPLETE;
- zero, one, and many accepted attempts; rejected-only evidence;
- prompt mismatch; mode present including null; background absent, null,
  numeric zero, string false, and Boolean false;
- overlapping inclusive windows and one attempt matching multiple windows;
- outside-window canonical-heading ACCEPTED and REJECTED positives plus an
  ordinary negative.

Retained conservation is mandatory:

- iter-0091 C1 raw parent line 94 has explicit Boolean
  `run_in_background:false`, no `mode`, and its matching delayed result has the
  `is_error` key absent; it remains COMPLETE.
- iter-0091 C2 contains one rejected invalid-mode attempt and one accepted
  background-omitted attempt; it remains CONTRACT-VIOLATION, never two accepted
  dispatches and never a retroactive Stage-B success.
- Existing retained 0088/0090/0091 self-test facts and P-0091-A3 outside-window
  escalation stay unchanged unless the raw evidence itself proves otherwise.

### R4 — mirrors and evidence document

- Synchronize the canonical skill change to the tracked `.agents` mirror and
  ignored `.claude` installed mirror. No unrelated skill bytes change.
- Add `autoresearch/iterations/0092-plan-native-foreground-dispatch.md` with the
  frozen hypothesis, Fable/Grok/Terra attestations, exact gates, honest
  non-bypass scope, and a clearly unearned terminal status until live arms run.
- Do not update broad HANDOFF/DECISIONS claims until the live matrix earns a
  terminal result.

### R5 — post-implementation ship gate (not implementation credit)

After the formal implementation pipeline passes, run the separately frozen
external matrix. Exact serial order is:

`control-simple` → `candidate-simple` → `candidate-discovery` →
`control-discovery`.

- Sonnet 5 owns the four live PLAN arms. Terra owns mechanical self-tests and
  retained replay. Fable 5 and Grok 4.5 own blind A/B plan adjudication; neither
  is a test arm.
- Candidate must produce exactly one ACCEPTED, zero REJECTED, exact digest,
  mode absent, explicit foreground false, valid PASS plan, no denial, no
  IMPLEMENT dispatch, no detached process, no product mutation, and a
  quiescent watcher in both goals.
- Either blind judge choosing control on either goal, or a candidate-only
  CRITICAL/HIGH finding, fails the candidate. Missing/malformed judgment also
  fails. Ties are allowed; this is no-regression, not superiority.
- Candidate/control summed PLAN receipt duration must be ≤1.25. Each matched
  arm ratio must be ≤1.50. No completed-arm rerun or post-hoc tie breaker.
- Infrastructure replacement is allowed only before any in-window top-level
  PLAN Agent use exists. Once an attempt exists, oracle evidence wins and the
  arm cannot be rerun.
- Any miss reverts R1's PLAN call-shape product change. R2/R3 may survive only
  if their independent self-tests and retained replay pass.

## Out of scope

- No native Agent wrapper, transcript rewrite/interception, new runtime
  abstraction, state field, dispatch id, renderer mode, adapter, hook, or flag.
- No PLAN-pair, extra PLAN round, model/engine change, worker intelligence pin,
  or content determinism.
- No changes to other phases, Codex/omp routes, canonical PLAN body, adapter
  bytes, prompt digest semantics, or H1-v3 status.
- No statistical superiority or broad full-pipeline performance claim from the
  N=1-per-goal canary.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 benchmark/ceiling/scripts/plan-dispatch-oracle.py --self-test",
      "exit_code": 0
    },
    {
      "cmd": "diff -q config/skills/devlyn:resolve/SKILL.md .agents/skills/devlyn:resolve/SKILL.md && diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md",
      "exit_code": 0
    },
    {
      "cmd": "bash scripts/lint-skills.sh",
      "timeout_sec": 300,
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
