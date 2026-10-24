# 0257 claude diagnosis (read-only, post hoc)

Written after the result, at the owner's request to find why the package does not help Claude. It changes no reading
in [RESULT.md](../RESULT.md). Evidence root: `~/.local/share/nx01/0257-live/output/<cell>/` (`final.txt`,
`snapshot/`, `run/stdout`, `assessment/*/stdout`, verdicts). Every count below was taken from those files. Only the
F10 completion table is a registered test; the other counts were chosen after seeing it, so they are screens.

## Conclusions

1. **A pattern more frequent in Claude B in this sample: it notices a case the request does not spell out, leaves it
   and reports it.** It tracks the one Holm-rejected test (F10) and is a plausible part of the D3 gap. Codex
   with the same text does not show it. That one mechanism drives both tasks is a hypothesis.
2. **The responsible package component is not identified.** No F10 B transcript names a principle, and the package
   also adds skills, settings and delivery text. Separating them needs an ablation.
3. **False completions occur in both arms by the same mechanism.** The package does not eliminate them; these
   counts cannot show whether it changes their frequency.

## 1. Leaving a case the request does not spell out

**F10.** Every one of the 8 A cells adds an `entity.parse.failed` (or equivalent) error handler, so a body the JSON
parser rejects gets `400 { error: 'invalid_body', field: 'body' }`. None of the 8 B cells does; they keep Express's
default HTML 400 (`snapshot/server/index.js`; one-sided Fisher p = 7.8e-5, the same table as the registered F10
completion test). The B files are about 30 lines shorter (92–112 vs 111–138).

B sees the case and decides not to handle it. 7 of 8 B reports list it with a scope reason:

- c002: "The request didn't specify this case."
- c009: "The request only covered missing or invalid fields."
- c018: "The request didn't define that case."
- c034: "The request doesn't define a `field` for that case."
- c041: "The request didn't cover this case."
- c050: "the request didn't specify this case."
- c057: under the heading "Choices the request didn't specify".
- c025 does not mention it.

Three A reports also call the handler unrequested and add it anyway: c049 "Additions you didn't ask for: JSON that
can't be parsed also gets `400 invalid_body`"; c058 "Two additions you didn't ask for"; c033 "two choices the request
didn't specify: malformed JSON gets a 400 with `field: 'body'`". Four A reports (c001, c010, c026, c042) describe the
handler without calling it unrequested, so some A cells may read it as part of the requested invalid-body behavior;
c017's report is empty. The code difference (8/8 vs 0/8) holds either way.

**F11 points to what B declines.** The registered malformed-JSON probe returns JSON 400 in 16/16 claude A F10/F11
cells and 6/16 B cells, but the B split is F10 0/8 and F11 6/8. On F11 most B cells add the handler, also as an
unrequested case (c054: "I added this case, which you didn't ask for"; c045: "The request didn't mention it"). F11's
request already defines the body-level error (`{ error: 'invalid_body' }`, no field); F10's defines only per-field
errors (`field: '<name>'`), so handling it there means choosing a `field` value, as c034 says. One reading consistent
with both tasks: B leaves a case when closing it means choosing a response shape the request did not give. This is a
post hoc reading of two tasks.

**D3.** The request says "Do not change public APIs" and "Keep in-process subcommand parsing … compatible". In 10 of
16 B cells, `_parseCommand` calls a private parser (`this._parseOptions…(unknown)`) instead of the public
`parseOptions`, so subclass overrides stop taking part in `parse()`; in A, 4 of 16 (one-sided Fisher p = 0.037,
post hoc). This is the codex assessor's most common D3 finding in both arms. 6 of the 10 B reports disclose it and
give a reason:

- d241: "Nothing in the repo does this, and I chose it over keeping the delimiter count as hidden state on the
  command object."
- d049: "Nothing in the repo does this, and it avoids changing the public return shape."
- d177: "Overriding it isn't documented and the public signature is unchanged, but it is a small behaviour difference."

This is also a real design tradeoff: keeping the public path means carrying delimiter state on the command, and the
assessors find reentrancy defects in cells that did that (d018 and d193 in A, d162 in B); d017 (B) chose that side
and completed. Three of A's four bypass reports disclose the bypass too (d065, d161, d225), so it exists in bare
Claude. Claude B completes D3 in 5 of 16 cells, A in 10.

**Codex does not show it.** Codex reads the same `AGENTS.md` in B. It bypasses `parseOptions` in 0/16 cells in both
arms, and adds a parse handler on F10 in 0/8 A and 1/8 B cells. So the count difference is specific to Claude in
this sample.

