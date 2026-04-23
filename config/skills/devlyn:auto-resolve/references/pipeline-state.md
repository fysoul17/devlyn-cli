# Pipeline State — `.devlyn/pipeline.state.json`

Control plane for a single auto-resolve run. Contains pointers and state only — never copied content from the spec or findings files.

## Purpose

Every phase reads `pipeline.state.json` to answer:
- What base git SHA am I diffing against? (prevents diff-scope drift across phases)
- Where is the canonical criteria source? (spec file path or generated file path)
- What route was selected and why?
- Which criteria are verified / failed and with what evidence?
- What is the current fix-loop round and max?
- Where are the artifacts from phases that already ran?
- What SHA did EVALUATE first pass at? (post-EVAL invariant check)

State.json is the only cross-phase mutable state. Spec files and `<phase>.findings.jsonl` are immutable within a run.

## File location

`.devlyn/pipeline.state.json` during a run; moved to `.devlyn/runs/<run_id>/pipeline.state.json` at PHASE 5 (archive).

Created by PHASE 0 on run start. At PHASE 5, the entire `.devlyn/` run artifact set is **moved** (not deleted) into `.devlyn/runs/<run_id>/`. See `## Archive contract` below.

## Canonical schema (v1.2)

```json
{
  "version": "1.2",
  "run_id": "ar-<ISO8601-compact>-<uuidv7-short>",
  "started_at": "<ISO-8601 UTC>",
  "engine": "auto" | "codex" | "claude",
  "base_ref": {
    "branch": "<string, e.g. 'main'>",
    "sha": "<full 40-char git sha captured at Phase 0 start>"
  },
  "eval_passed_sha": "<git sha recorded when PHASE 2 first returns PASS or PASS_WITH_ISSUES>" | null,
  "route": {
    "selected": "fast" | "standard" | "strict" | null,
    "user_override": true | false,
    "bypasses": ["<phase-name>", "..."],
    "stage_a": {
      "at": "<ISO-8601 UTC>" | null,
      "reasons": ["<string>", "..."]
    },
    "stage_b": {
      "at": "<ISO-8601 UTC>" | null,
      "escalated_from": "fast" | "standard" | null,
      "reasons": ["<string>", "..."]
    }
  },
  "source": {
    "type": "spec" | "generated",
    "spec_path": "<string path>" | null,
    "spec_sha256": "<hex>" | null,
    "criteria_path": "<string path>" | null,
    "criteria_sha256": "<hex>" | null,
    "criteria_anchors": ["spec://requirements", "..."]
  },
  "criteria": [
    {
      "id": "C1",
      "ref": "<anchor>",
      "status": "pending" | "implemented" | "verified" | "failed",
      "evidence": [
        {"file": "<string>", "line": <int>, "note": "<string>"}
      ],
      "failed_by_finding_ids": ["<string>"]
    }
  ],
  "phases": {
    "<phase_name>": {
      "verdict": "PASS" | "PASS_WITH_ISSUES" | "NEEDS_WORK" | "FAIL" | "BLOCKED" | null,
      "engine": "codex" | "claude" | "bash" | "dual" | null,
      "model": "<string>" | null,
      "started_at": "<ISO-8601 UTC>" | null,
      "completed_at": "<ISO-8601 UTC>" | null,
      "duration_ms": <int> | null,
      "round": <int>,
      "triggered_by": "<phase-name>" | null,
      "pre_sha": "<git sha captured before this phase spawned; used for per-phase diff invariant>" | null,
      "artifacts": {
        "findings_file": "<path>" | null,
        "log_file": "<path>" | null
      }
    }
  },
  "rounds": {
    "global": <int>,
    "max_rounds": <int>
  },
  "perf": {  // OPTIONAL — present only when --perf flag is passed (v3.4 demoted from mandatory)
    "wall_ms": <int>,
    "tokens_total": <int>,
    "per_phase": [
      {"phase": "<name>", "engine": "codex" | "claude" | "bash" | "dual", "wall_ms": <int>, "tokens": <int>, "round": <int>, "triggered_by": "<phase>" | null}
    ]
  }
}
```

## Field semantics

### Top-level

- `version` — schema version; current value `1.2`. Orchestrators must refuse incompatible versions.
- `run_id` — unique, time-sortable run identifier in format `ar-<UTC-compact>-<12 hex>`. Example: `ar-20260423T163044Z-018f4c2a1b9c`.
- `started_at` — Phase 0 start, ISO-8601 UTC.
- `engine` — user-provided `--engine` flag value, or `auto` default.
- `base_ref` — git state captured at Phase 0. **All subsequent `git diff` commands use this SHA**, not `HEAD~1` or `main`. This eliminates diff-scope drift.
- `eval_passed_sha` — `null` until PHASE 2 first returns `PASS` or `PASS_WITH_ISSUES`. At that moment the orchestrator records `git rev-parse HEAD` here. After this field is populated, the **post-EVAL findings-only invariant** applies: PHASE 3 (CRITIC) must not write any non-doc files (reverted on violation), and PHASE 4 (DOCS) may only touch doc-allowlist paths. See `invariants` section of the skill.

