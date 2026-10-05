# pipeline.state.json schema

Single authoritative verdict source for `/devlyn-resolve`. The orchestrator branches on `state.phases.<name>.verdict` directly — never parses `.devlyn/*.findings.jsonl` for routing. Living document; bump `version` on a breaking change.

## Top-level shape

```json
{
  "version": "3.0",
  "role_config_input": null,
  "run_id": "rs-<UTC-timestamp>-<12-hex>",
  "started_at": "2026-04-30T12:00:00Z",
  "session_id": null,
  "engine": "claude",
  "engine_source": "default",
  "mode": "spec",
  "pair_verify": false,
  "complexity": null,
  "risk_profile": { "high_risk": false, "reasons": [], "risk_probes_enabled": false, "risk_probes_explicit": false, "pair_default_enabled": true },
  "risk_probes_digest": null,
  "process_evidence": null,
  "base_ref": { "branch": "main", "sha": "abc123..." },
  "rounds": { "max_rounds": 4, "global": 0 },
  "untracked_baseline_sha256": null,
  "source": {
    "type": "spec",
    "spec_path": "docs/roadmap/phase-1/X.md",
    "spec_sha256": "...",
    "expected_sha256": null,
    "criteria_path": null,
    "criteria_sha256": null
  },
  "phases": {
    "plan": null,
    "probe_derive": null,
    "implement": null,
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
- **complexity** — `null | "trivial" | "medium" | "large"`. The PHASE 0 freeze records it for free-form runs (`--complexity`, required there); spec/verify-only leave it null.
- **engine** — any engine name with a shipped adapter (`_shared/adapters/<name>.md`); `"claude"` and `"codex"` today. A required unavailable engine stops the run with `BLOCKED:<engine>-unavailable`.
- **engine_source** — `"flag" | "engines.json" | "default"` — provenance of the resolved executor engine (`_shared/engine-preflight.md#role-resolution`). Optional on archived pre-iter-0038 runs; absent means `default`.
- **source** — downstream contract provenance. Spec/verify-only set `type: "spec"`, `spec_path`, `spec_sha256`, and `expected_sha256` (the sibling `spec.expected.json` bytes at bootstrap, or null when absent; MECHANICAL, the judge snapshot, process evidence and delivery refuse a changed or newly appeared contract). Verify-only also sets `diff_base_sha`: the commit its supplied ref resolved to, from which bootstrap diffed `.devlyn/external-diff.patch`, or null for a supplied patch file; the judge snapshot reports it as `base_sha`. Free-form sets `type: "generated"`, `goal_path: ".devlyn/goal.raw.txt"` + exact-byte `goal_sha256`, and `criteria_path: ".devlyn/criteria.generated.md"` + raw-byte `criteria_sha256` (bound by the PHASE 0 freeze). MECHANICAL and the VERIFY judge snapshot re-check these hashes before use.
- **`.devlyn/external-diff.patch` artifact** — verify-only Git patch with `a/` and `b/` path prefixes (`git diff --binary --src-prefix=a/ --dst-prefix=b/`). A zero-byte file means no changes; file-path checks reject malformed or other-prefix input. File exclusions cover both names in rename/copy headers. The verifier fails closed if the artifact exists outside `"verify-only"` mode.
- **risk_profile** — PHASE 0 routing state. Bootstrap writes the probe and pair flag fields; the freeze writes `high_risk`/`reasons` from `--high-risk-reason`, from declared `required_risk_probe_requirements` (reason `declared-risk-probe-requirements`), and the automatic probe decision. `high_risk` controls automatic risk probes; `risk_probes_enabled` / `risk_probes_explicit` preserve their current semantics; `pair_default_enabled` is false only for explicit `--no-pair`. `risk_profile` must remain an object with boolean `high_risk`, `risk_probes_enabled`, `risk_probes_explicit`, and `pair_default_enabled` fields when present, plus `reasons` as a string list. Malformed state blocks VERIFY because it can hide required routes.
- **risk_probes_digest** — top-level sha256 written by PHASE 1.5 after probe validation; VERIFY MECHANICAL replay semantics live in `phases/mechanical.md` step 1.
- **process_evidence** — absent or JSON null for legacy runs and new runs with no captured obligation; otherwise an append-only array of `{phase, round, manifest: {path, sha256}, streams: [{id, stdout: {path, sha256}, stderr: {path, sha256}}]}` carriers. Paths are worktree-relative and live under `.devlyn/process-evidence/<run_id>/<phase>/round-<round>/`. A successful IMPLEMENT completion/transition validates every sibling `spec.expected.json.process_evidence[]` item declared for `phase: "implement"`, rehashes both raw streams (including zero-byte files), and appends the carrier before accepting the checkpoint. Missing, altered, escaping, duplicate-id, or expectation-mismatched evidence blocks without a state mutation. Later phases reuse the same carrier shape; no schema-major bump is required because readers must accept absent/null legacy state.
- **base_ref.branch** — checked-out branch name, or `null` for a detached HEAD; `base_ref.sha` remains the exact immutable base in both states.
- **rounds.global** — repair IMPLEMENT admissions committed by `state-phase-write.py`, independent of invocation `round`; `max_rounds` defaults to 4. Normal phased advancement uses a fresh IMPLEMENT invocation round without a repair charge. Downstream phases carry the current IMPLEMENT round, or zero before IMPLEMENT.
- **phases.implement.exec** — only on phase-gated runs (the bound plan has two or more `### Phase <k>` blocks): `{ "total": N, "current": k, "statuses": ["PASS"|"FAIL"|null, ...] }`. The writer creates it at the first IMPLEMENT spawn, records FAIL on a failed IMPLEMENT completion (current kept) and on PASS marks the phase and advances current. Phase definitions live in plan.md (immutable contract); progress lives here. Absent on single-phase runs. `cumulative.patch` for such runs is `git diff <base_ref.sha>...HEAD`.
- **phases.probe_derive** — optional PHASE 1.5 entry when `--risk-probes` is enabled. Artifacts include `.devlyn/risk-probes.jsonl`. Probe failures later surface through VERIFY MECHANICAL as `correctness.risk-probe-failed`, or as `correctness.verification-timeout` when the probe exceeds its verification budget.
- **phases.implement.durability** — append-only VERIFY repair checkpoints, one `{round, origin_phase: "verify", triggering_findings_sha256, pre_fix_sha, fix_commit_sha}` per `durability-enforce`; fresh VERIFY re-entry rechecks the round's entry against the clean tree and the merged findings.
- **`.devlyn/repair-settle.r<n>.json` artifact** — the post-fix checkpoint's settlement record for repair IMPLEMENT round `<n>` (`finish-gate.py --settle-repair --round <n>`): each out-of-surface path and the outcome of returning it to its pre-run state, failures included. It is distinct from the finish gate's first-result record.
- **untracked_baseline_sha256** — sha256 of `.devlyn/untracked.baseline`, bound by the first phase spawn; MECHANICAL refuses to seal against different baseline bytes.
- **`.devlyn/untracked.baseline` artifact** — written at PHASE 0 (`spec-verify-check.py --write-untracked-baseline`) as JSON with three lists of paths. `untracked` holds the untracked files already present; `ignored` is the complete inventory of ignored entries, an ignored directory collapsed to one entry. A path equal to or under an entry of either list is covered and is the user's: in normal mode it is compared by path and kind only, only an exact `authorized_surface` entry naming it adopts it, and it is never deleted. Deletion is decided by a script, against an inventory verified by `untracked_baseline_sha256`. `sparse_absences` holds the skip-worktree paths the worktree lacked, which is a sparse checkout's absences. In normal mode, VERIFY MECHANICAL flags unauthorized untracked files the baseline does not cover and seals only a tree whose untracked files it covers. A skip-worktree path keeps Git's sparse treatment only while `sparse_absences` lists it and it is still absent (`.devlyn/` exempt; semantics in `phases/mechanical.md`).
- **verify.coverage_failed** — archived telemetry only; it never gates dispatch. After MECHANICAL passes, `verify-judges.py` starts both judges concurrently whenever `pair_default_enabled != false` and the OTHER engine is available; a primary blocker never skips the pair. A verdict-binding MECHANICAL blocker still skips both, recorded by the same supervisor call. Legacy complexity values remain accepted only for archived compatibility.
- **verify.pair_trigger** — decision state written by the merge from the pre-launch dispatch record, identical in `verify.pair_trigger` and `phases.verify.pair_trigger`: `{ "eligible": boolean, "reasons": string[], "skipped_reason": string|null }`. Eligible state has `skipped_reason: null` and the outcome-independent reasons as telemetry. Canonical reasons are `pair.default`, `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, and `judge.warning`. Ineligible new-run state has empty reasons and only `user_no_pair`, `mechanical_blocker`, `auto_pair_other_engine_unavailable`, or null; `primary_judge_blocker` remains parser-recognized only for archived v2.0 replay and retains its existing pre-known-reason rejection. Explicit `mode.pair-verify` cannot use the unavailable-engine skip. Missing, contradictory, or unknown trigger state BLOCKs VERIFY.

## Per-phase shape

Each entry under `phases.<name>` (for `plan`, `probe_derive`, `implement`, `verify`, `final_report`; archived runs may also carry the retired `surface_close`, `build_gate` and `cleanup` entries):

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
  "artifacts": { "findings_file": null, "log_file": null },
  "sub_verdicts": null
}
```

