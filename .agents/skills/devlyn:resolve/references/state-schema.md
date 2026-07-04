# pipeline.state.json schema

Single authoritative verdict source for `/devlyn:resolve`. The orchestrator branches on `state.phases.<name>.verdict` directly — never parses `.devlyn/*.findings.jsonl` for routing. Living document; bump `version` on a breaking change.

## Top-level shape

```json
{
  "version": "2.0",
  "run_id": "rs-<UTC-timestamp>-<12-hex>",
  "started_at": "2026-04-30T12:00:00Z",
  "engine": "claude",
  "mode": "spec",
  "pair_verify": false,
  "complexity": null,
  "risk_profile": { "high_risk": false, "reasons": [], "risk_probes_enabled": false, "pair_default_enabled": true },
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
- **pair_verify** — boolean. Set true only when the user passed `--pair-verify`; otherwise false. This is the durable state evidence for the `mode.pair-verify` pair-trigger reason. It is mutually exclusive with `risk_profile.pair_default_enabled == false` from `--no-pair`; `verify-merge-findings.py` blocks the contradictory state.
- **complexity** — `null | "trivial" | "medium" | "large"`. Free-form mode populates this; spec/verify-only mode leaves it null.
- **engine** — any engine name with a shipped adapter (`_shared/adapters/<name>.md`); `"claude"` and `"codex"` today. A required unavailable engine stops the run with `BLOCKED:<engine>-unavailable`.
- **engine_source** — `"flag" | "engines.json" | "default"` — provenance of the resolved executor engine (`_shared/engine-preflight.md#role-resolution`). Optional on archived pre-iter-0038 runs; absent means `default`.
- **source** — provenance for the contract all downstream phases read. Spec and verify-only mode set `type: "spec"`, `spec_path`, and `spec_sha256`. Free-form mode sets `type: "generated"`, leaves `spec_path`/`spec_sha256` null, and must set `criteria_path: ".devlyn/criteria.generated.md"` plus `criteria_sha256` from the generated file's raw bytes. VERIFY re-checks the matching hash before judging.
- **risk_profile** — PHASE 0 classification for conditional defaults. `high_risk` records durable-risk signals from the goal/spec; `risk_probes_enabled` is true for explicit `--risk-probes` or high-risk specs unless `--no-risk-probes`; `pair_default_enabled` is false only for explicit `--no-pair`. `risk_profile` must remain an object with boolean `high_risk`, `risk_probes_enabled`, and `pair_default_enabled` fields when present, plus `reasons` as a list of strings. Malformed `risk_profile` blocks VERIFY because pair-trigger reasons derive `risk.high` and `risk_probes.enabled` from this state.
- **rounds.global** — incremented every fix-loop pass (BUILD_GATE → fix-loop, VERIFY → fix-loop, OR a phase-gate fix respawn inside phase-gated IMPLEMENT).
- **phases.implement.exec** — only on phase-gated large runs (plan.md has `## Execution phases` with >1 phase): `{ "total": N, "current": k, "statuses": ["PASS"|"FAIL"|null, ...], "commits": ["<sha>", ...] }`. Phase definitions live in plan.md (immutable contract); progress lives here (routing truth — never route on plan.md checkboxes). Absent on single-phase runs. `cumulative.patch` for such runs is `git diff <base_ref.sha>...HEAD`.
- **phases.probe_derive** — optional PHASE 1.5 entry when `--risk-probes` is enabled. Artifacts include `.devlyn/risk-probes.jsonl`. Probe failures later surface through BUILD_GATE/VERIFY as `correctness.risk-probe-failed`.
- **bypasses** — array of phase names from `--bypass`. Valid: `"build-gate" | "cleanup"`. PLAN, IMPLEMENT, VERIFY are non-bypassable (orchestrator rejects at parse time).
- **implement_passed_sha** — captured at end of PHASE 2; null until then. Activates the post-implement invariant for CLEANUP and VERIFY.
- **criteria** — generated from spec's `## Requirements` checklist (one per `- [ ]`). `status: pending → implemented` is the legal transition. `failed_by_finding_ids` populates when VERIFY surfaces a finding tied to a criterion.
- **verify.coverage_failed** — set by VERIFY's JUDGE sub-phase when a spec axis could not be exercised against the diff. Triggers pair-mode escalation when set. Pair-mode also triggers for `state.pair_verify == true`, verify-only mode, high-risk specs, active risk probes, actionable solo-headroom hypotheses, `complexity: high` specs, or current free-form `state.complexity` of `"large"` when MECHANICAL and the primary JUDGE have no verdict-binding blockers. Legacy/external spec `complexity: large` remains accepted for compatibility; new specs use `high`. Legacy `"high"` state remains accepted by the merge validator only for archived run compatibility.
- **verify.pair_trigger** — VERIFY's trigger decision: `{ "eligible": boolean, "reasons": string[], "skipped_reason": string|null }`. The shape is strict: `eligible: true` requires a non-empty reasons list containing every applicable canonical eligible reason and only canonical eligible reasons, plus `skipped_reason: null`; `eligible: false` requires an empty reasons list and may set only `user_no_pair`, `mechanical_blocker`, `primary_judge_blocker`, `auto_pair_other_engine_unavailable`, or null as the skip cause. Canonical eligible reasons are `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, and `judge.warning`. `user_no_pair` is valid only when `risk_profile.pair_default_enabled == false` from an explicit `--no-pair`; `mechanical_blocker` and `primary_judge_blocker` are valid only when the matching source has a verdict-binding finding; `auto_pair_other_engine_unavailable` is valid only when every applicable trigger reason is automatic (none is `mode.pair-verify`) and no pair-judge engine is available per role resolution (pre-iter-0038 SKILL.md already used this skip; the schema previously omitted it — reconciled). If state implies a pair decision is required but `pair_trigger` is missing, if it records `eligible:false` with no supported skip reason, if an eligible trigger omits an applicable reason such as `spec.solo_headroom_hypothesis`, or if any combination is malformed, `verify-merge-findings.py` blocks VERIFY.

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
  "artifacts": { "findings_file": null, "log_file": null },
  "sub_verdicts": null
}
```

- `verdict` — `"PASS" | "PASS_WITH_ISSUES" | "FAIL" | "NEEDS_WORK" | "BLOCKED"`. PHASE 6 (FINAL_REPORT) writes its own verdict per the terminal-verdict precedence.
- `triggered_by` — null on first run; one of `"build_gate" | "verify"` when the phase is a fix-loop respawn.
- `pre_sha` — captured by orchestrator before CLEANUP and (if needed) other allowlist-enforced phases. Used to validate the post-spawn diff.
- `sub_verdicts` — only populated for VERIFY: `{ "mechanical": "PASS|FAIL", "judge": "PASS|...", "pair_judge": "PASS|..." | null }`. Values are normalized by `verify-merge-findings.py`; model prose verdicts cannot upgrade or downgrade the deterministic findings-derived verdict.
- `merged` — only populated for VERIFY after `verify-merge-findings.py --write-state`: `{ "verdict": "...", "findings_file": ".devlyn/verify-merged.findings.jsonl", "summary_file": ".devlyn/verify-merge.summary.json" }`.
- `pair_trigger` — only populated for VERIFY; same shape as top-level `verify.pair_trigger` when the phase stores it locally.
- `correctness.risk-probe-failed` — emitted by `spec-verify-check.py --include-risk-probes` when an executable probe derived from the visible `## Verification` section fails.