### Route

- `selected` — `fast` / `standard` / `strict`, or `null` before Phase 0 decides.
- `user_override` — `true` if user passed `--route <value>`.
- `bypasses` — list of phase names the user explicitly bypassed via `--bypass <phase>`. Surfaced in the final report's `Guardrails bypassed` line. Empty list if no bypass.
- `stage_a` — initial routing at Phase 0, based on spec frontmatter + content scan.
- `stage_b` — post-BUILD checkpoint at Phase 1.4 completion. **Can only escalate** (fast → standard → strict), never de-escalate. `at` is `null` if no escalation.
- `reasons` — human-readable decision rationale, surfaced in final report.

### Source

- `type` — `spec` (roadmap spec file) or `generated` (ad-hoc task).
- `spec_path` + `spec_sha256` — canonical spec pointer + integrity hash for spec runs. Each phase re-computes and compares before reading. Mismatch → phase writes `verdict: "BLOCKED"` with reason `spec_sha256 mismatch`.
- `criteria_path` + `criteria_sha256` — same pair for generated runs. `criteria_sha256` is populated by PHASE 1 BUILD after it creates `criteria.generated.md`. Subsequent phases verify it the same way.
- `criteria_anchors` — enumerated anchors downstream phases may reference.

### Criteria

One entry per testable criterion extracted from the source. State machine: `pending → implemented → verified | failed`.

### Phases

Key is phase name (v3.4 set): `build`, `build_gate`, `browser_validate`, `evaluate`, `fix_loop`, `critic`, `docs`, `final_report`.

- `verdict` — `PASS` / `PASS_WITH_ISSUES` / `NEEDS_WORK` / `FAIL` / `BLOCKED` / `null`. **Single canonical verdict source** — orchestrator branches on this, never by parsing artifact files.
- `engine` / `model` — which model ran this phase. `bash` for build-gate. `dual` for `critic` security sub-pass on `--engine auto`.
- `round` — which fix-loop round this execution belongs to. Phases that run once: `1`. `build_gate`, `browser_validate`, `evaluate`, `critic` increment with fix-loop iterations.
- `triggered_by` — for phases re-run via the unified fix loop (PHASE 2.5), records the triggering phase name (`build_gate` / `browser_validate` / `evaluate` / `critic`). Also written on fix-loop entries themselves. `null` for the first run.
- `pre_sha` — captured by the orchestrator immediately before spawning a post-EVAL phase (`git rev-parse HEAD`). Used by the post-EVAL invariant to diff **only what this phase touched**. Applies to `critic` and `docs`. `null` for PARSE/BUILD/BUILD_GATE/BROWSER/EVAL (those use `base_ref.sha`).
- `artifacts` — pointers to phase output files. Phases that emit structured findings write both `findings_file` and `log_file`. `critic` writes a single `.devlyn/critic.findings.jsonl` carrying both design and security rule_id prefixes. DOCS leaves both `null` (its output is git commits).
- `sub_verdicts` (only on `critic`) — `{"design": <verdict>, "security": <verdict>}`; overall `verdict` = WORSE of the two per `references/phases/phase-3-critic.md`.
- `dep_audit` (only on `critic`) — `{"ran": bool, "command": "<cmd>", "high": N, "critical": N}` populated when critic's security sub-pass ran `npm audit` / `pip-audit` / equivalent.

### Rounds

- `global` — shared round counter across all fix-loop invocations regardless of trigger. Increments once per fix-loop iteration.
- `max_rounds` — cap from `--max-rounds` flag (default 4).

### Perf (opt-in via `--perf`, v3.4)

When `--perf` is passed, the orchestrator records wall-time and token consumption per phase for retrospective benchmarking. When the flag is omitted (the default), the `perf` block is absent from state.json and the orchestrator skips timing/token bookkeeping — Karpathy P2 (Simplicity First) applied: no mandatory meta-measurement.

When enabled:
- `wall_ms` — total wall-clock from PHASE 0 start to PHASE 5 end, in milliseconds.
- `tokens_total` — sum of `per_phase[].tokens`.
- `per_phase` — one entry per phase execution. Fields: `phase`, `engine`, `wall_ms`, `tokens` (from subagent `total_tokens` or Codex usage; `bash` reports 0), `round`, `triggered_by`.

