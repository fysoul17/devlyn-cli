# 0162 — Stop an evidenced unauthorized repair dispatch

2026-09-13. User: “오케이 계속.” Root implements directly; actual Fable5.1 and
Grok4.6 advise independently. Frozen comparisons remain unchanged.

## Why and prediction

**Pre-flight0:** remove the unconditional product-repair dispatch when the
required external gate tool is demonstrably absent and supplying it is prohibited.
**Mission1:** reduce a witnessed full-route failure-handling cost, not search for
a task that makes the harness win. Frozen0159's BUILD_GATE FAIL took217.718s;
its subsequent IMPLEMENT round1 took52.005s, made no product edit and returned
BLOCKED because mypy/Ruff were unavailable under explicit no-install constraints.
That duration is historical cost, not a measured saving from this change.

Prediction registered before draws: the existing FAIL branch dispatches repair;
a constrained replacement stops only proven prohibited-tool cases while genuine
product failures, available tools/routes, authorized supply and uncertain evidence
retain repair. No new phase, detector, flag, evidence schema or tool installer.

## Change and source boundary

Only the parent BUILD_GATE FAIL branch changes, plus its tracked mirror.
A parent probe must identify the invoked external tool from unchanged base
configuration and bind interpreter, working directory and effective environment
to the actual invocation and runner call sites. Parent PATH or stderr wording
alone is insufficient. Explicit task/spec constraints must prohibit supplying
the tool through any authorized route; an existing usable environment retains
repair. Mixed failures halt only when that established blocker makes required
gates unrepairable: other findings stay visible and unrepaired.

The halt reason is report-level `BLOCKED:required-tools-unavailable`; BUILD_GATE
stays FAIL. Existing findings, raw streams and sealed manifests stay unchanged;
parent probe/citation evidence is separate. No repair means no round increment.
Worker gate commands, capability-denial classification, state/evidence writers,
normal repair/checkpoint/exhaustion and post-CLEANUP verification stay unchanged.

## Registered extracted routing screen

One fresh read-only native Codex session per arm, requested gpt-6-astra/high,
fixed old→candidate order,600s bound, no retries. Same12 supplied-fact cases;
only the parent branch differs. Prompts and inputs were hashed before admission.

| Decision | Existing branch | Candidate |
| --- | --- | --- |
| 3 confirmed prohibited-tool cases, including mixed findings | 3 REPAIR | 3 HALT |
| 9 repair controls | 9 REPAIR | 9 REPAIR |
| Target routing decisions | 9/12 | 12/12 |
| Native response time, descriptive only | 31.369s | 26.375s |

Controls include product imports, misleading stderr from an installed tool,
authorized installation, changed config, wrong probe environment, diagnosis
without a probe, missing prohibition, an available configured environment and
probe errors. Both responses select preservation of all findings. FAIL and zero
round increment were fixed by response schema and earn no independent behavioral
preservation credit. Twelve rows share a session: not12 independent trials.
No actual probe, worker dispatch, state mutation or full resolve was exercised.
Ambient skill-load warnings remain despite requested discovery isolation;
provider-effective Codex identity and whole-run billed cost are not certified.
No stable latency, successful-resolution speed or general quality/pair claim.

## Review, checks and limits

Initial actual Fable/Grok NEEDS_WORK identified unbound environment, mixed-failure
ambiguity and sealed-evidence risks; root revised before the registered draws.
Final Fable NEEDS_WORK (MEDIUM evidence-field specificity, LOW environment wording
and readability); Grok PASS (MEDIUM possible product-module/tool confusion, LOW
skill-only phase/report distinction). Both found no final CRITICAL/HIGH.
Root accepts PASS_WITH_ISSUES: current text already requires actual bound probe,
cited constraints and separate evidence; no concrete false-halt counterexample
was demonstrated. Additional fixed field/schema wording is not promoted. Source
review does not certify native behavior, and MEDIUM/LOW advice remains retained.

Root audit checks exact registered candidate bytes, tracked mirror, all12 raw
routing answers and immutable0159/0161 archive hashes. Initial full lint failed
only on the ignored local installed mirror; later reobservation found that mirror
already equal to the candidate (refresh cause not independently attributed).
A guarded overwrite therefore made no change. Final full lint: PASS318.525s.

**No overengineering / Optimized:** replace one unconditional dispatch clause;
no added phase or runtime helper. **No guesswork / No workaround:** preserve
failures and distinguish supplied-fact routing from actual execution. **Worldclass /
Best practice / Production ready:** exact source checks, independent advice and
explicit unchanged failed evidence; uncertainty retains repair. Further deleting
the environment, base-config or prohibition conditions reopens the tested false-
halt cases. Removing mixed-finding precedence makes the target ambiguous again.

Evidence: `.devlyn/0162-evidence.tar.gz`, SHA256 `012f8eec71b457d127f8f92e59fc80167afe5580d66410654608c68b05e08501`,
67 byte-verified members. Delivery lives separately in
`.devlyn/0162-delivery/`, receiptbd8f368bce65a7433e68f9cf.
Next: a separately registered actual parent-invocation check of probe discovery,
no repair dispatch and preserved terminal evidence before claiming saved time.
No frozen run restart, reserved confirmation opening or winning-task search.
Follow [HANDOFF](../HANDOFF.md).
