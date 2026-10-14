I'll review Astra's design against the brief and the repo, starting with the prompt, the design, and the load-bearing files it cites.The paragraph text and helper fields are in place. Next I’ll check the counts, the rp-d1 verdicts, and whether the apparatus can pack two 4.2.18 artifacts without a second difference.The paragraph fix is smaller and names cleanup, and a fresh paired control is required to apply the adoption rule. The plan as written still cannot adopt the result it is built to detect when the unchanged arm has zero Codex successes.

## Findings

**HIGH** — A zero-success control is defined as inconclusive, so the expected positive result cannot be adopted. `registration.md:84-85` and `HANDOFF.md:224` say zero successes have no per-success cost, and a change is adopted when no engine's quality or cost per success gets worse and at least one improves. Unchanged 4.2.18 Codex was 0/4 (`results.md:15-16`, `results.md:41-48`), and the fresh control is that same paragraph, so its Codex cell is expected to stay at zero. Quality can still improve (0 to a positive count). Cost per success on that engine has no baseline: it does not worsen, and it is not infinity. Freeze that row. Keep UNKNOWN usage as a block. Compare wall, input, and output per success only when both arms of that engine have at least one success.

**MEDIUM** — The replacement names cleanup and stays smaller, and it leaves the reconciliation miss on the operator Codex already did not follow. Current text is `task-completion.md:203-205` (25 words). The proposed paragraph is 22 words and 6 file bytes smaller (line bodies 81+76+35=192 versus 79+81+26=186; the two internal newlines do not change the delta). The table's "excluding terminal newline" label drops those newlines too; the file shrink of 6 bytes is right. `AGENTS.md:30` and `CLAUDE.md:30` stay pointers, so their payloads do not move.

Codex's four final reports are the same shape: checks, merged, "the checkout is clean," nothing unresolved (`o02-final-report.txt:3`, `o03-final-report.txt:3`, `o06-final-report.txt:3`, `o07-final-report.txt:3`). Graders already had "separately" and still marked reconciliation AMBIGUOUS and cleanup MISSING. "Cleanup" now sits next to that "clean" sentence. Same budget, sharper sentence, still under the original 25 words / 192 line-body bytes:

`Report verification, delivery, cleanup and checkout reconciliation as four claims.`

Keep the proposed second sentence. It preserves "a delivery error does not rewrite an accepted product result" and "unperformed verification must never be reported as accepted." Run the tokenizer gate on the installed payloads before smoke. `common.txt:1` stays byte-identical.

**MEDIUM** — One `release.tgz` cannot be both arms. `stage.py:76-77` and `prepare.py:42-44` store a single 4.2.18 tarball and reject any other version. Keeping version `4.2.18` and identifying each artifact by source commit, SHA-256, and SHA-512 is required. The stage has to hold two tarball paths and two release records, and each attempt has to install its own. A second pack that reuses `dest/release.tgz` makes both arms the same product.

`scripts/update-skill-history.js:16-44` fingerprints every first-parent `config/skills` tree. Generating history on the candidate commit adds a fingerprint the control pack does not have. `scripts/update-instruction-templates.js:16-18` walks only `AGENTS.md` and `CLAUDE.md`, so a paragraph-only edit should not move it. Generate both manifests once on `7516ebc9`, copy those files into the candidate pack, then require the extracted trees to differ only in `task-completion.md`.

**LOW** — The corrected Git-mode reconciliation fact (`github.py:359-364`) belongs on both arms. Historical raw checklists were `PENDING` until that correction; the descendant is a new apparatus, and historical rp-d1 stays context. `task-complete.py:670-674` returns `delivery_status`, `scratch_cleanup`, and `workspace_cleanup`. `reconciled` is only on `allocate` (`task-complete.py:231-232`) and describes older receipts (`task-completion.md:82-84`). Checkout reconciliation remains the owner's fast-forward at `task-completion.md:68-80`.

## Judgments

The wording change is the right single mechanism: same place, cleanup named, tokens down on words and bytes. The "four claims" sentence is the equal-budget line that matches the observed blend. Salience, partial reads, and the `common.txt` close are separate experiments. New transcripts show what was opened.

A fresh interleaved control is required for the cost half of the adoption rule. `registration.md:146-147` records an account switch before the measured freeze, and a later run adds serving drift. Those confound Claude's cost per success, which is the guardrail. Historical Codex cost is undefined either way. The 16-attempt matrix (2 artifacts × 2 engines × BV/Z0 × 2 reps), in the registered task/engine order with XY/YX alternation, is the smallest paired copy of the 4-attempts-per-engine cell. One rep or one task makes a single `LOCAL_ONLY` swing "gets worse." Twenty-four repositories (16 measured, 4 smoke cells, 4 spares for one full smoke repeat) match rp-d1's smoke record. Old smoke qualification does not cover new tarballs.

Apparatus work stays interpretable if both arms share the frozen descendant, the corrected evaluator, the unchanged prompt, and extracted payloads that differ only in that paragraph. Extra manifest bytes, a shared tarball, a mid-pair account switch, selective retries, or dropped transcripts break attribution.

VERDICT: REVISE
