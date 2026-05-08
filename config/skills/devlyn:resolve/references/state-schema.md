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
  "complexity": null,
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
- **complexity** — `null | "trivial" | "medium" | "large"`. Free-form mode populates this; spec/verify-only mode leaves it null.
- **engine** — `"claude" | "codex" | "auto"` initially; rewritten by engine-preflight if a downgrade fired.
- **rounds.global** — incremented every fix-loop pass (BUILD_GATE → fix-loop OR VERIFY → fix-loop).
- **phases.probe_derive** — optional PHASE 1.5 entry when `--risk-probes` is enabled. Artifacts include `.devlyn/risk-probes.jsonl`. Probe failures later surface through BUILD_GATE/VERIFY as `correctness.risk-probe-failed`.
- **bypasses** — array of phase names from `--bypass`. Valid: `"build-gate" | "cleanup"`. PLAN, IMPLEMENT, VERIFY are non-bypassable (orchestrator rejects at parse time).
- **implement_passed_sha** — captured at end of PHASE 2; null until then. Activates the post-implement invariant for CLEANUP and VERIFY.
- **criteria** — generated from spec's `## Requirements` checklist (one per `- [ ]`). `status: pending → implemented` is the legal transition. `failed_by_finding_ids` populates when VERIFY surfaces a finding tied to a criterion.
- **verify.coverage_failed** — set by VERIFY's JUDGE sub-phase when a spec axis could not be exercised against the diff. Triggers pair-mode escalation when set. Pair-mode also triggers for `complexity: high` specs or `state.complexity` of `"high"`/`"large"` when MECHANICAL has no HIGH/CRITICAL blockers.
- **verify.pair_trigger** — VERIFY's trigger decision: `{ "eligible": boolean, "reasons": string[], "skipped_reason": string|null }`. If eligible with any reason, `pair_judge` must be non-null.

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
  "model": "claude-opus-4-7",
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

1. **Before each phase spawn**: orchestrator writes `phases.<name>.{started_at, round, triggered_by}` and (when applicable) `pre_sha`.
2. **After each agent returns**: orchestrator validates `verdict`, `completed_at`, `duration_ms`, `artifacts` are populated. Missing fields → orchestrator fills from observable state. Branching on a null verdict is undefined behavior.
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

Follow-up notes: any `--continue-on-large` assumptions, any silent fallbacks (engine downgrade), any `state.verify.coverage_failed` axes.

## Archive contract

PHASE 6 step 4 moves `.devlyn/*` (excluding `.devlyn/runs/`) into `.devlyn/runs/<run_id>/`. The `.devlyn/runs/` directory keeps the last 10 completed runs (sorted by `started_at`). Best-effort prune; archive failure does not change the run's verdict.
