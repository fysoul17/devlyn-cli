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

`.devlyn/pipeline.state.json` during a run; moved to `.devlyn/runs/<run_id>/pipeline.state.json` at PHASE 8 (archive).

Created by PHASE 0 on run start. At PHASE 8, the entire `.devlyn/` run artifact set is **moved** (not deleted) into `.devlyn/runs/<run_id>/`. See `## Archive contract` below.

## Canonical schema (v1.1)

```json
{
  "version": "1.1",
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
  }
}
```

## Field semantics

### Top-level

- `version` — schema version. Bump on breaking changes. Orchestrators must check and refuse incompatible versions. **v1.1** adds: `eval_passed_sha`, `route.bypasses`, `source.criteria_sha256` as a schema field (previously only mentioned in prose), `phases.*.triggered_by`, and `PASS_WITH_ISSUES` / `NEEDS_WORK` to the verdict enum.
- `run_id` — stable identifier. Format: `ar-<ISO8601-compact>-<uuidv7-short>` where ISO8601-compact is `YYYYMMDDTHHMMSSZ` and uuidv7-short is the first 12 hex chars of a UUIDv7 (time-sortable, collision-safe). Example: `ar-20260423T163044Z-018f4c2a1b9c`. Orchestrator generates via `date -u +%Y%m%dT%H%M%SZ` + uuidv7 library (or fallback: `openssl rand -hex 6` — still safe because the ISO timestamp is high-resolution enough for non-concurrent runs).
- `started_at` — Phase 0 start, ISO-8601 UTC.
- `engine` — user-provided `--engine` flag value, or `auto` default.
- `base_ref` — git state captured at Phase 0. **All subsequent `git diff` commands use this SHA**, not `HEAD~1` or `main`. This eliminates diff-scope drift.
- `eval_passed_sha` — `null` until PHASE 2 first returns `PASS` or `PASS_WITH_ISSUES`. At that moment the orchestrator records `git rev-parse HEAD` here. After this field is populated, the **post-EVAL findings-only invariant** applies: any phase other than PHASE 7 (DOCS) that writes non-doc files is reverted by the orchestrator and its attempt becomes a finding. See `invariants` section of the skill.

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

Key is phase name: `build`, `build_gate`, `browser_validate`, `evaluate`, `fix_loop`, `simplify`, `review`, `challenge`, `security_review`, `clean`, `docs`, `final_report`.

- `verdict` — `PASS` / `PASS_WITH_ISSUES` / `NEEDS_WORK` / `FAIL` / `BLOCKED` / `null`. **Single canonical verdict source** — orchestrator branches on this, never by parsing artifact files.
- `engine` / `model` — which model ran this phase. `bash` for build-gate. `dual` for security_review on `--engine auto`.
- `round` — which fix-loop round this execution belongs to. Phases that run once: `1`. `build_gate`, `browser_validate`, `evaluate`, `challenge`, `security_review` increment with fix-loop iterations.
- `triggered_by` — for phases re-run via the unified fix loop (PHASE 2.5), records the triggering phase name (`build_gate` / `browser_validate` / `evaluate` / `challenge` / `simplify` / `review` / `security_review` / `clean` / `docs`). Also written on fix-loop entries themselves. `null` for the first run. See the unified fix-loop contract in the skill.
- `pre_sha` — captured by the orchestrator immediately before spawning this phase (`git rev-parse HEAD`). Used by the post-EVAL invariant to diff **only what this phase touched**, not everything since EVAL first passed — the latter would misattribute legitimate fix-loop commits to a later findings-only phase. `null` for phases that ran before the invariant activated or whose diff baseline is otherwise unneeded (PARSE, BUILD, BUILD GATE, BROWSER, EVAL use `base_ref.sha` instead).
- `artifacts` — pointers to phase output files. Phases that emit structured findings write both `findings_file` and `log_file`. Phases that used to fix-in-place (Simplify/Review/Clean) are now findings-only post-EVAL and so they also get findings files. DOCS leaves both `null` (its output is git commits).

### Rounds

- `global` — shared round counter across all fix-loop invocations regardless of trigger. Increments once per fix-loop iteration.
- `max_rounds` — cap from `--max-rounds` flag (default 4).

## Anchor syntax

Format: `<scheme>://<section>[/<index>]`. `scheme` is `spec` or `criteria.generated`. `section` is slug-lowercased H2. `index` is optional 0-based position.

## Write protocol

- **Phase 0 (PARSE + PREFLIGHT + ROUTE)** — creates state.json with `version`, `run_id`, `started_at`, `engine`, `base_ref`, `rounds.max_rounds`, empty `phases`, and (after preflight step) populates `source`, `criteria[]` with `status: pending`, `route.selected`, `route.stage_a`, `route.bypasses`. `eval_passed_sha` remains `null`.
- **Each phase start** — orchestrator writes `phases.<name>.started_at`, `round`, `triggered_by` (if re-run).
- **Each phase end** — phase writes `phases.<name>.{verdict, completed_at, duration_ms, artifacts}`. Build and Evaluate additionally update `criteria[]` state. **When EVALUATE first returns PASS/PASS_WITH_ISSUES**, orchestrator sets `state.eval_passed_sha = git rev-parse HEAD` — this is the reference point for the post-EVAL invariant.
- **Phase 1.4 completion checkpoint** — orchestrator runs Stage B routing check; writes `route.stage_b` on escalation.
- **Phase 8 (FINAL REPORT + ARCHIVE)** — reads state.json for the report, renders the report, then archives (see below).

## Archive contract (PHASE 8)