Written at phase completion; totals roll up at PHASE 5.

## Anchor syntax

Format: `<scheme>://<section>[/<index>]`. `scheme` is `spec` or `criteria.generated`. `section` is slug-lowercased H2. `index` is optional 0-based position.

## Write protocol

- **Phase 0 (PARSE + PREFLIGHT + ROUTE)** — creates state.json with `version`, `run_id`, `started_at`, `engine`, `base_ref`, `rounds.max_rounds`, empty `phases`, and (after preflight step) populates `source`, `criteria[]` with `status: pending`, `route.selected`, `route.stage_a`, `route.bypasses`. `eval_passed_sha` remains `null`.
- **Each phase start** — orchestrator writes `phases.<name>.started_at`, `round`, `triggered_by` (if re-run).
- **Each phase end** — phase writes `phases.<name>.{verdict, completed_at, duration_ms, artifacts}`. Build and Evaluate additionally update `criteria[]` state. **When EVALUATE first returns PASS/PASS_WITH_ISSUES**, orchestrator sets `state.eval_passed_sha = git rev-parse HEAD` — this is the reference point for the post-EVAL invariant.
- **Phase 1.4 completion checkpoint** — orchestrator runs Stage B LITE routing check; writes `route.stage_b` on escalation.
- **Phase 5 (FINAL REPORT + ARCHIVE)** — reads state.json for the report, renders the report, then archives (see below).

## Archive contract (PHASE 5)

Best-effort move-and-prune. Replaces the previous "delete `.devlyn/`" behavior.

1. Create `.devlyn/runs/<run_id>/` with `mkdir -p`.
2. Move `.devlyn/pipeline.state.json`, every `.devlyn/<phase>.findings.jsonl`, every `.devlyn/<phase>.log.md`, every `.devlyn/fix-batch.round-*.json`, and `.devlyn/criteria.generated.md` (if exists) into that directory. Use `mv` (atomic within a filesystem).
3. Prune to the last 10 completed runs. List `.devlyn/runs/*/pipeline.state.json`, sort by enclosing `run_id` (lexicographic = chronological because run_ids start with a compact ISO8601 timestamp), and delete the oldest directories until at most 10 remain. **Never delete a directory whose `pipeline.state.json` has `phases.final_report.verdict == null`** — those are still in flight.
4. Kill any dev-server process spawned by PHASE 1.5 (BROWSER VALIDATE).

Best-effort; no cross-process lock. Pruning is idempotent on sorted run_id list, so concurrent runs at worst delete a run already slated for pruning.

## Integrity invariants

The orchestrator enforces:

1. `base_ref.sha` never changes after Phase 0.
2. `source.spec_sha256` (or `source.criteria_sha256` for generated runs) is re-verified at every phase start. Mismatch → the phase writes `verdict: "BLOCKED"` with reason. Missing hash is allowed ONLY on the phase that first populates it (PHASE 0 for spec; PHASE 1 for generated).
3. `route.selected` can only escalate via `stage_b`. No de-escalation.
4. `rounds.global` never exceeds `rounds.max_rounds`.
5. `criteria[].status` progression is monotonic per round: `pending → implemented → verified | failed`. A `failed` criterion can return to `implemented` via a subsequent fix-loop round, then be re-evaluated.
6. **Post-EVAL findings-only** (per-phase diff, not cumulative): once `eval_passed_sha` is non-null, each post-EVAL phase (CRITIC, DOCS) records `phases.<phase>.pre_sha = git rev-parse HEAD` at spawn time. After completion, the orchestrator runs `git diff --name-only <phases.<phase>.pre_sha> -- ':!.devlyn/**'`. For CRITIC (findings-only), any non-empty diff triggers `git reset --hard <pre_sha>` + `invariant.post-eval-code-mutation` finding + fix-loop entry. For DOCS, only doc-file-allowlist paths are legal; everything else triggers the same flow. `pre_sha` (not cumulative `eval_passed_sha`) is the correct baseline because fix-loop commits between EVAL and CRITIC are legitimate — they were re-EVALed. The `:!.devlyn/**` pathspec excludes orchestrator bookkeeping writes.

Violations indicate a bug in the orchestrator. Do not attempt silent recovery.

## Non-goals

- Crash-resume / workflow-engine semantics. State.json enables audit and orchestrator branching, not resume-from-crash.
- Full SARIF export from state.json. `<phase>.findings.jsonl` is the SARIF-aligned surface; state.json is internal.
- Per-finding history across runs. Current run's findings live in its `runs/<run_id>/` directory; cross-run comparison is manual.
