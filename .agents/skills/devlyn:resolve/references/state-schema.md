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
- **mode** — `"free-form" | "spec" | "verify-only"`.
- **pair_verify** — boolean. True only for `--pair-verify`. Pairing is already default-when-available; this flag makes OTHER-engine availability an explicit fail-closed promise and adds `mode.pair-verify` telemetry. It is mutually exclusive with `risk_profile.pair_default_enabled == false` from `--no-pair`.
- **complexity** — `null | "trivial" | "medium" | "large"`. Free-form mode populates this; spec/verify-only mode leaves it null.
- **engine** — any engine name with a shipped adapter (`_shared/adapters/<name>.md`); `"claude"` and `"codex"` today. A required unavailable engine stops the run with `BLOCKED:<engine>-unavailable`.
- **engine_source** — `"flag" | "engines.json" | "default"` — provenance of the resolved executor engine (`_shared/engine-preflight.md#role-resolution`). Optional on archived pre-iter-0038 runs; absent means `default`.
- **source** — provenance for the contract all downstream phases read. Spec and verify-only mode set `type: "spec"`, `spec_path`, and `spec_sha256`. Free-form mode sets `type: "generated"`, leaves `spec_path`/`spec_sha256` null, and must set `criteria_path: ".devlyn/criteria.generated.md"` plus `criteria_sha256` from the generated file's raw bytes. VERIFY re-checks the matching hash before judging.
- **risk_profile** — PHASE 0 routing state. `high_risk` controls automatic risk probes; `risk_probes_enabled` / `risk_probes_explicit` preserve their current semantics; `pair_default_enabled` is false only for explicit `--no-pair`. `risk_profile` must remain an object with boolean `high_risk`, `risk_probes_enabled`, `risk_probes_explicit`, and `pair_default_enabled` fields when present, plus `reasons` as a string list. Malformed state blocks VERIFY because it can hide required routes.
- **risk_probes_digest** — top-level sha256 written by PHASE 1.5 after probe validation; BUILD_GATE/VERIFY replay semantics live in `phases/build-gate.md` step 4.
- **rounds.global** — incremented every fix-loop pass (BUILD_GATE → fix-loop, VERIFY → fix-loop, OR a phase-gate fix respawn inside phase-gated IMPLEMENT).
- **phases.implement.exec** — only on phase-gated large runs (plan.md has `## Execution phases` with >1 phase): `{ "total": N, "current": k, "statuses": ["PASS"|"FAIL"|null, ...], "commits": ["<sha>", ...] }`. Phase definitions live in plan.md (immutable contract); progress lives here (routing truth — never route on plan.md checkboxes). Absent on single-phase runs. `cumulative.patch` for such runs is `git diff <base_ref.sha>...HEAD`.
- **phases.probe_derive** — optional PHASE 1.5 entry when `--risk-probes` is enabled. Artifacts include `.devlyn/risk-probes.jsonl`. Probe failures later surface through BUILD_GATE/VERIFY as `correctness.risk-probe-failed`.
- **bypasses** — array of phase names from `--bypass`. Valid: `"build-gate" | "cleanup"`. PLAN, IMPLEMENT, VERIFY are non-bypassable (orchestrator rejects at parse time).
- **implement_passed_sha** — captured at end of PHASE 2; null until then. Activates the post-implement invariant for CLEANUP and VERIFY.
- **criteria** — spec mode uses one entry per `## Requirements` checkbox. Free-form mode uses one non-authoritative entry with `ref: "criteria.generated://goal"`; it becomes `implemented` only when every raw Goal clause is satisfied, never from regenerated 3-5 bullets. `failed_by_finding_ids` records VERIFY findings.
- **`.devlyn/untracked.baseline` artifact** — written at PHASE 0 (`spec-verify-check.py --write-untracked-baseline`); BUILD_GATE flags created-during-run unauthorized untracked files against it (`.devlyn/` exempt; semantics in `phases/build-gate.md` step 4).
- **verify.coverage_failed** — outcome-dependent telemetry set when JUDGE cannot exercise a spec axis. It no longer gates pair dispatch: after MECHANICAL passes, `pair.default` dispatches both judges concurrently whenever `pair_default_enabled != false` and the OTHER engine is available. An orchestrator without foreground parallel dispatch runs the same two required judges sequentially; a primary blocker never skips the pair. A verdict-binding MECHANICAL blocker still skips both. Legacy complexity values remain accepted only for archived compatibility.
- **verify.pair_trigger** — strict decision state: `{ "eligible": boolean, "reasons": string[], "skipped_reason": string|null }`. Schema v3.0 eligible state requires `pair.default` plus every applicable telemetry reason and `skipped_reason: null`; outcome-dependent reasons are appended after both judges return. Canonical reasons are `pair.default`, `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, and `judge.warning`. Ineligible new-run state has empty reasons and only `user_no_pair`, `mechanical_blocker`, `auto_pair_other_engine_unavailable`, or null; `primary_judge_blocker` remains parser-recognized only for archived v2.0 replay and retains its existing pre-known-reason rejection. Explicit `mode.pair-verify` cannot use the unavailable-engine skip. Missing, contradictory, incomplete, or unknown trigger state BLOCKs VERIFY.

## Per-phase shape

Each entry under `phases.<name>` (for `plan`, `probe_derive`, `implement`, `build_gate`, `cleanup`, `verify`, `final_report`):

```json
{
  "started_at": "2026-04-30T12:00:01Z",
  "completed_at": "2026-04-30T12:00:30Z",
  "duration_ms": 29000,
  "round": 0,
  "triggered_by": null,
  "verdict": "PASS",
  "engine": "claude",
  "model": "<exact model id that ran this phase>",
  "pre_sha": null,
  "post_sha": null,
  "artifacts": { "findings_file": null, "log_file": null },
  "sub_verdicts": null
}
```

`history` is absent until a phase is re-entered. Immediately before re-entry overwrites the live `started_at`, `verdict`, `completed_at`, and `duration_ms`, `state-phase-write.py` appends those prior values as one object to `history[]`, creating the append-only array on first re-entry.

- `verdict` — `"PASS" | "PASS_WITH_ISSUES" | "FAIL" | "NEEDS_WORK" | "BLOCKED"`. PHASE 6 (FINAL_REPORT) writes its own verdict per the terminal-verdict precedence.
- `triggered_by` — null on first run; one of `"build_gate" | "verify"` when the phase is a fix-loop respawn.
- `pre_sha` — captured by orchestrator before CLEANUP and (if needed) other allowlist-enforced phases. Used to validate the post-spawn diff.
- `post_sha` — captured on CLEANUP complete when that phase ran; finish-gate subtracts `pre_sha..post_sha` as the cleanup window.
- `sub_verdicts` — only populated for VERIFY: `{ "mechanical": "PASS|FAIL", "judge": "PASS|...", "pair_judge": "PASS|..." | "TIMEOUT" | null }`. Values are normalized by `verify-merge-findings.py`; model prose verdicts cannot upgrade or downgrade the deterministic findings-derived verdict. `sub_verdicts.pair_judge` is `"TIMEOUT"` when a pair judge exceeded its wall budget and a valid `.devlyn/verify.pair.timeout.json` marker was read — semantics in `references/phases/verify.md` (pair budget section).
- `judge_durations_ms` — only populated for VERIFY: `{ "judge": <non-negative int>, "pair_judge": <non-negative int|null> }`. The orchestrator writes each wall duration when it collects that judge's result; values remain a sibling of `sub_verdicts`, whose values stay normalized strings. VERIFY spawn resets this key to null so re-entry cannot retain prior-round timings.
- `merged` — only populated for VERIFY after `verify-merge-findings.py --write-state`: `{ "verdict": "...", "findings_file": ".devlyn/verify-merged.findings.jsonl", "summary_file": ".devlyn/verify-merge.summary.json" }`.
- `pair_trigger` — only populated for VERIFY; same shape as top-level `verify.pair_trigger` when the phase stores it locally.
- `correctness.risk-probe-failed` — emitted by `spec-verify-check.py --include-risk-probes` when an executable probe derived from the visible `## Verification` section fails.

