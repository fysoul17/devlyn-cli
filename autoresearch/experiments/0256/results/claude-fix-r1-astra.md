**1. Target the scope-narrowing behavior for a screen; no particular principle is established as its cause.**

The strongest evidence is c12: Claude probes malformed JSON, observes HTML 400, then explicitly leaves it because the request did not list it. c02 gives the same rationale. That makes recognized-but-unhandled failure behavior testable.

The diagnosis overstates its explanatory reach:

- **c15 has no final report.** Its missing handler corroborates the implementation pattern, but self-killing explains its termination.
- **c12 has another defect:** `Number.isSafeInteger` rejects a positive integer permitted by the request. Fixing parsing alone would not establish completion.
- **Assessment is inconsistent:** c02/c15’s findings demand `field:'name'` for JSON `null`, whereas accepted A implementations return `field:'body'`. The JSON-versus-HTML difference is real; the precise field criterion needs freezing.

These distinctions are visible in the [audit](audit.md) and verified snapshots/transcripts. c05 succeeds under identical principles. **No overengineering**, **First-principles thinking**, and the Saint-Exupéry rule remain plausible influences, not isolated causes; **Production ready** already points toward handling expected failures.

Delivery/executor instructions demonstrably cause additional work. However, roughly 124–131-second mutation-test stalls dominate three F-task time gaps. Removing delivery instructions is therefore neither an established quality remedy nor an explanation for the entire slowdown.

**2. Candidate: delete one sentence, experimentally.**

From **No overengineering**, delete exactly:

> `smallest change that closes the goal. `

The resulting opening is:

> **No overengineering** — New abstractions require an observed failure mode they prevent.

Leave the remainder unchanged. This tests whether the explicit minimization instruction encourages narrowing behavior while retaining the concrete safeguards against unnecessary abstractions and code.

Measured in memory against `AGENTS.md`: **−38 characters, −6 words; estimated token delta −9 and −8** using the repository’s respective character and word gauges. These are estimates, not native Claude token counts; verify the actual instruction-token delta before qualification.

This removes canonical wording, so **owner approval of this exact deletion is required before experimentation**. Nothing was edited.

Rejected alternative: delete Delivery’s `task-completion.md` lookup clause. It has stronger evidence for reducing bookkeeping, but no demonstrated connection to the quality defect and could weaken delivery reliability. Do not bundle it with this candidate. Another appended definition-of-done reminder would also revisit the rejected 0235 direction.

**3. Smallest useful measurement: eight fresh Claude cells, run first.**

Use **F10/F11 × unchanged installed 4.2.24 B / deletion-only R × two replicates**. Pair arms adjacently and reverse order in replicate two. Reuse 0256’s pins, prompts, sources, grading, audit and reconciled accounting through a separately frozen adaptation. Historical B cells are not contemporary controls.

The existing oracle misses parser-level bodies. Add a hidden, arm-neutral witness sending raw `{bad` and valid JSON `null`: require HTTP 400, JSON `error:'invalid_body'`, and unchanged storage. For parser-rejected F10 bodies, accept either `field:'name'` or `field:'body'` symmetrically. Preserve existing field-validation checks; additionally freeze F11’s large-positive-integer acceptance.

**Proposed frozen prediction:**

> R passes both parser probes in 4/4 cells; B fails in at least two. R completes more cells, with no per-task completion/check/oracle-row regression, no new paired severe defect, zero false completion/scope violation/data harm, and no increase in wall, input or output per correct completion.

Charge failures to costs. Advance only if every condition holds. A regression or no improvement despite baseline failures rejects; no baseline omission yields **NO_FAILURE_OBSERVED**; unresolved evidence or usage yields **INCONCLUSIVE**. Passing licenses broader fresh-task and both-engine testing, not shipment.

Run this **before** the queued powered study. More bare/package replicates estimate package performance; they cannot isolate this sentence. Keep the questions and evidence separate.

**4. I0185 is an exposure confound.**

The skip requires both `bin/devlyn.js` and package name `devlyn-cli`. It preserves a faithful package-as-shipped comparison, but prevents attributing I0185 differences to principles. Remaining skill/settings effects are unresolved, not proven variance. Future registrations must hash/assert actual loaded instructions and explicitly stratify the skip or declare a uniformly exposed treatment; silently injecting principles would change arm B.

VERDICT: TARGET literal scope narrowing. The evidence supports a narrow ablation screen, with no change admitted yet.
