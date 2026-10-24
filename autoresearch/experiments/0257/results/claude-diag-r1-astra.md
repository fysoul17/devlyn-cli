No files changed. Findings refer to the [diagnosis](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-diagnosis/autoresearch/experiments/0257/results/claude-diagnosis.md) and [addendum](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-diagnosis/autoresearch/experiments/0257/RESULT.md:162). Cell paths below are relative to the supplied evidence root.

1. **MEDIUM — The proposed mechanism is presented as established.**
   **Text:** “One package-specific habit”; “the package makes it more frequent”; “So the effect is Claude reading this text.” Diagnosis L10, L53–58; addendum L165–168.
   **Evidence:** Bare Claude also bypasses `parseOptions` in 4/16 D3 cells. The experiment changes the whole package, including skills, settings and delivery instructions. D3 also supports a competing explanation: d241 `final.txt:31` and d209 `final.txt:25` explicitly weigh override compatibility against shared parser state; d017 `final.txt:26` chooses the opposite tradeoff. Assessors report reentrancy problems in state-based implementations d018, d193 and d162.
   **Fix:** Describe a pattern more frequent in Claude B **in this sample**, label the shared mechanism a hypothesis, and acknowledge the D3 design tradeoff. State that the responsible package component remains unidentified.

2. **MEDIUM — Shared false completions do not establish no package effect.**
   **Text:** “not a package effect”; “The package neither causes nor prevents them.” Diagnosis L14–15; addendum L169–170.
   **Evidence:** The verified counts establish occurrence in both arms: D4 A7/B9 and I0185 A5/B1. They do not establish equal rates or exclude a package contribution. I0185’s absent principles text excludes that text’s direct influence, not every package component.
   **Fix:** “False completions occur in both arms. The package does not eliminate them; these observations do not establish whether it changes their frequency.”

3. **MEDIUM — Incorrect completion count among Codex cells without handlers.**
   **Text:** “codex F10 cells that lack it still complete 5/8 in both arms.” Diagnosis L64–65.
   **Evidence:** A completes **5/8** without handlers; B completes **4/7** without handlers. B’s fifth overall completion, c059, contains a handler at `c059-F10-codex-B-r8/snapshot/server/index.js:64`.
   **Fix:** “Codex completes 5/8 overall in each arm; among cells without a handler, A completes 5/8 and B 4/7.”

4. **MEDIUM — The measurement explanation conflates two inputs and assumes assessor randomness.**
   **Text:** “It explains the one Holm-rejected test (F10)”; “Claude B’s 0/8 therefore also reflects which code the assessor happened to question.” Diagnosis L10–11, L65.
   **Evidence:** All eight Claude B Codex assessments cite valid JSON **`null`** and require `field:'name'`. The registered probe sends malformed **`{`** and accepts any JSON error object (`results/witnesses/f-malformed-json.js:66`, L92). Claude A handlers return `field:'body'`, yet all eight complete. This supports inconsistent assessment treatment, but does not identify its cause.
   **Fix:** Separate handler presence, malformed-JSON probe results and completion judgments. Report their association and the assessment inconsistency without attributing it to what the assessor “happened” to examine.

5. **MEDIUM — c15 cannot corroborate the reported sentence.**
   **Text:** “0256 (c02, c12, c15) show the same F10/F11 sentence.” Diagnosis L60.
   **Evidence:** 0256 c15’s `final.txt` is empty. The prior RESULT addendum L152 explicitly records its self-termination and absent report.
   **Fix:** “0256 c02 and c12 report the same rationale; c15 also omitted the handler but ended without a report.”

6. **MEDIUM — The instruction quotation omits a material qualification.**
   **Text:** “A change is finished when no further line, branch, flag, or doc paragraph can be removed”; “Production ready … points the other way and loses.” Diagnosis L79–81.
   **Evidence:** Installed `snapshot/AGENTS.md:28` continues **“without breaking a learned failure mode. Not before.”** That qualification matters when interpreting the instruction as encouraging omission. No transcript establishes that one principle defeated another.
   **Fix:** Include the qualification and describe these clauses as candidate interpretations. Replace “loses” with “would support handling the failure path.”

7. **LOW — c057 does provide a scope rationale.**
   **Text:** “c057 lists it without a reason”. Diagnosis L32.
   **Evidence:** `c057-F10-claude-B-r8/final.txt:27` says “Choices the request didn’t specify:” above the malformed-JSON disclosure at L30.
   **Fix:** Quote that heading. The addendum’s **7/8** scope-rationale count is supported.

8. **LOW — The A-report summary overstates agreement.**
   **Text:** “3 of A’s 4 bypass reports use the same wording”. Diagnosis L53.
   **Evidence:** d065 and d161 explicitly acknowledge ignored overrides. d225 `final.txt:30` instead says subclasses “lose the fix” and “Parsing otherwise still works,” understating the broader compatibility loss.
   **Fix:** “Three A reports mention a subclass limitation; two explicitly acknowledge that overrides stop affecting parsing.”

9. **LOW — Option 3 selectively emphasizes a benefit.**
   **Text:** “Keep the package as is for Claude; Codex benefits from it (B_BETTER).” Diagnosis L111.
   **Evidence:** B_BETTER is correct, but the existing RESULT also records higher Codex confirmation costs. Invoking only Codex’s benefit gives the Claude status-quo option favorable framing. No option is actually selected.
   **Fix:** “Keep the current package pending more evidence.” Present Codex’s benefits and costs separately if needed.

The remaining principal counts, both Fisher p-values, cited AGENTS line numbers and commit references check out.

VERDICT: REVISE