`history` is absent until a phase is re-entered. Immediately before re-entry overwrites the live lifecycle, `state-phase-write.py` appends those prior values as one object to `history[]`, creating the append-only array on first re-entry. Codex worker history also retains its state-bound `invocation_receipt`; PLAN history retains the complete prompt/output receipt. Owner phase history preserves output/checkpoint digests, its round and present execution kind/worker provenance; historical absence of the kind remains absent.

- `verdict` — ordinary phases use `"PASS" | "PASS_WITH_ISSUES" | "FAIL" | "NEEDS_WORK" | "BLOCKED"`; FINAL_REPORT persists the full terminal verdict, including `BLOCKED:<reason>`.
- `execution_kind` — owner PLAN uses `"orchestrator_context"` with null engine/model fields and no worker prompt, receipt or role identity. Worker claims and current-round worker artifacts are rejected; unknown or null kinds fail closed.
- `model_requested` / `model_effective` — `model_requested` is supplied by the orchestrator through `--model`; schema-v3 completion cannot replace the spawn engine or requested model. Schema-v3 Codex IMPLEMENT and historical worker PLAN phases validate requested dispatch using the canonical `.devlyn/<phase>.invocation.<round>.json`; state rehashes the receipt, round-scoped prompt and worker session and cross-checks model, sandbox, prompt, run, phase, round and exit. A structured native model-reroute event or malformed JSONL blocks completion, even at exit0. The receipt proves argv delivery, so `model_effective` remains null; absence of a reroute is not positive model attestation. Arbitrary paths and plaintext `model:` headers are not evidence. Claude JSON output accepts a singleton `modelUsage` key or, for multiple entries, the sole key whose token counters exactly match top-level usage. Missing/malformed evidence and requested/effective mismatch fail closed: the phase verdict becomes `BLOCKED` and completion fails.
- `output_sha256` — on schema-v3 PLAN completion, SHA-256 of exact `.devlyn/plan.md` bytes. Only caller-verdict BLOCKED with a lexically absent, never-bound plan records null; receipt/session attestation still applies. This terminal null permits only FINAL_REPORT lifecycle operations while the path remains lexically absent. Bound bytes are rehashed on later spawn/completion/transition, including BLOCKED; legal PLAN re-entry replaces the digest only at the new PLAN completion. FINAL_REPORT completion binds exact `.devlyn/final-report.md` bytes here and its canonical path in `artifacts.log_file`.
- `invocation_receipt` — state-bound `{path, sha256, sandbox, sandbox_network_access, argv_sha256, exit_code}` for schema-v3 Codex IMPLEMENT and historical worker PLAN. Receipt schema 2.0 makes `sandbox` exactly `workspace-write` and `sandbox_network_access` exactly `false`. A missing CI capability or wider phase authority blocks before launch. Pre-2.0 receipts are intentionally rejected rather than migrated because they did not attest this capability; do not rewrite in-flight evidence. Continue through the owning session or start in a distinct worktree; restarting via explicit manual archive requires the operator to establish that prior writers stopped, never automatic archival to defeat admission refusal. A completed final report does not prove all interactive writers exited. The receipt is retained in history and rehashed before archive.
- `triggered_by` — null on first IMPLEMENT, phased advancement and phase-gate repair; VERIFY repair records `"verify"`.
- `pre_sha` — VERIFY only: HEAD recorded by the writer when the span opens. MECHANICAL seals only source at this HEAD.
- `sub_verdicts` — only populated for VERIFY: `{ "mechanical": "PASS|...", "judge": "PASS|...", "pair_judge": "PASS|..." | "TIMEOUT" | null }`. Values are normalized by `verify-merge-findings.py`: each seat is the worse of its authenticated findings and its own terminal verdict, so model prose cannot upgrade a finding. `sub_verdicts.pair_judge` is `"TIMEOUT"` when the pair runner's transport records `outcome: "timed_out"` and the pair left no findings.
- `judge_durations_ms` — only populated for VERIFY: `{ "judge": <non-negative int|null>, "pair_judge": <non-negative int|null> }`, copied by the merge from each launched seat's runner-written `elapsed_ms`; values remain a sibling of `sub_verdicts`, whose values stay normalized strings. VERIFY spawn resets this key to null so re-entry cannot retain prior-round timings.
- `merged` — only populated for VERIFY after `verify-merge-findings.py --write-state`: `{ "verdict": "...", "findings_file": ".devlyn/verify-merged.findings.jsonl", "summary_file": ".devlyn/verify-merge.summary.json" }`.
- `pair_trigger`, `dispatch`, `executions` — only populated for VERIFY by the merge: the published trigger, the `{path, sha256, bytes}` binding of `.devlyn/verify-judge.r<round>.dispatch.json`, and sealed captures of seats that did not exit 0.
- `source_seal` — VERIFY only, current round: the merge's `{path, sha256, bytes}` binding of `.devlyn/source-seal.json`, whose `seal.head` is the commit delivery may publish. Archive rehashes it.
- `correctness.risk-probe-failed` — emitted by `spec-verify-check.py --include-risk-probes` when an executable probe derived from the visible `## Verification` section fails.

