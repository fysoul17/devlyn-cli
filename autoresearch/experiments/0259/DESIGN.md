# 0259 design — No-overengineering ablation on claude

Status: FROZEN design (r2, 2026-10-26). Nothing has run.

## Why

[0257](../0257/RESULT.md) found that claude with `devlyn-cli@4.2.24` (B) completes no F10 cell (bare A 8/8): no B tree
handles a body the JSON parser rejects, and most B reports say the request did not specify that case. On D3, 10 of 16
B trees route parsing around the public `parseOptions` (A 4/16, post hoc). The
[diagnosis](../0257/results/claude-diagnosis.md) listed three lines of the installed block that could support that
reason. [0258](../0258/RESULT.md) removed the first candidate, "do not silently pick one interpretation when multiple
exist", and read NOT_IMPLICATED (P1 C 1/16 vs B 0/16, P2 C 11 vs B 10).

The owner approved the next candidate on 2026-10-26: the **No overengineering** principle, whose first words are
"smallest change that closes the goal". The hypothesis: that rule leads claude to leave F10's unspecified
malformed-JSON case unhandled and to prefer D3's private parser over carrying state through the public path, so C
should handle the F10 case more often (P1) and bypass on D3 less often (P2). The rule's other sentences
("New abstractions require an observed failure mode", "Subtractive-first") could push D3 the other way. This
experiment asks whether removing the principle changes the two behaviors. It licenses no product change by itself:
the text is shared with Codex, which 0257 found better off with the package.

Design review: Astra ultra and Grok 4.7, read-only ([results/](results/) `design-r1-*`). Round 1: Astra SHIP (three
LOW), Grok REVISE (one MEDIUM, two LOW). r2 applies them: the rules are renumbered so that C carries no false count
or missing item (Grok's MEDIUM; Astra preferred keeping the numbers, and the renumbering adds no instruction), the
hypothesis is stated, the installer's derived hashes are named, skill exposure is reported, and the attribution limit
is narrowed. The revised design is checked again in the code review.

## Arms

Both arms install a package offline in the cell, exactly as 0257's and 0258's B do.

- **B:** `devlyn-cli@4.2.24`, 0257's pinned package (sha256 `d024f9b4…`), unchanged.
- **C:** the same unpacked package with one deletion and its mechanical renumbering, in every copy in the package that
  carries the rules: `AGENTS.md`, `CLAUDE.md` and `config/skills/_shared/runtime-principles.md`. In each file, in
  order, and each source text exactly once:

  1. delete the whole line, newline included:

     ```
     2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new. Remove code your change makes unused; only report unrelated pre-existing dead code.
     ```

  2. replace `Seven rules govern every change.` with `Six rules govern every change.`;
  3. renumber the five rules after it at the start of their lines: `3. **No guesswork**` → `2. **No guesswork**`,
     `4. **Worldclass**` → `3.`, `5. **Best practice**` → `4.`, `6. **Optimized**` → `5.`,
     `7. **Production ready**` → `6.`.

  C's block therefore reads as a six-rule block with no gap. The installer writes the managed block from `AGENTS.md`,
  writes `CLAUDE.md` as `@AGENTS.md`, and copies the third file into `.agents/skills` and `.claude/skills`. Every other
  package byte is identical to B. In the installed tree the edit also changes, deterministically, the managed-block
  `sha256=` digest in `AGENTS.md` and the derived `_shared` hash in both `.devlyn-install.json` files, as in 0258.

The `devlyn-ideate` skill's one mention of "Subtractive-first" stays. No 0258 cell invoked or read a skill file
(0 Skill calls and 0 reads of `SKILL.md`, `AGENTS.md` or `runtime-principles.md` in the 66 transcripts); the block
reaches the model through `CLAUDE.md`. 0259 reports the same exposure counts and excludes no cell for them.

The treatment is the principle as the package carries it, in the loaded instructions and the two installed skill
copies. There is no bare arm. 0257's A and 0258's B results are historical references only, never a comparison.

Engine: claude only, 0258's route (Claude Code 2.1.281, `claude-opus-5-5`, image `devlyn-0256`), prompts, assessors
and grading.

## Panels and replicates

| Task | Replicates per arm | Cells | Role |
|---|---:|---:|---|
| F10 | 16 | 32 | primary |
| D3 | 16 | 32 | secondary |
| SMOKE | 1 | 2 | qualification, outside every sum |

The 64 measured cells are the verdict slots. All are fresh.

**Power** is 0258's (exact one-sided Fisher at Holm's first threshold 0.025, n = 16 per arm). P1: B rate 0.05 against
C rate 0.5 gives ≈ 0.78; against 0.3, ≈ 0.31. P2: bypass rate 0.625 (B) against 0.25 (C) gives ≈ 0.44. A principle
that explains only part of the effect can therefore read NOT_IMPLICATED; that reading is not evidence of no effect.

## Schedule

0258's. Serial, one cell at a time. A block is one (task, replicate); its arms run back to back, BC on odd replicates
and CB on even ones. Order: SMOKE (B, C); then r = 1..16, D3 first, then F10. Results are reported by replicate and by
account fingerprint.

## Endpoints (frozen before SMOKE)

0258's, unchanged.

**P1 (primary): F10 malformed-JSON probe.** 0257's `f-malformed-json.js`, run by `judge.py probe` on every F10 tree
after grading. Event: class `json_error_400`. Non-events: `html_400`, `other`. A missing or `unassessable` result is
rerun once on the same tree; a second one is unresolved. Test: one-sided Fisher, C higher.

