# 0156 — Sibling-aware spec authoring preflight

2026-09-12. Mission 1, intent fidelity. Continuing the owner's sequential
verification request, root implements directly without resolve; actual native
Fable 5.1 and Grok 4.6 review independently. Prospective task receipt
`4ffc705adfa9c741d9ab570e` owns the branch and disposable native scratch.
Baseline is `6676f59920d62b0359d730a8ab44ff7739c2f953`.

## Observed failure and decision

The next semantic-authoring screen first required a root-authored reference
guard to distinguish permitted existing `Any` annotations from prohibited new
annotations through the current checker. Its preflight exposed a real caller
mismatch before any model draw: template-style human-readable Verification plus
valid sibling `spec.expected.json` returned `--check` exit 2, while
`--check-expected` accepted the sibling. All ten reference controls stopped
before their guard could run. These were preflight failures, not semantic misses.

Why: ideate writes a sibling contract and requires both authoring checks
(`config/skills/devlyn:ideate/SKILL.md:112`), but `run_check_mode` always parsed
the Markdown's inline carrier. Spec runtime already gives the sibling priority.
Malformed siblings could also pass `--check` when valid inline JSON was present.

Root adds sibling selection after existing actual-Markdown metadata validation
in `run_check_mode`. Existing load/shape and sibling-spec validators do the
work. A bad sibling names the offending file and exits 2; no inline fallback,
staging or execution. With no sibling, the legacy path retains its behavior.
The two main caller sentences name the authoritative carrier and error path.

**No workaround / Production ready:** authoring checks the contract runtime
will consume. **No overengineering / Best practice:** reuse validators, add no
flag/helper/schema, preserve the generated runtime path and standalone
`--check-expected` convention. Deleting `--check` instead would lose validation
against an actual named in-place spec. **No guesswork / Worldclass:** recorded
predictions, real CLI controls and independent advice precede acceptance.
**Optimized:** this is a correctness repair; no speed improvement is measured.

## Verification

All 28 before/after controls match registered predictions. Sixteen authoring
exits change; all runtime outcomes remain unchanged. Cases cover both `spec.md`
and `request.md`, a misleading neighboring `spec.md`, sibling/inline precedence,
invalid/empty/pure-design contracts, actual-source complexity and absent-carrier
compatibility. Preflight preserves staged and result bytes. Four additional
controls confirm actual-source hypothesis-command binding, with no execution.

The root reference then passes all ten carrier-shape checks, permits three
allowed variants and rejects seven annotation violations via actual
`correctness.spec-literal-mismatch` findings. Every variant independently passes
the intended port-list behavior and the three original tests. This validates a
fixture-specific executable guard, not model authoring or arbitrary Python typing.

Deleting the new sibling branch restores the original exit 2 on a valid sibling
spec; baseline and pruned checks create no command marker. AST scope comparison
shows only `run_check_mode` and `run_self_test` changed. Canonical, tracked
`.agents` and owned ignored `.claude` mirrors match.

Full lint passes in **284.247s**, bound to source-diff SHA-256
`8fed2c39062c0a40db3b96f90d3db14ca3b77da97713ab706cb1ac171fe28d86`.
The first full run failed in 277.930s on two document-text contracts; explicit
complexity/legacy-carrier wording was restored, without weakening those checks.
Final native source review: Fable **PASS_WITH_ISSUES**, Grok **PASS**; the final
wording delta receives the same verdicts. Root closes pending lint/self-test
conditions with actual output; no in-scope CRITICAL/HIGH remains.

Retained limits: `--check-expected` still reads `spec.md` by convention, so a
named in-place dual-check flow may also inspect that neighbor. Sibling `is_file`
gating follows runtime. Generated execution deliberately ignores sibling
contracts and does not use the new spec-source precedence. Shared-directory
sibling ownership and general semantic completeness are not solved here.

Evidence `.devlyn/0156/` preserves initial reference and apparatus failures:
an accidentally selected benchmark route, a missing relocated CLI dependency,
and an unsupported observable-command prefix. Corrected controls retain their
predictions and raw results; none is a model retry or historical regrade.

## Extracted authoring screen

The separately frozen `AUTHORING-REGISTRATION.json` binds the accepted source,
current sibling template/schema, one new synthetic port-list task, baseline,
ten hidden controls and native runner before admission. Root executes proposed
artifacts unchanged. Native Codex `gpt-6-astra/high` proposes files without tools
or implementation; Fable/Grok remain read-only reviewers. No full skill run.

At most two 600-second draws: the second runs only after the first retains the
task and passes every control. Missing guards, malformed proposals, misses and
false blocks are failures; provider/terminal/identity failures are incomplete.
No retry, repair feedback or success-only denominator. Passing this screen
licenses no template repair, general recall, comparative quality or speed claim.
Frozen 0140/0147 records remain unchanged.

The first native draw exits 0 in **354.966s** and retains the requested task,
but its unchanged proposal **FAILS**: all ten shapes validate, then a task-local
scope guard rejects the runner-owned `.devlyn/pipeline.state.json`. All three
allowed cases are false blocks. The seven violating cases never reach annotation
inspection; their matching failure exits are **not semantic detections**.
The registered first-failure stop leaves draw 2 **NOT_RUN**.

A separately labeled root diagnostic removes exactly the call to `scope_guard()`
from a copy. All three allowed cases then pass and all seven violations fail at
the annotation guard. This identifies the overbroad scope check as the observed
blocker; it does not repair, regrade or rescue the native draw. Neither this
478-line task-local checker nor a generic annotation scanner is promoted.

Native CLI 0.154.0 reports `gpt-6-astra/high`, read-only, and no observed tool
sections. Despite requested discovery controls, stderr contains host/project
skill-load warnings: reference-only context isolation is not established. This
extracted proposal screen omits full ideate execution/repair and uses one known
failure family in a synthetic task; no production failure rate, broad semantic
coverage, model superiority or speed claim follows. Original proposal SHA-256:
`ee3a197f148b02a5f18ff79dd4a4c97668fa203ced354fe6f5db2ce92459076c`.

The preflight source repair is accepted independently of this negative research
result. Source evidence is `.devlyn/0156-evidence.tar.gz`; matching-source CI and
delivery follow acceptance. Broader semantic coverage and matched comparison
remain open.