**Earlier sightings.** 0233 (C arm, r2) and 0256 (c02, c12) give the same F10/F11 reason; 0256's c15 also left the
handler out but ended without a report. 0256 left the principles unchanged because those cells could not pick out
one sentence; 0257 measured the gap on fresh cells as prediction 6, and it held.

**Assessment note.** The blinded codex assessor does not treat the omission evenly. In all 8 claude B cells it raises
the same finding: a JSON `null` body is rejected by Express's default parser before validation, giving HTML instead
of `{ error: 'invalid_body', field: 'name' }`. Codex A cells that keep the same default parser with no handler still
complete in 4 of 7 (c003, c035, c051, c060); codex B's handler-free completions all set `express.json({ strict: false })`
(c004, c020, c036, c052), and its three default-parser cells complete 0/3. Claude A's handlers answer that input with
`field: 'body'`, not `'name'`, and all 8 are assessed complete. So the assessor objects to B's HTML response, not to
the exact field, and its grading of the omission varies across cells; that unevenness is a competing contributor to
the completion gap, and its cause is not established. The handler counts and the probe above do not depend on the assessor.

## 2. Which text

The B cells load the managed block of `AGENTS.md` (through `CLAUDE.md` = `@AGENTS.md`), two skill listings and the
project settings. No F10 B transcript contains a principle's name ("overengineering", "smallest", "Saint-Exupéry",
"subtractive", "Production ready"), as in 0256. Lines of the installed block (`snapshot/AGENTS.md`) that could be
read as supporting the reports' reason:

- L17 **No overengineering** — "smallest change that closes the goal. New abstractions require an observed failure
  mode they prevent."
- L27 **First-principles thinking** — "Challenge the requirement … do not silently pick one interpretation when
  multiple exist … push back when a simpler path is genuinely better."
- L28 **Saint-Exupéry** — "A change is finished when no further line, branch, flag, or doc paragraph can be removed
  without breaking a learned failure mode."

L22 **Production ready** ("behavior under failure is what the user expects") would support handling the case. The
F11 reading above fits L27's "do not silently pick one interpretation" best, but that is an interpretation, not
evidence. The delivery and executor lines (L33–L34), the skill listings and the settings are also present in every B
cell. Only removing one at a time can separate them. The block is the owner's canonical text, so any ablation needs
the owner's approval of the exact deletion (0256 addendum).

## 3. False completions

All 22 are claude cells: D4 A 7, B 9; I0185 A 5, B 1. Codex has none. The mechanism is the same in both arms
([RESULT.md](../RESULT.md) "Safety"):

- **D4:** a general bound ("every blocking step has a 10-second limit") is claimed from the tests the cell ran. Those
  tests do not exercise a writer that dies before opening, stalls, or reads stdin late; the witnesses hang the tree.
- **I0185:** the report says a failed first install cleans up the skills directory it created (d025: "a first install
  that fails leaves no skills directory"), from single-process failure tests; K5's interleaving leaves it behind.

0256 found the same mechanism (d28 in B, d24 in A). The I0185 B cells carry no principles text (installer limit, see
the 0256 addendum), so d025's false completion cannot come from that text. The package's "No guesswork" sentence
binds conclusions to evidence but does not stop a general claim drawn from narrow evidence. A completion-claim
sentence was added to the contract on 2026-07-09 (62196bf7) and removed the same day, unmeasured (9d5ca836,
iter-0069). Fixing this habit is a separate candidate from section 1.

## Options for the owner

None is chosen here.

1. **Ablation screen for section 1.** Claude only, F10 and D3, B against B minus one approved deletion (for example
   L27's "do not silently pick one interpretation" clause, or L17's second sentence), predictions frozen before it
   runs. The 0257 apparatus can run it.
2. **Separate candidate for section 3.** For example a completion claim must name the case that exercises it.
   Measured on D4 and I0185 against the witnesses.
3. **Change nothing for now.** Keep the current package pending more evidence.

## Review

Astra ultra and Grok 4.7 checked it read-only in two rounds ([r1 prompt](claude-diag-r1-prompt.md),
[Astra](claude-diag-r1-astra.md), [Grok](claude-diag-r1-grok.md); [r2 prompt](claude-diag-r2-prompt.md),
[Astra](claude-diag-r2-astra.md), [Grok](claude-diag-r2-grok.md)). Round 1 (both REVISE) narrowed the causal claims,
added the F11 split and the D3 tradeoff, and corrected the assessment note and several quotes. Round 2 (both REVISE,
MEDIUM only) added the A report split, Claude A's `field: 'body'` assessment and the F11 wording in the addendum; those
fixes are applied here without a third round.
