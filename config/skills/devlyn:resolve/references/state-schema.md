# pipeline.state.json schema

Single authoritative verdict source for `/devlyn:resolve`. The orchestrator branches on `state.phases.<name>.verdict` directly — never parses `.devlyn/*.findings.jsonl` for routing. Living document; bump `version` on a breaking change.

## Top-level shape

```json
{
  "version": "3.0",
  "run_id": "rs-<UTC-timestamp>-<12-hex>",
  "started_at": "2026-04-30T12:00:00Z",
  "engine": "claude",
  "mode": "spec",
  "pair_verify": false,
  "complexity": null,
  "risk_profile": { "high_risk": false, "reasons": [], "risk_probes_enabled": false, "risk_probes_explicit": false, "pair_default_enabled": true },
  "risk_probes_digest": null,
  "process_evidence": null,
  "base_ref": { "branch": "main", "sha": "abc123..." },
  "rounds": { "max_rounds": 4, "global": 0 },
  "bypasses": [],
  "implement_passed_sha": null,
  "source": {
    "type": "spec",
    "spec_path": "docs/roadmap/phase-1/X.md",
    "spec_sha256": "...",
    "criteria_path": null,
    "criteria_sha256": null
  },
  "criteria": [
    { "id": "C1", "ref": "spec://requirements/0", "status": "pending", "evidence": [], "failed_by_finding_ids": [] }
  ],
  "phases": {
    "plan": null,
    "probe_derive": null,
    "implement": null,
    "surface_close": null,
    "build_gate": null,
    "cleanup": null,
    "verify": null,
    "final_report": null
  },
  "verify": { "coverage_failed": false, "pair_trigger": null }
}
```

## Field rules

