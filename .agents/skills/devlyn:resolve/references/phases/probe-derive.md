# PHASE 1.5 — RISK_PROBES (canonical body)

Per-engine adapter header is prepended at runtime. This file is engine-agnostic.

<role>
Convert visible verification obligations into executable probes. You are not a
second planner, critic essay, or debate participant. Your output is JSONL only.
</role>

<input>
- Source spec or generated criteria.
- `.devlyn/plan.md`.
- Codebase read/search at `state.base_ref.sha`.
</input>

<forbidden_input>
Do not read `spec.expected.json`, `.devlyn/spec-verify.json`,
`BENCH_FIXTURE_DIR`, benchmark fixture/verifier paths, `.devlyn/*.findings.jsonl`,
`.claude/skills`, `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness
docs unless the orchestrator pasted a specific excerpt into the prompt.
</forbidden_input>

<task>
Read the visible `## Verification` section. Emit 1 to 3 executable probes
that cover the highest-risk bullets whose failure would change observable
behavior. Prefer bullets that combine ordering/priority, rollback/state
mutation, idempotency, auth/error priority, stdout/stderr, or exact output
shape. Treat CLI/process errors and HTTP error responses as different contracts:
CLI errors must prove exit/stderr behavior, while HTTP errors must prove the
status code and response body. When the visible verification text names concurrent or near-concurrent
mutations, the probe must overlap the operations and assert the complete
externally-visible state, not just that every request returned a success code.
When a batch/import operation must be all-or-nothing, the probe must exercise a
mixed valid/invalid batch and prove the externally-visible state is unchanged
after the failure.

If the visible spec includes a solo-headroom hypothesis, the first probe must
target that hypothesis: use the visible command/input shape it names, exercise
the behavior the spec says `solo_claude` is expected to miss, and assert the
full observable result. The emitted probe `cmd` must contain the hypothesis's
backticked observable command so `.devlyn/risk-probes.jsonl` can be validated
mechanically, and `derived_from` must be an exact substring of that hypothesis
bullet. Do not replace the hypothesis with a neighboring easier edge case, and
do not cite hidden or benchmark-only verifier files.

For high-complexity specs with two or more behavior bullets, at least one probe
must be compound: one command must exercise two or more visible verification
bullets together. Do not split every risk into isolated one-axis probes.

Compound means interaction, not a checklist in one script. If the visible
verification text includes priority/ordering plus rollback, blocked intervals,
or failed-operation state, the first probe must be a dominance-loss scenario:
an earlier lower-priority/input-order entity would succeed alone, a later
higher-priority entity consumes or blocks the critical resource first, a failed
or blocked middle entity must not corrupt state, and the assertion must compare
the complete externally-visible result (accepted/scheduled rows, rejected rows,
remaining/state rows when present, exit/stdout/stderr).

When a verification bullet contains an alternative such as "rejected or moved
later", the probes must cover both sides when bounded: one case with a later
valid placement and one case with no later valid placement, where rejection is
the only correct outcome. Do not test only the easier side of an "or" clause.
For blocked-interval bullets, include boundary probes where a candidate starts
exactly at `blocked.start`, ends exactly at `blocked.end`, and has only a
one-minute overlap. Half-open assumptions must be tested by the command rather
than left implicit in prose.

When a placement algorithm may advance a candidate start past a blocked
interval or already-accepted entity, include a no-later-valid case where the
advanced start would exceed the active availability/window bound. The expected
result must reject that entity. A probe is too weak if every advanced candidate
still has enough room after the advance; that misses window-bound recheck bugs.

When a verification bullet names `remaining`, inventory, stock, balances, or
state after failures, assert the full externally-visible state. Rows with zero
quantity do not represent remaining availability; a probe that checks remaining
state should fail if zero-quantity rows are emitted unless the visible spec
explicitly requires zero rows. For all-or-nothing rollback, include a later
entity that can succeed only if the failed entity returned every tentative
allocation.

When visible bullets combine priority ordering, all-or-nothing rollback,
single-resource or single-warehouse constraints, choice ordering such as FEFO,
and `remaining` output, prefer one compound probe over isolated checks. The
probe must include: a lower-priority input-first entity that loses because a
higher-priority entity consumes stock first; a middle entity that tentatively
allocates at least one line/lot and then fails another line; a later entity that
can succeed only if that failed entity rolled back; a single-resource constraint
case where total cross-resource stock would be enough but no single allowed
resource is enough; and full expected `remaining` output sorted exactly as the
visible spec says, with zero-quantity rows absent unless explicitly required.
For all-or-nothing allocation probes, the failed middle entity must not be
pre-rejected by a whole-order availability shortcut. It must allocate a scarce
first line from mutable state, then fail a later line because that SKU/resource
is absent or otherwise impossible under the visible contract. The later entity
must request the same scarce first-line SKU so the probe proves rollback by
observable success, not by internal reasoning.

