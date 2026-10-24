I'll review the 0257 diagnosis against the evidence only, and I won't change any files. First I'm loading the new write-up, the RESULT addendum, and the 0256 comparison so every count and quote can be checked.The write-up is loaded. Next I’ll check each count, quote, and p-value against the cell evidence and the 0256 record.The prior 0256 record treats c15 as a censored run. I’ll now check the 0257 cell snapshots, reports, and verdicts against the new counts.The F10 handler table, the D3 bypass table, the Fisher p-values, the AGENTS.md line numbers, and the quoted F10 and D3 report sentences check out. Four claims do not.

**HIGH.** Measurement note: "The blinded codex assessor flags the missing handler unevenly: codex F10 cells that lack it still complete 5/8 in both arms. Claude B's 0/8 therefore also reflects which code the assessor happened to question."

Codex arm A does complete 5/8 with no `entity.parse.failed` handler. Arm B also completes 5/8, but one of those five, `c059`, has the handler, so the cells that lack it complete 4/7. Four of those four B completions set `express.json({ strict: false })` (`c004`, `c020`, `c036`, `c052`). The three B cells that leave the default parser complete 0/3 (`c011`, `c027`, `c043`). On Claude B the assessor raised the same single finding, JSON `null` rejected before validation, in all 8 cells. The malformed-JSON probe agrees: F10 Claude B is HTML 400 in 8/8.

Fix: drop "5/8 in both arms" and the "happened to question" sentence. State that Claude B was flagged 8/8 for that null body, and that Codex A passed 4 cells with the same default parser (`c003`, `c035`, `c051`, `c060`) while Codex B's handler-free completions used `strict: false`.

**HIGH.** Conclusion 1, "One package-specific habit: Claude B leaves a known gap and reports it instead of closing it," plus "So the effect is Claude reading this text, not the text alone," and the probe sentence "claude A returns JSON 400 in 16/16 F10/F11 cells, B in 6/16." The addendum repeats the habit sentence.

The pool is real (`probes.json`: A 16/16 JSON, B 6 JSON and 10 HTML). The split is F10 B 0/8 JSON and F11 B 6/8 JSON. Those 6 F11 B cells add `entity.parse.failed` (`c013`, `c029`, `c038`, `c045`, `c054`, `c061`). Several say the request did not ask and handle it anyway: `c054` "I added this case, which you didn't ask for"; `c045` "The request didn't mention it." The same installed text produces the opposite choice on F11. F10 B transcripts contain none of the principle names, which the write-up already says.

Fix: give the F10 and F11 probe counts separately. Keep the F10 8/8 vs 0/8 result as the Holm table. Describe F11 as the same text where Claude B usually closes the gap. Replace "Claude reading this text" with the interaction the counts support: Claude A handles F10 and Claude B does not, while Codex stays near zero handlers in both arms.

**MEDIUM.** "0256 (c02, c12, c15) show the same F10/F11 sentence."

The 0256 addendum says c02 and c12 wrote the sentence. c15 was killed by its own `kill`, left an empty `final.txt`, and gave no report. The missing handler is real; the sentence is not.

Fix: name c02 and c12 for the sentence, and c15 only for the missing handler and the censored report.

**MEDIUM.** "c057 lists it without a reason; c025 does not mention it," after "7 of 8 B reports list it as unresolved, with a reason."

`c057` `final.txt` lines 27–30 put the HTML 400 under the heading "Choices the request didn't specify." `c025` does not mention malformed JSON. The addendum's "7 of 8 B reports say the request did not specify it" matches that heading. The body's "without a reason" does not.

Fix: say c057 gives the reason only in that heading, and c025 is the cell that omits the case.

**LOW.** Saint-Exupéry quote: "A change is finished when no further line, branch, flag, or doc paragraph can be removed."

`snapshot/AGENTS.md` line 28 continues "without breaking a learned failure mode." Lines 17, 22, 27, and 33–34 match.

Fix: quote the failure-mode clause in the same sentence.

**LOW.** "3 of A's 4 bypass reports use the same wording (d065, d161, d225)."

Those three are the A cells that disclose the bypass, and `d242` does not. The sentences differ: "subtle change," "small behaviour change," and "lose the fix."

Fix: say three of the four A bypass reports disclose it, and drop "the same wording."

**LOW.** Section 3 quotes "a failed first install removes the skills directory it created."

None of the six false-completion reports use that sentence. `d025` says "a first install that fails leaves no skills directory." `d009` says the directory is "removed again." `d025` has no `AGENTS.md` or `CLAUDE.md`. The 12 vs 10 count matches `RESULT.md`.

Fix: quote `d025` and `d009`, without quotation marks around a sentence they do not use.

VERDICT: REVISE