## Write protocol

Phase lifecycle (`started_at`/`completed_at`/`duration_ms`/`round`/`triggered_by`/`verdict`) is written by a deterministic script, never hand-edited JSON — a hand-edited fix-loop respawn left `started_at` stale in iter-0042 (`autoresearch/iterations/0042-compliance-drift-probes.md`), corrupting cross-phase ordering because `completed_at`/`round`/`triggered_by` advanced to the new round while `started_at` didn't. Phase workers report their verdict and artifact paths in their reply; they never edit `pipeline.state.json` themselves.

1. **Spawn** (before every phase dispatch, including a fix-loop respawn — one call per outer phase-gated IMPLEMENT run, not per inner sub-phase): `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase <name> spawn --round <N> [--triggered-by build_gate|verify] [--pre-sha <sha>] [--engine <e>] [--model <m>]`. Resets `started_at` to now and nulls `completed_at`/`duration_ms`/`verdict`/`artifacts`/`sub_verdicts` — a respawn can never inherit a prior round's stale timing or verdict. Fields the script doesn't own (e.g. `phases.implement.exec`, the phase-gated progress tracker) are left untouched.
2. **Complete** (after the orchestrator reads the phase's reply and determines the verdict): `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase <name> complete --verdict <V> [--findings-file <path>] [--log-file <path>]`. `duration_ms` is derived from the phase's own recorded `started_at` — it cannot drift from `completed_at`. `--verdict` is required for every phase except VERIFY: `verify-merge-findings.py --write-state` is the sole writer of `phases.verify.verdict`, so `complete verify` is always called without `--verdict` (an explicit one is rejected) and preserves what's already on disk.
3. **Before archive** (PHASE 6 step 3): `phases.final_report.verdict` must be non-null. Archive prune skips runs whose final_report verdict is null (treated as in-flight).

## Terminal verdict (PHASE 6)

Precedence:

1. `phases.<any>.verdict == "BLOCKED"` → terminal `BLOCKED:<reason>`.
2. `phases.verify.verdict == "NEEDS_WORK"` after fix-loop exhaustion → terminal `NEEDS_WORK`.
3. `phases.verify.verdict == "PASS_WITH_ISSUES"` → terminal `PASS_WITH_ISSUES`.
4. `phases.verify.verdict == "PASS"` → terminal `PASS`.
5. Verify-only mode: terminal = `phases.verify.verdict` directly (PHASE 1-4 are skipped).

## Final-report shape

Header: `run_id | engine | mode | complexity | verdict | wall_time_s`.

Per-phase summary table: `phase | verdict | duration_ms | round | triggered_by | findings_count`.

Findings table (post-IMPLEMENT phases only — they are findings-only): each finding's `severity | rule_id | file:line | message | confidence`.

Follow-up notes: any `--continue-on-large` assumptions, pair/risk-probe opt-out state, engine setup guidance for `BLOCKED:<engine>-unavailable`, `/devlyn:ideate` guidance for `BLOCKED:solo-headroom-hypothesis-required` that asks for the visible behavior `solo_claude` is expected to miss, `/devlyn:ideate` guidance for `BLOCKED:solo-ceiling-avoidance-required` that asks for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`, and any `state.verify.coverage_failed` axes.

## Archive contract

PHASE 6 step 4 moves the per-run artifact set (`PER_RUN_PATTERNS` in `archive_run.py` — the single source of truth) into `.devlyn/runs/<run_id>/`. Machine config such as `.devlyn/engines.json` is not a run artifact and stays in place. The `.devlyn/runs/` directory keeps the last 10 completed runs (sorted by `started_at`). Best-effort prune; archive failure does not change the run's verdict.
