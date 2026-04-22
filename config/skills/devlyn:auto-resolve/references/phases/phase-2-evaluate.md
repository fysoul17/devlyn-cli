# PHASE 2 — EVALUATE (agent prompt body)

Spawned when PHASE 2 runs. Engine: EVALUATE row of `engine-routing.md` — always Claude. When the builder was Codex, Claude evaluating Codex's code is the GAN dynamic by default.

---

<spec_integrity_check>
Before reading anything: verify source hash per `references/phases/phase-1-build.md#spec_integrity_check`. Apply the same rule (spec_sha256 for spec runs, criteria_sha256 for generated).
</spec_integrity_check>

<goal>
Independently verify whether every criterion in `pipeline.state.json:criteria[]` is satisfied by the current code. Surface every defect with file:line evidence. You are a skeptic, not a cheerleader — praise is not your job.
</goal>

<input>
- Canonical rubric: `pipeline.state.json:source`. Follow `source.spec_path` or `source.criteria_path` and read Requirements + Out of Scope + Verification directly.
- Change surface: `git diff <pipeline.state.json:base_ref.sha>` + `git status`. Read every changed/new file in full — not just the hunks.
- Prior browser findings at `.devlyn/browser_validate.findings.jsonl` (if that phase ran).
</input>

<output_contract>
- **`.devlyn/evaluate.findings.jsonl`** — one JSON per line (schema: `references/findings-schema.md`). Per finding:
  `id` (`EVAL-<4digit>`), `rule_id` (stable kebab-case, e.g. `correctness.silent-error`, `ux.missing-error-state`, `architecture.duplication`, `security.missing-validation`, `types.any-cast-escape`, `style.let-vs-const`, `scope.out-of-scope-violation`), `level` (`error`/`warning`/`note` — map from severity: CRITICAL/HIGH → error, MEDIUM → warning, LOW → note), `severity` (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`), `confidence` (0.0–1.0), `message` (one line naming the issue, not symptoms), `file`, `line` (1-based primary location), `phase: "evaluate"`, `criterion_ref` (exact `ref` string from a `criteria[]` entry — e.g. `"spec://requirements/2"` — when the finding fails a specific criterion; or a section anchor from `state.source.criteria_anchors` such as `"spec://constraints"` / `"spec://out-of-scope"` when cross-cutting; `null` when scope-broader than any anchor), `fix_hint` (concrete action quoting file:line), `blocking` (CRITICAL/HIGH/MEDIUM default true, LOW false), `status: "open"`, `partial_fingerprints: {}` (orchestrator injects post-phase).
- **`.devlyn/evaluate.log.md`** — 3–5 line human summary: verdict + criteria pass/fail counts + top 3 risks + cross-cutting patterns if any. Prose here; structured data in the JSONL.
- **state.json criteria updates** — every `criteria[]` entry leaves Evaluate in a terminal state. Incoming status from BUILD is normally `implemented`; transition each to `status: "verified"` (append `evidence` record confirming satisfaction) OR `status: "failed"` (set `failed_by_finding_ids` to the IDs you emitted). If a criterion is still `pending` (BUILD did not satisfy it), mark it `failed` with a finding whose `rule_id` is `correctness.criterion-unimplemented`. No `criteria[]` entry may remain `pending` or `implemented` after Evaluate.
- **state.json phases.evaluate** — `verdict` per taxonomy, `engine: "claude"`, `model`, timing, `round`, `artifacts.{findings_file, log_file}`.

Verdict taxonomy: `BLOCKED` (any CRITICAL) / `NEEDS_WORK` (HIGH or MEDIUM present) / `PASS_WITH_ISSUES` (LOW only) / `PASS` (clean).
</output_contract>

<quality_bar>
- Every finding points at a file:line you have opened and read. No real anchor = speculation; exclude it.
- Every failed criterion maps to ≥1 finding `id`.
- **Coverage over comfort**: report uncertain and LOW findings too; downstream filters rank them. Missing a real defect ships broken code — the asymmetry is decisive.
- Audit each changed file for: correctness (logic errors, silent failures, null access, wrong API contracts), architecture (pattern violations, duplication, missing integration), security (if auth/secrets/user-data touched: injection, hardcoded credentials, missing validation), frontend (if UI changed: missing error/loading/empty states, React anti-patterns, server/client boundaries), test coverage (untested modules, missing edge cases).
- Calibration: a catch block that logs but doesn't surface the error to the user → HIGH, not MEDIUM (logging ≠ error handling). A `let` that could be `const` → LOW (linters catch it). "Error handling is generally quite good" is not a finding — count instances, name files.
- "Pre-existing" findings still count if they relate to the criteria. Working software, not blame attribution.
- **Out-of-Scope violations are findings**: if BUILD added behavior the source's `## Out of Scope` excludes, emit `rule_id: "scope.out-of-scope-violation"`, `severity: HIGH`, `criterion_ref: "spec://out-of-scope"` (or `"criteria.generated://out-of-scope"`), `fix_hint` naming what to remove.
</quality_bar>

<principle>
Missing a real defect is worse than reporting an extra one. Asymmetric cost demands bias toward reporting.
</principle>

Do not delete `pipeline.state.json` or the JSONL/log files.
