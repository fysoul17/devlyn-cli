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

State.json is the only cross-phase mutable state. Spec files and `<phase>.findings.jsonl` are immutable within a run.

## File location

`.devlyn/pipeline.state.json`

Created by PHASE 0 on run start. Deleted by PHASE 8 (FINAL REPORT) as part of cleanup.

## Canonical schema (v1.0)

```json
{
  "version": "1.0",
  "run_id": "ar-<YYYYMMDD>-<HHMMSS>-<6hex>",
  "started_at": "<ISO-8601 UTC>",
  "engine": "auto" | "codex" | "claude",
  "base_ref": {
    "branch": "<string, e.g. 'main'>",
    "sha": "<full 40-char git sha captured at Phase 0 start>"
  },
  "route": {
    "selected": "fast" | "standard" | "strict" | null,
    "user_override": true | false,
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
      "verdict": "PASS" | "FAIL" | "NEEDS_WORK" | "BLOCKED" | null,
      "engine": "codex" | "claude" | "bash" | null,
      "model": "<string>" | null,
      "started_at": "<ISO-8601 UTC>" | null,
      "completed_at": "<ISO-8601 UTC>" | null,
      "duration_ms": <int> | null,
      "round": <int>,
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

- `version` — schema version. Bump on breaking changes. Orchestrators must check and refuse incompatible versions.
- `run_id` — stable identifier for this run. Used for log correlation.
- `started_at` — Phase 0 start, ISO-8601 UTC.
- `engine` — user-provided `--engine` flag value, or `auto` default.
- `base_ref` — the git state captured at Phase 0. **All subsequent `git diff` commands must use this SHA**, not `HEAD~1` or `main`. This eliminates the diff-scope drift that previously existed (Evaluate used `HEAD~1`, Review/Challenge/Security/Docs used `main`).

### Route

- `selected` — current route. One of `fast` | `standard` | `strict`, or `null` if routing has not yet been determined (e.g., before Phase 0.5 Stage A decides, or when the routing subsystem is not yet active). A non-null value must be present before PHASE 1 BUILD begins.
- `user_override` — `true` if user passed `--route <value>`, else `false`.
- `stage_a` — initial routing decision at Phase 0.5 based on spec frontmatter + spec content scan.
- `stage_b` — routing checkpoint at Phase 1.4 completion. Can only **escalate** (fast → standard → strict), never de-escalate. `at` is `null` if no escalation occurred.
- `reasons` — human-readable decision rationale. Surfaces in the final report for transparency.

### Source

- `type` — `spec` if the task referenced a roadmap spec file (`docs/roadmap/phase-N/*.md`); `generated` otherwise.
- `spec_path` + `spec_sha256` — canonical spec pointer + integrity hash. Each phase re-computes the hash before reading. Mismatch → ABORT (spec changed mid-run is a pipeline invariant violation).
- `criteria_path` + `criteria_sha256` — for `generated` type only. Path to `.devlyn/criteria.generated.md` produced by Phase 1 when no spec exists.
- `criteria_anchors` — enumerated list of anchors downstream phases may reference. Populated by Phase 0.5 from the source file's section headings.

### Criteria

One entry per testable criterion extracted from the source.

- `id` — stable ID within this run (`C1`, `C2`, ...). Assigned at Phase 0.5.
- `ref` — anchor pointing to source. E.g., `spec://requirements/0` is the first `- [ ]` item under `## Requirements` in the spec file.
- `status` — state machine:
  - `pending` — assigned at Phase 0.5, not yet implemented
  - `implemented` — Build phase marked it as done
  - `verified` — Evaluate phase confirmed satisfaction with evidence
  - `failed` — Evaluate phase found a defect; see `failed_by_finding_ids`
- `evidence` — list of file:line references where the criterion is satisfied. Populated by Evaluate.
- `failed_by_finding_ids` — populated by Evaluate when status is `failed`. References finding IDs from the corresponding `.devlyn/<phase>.findings.jsonl`.

### Phases

Key is phase name: one of `build`, `build_gate`, `browser_validate`, `evaluate`, `fix_loop`, `simplify`, `review`, `challenge`, `security_review`, `clean`, `docs`, `final_report`. Value is the phase execution record.

- `verdict` — phase's final verdict, or `null` if not started or in progress. This is the **single canonical verdict source** — orchestrator branches on this field directly, never by parsing artifact files.
- `engine` / `model` — which model ran this phase. `bash` for build-gate (deterministic, model-agnostic).
- `round` — which fix-loop round this execution belongs to. Phases that run once always have `1`. `build_gate` and `evaluate` increment with fix-loop iterations.
- `artifacts` — explicit pointers to the phase's output files. Phases that emit structured findings (Build Gate, Browser Validate, Evaluate, Challenge, Security Review) write both `findings_file` and `log_file`. Phases that fix-in-place (Simplify, Clean, Docs) leave both `null` — their output is the git commits they produce. See `references/findings-schema.md` for findings format.

### Rounds

- `global` — shared round counter across PHASE 1.4-fix and PHASE 2.5. Increments on each fix-loop iteration.
- `max_rounds` — cap from `--max-rounds` flag (default 4).

## Anchor syntax

Format: `<scheme>://<section>[/<index>]`

- `scheme` — `spec` (for `spec_path`) or `criteria.generated` (for `criteria_path`).
- `section` — slug-lowercased H2 heading from the source file. `## Requirements` → `requirements`; `## Out of Scope` → `out-of-scope`.
- `index` — optional zero-based position within a list in that section. Applies to bulleted or checkbox lists only.

Examples:
- `spec://requirements/0` — first item in `## Requirements` of the spec
- `spec://out-of-scope` — entire `## Out of Scope` section
- `criteria.generated://requirements/2` — third item in the generated criteria's Requirements section

## Write protocol

- **Phase 0 (PARSE INPUT)** — creates state.json with `version`, `run_id`, `started_at`, `engine`, `base_ref`, `rounds.max_rounds`, empty `phases`, empty `route.selected`.
- **Phase 0.5 (SPEC PREFLIGHT & ROUTE STAGE A)** — populates `source`, `criteria[]` (with `status: pending`), `route.selected`, `route.stage_a`.
- **Each phase start** — orchestrator writes `phases.<name>.started_at`, `round`.
- **Each phase end** — phase writes `phases.<name>.{verdict, completed_at, duration_ms, artifacts}`. Build and Evaluate additionally update `criteria[].status`, `evidence`, and `failed_by_finding_ids`.
- **Phase 1.4 completion checkpoint** — orchestrator runs Stage B routing check; if escalation is triggered, writes `route.stage_b`.
- **Phase 8 (FINAL REPORT)** — reads state.json for report generation, then deletes the `.devlyn/` directory.

## Integrity invariants

The orchestrator must enforce:

1. `base_ref.sha` never changes after Phase 0. All subsequent diffs use this SHA.
2. `source.spec_sha256` is re-verified at phase start. Mismatch → ABORT with a clear error.
3. `route.selected` can only escalate (fast → standard → strict) in `stage_b`. No de-escalation.
4. `rounds.global` never exceeds `rounds.max_rounds`.
5. `criteria[].status` progression is monotonic per round: `pending → implemented → verified | failed`. A `failed` criterion can return to `implemented` only via a subsequent fix-loop round, then be re-evaluated.

Violations indicate a bug in the orchestrator. Do not attempt silent recovery.

## Example

```json
{
  "version": "1.0",
  "run_id": "ar-20260422-163044-a7f3b1",
  "started_at": "2026-04-22T16:30:44Z",
  "engine": "auto",
  "base_ref": {"branch": "main", "sha": "abc1234567890abcdef1234567890abcdef123456"},
  "route": {
    "selected": "standard",
    "user_override": false,
    "stage_a": {
      "at": "2026-04-22T16:30:47Z",
      "reasons": [
        "spec.complexity = medium",
        "0 risk-signal hits in spec sections",
        "1 internal dependency verified done"
      ]
    },
    "stage_b": {"at": null, "escalated_from": null, "reasons": []}
  },
  "source": {
    "type": "spec",
    "spec_path": "docs/roadmap/phase-2/2.3-order-cancel.md",
    "spec_sha256": "f4e8a1c9b2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9",
    "criteria_path": null,
    "criteria_sha256": null,
    "criteria_anchors": [
      "spec://requirements",
      "spec://out-of-scope",
      "spec://verification",
      "spec://constraints"
    ]
  },
  "criteria": [
    {
      "id": "C1",
      "ref": "spec://requirements/0",
      "status": "verified",
      "evidence": [{"file": "src/api/orders/cancel.ts", "line": 42, "note": "POST /orders/:id/cancel handler"}],
      "failed_by_finding_ids": []
    },
    {
      "id": "C2",
      "ref": "spec://requirements/1",
      "status": "failed",
      "evidence": [],
      "failed_by_finding_ids": ["EVAL-0007"]
    }
  ],
  "phases": {
    "build": {
      "verdict": "PASS", "engine": "codex", "model": "gpt-5.4",
      "started_at": "2026-04-22T16:30:48Z", "completed_at": "2026-04-22T16:31:30Z",
      "duration_ms": 42100, "round": 1,
      "artifacts": {
        "findings_file": null,
        "log_file": null
      }
    },
    "build_gate": {
      "verdict": "PASS", "engine": "bash", "model": null,
      "started_at": "2026-04-22T16:31:30Z", "completed_at": "2026-04-22T16:31:48Z",
      "duration_ms": 18200, "round": 1,
      "artifacts": {
        "findings_file": ".devlyn/build_gate.findings.jsonl",
        "log_file": ".devlyn/build_gate.log.md"
      }
    },
    "evaluate": {
      "verdict": "NEEDS_WORK", "engine": "claude", "model": "claude-opus-4-7",
      "started_at": "2026-04-22T16:31:48Z", "completed_at": "2026-04-22T16:33:12Z",
      "duration_ms": 83900, "round": 1,
      "artifacts": {
        "findings_file": ".devlyn/evaluate.findings.jsonl",
        "log_file": ".devlyn/evaluate.log.md"
      }
    }
  },
  "rounds": {"global": 1, "max_rounds": 4}
}
```

## Non-goals

- Crash-resume / workflow engine semantics. State.json tracks state for audit and orchestrator branching. Resume from mid-run is not supported. (Adding that later would require tested end-to-end recovery semantics — out of scope here.)
- Export to external workflow viewers (SARIF, Tekton). This schema is internal.
- Per-finding history across runs. Findings live in `<phase>.findings.jsonl`; state.json tracks only their current count and IDs.