## Write protocol

Phase lifecycle (`started_at`/`completed_at`/`duration_ms`/`round`/`triggered_by`/`verdict`) is written by a deterministic script, never hand-edited JSON — a prior hand-edited fix-loop respawn left `started_at` stale, corrupting cross-phase ordering because `completed_at`/`round`/`triggered_by` advanced to the new round while `started_at` didn't. Phase workers report their verdict and artifact paths in their reply; they never edit `pipeline.state.json` themselves.

1. **Spawn** (before every phase dispatch, including a fix-loop respawn — one call per outer phase-gated IMPLEMENT run, not per inner sub-phase): `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase <name> spawn --round <N> [--triggered-by build_gate|verify] [--pre-sha <sha>] [--engine <e>] [--model <m>]`. Re-entry applies the `history` rule above, then resets `started_at` to now and nulls `completed_at`/`duration_ms`/`verdict`/`artifacts`/`sub_verdicts`; VERIFY also nulls `judge_durations_ms`. A VERIFY spawn also deletes the prior round's on-disk VERIFY artifacts (`verify*.jsonl`, `verify-merge.summary.json`, `*-judge.*`) so stale findings cannot read as current-round evidence. Fields the script doesn't own (e.g. `phases.implement.exec`) are left untouched.
2. **Complete** (after the orchestrator reads the phase's reply and determines the verdict): `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase <name> complete --verdict <V> [--post-sha <sha>] [--findings-file <path>] [--log-file <path>]`. `duration_ms` is derived from the phase's own recorded `started_at` — it cannot drift from `completed_at`. `--verdict` is required for every phase except VERIFY: `verify-merge-findings.py --write-state` is the sole writer of `phases.verify.verdict`, so `complete verify` is always called without `--verdict` (an explicit one is rejected) and preserves what's already on disk.
3. **Before archive** (PHASE 6 step 5): `phases.final_report.verdict` must be non-null. Archive prune skips runs whose final_report verdict is null (treated as in-flight).

## Terminal verdict (PHASE 6)

Precedence:

1. finish-gate exit 1 or 2 → `BLOCKED:finish-gate-unclean`; `phases.<any>.verdict == "BLOCKED"` → terminal `BLOCKED:<reason>`.
2. `phases.verify.verdict == "NEEDS_WORK"` after fix-loop exhaustion → terminal `NEEDS_WORK`.
3. `phases.verify.verdict == "PASS_WITH_ISSUES"` or finish-gate findings file present → terminal `PASS_WITH_ISSUES`.
4. `phases.verify.verdict == "PASS"` → terminal `PASS`.
5. Verify-only mode: terminal = `phases.verify.verdict` directly (PHASE 1-4 are skipped).

## Final-report shape

Header: `run_id | engine | mode | complexity | verdict | wall_time_s`.

Per-phase summary table: `phase | verdict | duration_ms | round | triggered_by | findings_count`.

Findings table (post-IMPLEMENT phases only — they are findings-only): each finding's `severity | rule_id | file:line | message | confidence`.

Follow-up notes: any large-mode assumptions, any pair-judge TIMEOUT surfaced as `solo verdict after pair TIMEOUT`, pair/risk-probe opt-out state, engine setup guidance for `BLOCKED:<engine>-unavailable`, `/devlyn:ideate` guidance for `BLOCKED:solo-headroom-hypothesis-required` that asks for the visible behavior `solo_claude` is expected to miss, `/devlyn:ideate` guidance for `BLOCKED:solo-ceiling-avoidance-required` that asks for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`, and any `state.verify.coverage_failed` axes.

## Archive contract

PHASE 6 step 4 moves the per-run artifact set (`PER_RUN_PATTERNS` in `archive_run.py` — the single source of truth) into `.devlyn/runs/<run_id>/`. Machine config such as `.devlyn/engines.json` is not a run artifact and stays in place. The `.devlyn/runs/` directory keeps the last 10 completed runs (sorted by `started_at`). Best-effort prune; archive failure does not change the run's verdict.