- **version** — string. Bump major on a breaking schema change.
- **session_id** — optional string or null stamped from `CLAUDE_CODE_SESSION_ID`; a missing/null value leaves Stop-hook pressure inert.
- **mode** — `"free-form" | "spec" | "verify-only"`.
- **pair_verify** — boolean. True only for `--pair-verify`. Pairing is already default-when-available; this flag makes OTHER-engine availability an explicit fail-closed promise and adds `mode.pair-verify` telemetry. It is mutually exclusive with `risk_profile.pair_default_enabled == false` from `--no-pair`.
- **complexity** — `null | "trivial" | "medium" | "large"`. Free-form mode populates this; spec/verify-only mode leaves it null.
- **engine** — any engine name with a shipped adapter (`_shared/adapters/<name>.md`); `"claude"` and `"codex"` today. A required unavailable engine stops the run with `BLOCKED:<engine>-unavailable`.
- **engine_source** — `"flag" | "engines.json" | "default"` — provenance of the resolved executor engine (`_shared/engine-preflight.md#role-resolution`). Optional on archived pre-iter-0038 runs; absent means `default`.
- **source** — downstream contract provenance. Spec/verify-only set `type: "spec"`, `spec_path`, and `spec_sha256`. Free-form sets `type: "generated"`, `goal_path: ".devlyn/goal.raw.txt"` + exact-byte `goal_sha256`, and `criteria_path: ".devlyn/criteria.generated.md"` + raw-byte `criteria_sha256`. VERIFY re-checks its contract hash.
- **`.devlyn/external-diff.patch` artifact** — verify-only input; the verifier consumes it only when `mode` is `"verify-only"` and fails closed if it exists in any other mode.
- **risk_profile** — PHASE 0 routing state. `high_risk` controls automatic risk probes; `risk_probes_enabled` / `risk_probes_explicit` preserve their current semantics; `pair_default_enabled` is false only for explicit `--no-pair`. `risk_profile` must remain an object with boolean `high_risk`, `risk_probes_enabled`, `risk_probes_explicit`, and `pair_default_enabled` fields when present, plus `reasons` as a string list. Malformed state blocks VERIFY because it can hide required routes.
- **risk_probes_digest** — top-level sha256 written by PHASE 1.5 after probe validation; BUILD_GATE/VERIFY replay semantics live in `phases/build-gate.md` step 4.
- **process_evidence** — absent or JSON null for legacy runs and new runs with no captured obligation; otherwise an append-only array of `{phase, round, manifest: {path, sha256}, streams: [{id, stdout: {path, sha256}, stderr: {path, sha256}}]}` carriers. Paths are worktree-relative and live under `.devlyn/process-evidence/<run_id>/<phase>/round-<round>/`. A successful IMPLEMENT completion/transition validates every sibling `spec.expected.json.process_evidence[]` item declared for `phase: "implement"`, rehashes both raw streams (including zero-byte files), and appends the carrier before accepting the checkpoint. Missing, altered, escaping, duplicate-id, or expectation-mismatched evidence blocks without a state mutation. Later phases reuse the same carrier shape; no schema-major bump is required because readers must accept absent/null legacy state.
- **base_ref.branch** — checked-out branch name, or `null` for a detached HEAD; `base_ref.sha` remains the exact immutable base in both states.
- **rounds.global** — incremented every fix-loop pass (BUILD_GATE → fix-loop, VERIFY → fix-loop, OR a phase-gate fix respawn inside phase-gated IMPLEMENT).
- **phases.implement.exec** — only on phase-gated large runs (plan.md has `## Execution phases` with >1 phase): `{ "total": N, "current": k, "statuses": ["PASS"|"FAIL"|null, ...], "commits": ["<sha>", ...] }`. Phase definitions live in plan.md (immutable contract); progress lives here (routing truth — never route on plan.md checkboxes). Absent on single-phase runs. `cumulative.patch` for such runs is `git diff <base_ref.sha>...HEAD`.
- **phases.probe_derive** — optional PHASE 1.5 entry when `--risk-probes` is enabled. Artifacts include `.devlyn/risk-probes.jsonl`. Probe failures later surface through BUILD_GATE/VERIFY as `correctness.risk-probe-failed`, or as `correctness.verification-timeout` when the probe exceeds its verification budget.
- **phases.surface_close** — generated trivial/medium one-shot: `pre_sha`, `input_patch_sha256`, assembled-byte `prompt_sha256`, `untracked_before`; spawn requires Claude plus a requested model, and `surface-check` gates PASS. `.devlyn/surface-close.output.json` retains the Claude JSON wrapper used for completion attestation while the round JSONL remains the execution-audit backstop. Automatic Claude unavailability alone records null verdict plus `skipped_reason: "auto_surface_close_claude_unavailable"`. After an adjudication-malformed reply only, successful rollback plus transcript write-audit records the two nonterminal fields `skipped_reason: "surface_close_rolled_back_adjudication_malformed"` and `continued_after_block: true`; neither creates a terminal floor. Other failures store bare `"BLOCKED"`. `durability[]` is append-only: `{round, origin_phase, receipt_path, receipt_sha256, restore_commit_sha}` per `.devlyn/closure-durability.round-<n>.json`.
- **bypasses** — array of phase names from `--bypass`. Valid: `"build-gate" | "cleanup"`. PLAN, IMPLEMENT, VERIFY are non-bypassable (orchestrator rejects at parse time).
- **implement_passed_sha** — captured at end of PHASE 2; null until then. Activates the post-implement invariant for SURFACE_CLOSE, CLEANUP, and VERIFY.
- **criteria** — generated from spec's `## Requirements` checklist (one per `- [ ]`). `status: pending → implemented` is the legal transition. `failed_by_finding_ids` populates when VERIFY surfaces a finding tied to a criterion.
- **`.devlyn/untracked.baseline` artifact** — written at PHASE 0 (`spec-verify-check.py --write-untracked-baseline`); BUILD_GATE flags created-during-run unauthorized untracked files against it (`.devlyn/` exempt; semantics in `phases/build-gate.md` step 4).
- **verify.coverage_failed** — outcome-dependent telemetry set when JUDGE cannot exercise a spec axis. It no longer gates pair dispatch: after MECHANICAL passes, `pair.default` dispatches both judges concurrently whenever `pair_default_enabled != false` and the OTHER engine is available. An orchestrator without foreground parallel dispatch runs the same two required judges sequentially; a primary blocker never skips the pair. A verdict-binding MECHANICAL blocker still skips both. Legacy complexity values remain accepted only for archived compatibility.
- **verify.pair_trigger** — strict decision state: `{ "eligible": boolean, "reasons": string[], "skipped_reason": string|null }`. Schema v3.0 eligible state requires `pair.default` plus every applicable telemetry reason and `skipped_reason: null`; outcome-dependent reasons are appended after both judges return. Canonical reasons are `pair.default`, `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, and `judge.warning`. Ineligible new-run state has empty reasons and only `user_no_pair`, `mechanical_blocker`, `auto_pair_other_engine_unavailable`, or null; `primary_judge_blocker` remains parser-recognized only for archived v2.0 replay and retains its existing pre-known-reason rejection. Explicit `mode.pair-verify` cannot use the unavailable-engine skip. Missing, contradictory, incomplete, or unknown trigger state BLOCKs VERIFY.

## Per-phase shape

Each entry under `phases.<name>` (for `plan`, `probe_derive`, `implement`, `surface_close`, `build_gate`, `cleanup`, `verify`, `final_report`):

```json
{
  "started_at": "2026-04-30T12:00:01Z",
  "completed_at": "2026-04-30T12:00:30Z",
  "duration_ms": 29000,
  "round": 0,
  "triggered_by": null,
  "verdict": "PASS",
  "engine": "claude",
  "model_requested": "<orchestrator-selected model id or null>",
  "model_effective": "<session-attested model id or null>",
  "pre_sha": null,
  "post_sha": null,
  "artifacts": { "findings_file": null, "log_file": null },
  "sub_verdicts": null
}
```

`history` is absent until a phase is re-entered. Immediately before re-entry overwrites the live lifecycle, `state-phase-write.py` appends those prior values as one object to `history[]`, creating the append-only array on first re-entry. Codex worker history also retains its state-bound `invocation_receipt`; PLAN history retains the complete prompt/output receipt.

- `verdict` — `"PASS" | "PASS_WITH_ISSUES" | "FAIL" | "NEEDS_WORK" | "BLOCKED"`. PHASE 6 (FINAL_REPORT) writes its own verdict per the terminal-verdict precedence.
- `model_requested` / `model_effective` — `model_requested` is supplied by the orchestrator through `--model`; schema-v3 completion cannot replace the spawn engine or requested model. Schema-v3 Codex PLAN/mutation/BUILD_GATE phases derive `model_effective` only from the canonical `.devlyn/<phase>.invocation.<round>.json` written around the actual monitored child; state rehashes that receipt plus the round-scoped `.devlyn/<phase>.prompt.<round>` and canonical worker session, and cross-checks model, sandbox, prompt, run, phase, round, and exit. Arbitrary paths and plaintext `model:` headers are not evidence. Claude JSON output accepts a singleton `modelUsage` key or, for multiple entries, the sole key whose token counters exactly match top-level usage. Missing/malformed evidence and requested/effective mismatch fail closed: the phase verdict becomes `BLOCKED` and completion fails.
- `output_sha256` — on schema-v3 PLAN completion, SHA-256 of exact `.devlyn/plan.md` bytes. Only caller-verdict BLOCKED with a lexically absent, never-bound plan records null; receipt/session attestation still applies. This terminal null permits only FINAL_REPORT lifecycle operations while the path remains lexically absent. Bound bytes are rehashed on later spawn/completion/transition, including BLOCKED; legal PLAN re-entry replaces the digest only at the new PLAN completion. FINAL_REPORT completion binds exact `.devlyn/final-report.md` bytes here and its canonical path in `artifacts.log_file`.
- `invocation_receipt` — state-bound `{path, sha256, sandbox, sandbox_network_access, argv_sha256, exit_code}` for schema-v3 Codex PLAN/IMPLEMENT/BUILD_GATE/CLEANUP. Receipt schema 2.0 makes `sandbox` exactly `workspace-write`; `sandbox_network_access` is exactly `true` for BUILD_GATE and `false` for the other mutation phases. A missing CI capability or wider phase authority blocks before launch. Pre-2.0 receipts are intentionally rejected rather than migrated because they did not attest this capability; do not rewrite in-flight evidence. Continue through the owning session or start in a distinct worktree; restarting via explicit manual archive requires the operator to establish that prior writers stopped, never automatic archival to defeat admission refusal. A completed final report does not prove all interactive writers exited. The receipt is retained in history and rehashed before archive.
- `triggered_by` — null on first run; one of `"build_gate" | "verify"` when the phase is a fix-loop respawn.
- `pre_sha` — captured before SURFACE_CLOSE or CLEANUP. It bounds that phase's post-spawn diff and rollback.
- `post_sha` — captured when SURFACE_CLOSE or CLEANUP completes; finish-gate subtracts CLEANUP's `pre_sha..post_sha` window.
- `sub_verdicts` — only populated for VERIFY: `{ "mechanical": "PASS|FAIL", "judge": "PASS|...", "pair_judge": "PASS|..." | "TIMEOUT" | null }`. Values are normalized by `verify-merge-findings.py`; model prose verdicts cannot upgrade or downgrade the deterministic findings-derived verdict. `sub_verdicts.pair_judge` is `"TIMEOUT"` when a pair judge exceeded its wall budget and a valid `.devlyn/verify.pair.timeout.json` marker was read — semantics in `references/phases/verify.md` (pair budget section).
- `judge_durations_ms` — only populated for VERIFY: `{ "judge": <non-negative int>, "pair_judge": <non-negative int|null> }`. The orchestrator writes each wall duration when it collects that judge's result; values remain a sibling of `sub_verdicts`, whose values stay normalized strings. VERIFY spawn resets this key to null so re-entry cannot retain prior-round timings.
- `merged` — only populated for VERIFY after `verify-merge-findings.py --write-state`: `{ "verdict": "...", "findings_file": ".devlyn/verify-merged.findings.jsonl", "summary_file": ".devlyn/verify-merge.summary.json" }`.
- `pair_trigger` — only populated for VERIFY; same shape as top-level `verify.pair_trigger` when the phase stores it locally.
- `correctness.risk-probe-failed` — emitted by `spec-verify-check.py --include-risk-probes` when an executable probe derived from the visible `## Verification` section fails.

