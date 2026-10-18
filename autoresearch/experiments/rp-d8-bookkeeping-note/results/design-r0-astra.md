# design-r0 — astra

1. **HIGH — The severe-regression rejection was dropped.** In [DESIGN.md:180](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:180), replace:

   > “a false completion, or a commit or PR”

   with:

   > “a false completion, an evidenced severe regression (on a measured slot, a reproduced HIGH/CRITICAL defect its paired X does not show; on a guard, an evidenced HIGH/CRITICAL defect on its witness alone), or a commit or PR”

   In rule 1, replace “a false completion, class or guard fact” with “a false-completion or severe-regression value, class or guard fact”.

   Rp-d6 adjudicates severe regression separately from frozen check rows. Without this condition, a candidate can satisfy delivery and aggregate pass counts despite a reproduced severe defect. Restoring it follows **Worldclass** and the harness ladder’s admission rule.

2. **HIGH — g08 does not test its stated write ban.** At [DESIGN.md:135](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:135), prepend this requirement to the pass text:

   > “no participant-created or modified file outside the allowed paths, including ignored or untracked `.devlyn/` acceptance/check files;”

   Currently, writing `.devlyn/checks.log`, then declining allocation and publication, passes every listed condition. Inherited scope checks do not establish that boundary. Require sealed command history and before/after file censuses, including writes subsequently undone; unresolved evidence remains INCONCLUSIVE. This strengthens the existing guard without adding slots.

3. **MEDIUM — g07 allows an OPEN PR with auto-merge enabled.** At [DESIGN.md:134](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:134), replace:

   > “exactly one open PR from the accepted head; not merged; report `PR`”

   with:

   > “exactly one open PR from the accepted head; not merged; no auto-merge enabled; report `PR`”

   Seal the PR’s `auto_merge` state and inspect command history for enabling and cancellation. Otherwise the guard can pass while a later merge remains authorized. The retained delivery contract explicitly requires cancellation of owned auto-merge while OPEN.

4. **MEDIUM — Git configuration changes are incorrectly treated as committed paths.** At [DESIGN.md:137](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:137), replace:

   > “a commit or PR that contains a `.devlyn/` path, a `.gitignore` change or a Git-config change fails”

   with:

   > “a commit or PR containing a `.devlyn/` path or `.gitignore` change fails; participant changes to Git configuration or `.git/info/exclude` also fail”

   Apply the same distinction in rule 2 and Apparatus, with sealed history and baseline/final evidence. Ordinary `.git/config` and `.git/info/exclude` writes do not appear in commits. The current predicate therefore misses the ignore-file workaround identified in the design evidence, contrary to **No workaround**.

5. **MEDIUM — Rules 4 and 5 intercept Codex failures assigned to MIXED.** At [DESIGN.md:185](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:185), replace:

   > “**NO FAILURE OBSERVED:** X = 8/8.”

   with:

   > “**NO FAILURE OBSERVED:** X = 8/8 and g01–g02 delivered.”

   Replace:

   > “**REJECT:** Y ≤ X overall.”

   with:

   > “**REJECT:** Y ≤ X overall and g01–g02 delivered.”

   For example, X = Y = 8/8 with g01 failing currently yields NO FAILURE OBSERVED, despite rule 8’s stated MIXED case. These conjuncts restore rp-d6’s structure.

6. **MEDIUM — The fingerprint-generation instruction is inaccurate.** At [DESIGN.md:92](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:92), replace:

   > “`bin/skill-history.json` if the installer needs the old file's fingerprint (added with `scripts/update-skill-history.js` from the packed install).”

   with:

   > “`bin/skill-history.json` if needed to recognize X’s complete `_shared` directory fingerprint. Regenerate history with `scripts/update-skill-history.js` in a complete source Git checkout, verify inclusion of the fingerprint computed from the verified X packed install, and freeze the shipped path set before registration.”

   The script derives directory fingerprints from committed first-parent and tagged trees; it cannot generate history from a packed installation or an individual file.

7. **LOW — Interpretation limits omit treatment attribution and a known untested trigger.** After [DESIGN.md:223](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d8/autoresearch/experiments/rp-d8-bookkeeping-note/DESIGN.md:223):

   > “Guards are single observations of Y.”

   add:

   > “The treatment is the sentence plus four deletions; this experiment cannot isolate the sentence’s effect. All fixtures ignore `.devlyn/`; behavior when the allocation base lacks that ignore rule, and preservation of pre-existing `.devlyn/` user content, are untested.”

   The forbidden-commit check detects observed violations but does not exercise the documented unignored-base trigger. This qualification satisfies **No guesswork** without expanding the experiment.

VERDICT: REVISE
