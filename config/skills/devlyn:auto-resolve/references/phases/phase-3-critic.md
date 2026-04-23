# PHASE 3 — CRITIC (agent prompt body)

Spawned when PHASE 3 runs. Engine: CRITIC row of `engine-routing.md` — design sub-pass always Claude; security sub-pass delegated to the **native `security-review` skill** on every engine (findings-only native, no Dual cost).

**Findings-only**: CRITIC does NOT write code. Orchestrator routes `NEEDS_WORK`/`BLOCKED` findings into PHASE 2.5 with `triggered_by: "critic"`. No bespoke mini-loop inside CRITIC.

---

<spec_integrity_check>
Before reading anything: verify source hash per `references/phases/phase-1-build.md#spec_integrity_check`.
</spec_integrity_check>

<goal>
One post-EVAL critic pass with two parallel sub-concerns. Produce a single `.devlyn/critic.findings.jsonl` tagged by rule_id prefix, plus a single `.devlyn/critic.log.md`.
</goal>

<input>
- Change surface: `git diff <pipeline.state.json:base_ref.sha>`. Read every changed file in full, not just the hunks.
- `package.json` / `requirements.txt` / lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Pipfile.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`) — for dependency audit.
</input>

## Sub-pass 1: DESIGN (always Claude)

<design_goal>
Read the diff cold — no checklist, no prior-phase context. Find what a staff engineer would block before this PR ships. Any hesitation is a finding.
</design_goal>

<design_quality_bar>
- Every finding anchored to `file:line` in code you have opened, with a concrete fix. Vague ≠ finding.
- `fix_hint` is a specific change ("change X to Y because Z"), never "consider improving".
- Interrogate: would this survive 10x traffic? A midnight oncall page? A junior dev in 6 months? Are baked-in assumptions stated out loud (hardcoded limits, implicit ordering, missed business-logic edges)? Is error handling actually helpful or does it prevent crashes while leaving users confused? Are there simpler idiomatic approaches — not "clever" but genuinely better?
- **Stdlib-vs-hand-rolled calibration.** Emit `design.unidiomatic-pattern` when hand-rolled helper logic REPLACES a standard-library primitive AND is measurably less faithful to required behavior, portability, or error semantics. Concrete example: permission/writability checks should prefer `fs.accessSync(path, fs.constants.W_OK)` over mode-bit inspection (mode bits miss ACLs / platform-specific cases). Do NOT flag helper count alone; require a concrete file:line risk AND a named stdlib replacement that is measurably better.
- Do not open with praise.
- Rule_ids: `design.non-atomic-transaction`, `design.duplicate-pattern`, `design.hidden-assumption`, `design.unidiomatic-pattern`, `design.missing-integration`, etc.
- Severities: CRITICAL / HIGH / MEDIUM — no LOW (design is ship/no-ship).

**Design sub-verdict**: `PASS` only if zero design findings. Any open design finding → `NEEDS_WORK`.
</design_quality_bar>

## Sub-pass 2: SECURITY (native `security-review`)

<security_goal>
Delegate the security audit to the native Claude Code `security-review` skill. It performs an OWASP-scoped review of the pending changes on the current branch, returns findings-only (no code mutations — compatible with the post-EVAL invariant), and covers the same attack surface as the old custom pass without paying the Dual-model cost.
</security_goal>

<invocation>
Invoke the native skill via the Skill tool: `security-review`. No arguments needed — it reads `git diff` and `git status` on the current branch.

Capture its full text output to `.devlyn/security_review.log.md` verbatim. The native skill writes human-readable findings with concrete file:line references; parse those into `.devlyn/critic.findings.jsonl` entries with `phase: "critic"`, `rule_id: "security.<category>"`, and the severity the native skill assigned.

Normalization rules (output contract preservation):
- One JSONL line per native finding. Reuse `CRIT-<4digit>` ID sequence alongside design findings.
- `rule_id`: map the native category to the prefix `security.*`. Use one of the established kebab-case suffixes when obvious (`sql-injection`, `xss`, `path-traversal`, `ssrf`, `hardcoded-credential`, `missing-input-validation`, `missing-auth-check`, `privilege-escalation`, `data-exposure`, `insecure-dependency`, `missing-csrf`, `permissive-cors`); otherwise invent one in the same kebab-case pattern and log it.
- `severity`: keep the native classification. If the native output omits severity, infer CRITICAL for exploitable attack vectors, HIGH for direct vulnerabilities, MEDIUM for hardening gaps, LOW for informational — and record the inference in `critic.log.md`.
- `confidence`: 0.9 for findings the native skill stated with evidence; 0.7 when inferred. Never fabricate.

If the native skill invocation fails (unavailable, errored out, no output), set `phases.critic.sub_verdicts.security = "BLOCKED"` with a single finding `rule_id: "security.review-failed"`, `severity: CRITICAL`, message `"native security-review skill failed — manual security review required before ship"`. Do NOT fall back to a custom pass; surface the failure and halt CRITIC.

Dependency audit is included in the native skill's output when lockfiles changed. No separate `npm audit` / `pip-audit` invocation needed.
</invocation>

<security_quality_bar>
**Security sub-verdict** (derived from native findings):
- `PASS` — zero findings
- `PASS_WITH_ISSUES` — LOW only
- `NEEDS_WORK` — HIGH or MEDIUM present (security MEDIUM is blocking by design)
- `BLOCKED` — any CRITICAL, or native skill invocation failed
</security_quality_bar>

## Output contract

- **`.devlyn/critic.findings.jsonl`** — one JSONL file containing BOTH sub-passes' findings. Every line carries `phase: "critic"`. Rule_id prefix (`design.*` vs `security.*`) distinguishes sub-pass. ID prefix: `CRIT-<4digit>` (single sequence shared by both sub-passes for simplicity).
- **`.devlyn/critic.log.md`** — single prose summary: two sections ("Design" + "Security"). Each section: verdict + top 3 concerns framed actionably. Security section records the dep-audit command and its result.
- **state.json phases.critic** — record both sub-verdicts AND the combined verdict. Combined verdict = WORSE of the two:
  - Any `BLOCKED` → `BLOCKED`
  - Any `NEEDS_WORK` → `NEEDS_WORK`
  - Any `PASS_WITH_ISSUES` → `PASS_WITH_ISSUES`
  - Both `PASS` → `PASS`

## Principles

- Cold eyes catch what structured reviews miss. For design: "would I ship this with my name on it?" is the only question.
- For security: OWASP-anchored findings, file:line evidence. Speculative security concerns without a concrete attack vector are noise.
- Do NOT write code changes. Do NOT commit. Orchestrator handles routing.