## Write protocol

Phase lifecycle (`started_at`/`completed_at`/`duration_ms`/`round`/`triggered_by`/`verdict`) is written by a deterministic script, never hand-edited JSON — a prior hand-edited fix-loop respawn left `started_at` stale, corrupting cross-phase ordering because `completed_at`/`round`/`triggered_by` advanced to the new round while `started_at` didn't. Phase workers report their verdict and artifact paths in their reply; they never edit `pipeline.state.json` themselves.

1. **Spawn**: `state-phase-write.py --devlyn-dir .devlyn --phase <name> spawn --round <N> [--triggered-by build_gate|verify] [--pre-sha <sha>] [--engine <e>] [--model <requested-model>] [--prompt-sha256 <hex>]`. Re-entry preserves lifecycle/receipts in `history[]`, resets owned fields, and leaves fields such as `phases.implement.exec`; VERIFY also clears prior-round files. Schema-v3 Codex IMPLEMENT/BUILD_GATE/CLEANUP requires the requested model and prompt digest; an inherited top-level Codex engine is persisted into the phase rather than becoming an unattested null route. SURFACE_CLOSE additionally requires `--model <requested-model> --input-patch-sha256 <hex> --prompt-sha256 <hex> --untracked-before-json <array>`; use `surface-check --authorized-surface-json <array>`, `surface-adjudication-recover --authorized-surface-json <array>` only after its adjudication-malformed result, `surface-rollback` for other failures, or `surface-skip` only for automatic Claude unavailability.
2. **Transition** (normal direct handoff): `state-phase-write.py ... --phase <current> transition` takes the same completion/attestation arguments plus caller-specified `--next-phase`, `--next-round`, `--next-triggered-by`, `--next-engine`, `--next-model`, and next-phase metadata. It validates a fixed legal edge, applies complete plus spawn to a detached candidate, and replaces state once; either both lifecycle writes land or neither. A passing IMPLEMENT edge first validates and binds all declared process evidence through `_shared/process-evidence.py`. The verb returns JSON paths/digests/state facts only and never chooses a phase, engine, branch, prompt, or agent.
3. **Complete** (after the orchestrator reads the phase's reply and determines the verdict, when no next phase opens): `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase <name> complete --verdict <V> [--post-sha <sha>] [--findings-file <path>] [--log-file <path>] [--engine-session-log <path>]`. Pass only the phase/round canonical worker session. SURFACE_CLOSE passes `.devlyn/surface-close.output.json`; schema-v3 Codex PLAN/IMPLEMENT/BUILD_GATE/CLEANUP passes the wrapper-captured `.devlyn/<phase>.worker-session.<round>.jsonl` and requires its sibling invocation receipt plus `.devlyn/<phase>.prompt.<round>`. Never scan an engine-global session directory or synthesize a model header. `duration_ms` is derived from the phase's own `started_at`. `--verdict` is required except VERIFY, whose verdict remains owned by `verify-merge-findings.py --write-state`.
4. **Before archive** (PHASE 6 step 5): write `.devlyn/final-report.md` with exactly one first-line `<!-- devlyn:final-report run_id=<current state.run_id> -->` and a non-whitespace body, then complete FINAL_REPORT with `--log-file .devlyn/final-report.md`. Missing, unsafe, empty or mismatched report input fails before completion; the marker proves run identity, not semantic completeness. This also applies to BLOCKED missing-PLAN-output closure. Archive rehashes a present FINAL_REPORT `output_sha256` binding before any move; missing/altered files or malformed/null bindings fail without moving artifacts. Historical states with that field absent retain existing archive behavior. Archive prune skips runs whose final_report verdict is null (treated as in-flight).

## Terminal verdict (PHASE 6)

Precedence:

1. finish-gate exit 1 or 2 → `BLOCKED:finish-gate-unclean`; `phases.<any>.verdict == "BLOCKED"` → terminal `BLOCKED:<reason>`.
2. `phases.verify.verdict == "NEEDS_WORK"` after fix-loop exhaustion → terminal `NEEDS_WORK`.
3. `phases.verify.verdict == "PASS_WITH_ISSUES"` → terminal `PASS_WITH_ISSUES`; any finish-gate offender → `BLOCKED:finish-gate-unclean` under precedence 1.
4. `phases.verify.verdict == "PASS"` → terminal `PASS`.
5. Verify-only mode: terminal = `phases.verify.verdict` directly (PHASE 1-4 are skipped).

## Final-report shape

Header: `run_id | engine | mode | complexity | verdict | wall_time_s`.

Per-phase summary table: `phase | verdict | duration_ms | round | triggered_by | findings_count`; include SURFACE_CLOSE when run or skipped.

Findings table: each emitted finding's `severity | rule_id | file:line | message | confidence`.

Follow-up notes: when `phases.surface_close.continued_after_block` is true, exactly one explicit `pipeline continued to BUILD_GATE — surface_close_rolled_back_adjudication_malformed` line (never a terminal floor); any large-mode assumptions; any pair-judge TIMEOUT surfaced as `solo verdict after pair TIMEOUT`; pair/risk-probe opt-out state; engine setup guidance for `BLOCKED:<engine>-unavailable`; `/devlyn:ideate` guidance for `BLOCKED:solo-headroom-hypothesis-required` that asks for the visible behavior `solo_claude` is expected to miss; `/devlyn:ideate` guidance for `BLOCKED:solo-ceiling-avoidance-required` that asks for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`; and any `state.verify.coverage_failed` axes.

## Archive contract

PHASE 6 step 4 moves `PER_RUN_PATTERNS` plus every state-bound process manifest/raw stream and invocation receipt into `.devlyn/runs/<run_id>/`, preserving relative layout and rehashing each bound digest first. It includes every phase/round prompt and worker session, including BUILD_GATE, and revalidates the receipt's internal prompt/session digests; it never scans engine-global sessions. Unsafe paths, symlinks, missing files, digest mismatches, and destination collisions block archive visibly without changing the already-derived product verdict. Machine config stays; the last 10 completed runs remain.

## Explicit role configuration

PHASE0 `state-phase-write.py --freeze-roles --default-engine <orchestrator-default>` freezes `role_resolution` (legacy engine/source, three role entries, input paths/digests, snapshot digest). `role_config_input` holds only the validated per-run roles object and provenance; `role_no_pair` records that flag. No config reread after freezing. Missing legacy snapshots are compatible; present null/malformed snapshots fail. The helper does not launch models.

`state.engine` remains the legacy executor for unchanged PLAN/BUILD/probe routing. IMPLEMENT/CLEANUP spawn enforce frozen worker engine/model. VERIFY spawn explicitly records the primary in `phases.verify.engine`; merge, timeout and OTHER exclusion use it, falling back only when absent. Requested settings are distinct from native-observed fields. Explicit Codex worker effort binds `role_argv` against the existing invocation argv digest; effort remains dispatch evidence, not provider-internal attestation.

Successful explicit judges retain `<engine>-judge.r<round>.*` raw/prompt/argv/derived/evidence files; `verify.role_evidence` binds their hashes, observed model/nullable effort and named evidence basis. VERIFY history preserves those bindings. Merge alone binds successful evidence; archive rehashes every bound artifact. Canonical `<engine>-judge.stdout` is the current collector input and is never substituted for the immutable round raw. Failed raw remains diagnostic and cannot become a successful binding.