Each probe must run entirely from the worktree with standard shell/Node/Python
tools already present in the repo. Use inline temp-file scripts when needed.
Leave no tracked files behind. Probe commands must not call external network
APIs or write to external memory/telemetry services.
</task>

<output>
Write `.devlyn/risk-probes.jsonl`. Each line is one JSON object:

```json
{"id":"P1","derived_from":"verbatim substring from ## Verification","cmd":"shell command","exit_code":0,"stdout_contains":[],"stdout_not_contains":[],"tags":["ordering_inversion"],"tag_evidence":{"ordering_inversion":["input_order_would_choose_wrong_winner","asserts_processing_order_result"]}}
```

Rules:
- `derived_from` must be an exact substring of the visible `## Verification`
  bullet that the command directly exercises. For `error_contract`, use the
  invalid-input/stderr/JSON-error/exit-2 bullet, not a generic test-runner
  bullet.
- `tags` is required. Use only these shape tags:
  `ordering_inversion`, `boundary_overlap`, `prior_consumption`,
  `rollback_state`, `positive_remaining`, `stdout_stderr_contract`,
  `error_contract`, `http_error_contract`, `auth_signature_contract`,
  `idempotency_replay`, `concurrent_state_consistency`,
  `atomic_batch_state`, `shape_contract`.
- `tag_evidence` is required and must be a JSON object keyed by tag, never a
  top-level array. For these tags, include every listed evidence marker in the
  tag's array and make the command actually exercise it:
- Do not emit a shape tag unless the visible `## Verification` text names that
  kind of risk and the command exercises it. In particular, `boundary_overlap`
  is only for visible blocked-interval/window/overlap boundary semantics; do not
  use it for inventory, warehouse, or generic resource constraints.
  - `ordering_inversion`: `input_order_would_choose_wrong_winner`,
    `asserts_processing_order_result`.
  - `boundary_overlap`: `starts_at_blocked_start`, `ends_at_blocked_end`,
    `one_minute_overlap`.
  - `prior_consumption`: `same_resource_consumed_first`,
    `later_entity_fails_or_reroutes`.
  - `rollback_state`: `failed_entity_tentative_state_absent`,
    `later_entity_uses_released_state`.
  - `positive_remaining`: `asserts_full_remaining_state`,
    `zero_quantity_rows_absent`.
  - `stdout_stderr_contract`: `asserts_named_stream_output`.
  - `error_contract`: `asserts_error_payload_or_stderr`,
    `asserts_nonzero_or_exit_2`.
  - `http_error_contract`: `asserts_http_error_status`,
    `asserts_error_payload_body`.
  - `auth_signature_contract`: `asserts_signature_over_exact_bytes`,
    `asserts_tampered_or_missing_signature_rejected`.
  - `idempotency_replay`: `first_delivery_then_duplicate`,
    `duplicate_id_rejected_regardless_of_body`.
  - `concurrent_state_consistency`: `overlapping_mutations_exercised`,
    `all_successful_responses_reflected`, `distinct_identifiers_asserted`.
  - `atomic_batch_state`: `mixed_valid_invalid_batch`,
    `asserts_store_unchanged_after_failure`,
    `asserts_success_order_and_distinct_ids`.
  - `shape_contract` when the visible text names exact keys, fields, row
    shapes, JSON objects, response bodies, stdout/stderr objects, or exact error
    bodies: `uses_visible_input_key_names`,
    `asserts_visible_output_key_names`, `asserts_no_unexpected_output_keys`.
    If it names an exact JSON error object/body, also include
    `asserts_exact_error_object`.
  Tags not listed here may use an empty evidence list or be omitted from
  `tag_evidence`.
- `cmd` must not reference `BENCH_FIXTURE_DIR`, `verifiers/`, benchmark fixture
  paths, hidden oracle files, external URLs, or files outside the worktree.
  Localhost URLs are allowed only when the visible verification command needs a
  local server.
- Match the spec's visible input and output key names literally; do not invent
  aliases such as `stock` for `lots`, `order_id` for `id`, or `warehouse_id`
  for `warehouse`.
- When a verification bullet names exact keys, fields, row shapes, JSON object
  shape, or an exact error body, the probe must use `shape_contract` and assert
  exact key sets with parsed JSON/deep equality. A substring check is too weak:
  the command must fail on aliased keys, missing keys, and extra keys.