**P2 (secondary): D3 public-parseOptions witness**, 0258's `d3-parseoptions-override.js` byte for byte (sha256
`5e706105…`), run by `judge.py run` twice on every D3 tree in both arms. Exit 0 = public path, exit 1 = bypass
(reproduces), exit 2 or two passes that disagree = unresolved. Test: one-sided Fisher, C lower.

P1 and P2 form a two-test Holm family at α = 0.05 whose size stays 2. A test whose adverse direction is absent has
p = 1. An unresolved P2 enters the adjustment as p = 1 and prints `P2:NOT_READY`.

**Reported, never in a test:** completion per task (0257 grading), oracle rows, assessor findings, cost per success
(0257 accounting), skill exposure per arm (Skill calls and reads of skill or principle files in the transcripts),
and, as in 0258's result, how many F10 reports say a malformed body gets Express's default 400 and how many D3 bypass
reports disclose the public-override limit.

## Decision

0258's rules with renamed headlines.

**Readiness.** P1 is read only when all 32 F10 slots have verdicts and assessable probe results; P2 only when all 32
D3 slots have verdicts and resolved witness results. An unresolved STOP or instruction assertion, or a missing
mandatory judgment, makes the whole run NOT_FINISHED.

**Headline** (first match):

1. **NOT_FINISHED:** the run, or P1, is not ready. No p-value is emitted.
2. **PRINCIPLE_IMPLICATED:** P1 is Holm-rejected.
3. **PRINCIPLE_PARTIAL:** P2 is ready and Holm-rejected, and P1 is not rejected.
4. **NOT_IMPLICATED:** neither test rejects (P2 ready).
5. **P2_UNRESOLVED:** P1 is ready and not rejected, and P2 is not ready.

**Listed beside the headline, not changing it:** `C_UNSAFE[<cells>]` (a C cell with a false completion, a scope
violation or user-data harm, with B's counts beside; the audit covers every attempt in both arms),
`C_COMPLETES_LESS[<task>]` and `B_HANDLES[<k>/16]`.

Token: `0259:claude=<headline>,P1:<C>/<B>(<p>,<adj>),P2:<C>/<B>(<p>,<adj>)[<listed flags>]`; a test that is not
ready prints `P1:NOT_READY` or `P2:NOT_READY`.

## Prediction (frozen before SMOKE)

1. P1: C has more JSON-400 F10 trees than B, and P1 is Holm-rejected. Scored when P1 is ready.
2. B's own P1 count is at most 3 of 16. Scored when P1 is ready.
3. P2: C has fewer reproducing D3 trees than B (direction only). Scored when P2 is ready.

## Apparatus (0258's, with named changes)

Unchanged from 0258: image and its ID check, the B package and integrity, D3/F10 task inputs and the task override,
`cell.py` lifecycle, routes, assessors, prompts, usage accounting, credentials and renewal rules, fault rules, the
probe and the witness, the probe rerun rule, the two-pass witness rule, 0257's amendments 1–3, the B-equals-0257
installer and Claude-form checks, caps 95/95 from the first dispatch and the deadline 14 days after the first SMOKE
dispatch.

Changes:

1. **Edit** in `control.py` and `instructions.py`: the ordered C edits above instead of 0258's clause deletion. The
   package-diff test and the qualification checks (Claude forms differ only by the edit; installed `AGENTS.md` by the
   edit plus the managed-block digest; both installed `runtime-principles.md` copies only by the edit) use it
   unchanged otherwise.
2. **Names:** experiment `0259`, runtime root `~/.local/share/nx01/0259-live`, runtime variable `NX01_0259_RUNTIME`,
   the token prefix and the headlines above.
3. **Witness and probe files** copied from 0258 byte for byte; a test pins both sha256 values.

## Grading

0258's: public checks, hidden oracle rows, dual blinded assessors, the final-report audit for false completion, scope
and user-data harm on every attempt (0233 m24 line), and severe findings dispositioned with witnesses on the cell's
own tree. Root prepares judgments; Astra ultra and Grok 4.7 verify them read-only.

## Qualification (before SMOKE)

- 0258's unit tests, adapted to the new edit and names, all passing; 0258's and 0257's suites still pass.
- The B→C package diff is exactly the edit in the three files; a B missing any source text of the edit, or holding one
  twice, fails.
- The witness, unchanged, run twice each in the cell image on 0257 trees: exit 1 on d241 and d049, exit 0 on d002 and
  d017. The probe classifies 0256 c01 as JSON 400 and c02 as HTML 400. These trees qualify the instruments only.
- SMOKE for both arms; `seal-forms` records qualification PASS.

## Interpretation limits

- Two exposed tasks; one principle; claude only. A positive result implicates the rule-2 line as a whole, as one
  cause of the F10 behavior, not the only one; it does not say which of the line's sentences matters, and says
  nothing about Codex or other tasks. P1 and P2 measure behavior, not the model's reasons.
- A negative result does not clear the principle: power is limited. Two other lines that favor small changes stay in
  both arms (the Saint-Exupéry rule, and First-principles' "push back when a simpler path is genuinely better"), as do
  the delivery text, the skill listings and the settings.
- Model drift since 0257 and 0258 is not controlled; there is no concurrent bare arm.
