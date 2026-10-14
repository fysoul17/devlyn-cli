Recommend one paragraph rewrite and a fresh paired experiment. No files changed.

1. **The evidence establishes a reporting defect, but not its cognitive cause.**

   [The retained results](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d1-delivery-cost/results.md) show correct Codex delivery, cleanup and reconciliation in 4/4 runs. “Checkout clean” did not establish reconciliation, and cleanup was absent.

   The reporting rule sits at line 203 of a 233-line guide, immediately after the permissions paragraph. It names reconciliation but omits cleanup. The installed managed block supplies only a pointer to that guide: `bin/instructions.js` reads the root templates; `bin/devlyn.js` handles their installation/imports.

   The helper provides cleanup evidence through `delivery_status`, `scratch_cleanup` and `workspace_cleanup`. **`reconciled` actually comes from `allocate`, describing older receipts—not current-checkout reconciliation.** That remains an owner action.

   Under **No guesswork**, low salience, incomplete reading, brevity and the apparatus’s “changed / verified / unresolved” closing instruction remain hypotheses. Deleted transcripts prevent retrospective discrimination. The proposed experiment tests wording effectiveness; relocation and prompt effects would require separate experiments. Retained new transcripts can establish what was read, though not internal attention.

2. **Change only the existing reporting paragraph**, preserving its position. This follows **No overengineering** and isolates one mechanism.

   Exact old text at [task-completion.md:203](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-completion.md:203):

   ```text
   Report verification, delivery and checkout reconciliation separately. A delivery
   error does not rewrite an accepted product result; unperformed verification
   must never be reported as accepted.
   ```

   Exact replacement:

   ```text
   Report verification, delivery, cleanup and checkout reconciliation separately.
   Delivery errors do not rewrite accepted product results; never report unperformed
   verification as accepted.
   ```

   Verified whitespace-word / UTF-8-byte counts:

   | Scope | Before | After |
   |---|---:|---:|
   | Paragraph, excluding terminal newline | 25 / 192 | 22 / 186 |
   | Entire `task-completion.md` | 1,989 / 14,320 | 1,986 / 14,314 |
   | `AGENTS.md`, unchanged | 597 / 4,049 | 597 / 4,049 |
   | `CLAUDE.md`, unchanged | 597 / 4,049 | 597 / 4,049 |

   **Words and bytes do not prove token neutrality.** Require authoritative token-count nonincrease for both engines’ installed instruction payloads before any smoke exposure. Those counts remain unverified here. Keep `common.txt` byte-identical.

3. **Use fresh interleaved controls; historical rp-d1 is descriptive context.**

   Account changes, serving drift and unavailable raw transcripts make historical-only comparison insufficient. Pack control X from untouched `7516ebc9` and candidate Y from its one-paragraph branch, using identical frozen dependencies and generated manifests. Both are unpublished research artifacts. Require extracted payloads to differ only in that paragraph; publication-generated skill history must not introduce another difference.

   Install both through unchanged rp-d1 arm-B `0233.install()` behavior. Keep package version `4.2.18`, but identify each artifact by source commit, SHA-256/SHA-512 and packed/installed manifests—not version alone.

   **Register before running:** first freeze the protocol, prediction, schedule and gates; after qualification, freeze smoke receipts and measured inputs. Prediction: explicit four-category wording improves Codex report success without degrading either engine’s quality or cost per success. Require Astra ultra and Grok 4.7 approval before exposure and independent raw-evidence review afterward.

   **Measured matrix: 16 attempts.** Two artifacts × two engines × BV/Z0 × two repetitions:

   - Claude Code `2.1.296`, `claude-opus-5-5`, effort `max`.
   - Codex `0.162.1`, `gpt-6-sol`, effort `high`; children retain owner models.
   - Pair order follows `BV/Claude, BV/Codex, Z0/Codex, Z0/Claude, Z0/Claude, Z0/Codex, BV/Codex, BV/Claude`; run XY on odd pairs, YX on even pairs, serially.

   Freeze prompt, tasks, oracle, image, model cache, accounting and account identities across arms. Preregister same-account credential renewal at pair boundaries. Retain the original watchdogs; impose no token/cost budgets.

   Preserve the [four registered success conditions](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d1-delivery-cost/registration.md): requirements/scope and regression validation; exactly one correctly merged accepted PR; preservation of tracked user files and ignored sentinel; truthful verification, merge, cleanup and reconciliation reporting supported by both reviewers. Missing or ambiguous claims fail; truthful `CLEANUP_PENDING` remains allowed.

   Count every dispatched attempt, including failures and child usage. Adopt only if neither engine’s observed quality nor **any** wall/input/output cost-per-success metric worsens, and at least one improves. UNKNOWN accounting prevents adoption. A zero-success control leaves cost per success undefined: **inconclusive, not infinity**.

   Apparatus work is limited to frozen source-artifact identity support in `stage.py`/`prepare.verify_release`, paired scheduling with global STOP/remaining-repository checks, and summaries grouped by artifact. Preserve strict archive validation. Freeze the corrected Git-mode evaluator for both arms; identify this as a reviewed apparatus descendant, not the historical apparatus commit.

   Pre-create **24 private repositories**: 16 measured, four SM qualification cells, four smoke spares. The owner makes one fine-grained PAT edit selecting all, retaining the original permissions. Require fresh smoke for both engines and artifacts: old qualification does not cover new artifacts, credentials or release-bound receipts. Preserve archive→verify→delete→404 handling. Spares allow one complete smoke repeat; measured attempts are never replaced.

4. **Interpretation limits and review status.**

   Two repetitions support only this task/model setting. The unchanged prompt’s publishing ambiguity may recur. Extra artifact differences, asymmetric repairs, account/model changes between arms, selective retries, altered grading, missing usage or damaged evidence invalidate attribution. Retain raw evidence through final adjudication.

   Astra ultra returned **SHIP, no HIGH findings**. Grok 4.7 could not create its session because the read-only sandbox returned `FS_PERMISSION_DENIED`; its required review remains outstanding.

DESIGN: BLOCKED required Grok 4.7 review unavailable in this read-only seat
