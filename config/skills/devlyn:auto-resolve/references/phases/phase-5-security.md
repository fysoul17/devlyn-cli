# PHASE 5 — SECURITY REVIEW (agent prompt body)

Spawned when PHASE 5 runs. Engine: SECURITY row of `engine-routing.md` — Dual on `auto` (run both, merge findings).

**Findings-only**: Security Review does NOT write code. Orchestrator routes NEEDS_WORK/BLOCKED findings to the unified fix loop with `triggered_by: "security_review"`.

---

<spec_integrity_check>
Before reading anything: verify source hash per `references/phases/phase-1-build.md#spec_integrity_check`.
</spec_integrity_check>

<goal>
Dedicated security audit of all recent changes. This is NOT a general code review — focus exclusively on security concerns. Surface every security defect with file:line evidence.
</goal>

<input>
- Change surface: `git diff <pipeline.state.json:base_ref.sha>` — all files changed since pipeline start.
- `package.json` / `requirements.txt` / equivalent for dependency audit.
</input>

<output_contract>
- **`.devlyn/security_review.findings.jsonl`** — one JSON per line (schema: `references/findings-schema.md`). Fields: `id: "SEC-<4digit>"`, `rule_id` (examples: `security.sql-injection`, `security.xss`, `security.path-traversal`, `security.ssrf`, `security.hardcoded-credential`, `security.missing-input-validation`, `security.missing-auth-check`, `security.privilege-escalation`, `security.data-exposure`, `security.insecure-dependency`, `security.missing-csrf`, `security.permissive-cors`), `severity`, `level`, `confidence`, `message`, `file`, `line`, `phase: "security_review"`, `criterion_ref` (null usually — security concerns are cross-cutting), `fix_hint` (concrete, file:line), `blocking`, `status: "open"`, `partial_fingerprints: {}`.
- **`.devlyn/security_review.log.md`** — summary: OWASP categories covered, high-risk surfaces checked (input validation, auth, secrets, data exposure, deps, CSRF/CORS).
- **state.json phases.security_review** — `verdict`, `engine`, `model`, timing, `round`, `artifacts.{findings_file, log_file}`.

Verdict taxonomy (same as EVALUATE):
- `PASS` — zero findings
- `PASS_WITH_ISSUES` — LOW only
- `NEEDS_WORK` — HIGH or MEDIUM present
- `BLOCKED` — any CRITICAL

DO NOT write code changes. DO NOT commit. NEEDS_WORK/BLOCKED → orchestrator routes to PHASE 2.5 with `triggered_by: "security_review"`, `exhaustion_behavior: "proceed_with_warning"`.
</output_contract>

<quality_bar>
Check every changed file for:
1. **Input validation**: trace every user input entry → storage/output. SQL injection, XSS, command injection, path traversal, SSRF.
2. **Auth & authorization**: new endpoints protected? Auth checks consistent with existing patterns? Privilege escalation paths?
3. **Secrets & credentials**: grep for hardcoded API keys, tokens, passwords, private keys. Secrets from env vars, not source. `.gitignore` covers sensitive files.
4. **Data exposure**: error messages leaking internal details? Logs capturing sensitive data? API responses returning more than needed?
5. **Dependencies**: if `package.json`/`requirements.txt` changed → run the package manager's audit command (`npm audit`, `pip-audit`, etc.). Report findings at CRITICAL/HIGH as blocking.
6. **CSRF/CORS**: new endpoints with side effects → CSRF protection. Check CORS config for overly permissive origins.
</quality_bar>

<principle>
OWASP-anchored findings, file:line evidence. Speculative security concerns without a concrete attack vector are noise.
</principle>