Replaces the previous "delete `.devlyn/`" behavior.

1. Create `.devlyn/runs/<run_id>/` with `mkdir -p`.
2. Move `.devlyn/pipeline.state.json`, every `.devlyn/<phase>.findings.jsonl`, every `.devlyn/<phase>.log.md`, every `.devlyn/fix-batch.round-*.json`, and `.devlyn/criteria.generated.md` (if exists) into that directory. Use `mv` (atomic within a filesystem).
3. Acquire an advisory file lock on `.devlyn/runs/.prune.lock` via `flock` (or equivalent). If another run is pruning, skip pruning and continue.
4. With the lock held: list `.devlyn/runs/*/pipeline.state.json`, sort by their enclosed `run_id` (lexicographic sort is chronological because run_ids start with a compact ISO8601 timestamp), and delete the oldest directories until at most 10 remain. **Never delete a directory whose `pipeline.state.json` has `phases.final_report.verdict == null`** — those are still in flight.
5. Kill any dev-server process spawned by PHASE 1.5 (BROWSER VALIDATE).
6. Release the lock.

This gives the user a persistent audit trail (last 10 runs) while preventing unbounded growth. Cleanup is deterministic and concurrency-safe.

## Integrity invariants

The orchestrator enforces:

1. `base_ref.sha` never changes after Phase 0.
2. `source.spec_sha256` (or `source.criteria_sha256` for generated runs) is re-verified at every phase start. Mismatch → the phase writes `verdict: "BLOCKED"` with reason. Missing hash is allowed ONLY on the phase that first populates it (PHASE 0 for spec; PHASE 1 for generated).
3. `route.selected` can only escalate via `stage_b`. No de-escalation.
4. `rounds.global` never exceeds `rounds.max_rounds`.
5. `criteria[].status` progression is monotonic per round: `pending → implemented → verified | failed`. A `failed` criterion can return to `implemented` via a subsequent fix-loop round, then be re-evaluated.
6. **Post-EVAL findings-only** (per-phase diff, not cumulative): once `eval_passed_sha` is non-null, each post-EVAL phase (SIMPLIFY, REVIEW, CHALLENGE, SECURITY REVIEW, CLEAN, DOCS) records `phases.<phase>.pre_sha = git rev-parse HEAD` at spawn time. After completion, the orchestrator runs `git diff --name-only <phases.<phase>.pre_sha>` (NOT against `eval_passed_sha`). For findings-only phases, any non-empty diff triggers `git reset --hard <pre_sha>` + `invariant.post-eval-code-mutation` finding + fix-loop entry. For DOCS, only doc-file-allowlist paths are legal; everything else triggers the same flow. Using `eval_passed_sha` as the cumulative baseline would misattribute legitimate intermediate fix-loop commits to the current phase — `pre_sha` is the correct reference.

Violations indicate a bug in the orchestrator. Do not attempt silent recovery.

## Example

```json
{
  "version": "1.1",
  "run_id": "ar-20260423T163044Z-018f4c2a1b9c",
  "started_at": "2026-04-23T16:30:44Z",
  "engine": "auto",
  "base_ref": {"branch": "main", "sha": "abc1234567890abcdef1234567890abcdef123456"},
  "eval_passed_sha": "def2345678901bcdef2345678901bcdef2345678",
  "route": {
    "selected": "standard",
    "user_override": false,
    "bypasses": [],
    "stage_a": {
      "at": "2026-04-23T16:30:47Z",
      "reasons": ["spec.complexity = medium", "0 risk-signal hits", "1 internal dep verified done"]
    },
    "stage_b": {"at": null, "escalated_from": null, "reasons": []}
  },
  "source": {
    "type": "spec",
    "spec_path": "docs/roadmap/phase-2/2.3-order-cancel.md",
    "spec_sha256": "f4e8a1c9b2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9",
    "criteria_path": null,
    "criteria_sha256": null,
    "criteria_anchors": ["spec://requirements", "spec://out-of-scope", "spec://verification", "spec://constraints"]
  },
  "criteria": [
    {"id": "C1", "ref": "spec://requirements/0", "status": "verified", "evidence": [{"file": "src/api/orders/cancel.ts", "line": 42, "note": "POST /orders/:id/cancel handler"}], "failed_by_finding_ids": []}
  ],
  "phases": {
    "build": {"verdict": "PASS", "engine": "codex", "model": "gpt-5.4", "started_at": "...", "completed_at": "...", "duration_ms": 42100, "round": 1, "triggered_by": null, "artifacts": {"findings_file": null, "log_file": null}},
    "build_gate": {"verdict": "PASS", "engine": "bash", "model": null, "round": 1, "triggered_by": null, "artifacts": {"findings_file": ".devlyn/build_gate.findings.jsonl", "log_file": ".devlyn/build_gate.log.md"}},
    "evaluate": {"verdict": "PASS_WITH_ISSUES", "engine": "claude", "model": "claude-opus-4-7", "round": 1, "triggered_by": null, "artifacts": {"findings_file": ".devlyn/evaluate.findings.jsonl", "log_file": ".devlyn/evaluate.log.md"}}
  },
  "rounds": {"global": 0, "max_rounds": 4}
}
```

## Non-goals

- Crash-resume / workflow-engine semantics. State.json enables audit and orchestrator branching, not resume-from-crash.
- Full SARIF export from state.json. `<phase>.findings.jsonl` is the SARIF-aligned surface; state.json is internal.
- Per-finding history across runs. Current run's findings live in its `runs/<run_id>/` directory; cross-run comparison is manual.
