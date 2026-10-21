Harness² is a **system for searching over harness changes**: execute a baseline, propose procedural and domain edits, execute those candidates, compose another harness, and retain evidence for later tasks. Its relevance to devlyn is substantial for **research discipline**, but limited as a product architecture to import. Even `k=1` schedules four executions and three improvement stages, plus reflection; this does not establish token nonincrease. The reported gains concern different model/task configurations, not devlyn’s current solo engines. Borrow its insistence on execution evidence and minimal justified changes; do not treat its eight component types as a roadmap. ([README](https://github.com/google-research/harness2#readme); `harness2/core/ledger.py:15–33`; paper §3.2, §F.)

One important correction: **0233 measured the installed package, not the block alone**—skills and delivery helpers were available. Its Codex 9/12 versus 6/12 and Claude 3/12 versus 7/12 results cannot isolate the block’s effect. Also, the current templates are root `CLAUDE.md`/`AGENTS.md`; `bin/instruction-templates.json` is legacy migration data. (`autoresearch/iterations/0233-installed-baseline-and-failure-paths.md:38–42`; `experiments/0233/prepare.py:53–62`; `bin/instructions.js:5,223–225`.)

My ranked candidates follow. Harness² paths refer to the supplied clone.

1. **Use contrastive execution evidence to establish the current instruction-only baseline. — Research process**

   **Source:** `harness2/core/prompts.py:859–868,917–937`; paper §4 reports that editing without reference executions, probes, or library degraded Code 73.4→63.2 and Web 69.9→65.0.

   **Target:** reuse `autoresearch/experiments/0223/DESIGN.md` isolation and `0255/runner.py` accounting in a fresh registration.

   **Our failure:** the engine-dependent 0233 result remains unresolved; 0255 is explicitly offline integration, not efficacy evidence. Recent delivery experiments answer narrower questions. ([0255 README](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0255/README.md:3))

   **Prediction:** a self-contained instruction-core arm will use fewer whole-task tokens than the installed package without lowering completion/quality or increasing wall time. This is unproven; failure on either engine rejects that simplification.

   **Counterargument:** redefining “block-only” can silently change the task or leave broken helper pointers.

   **Smallest step:** design and freeze the exact payload and common endpoint. An explicit local-commit endpoint permits a self-contained core comparison; implicit PR+merge requires separate coverage. Start with existing D3/D4/B5 fixtures and E1 guard, after qualifying the existing accounting boundary. No new runner architecture.

2. **Keep edit-level evidence, including “confounded” and “no observed effect,” in existing records. — Research process**

   **Source:** `harness2/core/prompts.py:1105–1147`; `library.py:120–121`. The reflector distinguishes an adopted output from an effective edit and permits no durable lesson.

   **Target:** `autoresearch/DECISIONS.md`, existing experiment results, and `HANDOFF.md`; no new library.

   **Our failure:** rp-d1…rp-d8 repeatedly revisited delivery/reporting language. rp-d8 was **INCONCLUSIVE**, then adopted by owner decision—not a registered pass. Its successful outcomes do not establish that the bookkeeping note removed a scope objection; the control skips cited publication instead. ([rp-d8 results](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d8-bookkeeping-note/results.md:124))

   **Prediction:** replacing repeated narrative summaries with concise edit→trajectory→outcome records reduces researcher rereading tokens/time without changing product quality or runtime tokens.

   **Counterargument:** another compulsory reflection session would increase tokens; devlyn already has substantial records.

   **Smallest step:** replace, rather than append, the next handoff’s repetition with the existing outcomes: failed prose arms, rp-d4’s partial signal, rp-d8’s unresolved attribution. Preserve raw evidence and owner decisions separately. This follows **No guesswork** and **No overengineering**.

3. **Reconsider the existing helper-output candidate before inventing another instruction. — Product hypothesis**

   **Source:** `harness2/core/prompts.py:350–362,237–255`: choose the cheapest effective surface for the observed divergence; do not restate clear instructions.

   **Target:** `config/skills/_shared/task-complete.py`, specifically the already-tested rp-d4 output change.

   **Our failure:** Codex omitted cleanup reporting in 0/16 successful reports across earlier prompt arms. Actual cleanup largely happened. Moving evidence into helper output produced reporting in 2/4 versus 0/4, with lower observed tokens/time and all deliveries passing—but missed the registered 3/4 threshold. ([rp-d4 results](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d4-helper-report/results.md:29))

   **Prediction:** a fresh confirmation improves accurate cleanup reporting, preserves actual delivery, and does not increase whole-task tokens or wall time.

   **Counterargument:** four samples cannot establish that effect; the sentence was still ignored twice. It also cannot help agents that bypass the helper—the owner reports only 15–76% coverage.

   **Smallest step:** after the solo baseline, confirm the existing candidate against current behavior. Add neither a new report schema nor another always-on paragraph. Reporting omissions and failed delivery must remain separate outcomes.

4. **Consider a narrowly scoped completion hook only after proving a residual skipped invariant. — Deferred product mechanism**

   **Source:** `harness2/core/prompts.py:359–360,224–252` recommends hooks only for repeatedly ignored clear prose.

   **Target:** existing delivery predicates in `config/skills/_shared/task-complete.py`; installer integration would touch `bin/devlyn.js`.

   **Our failure:** delivery-helper bypass and premature termination. Historical Claude Stop blocks were honored 5/5, and one live incomplete run resumed to completion: `DECISIONS.md` entries 0074.3 and 0078.6.

   **Prediction:** a narrow check reduces premature completion without blocking valid local-only/read-only work, and avoided retries offset all hook-induced tokens/time.

   **Counterargument:** the retired hook depended on pipeline state, could fail open across session changes, and hit a CLI block limit. Codex’s route was disabled by policy, not proven equivalent. Today the installer deliberately removes it. ([Installer](/Users/aipalm/Documents/GitHub/devlyn-cli/bin/devlyn.js:890))

   **Smallest step:** design a measurable direct-task predicate and test current-host capabilities. An existing receipt check cannot detect every task that never allocated a receipt. Do not resurrect resolve or claim “unskippable” enforcement. Owner approval is required before changing installed behavior.

I would explicitly **not adopt**:

- **The online recursive loop or mandatory pairing.** Four executions plus improvement stages conflict with the token constraint absent demonstrated compensating savings. Devlyn 0234 already found no completion gain at approximately 2.3–3.5× input.
- **Blanket migration from prose into skills.** Paper Table 6 removes components from an already optimized `k=5` harness; it does not compare an optimized instruction-only baseline with adding one skill. Devlyn’s triggered `failure-paths.md` already failed quality admission. Conversely, 0223 shows that deletion can remove useful behavior.
- **Autonomous selection as product admission.** `selection.py:93–111` excludes baseline outputs from the released selection pool despite the prompts’ KEEP_BASE language. Paper E.6 includes choosing a 55-scoring output over an available 95-scoring one. Owner policy cannot be delegated to that selector.
- **Efficiency claims from shorter prose or fewer errors alone.** Paper E.4 reduces error rates while increasing JobBench calls 27.4→32.8 and LAB calls 20.8→25.2. Count complete execution resources, including retries and additional sessions.

**Apply candidate 1 first in this session: produce the concrete design for a current instruction-only comparison using existing infrastructure.** No product edit is yet justified by this review. The owner should decide the isolated payload and delivery endpoint after that design round; later hook installation, default behavior, or policy changes also return to the owner. Keep ideate deferred and pair contingent on measured lift.

VERDICT: Borrow Harness²’s evidence discipline first; establish the current solo block’s effect before adding any mechanism.