## Write protocol

Every non-self-test writer command, including role freezing, holds `.devlyn/pipeline.state.lock` before state read through final write or artifact clearing. `verify-merge-findings.py --write-state` holds the same lock across judge collection, merge and state write, once per VERIFY round (a second call refuses without writing); `verify-judges.py` reads state under it and releases it before invoking the merge. Callers never take the lock or edit state between writer commands. No nested lock or unlocked fallback.

Phase lifecycle (`started_at`/`completed_at`/`duration_ms`/`round`/`triggered_by`/`verdict`) is written by a deterministic script, never hand-edited JSON — a prior hand-edited fix-loop respawn left `started_at` stale, corrupting cross-phase ordering because `completed_at`/`round`/`triggered_by` advanced to the new round while `started_at` didn't. Phase workers report their verdict and artifact paths in their reply; they never edit `pipeline.state.json` themselves.

1. **Spawn**: IMPLEMENT admission selects the greatest started `(round, phase-order)` among IMPLEMENT and VERIFY. A merged VERIFY NEEDS_WORK or current IMPLEMENT gate FAIL admits one charged repair with the exact trigger; a completed phased IMPLEMENT with all preceding statuses PASS and current status null admits uncharged advancement. Both paths require the next invocation round. Counter validation and increment happen under the state lock, and refusal preserves original state bytes. `state-phase-write.py --devlyn-dir .devlyn --phase <name> spawn --round <N> [--triggered-by verify] [--engine <e>] [--model <requested-model>] [--prompt-sha256 <hex>]`. Re-entry preserves lifecycle/receipts in `history[]`, resets owned fields, and leaves fields such as `phases.implement.exec`; VERIFY also records `pre_sha`, clears prior-round files (findings, results, source seal) and both `pair_trigger` locations, keeping dispatch, trigger, evidence and verdict bindings in `history[]`; a re-entry after VERIFY repair first rechecks the round's `durability` receipt. Owner PLAN spans omit engine/model/prompt arguments. Metadata-bearing PLAN calls retain the legacy worker API; owner spans cannot be relabeled as workers. Code/doc upkeep belongs to the selected IMPLEMENT invocation. Schema-v3 Codex IMPLEMENT requires the requested model and prompt digest; an inherited top-level Codex engine is persisted into the phase rather than becoming an unattested null route.
2. **Transition** (normal direct handoff): `state-phase-write.py ... --phase <current> transition` takes the same completion/attestation arguments plus caller-specified `--next-phase`, `--next-round`, `--next-triggered-by`, `--next-engine`, and `--next-model`. Edges into PROBE_DERIVE and IMPLEMENT do not use it: they run standalone complete, `phase-prompt-render.py`, then standalone spawn (IMPLEMENT on Codex with the rendered digest). It validates a fixed legal edge, applies complete plus spawn to a detached candidate, and replaces state once; either both lifecycle writes land or neither. A passing IMPLEMENT edge first validates and binds all declared process evidence through `_shared/process-evidence.py`. The verb returns JSON paths/digests/state facts only and never chooses a phase, engine, branch, prompt, or agent.
3. **Complete** (after the orchestrator reads the phase's reply and determines the verdict, when no next phase opens atomically — a halt, or before a worker prompt renders): `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase <name> complete --verdict <V> [--findings-file <path>] [--log-file <path>] [--engine-session-log <path>]`. Pass only the phase/round canonical worker session. Schema-v3 Codex IMPLEMENT and historical worker PLAN pass the wrapper-captured `.devlyn/<phase>.worker-session.<round>.jsonl` and requires its sibling invocation receipt plus `.devlyn/<phase>.prompt.<round>`. Never scan an engine-global session directory or synthesize a model header. `duration_ms` is derived from the phase's own `started_at`. `--verdict` is required except VERIFY, whose verdict remains owned by `verify-merge-findings.py --write-state`, and FINAL_REPORT, whose verdict the writer derives (item 4).
4. **Final report** (PHASE 6 step 3): `state-phase-write.py --devlyn-dir .devlyn --phase final_report complete [--verdict BLOCKED:<reason>] [--detail <text>]` derives the terminal verdict (below), refuses an existing non-regular `.devlyn/final-report.md` before writing, renders the report with exactly one first-line `<!-- devlyn:final-report run_id=<state.run_id> -->`, binds its exact bytes in `output_sha256` under the lock and prints it. `--log-file` is rejected; a refusal writes nothing and leaves state unchanged. This also applies to BLOCKED missing-PLAN-output closure. Archive rehashes a present FINAL_REPORT `output_sha256` binding before any move; missing/altered files or malformed/null bindings fail without moving artifacts. Historical states with that field absent retain existing archive behavior. Archive prune skips runs whose final_report verdict is null (treated as in-flight).

## Terminal verdict (PHASE 6)

The writer derives it; the caller never chooses it. Precedence:

0. A completed PLAN whose bound `output_sha256` no longer verifies → `BLOCKED:phase-input-invalid`; work phases refuse such a PLAN except an exact `BLOCKED` close, VERIFY closes with its merged verdict, and FINAL_REPORT records it instead of refusing.
1. `.devlyn/finish-gate.summary.json` exit 2, or exit 1 once IMPLEMENT has started → `BLOCKED:finish-gate-unclean` (a missing summary refuses completion). Before IMPLEMENT a malformed gate (no usable PLAN surface) does not displace the halt's reason. The gate keeps its first result for the run.
2. A current `BLOCKED` phase verdict → the reason its current-round, state-bound evidence records, rehashed: a MECHANICAL capability denial in the bound VERIFY carrier → `BLOCKED:build-env-underprovisioned`; a blocked judge seat in the bound dispatch record → that seat's `BLOCKED:<reason>`. Findings and log prose are never routing inputs.
3. A current failing repair predecessor whose admission was refused with exhausted counters (`rounds.global == max_rounds`): VERIFY `NEEDS_WORK` (MECHANICAL failures included) → `NEEDS_WORK`; phase-gate IMPLEMENT FAIL → `BLOCKED:repair-budget-exhausted`. With budget remaining, completion needs a supplied halt reason.
4. Verify-only mode → the current VERIFY verdict.
5. Current VERIFY `PASS_WITH_ISSUES` or `PASS` → that verdict.

`--verdict BLOCKED:<reason>` is accepted only when none of these decides — a BLOCKED phase without a derivable reason, or a halt that state does not record — it is a bare label (`judge-route-unsupported:<engine>` is the one qualified family; prose goes to `--detail`) that never names `finish-gate-unclean`, `build-env-underprovisioned` or `repair-budget-exhausted`, and before any work phase it must be a PHASE 0 halt (a role-resolution refusal, `invalid-classification`, `large-needs-ideation` or `untracked-baseline-unwritable`); when evidence decides, a different supplied verdict is refused.

## Final-report shape

The writer renders: header `run_id | engine | mode | complexity | verdict | wall_time_s`; per-phase table `phase | verdict | duration_ms | round | triggered_by | findings_count | note` (owner PLAN, VERIFY MECHANICAL as orchestrator commands with no separate model, and this round's skipped inferred gates from the marked block in `mechanical.log.md`); pair and risk-probe status; findings table `source | severity | rule_id | file:line | message | confidence` from the current merged VERIFY findings and the finish gate (display-only: a missing or unreadable findings file becomes a follow-up note, never a refusal); follow-up notes for a large run's `## Assumptions` block, a pair TIMEOUT (`solo verdict after pair TIMEOUT`), `--no-pair`/`--no-risk-probes` opt-outs, engine setup guidance after `BLOCKED:<engine>-unavailable`, and `--detail`.

## Archive contract

PHASE 6 step 4 moves `PER_RUN_PATTERNS` plus every state-bound process manifest/raw stream and invocation receipt into `.devlyn/runs/<run_id>/`, preserving relative layout and rehashing each bound digest first. It includes every phase/round prompt and worker session and revalidates the receipt's internal prompt/session digests; it never scans engine-global sessions. Unsafe paths, symlinks, missing files, digest mismatches, and destination collisions block archive visibly without changing the already-derived product verdict. Machine config stays; the last 10 completed runs remain.

## Explicit role configuration

PHASE0 `state-phase-write.py --freeze-roles --default-engine <orchestrator-default> [--complexity C] [--high-risk-reason R]...` freezes `role_resolution` (legacy engine/source, three role entries, input paths/digests, snapshot digest) together with the classification above. `role_config_input` holds only the validated per-run roles object and provenance; `--no-pair` reaches it through `risk_profile.pair_default_enabled`, which bootstrap writes. No config reread after freezing. Missing legacy snapshots are compatible; present null/malformed snapshots fail. The helper does not launch models.

`state.engine` remains the legacy executor; PLAN stays orchestrator-fixed, VERIFY MECHANICAL runs orchestrator commands, and probe routing is unchanged. IMPLEMENT (including code/doc upkeep) enforces frozen worker engine/model. VERIFY spawn explicitly records the primary in `phases.verify.engine`; merge, timeout and OTHER exclusion use it, falling back only when absent. Requested settings are distinct from native-observed fields. Explicit Codex worker effort binds `role_argv` against the existing invocation argv digest; effort remains dispatch evidence, not provider-internal attestation.

Every dispatched judge retains `<engine>-judge.r<round>.*` raw/prompt/argv/transport files; successful seats also retain derived stdout and role evidence, which `verify.role_evidence` binds with observed model/nullable effort and the named evidence basis. Seats that did not exit 0 are sealed in `verify.executions` and never become a successful binding. VERIFY history preserves those bindings. Merge alone binds them; archive rehashes every bound artifact. The merge collects the authenticated round stdout; canonical `<engine>-judge.stdout` copies stay diagnostic.