- For cart/pricing specs whose visible verification covers duplicate combining,
  multiple line-promotion types, tax, coupon, and shipping, the compound success
  probe must include interleaved duplicate SKUs plus taxable and non-taxable
  items, then assert the full output object and item rows. Use `shape_contract`
  for this probe unless the command also proves the required
  `ordering_inversion` evidence markers.
- Empty output is invalid when this phase is enabled. If no bounded executable
  probe can be derived, write one JSONL object whose command exits nonzero and
  whose `derived_from` names the blocking verification bullet; BUILD_GATE will
  surface the inability as a concrete failure instead of silently proceeding.
- No prose, no Markdown, no summaries, no alternate plan.
</output>

<quality_bar>
- Executable beats rhetorical. A risk that cannot become a bounded command does
  not belong in this artifact.
- Keep probes small. They are BUILD_GATE obligations, not a replacement for the
  full test suite.
- Coverage over cleverness: mirror the verification bullet literally before
  inventing an edge case.
- If the spec includes a solo-headroom hypothesis and the emitted probes do not
  exercise the stated `solo_claude` miss with a `cmd` containing the hypothesis's
  backticked observable command and `derived_from` pointing at the hypothesis
  bullet, the artifact is too weak for pair-evidence work.
- If a probe passes while an implementation processes entities in input order
  instead of the required priority/order, or emits extra zero-value state rows,
  the probe is too weak.
- If priority/order appears in the visible contract, at least one probe must
  carry `ordering_inversion`.
- If blocked intervals, forbidden windows, or overlap appear in the visible
  contract, at least one probe must carry `boundary_overlap`.
  `boundary_overlap` is not satisfied by a generic overlap case. The same
  probe must assert a candidate starting exactly at the blocked interval start,
  a candidate ending exactly at the blocked interval end, and a one-minute
  overlap case with no later valid placement.
- If the domain has both windows/availability and conflicts that can push a
  candidate later, at least one probe must assert the pushed candidate is
  rejected when the pushed start plus duration no longer fits inside the same
  window. The full expected output must exclude that row from scheduled/accepted
  output and include the required rejection reason.
- If accepted operations reduce stock/state/availability for later operations,
  at least one probe must carry `prior_consumption`: a later lower-priority or
  later-submitted entity must fail or reroute only because an earlier accepted
  entity consumed the exact resource/lot/slot.
- If a visible contract has all-or-nothing rollback plus `remaining`, at least
  one probe must carry both `rollback_state` and `positive_remaining`; it must
  prove the rollback by a later successful entity and by the final remaining
  rows, not just by the rejected order reason.
- If `remaining` state appears in the visible contract, at least one probe must
  carry `positive_remaining` and assert that zero-quantity/zero-value rows are
  absent unless the visible spec explicitly requires them.
- If webhook signatures, raw-body signatures, HMAC, or `X-Signature` appear in
  the visible contract, at least one probe must carry
  `auth_signature_contract` and prove exact-byte signature verification plus a
  tampered or missing signature rejection.
- If replay, duplicate delivery, same id, already-seen ids, or idempotency
  appear in the visible contract, at least one probe must carry
  `idempotency_replay` and cover first delivery followed by duplicate rejection,
  including the case where the duplicate body would otherwise fail validation
  when the spec says duplicate wins.
- If an HTTP status error such as `400`, `401`, `409`, or `422` appears with a
  JSON error body, error object, or named error field, at least one probe must
  carry `http_error_contract` and assert both the exact status code and parsed
  response body. Do not use CLI `error_contract` for these HTTP-only checks
  unless the visible text also names process exit or stderr behavior.
- If concurrent, close-together, simultaneous, parallel, race, lost update, or
  many-at-once mutation semantics appear in the visible contract, at least one
  probe must carry `concurrent_state_consistency`. It must trigger overlapping
  mutations, then compare every successful response against the final
  externally-visible state and assert the identifiers are distinct. Do not use
  this tag for ordinary batch success cases that only require distinct ids.
- If a batch/import contract says one valid plus one invalid item fails while
  the later state remains the same as before, or otherwise says all-or-nothing /
  no partial updates / 0 inserts on failure, at least one probe must carry
  `atomic_batch_state`. It must execute a mixed valid/invalid batch, assert the
  store/list is unchanged after failure, and include an all-valid success case
  proving order and distinct ids.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. The discipline here is: visible contract
in, executable obligation out. Hidden oracle leakage is a blocker.
</runtime_principles>
