# 0260 design — Saint-Exupéry ablation on claude

Status: FROZEN design (r3, 2026-10-27). Nothing measured has run.

## Why

[0257](../0257/RESULT.md) found that claude with `devlyn-cli@4.2.24` (B) completes no F10 cell (bare A 8/8): no B tree
handles a body the JSON parser rejects, and most B reports say the request did not specify that case. On D3, 10 of 16
B trees route parsing around the public `parseOptions` (A 4/16, post hoc). Two single-line ablations followed, and
both read NOT_IMPLICATED:

- [0258](../0258/RESULT.md) removed "do not silently pick one interpretation when multiple exist": P1 C 1/16 vs
  B 0/16, P2 C 11 vs B 10.
- [0259](../0259/RESULT.md) removed the **No overengineering** principle: P1 C 6/16 vs B 2/16 (p 0.11, Holm 0.22),
  P2 C 10 vs B 8.

0259's interpretation limits named the Saint-Exupéry discipline rule as one of two remaining lines that favor small
changes. The owner approved it as the next candidate on 2026-10-27. Its operative sentence defines "done": "A change
is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure
mode." A handler for F10's malformed body guards against no failure the request or the tests show, so under that
definition it is removable. The hypothesis: the rule leads claude to leave F10's unspecified malformed-JSON case to
Express and to prefer D3's shorter private-parser route, so C should handle the F10 case more often (P1) and bypass on
D3 less often (P2). The experiment asks whether removing the rule changes the two behaviors. It licenses no product
change by itself: the text is shared with Codex, which 0257 found better off with the package.

Design review: Astra ultra and Grok 4.7, read-only ([results/](results/) `design-r1-*`). Round 1: Astra SHIP (one
LOW), Grok REVISE (one MEDIUM, four LOW). r2 applies them: a judge container that never starts no longer counts as a
probe or witness attempt (Grok's MEDIUM; code review round 2 extended it to a container whose start fails), the
in-slot rerun path and the 0259 exposure count are stated correctly, the headlines name a rule, and a positive result
is limited to the line as a whole. Both reviewers kept the whole-bullet deletion, the endpoints and the single-line
design.

## Arms

Both arms install a package offline in the cell, exactly as 0257–0259's B do.

- **B:** `devlyn-cli@4.2.24`, 0257's pinned package (sha256 `d024f9b4…`), unchanged.
- **C:** the same unpacked package with one deletion and its count change, in every copy in the package that carries
  the rules: `AGENTS.md`, `CLAUDE.md` and `config/skills/_shared/runtime-principles.md`. In each file, in order, and
  each source text exactly once:

  1. delete the whole line, newline included:

     ```
     - **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.
     ```

  2. replace `Three discipline rules govern HOW the principles are applied:` with
     `Two discipline rules govern HOW the principles are applied:`.

  The deleted line is the last of the three bullets, so C's block reads as a two-rule list with no gap and no
  renumbering. The installer writes the managed block from `AGENTS.md`, writes `CLAUDE.md` as `@AGENTS.md`, and copies
  the third file into `.agents/skills` and `.claude/skills`. Every other package byte is identical to B. In the
  installed tree the edit also changes, deterministically, the managed-block `sha256=` digest in `AGENTS.md` and the
  derived `_shared` hash in both `.devlyn-install.json` files, as in 0258 and 0259.

No other file in the package names Saint-Exupéry or carries the sentence (checked in B outside `node_modules`). In
0259's transcripts there were 0 Skill calls, and one B cell (F10 c021) and no C cell read `runtime-principles.md`;
the block reaches the model through `CLAUDE.md`. 0260 reports the same exposure counts and excludes no cell for them.

The treatment is the rule as the package carries it, in the loaded instructions and the two installed skill copies.
There is no bare arm. 0257's A and 0258/0259's B and C results are historical references only, never a comparison.

Engine: claude only, 0259's route (Claude Code 2.1.281, `claude-opus-5-5`, image `devlyn-0256`), prompts, assessors
and grading.

## Panels and replicates

| Task | Replicates per arm | Cells | Role |
|---|---:|---:|---|
| F10 | 16 | 32 | primary |
| D3 | 16 | 32 | secondary |
| SMOKE | 1 | 2 | qualification, outside every sum |

The 64 measured cells are the verdict slots. All are fresh.

**Power** is 0258's (exact one-sided Fisher at Holm's first threshold 0.025, n = 16 per arm). P1: B rate 0.05 against
C rate 0.5 gives ≈ 0.78; against 0.3, ≈ 0.31. P2: bypass rate 0.625 (B) against 0.25 (C) gives ≈ 0.44. A rule that
explains only part of the effect can therefore read NOT_IMPLICATED; that reading is not evidence of no effect.

## Schedule

0259's, byte for byte. Serial, one cell at a time. A block is one (task, replicate); its arms run back to back, BC on
odd replicates and CB on even ones. Order: SMOKE (B, C); then r = 1..16, D3 first, then F10. Results are reported by
replicate and by account fingerprint.

## Endpoints (frozen before SMOKE)

0259's, unchanged.

**P1 (primary): F10 malformed-JSON probe.** 0257's `f-malformed-json.js`, run by `judge.py probe` on every F10 tree
after grading. Event: class `json_error_400`. Non-events: `html_400`, `other`. A missing or `unassessable` result is
rerun once on the same tree; a second one is unresolved. Test: one-sided Fisher, C higher.

**P2 (secondary): D3 public-parseOptions witness**, 0258's `d3-parseoptions-override.js` byte for byte (sha256
`5e706105…`), run by `judge.py run` twice on every D3 tree in both arms. Exit 0 = public path, exit 1 = bypass
(reproduces), exit 2 or two passes that disagree = unresolved. Test: one-sided Fisher, C lower.

P1 and P2 form a two-test Holm family at α = 0.05 whose size stays 2. A test whose adverse direction is absent has
p = 1. An unresolved P2 enters the adjustment as p = 1 and prints `P2:NOT_READY`.

**Reported, never in a test:** completion per task (0257 grading), oracle rows, assessor findings, cost per success
(0257 accounting), skill exposure per arm, how many F10 reports say a malformed body gets Express's default 400, and
how many D3 bypass reports disclose the public-override limit.

## Decision

0259's rules; the two implicating headlines are renamed for a rule.

**Readiness.** P1 is read only when all 32 F10 slots have verdicts and assessable probe results; P2 only when all 32
D3 slots have verdicts and resolved witness results. An unresolved STOP or instruction assertion, or a missing
mandatory judgment, makes the whole run NOT_FINISHED.

**Headline** (first match):

1. **NOT_FINISHED:** the run, or P1, is not ready. No p-value is emitted.
2. **RULE_IMPLICATED:** P1 is Holm-rejected.
3. **RULE_PARTIAL:** P2 is ready and Holm-rejected, and P1 is not rejected.
4. **NOT_IMPLICATED:** neither test rejects (P2 ready).
5. **P2_UNRESOLVED:** P1 is ready and not rejected, and P2 is not ready.

**Listed beside the headline, not changing it:** `C_UNSAFE[<cells>]` (a C cell with a false completion, a scope
violation or user-data harm, with B's counts beside; the audit covers every attempt in both arms),
`C_COMPLETES_LESS[<task>]` and `B_HANDLES[<k>/16]`.

Token: `0260:claude=<headline>,P1:<C>/<B>(<p>,<adj>),P2:<C>/<B>(<p>,<adj>)[<listed flags>]`; a test that is not
ready prints `P1:NOT_READY` or `P2:NOT_READY`.

## Prediction (frozen before SMOKE)

1. P1: C has more JSON-400 F10 trees than B, and P1 is Holm-rejected. Scored when P1 is ready.
2. B's own P1 count is at most 3 of 16. Scored when P1 is ready.
3. P2: C has fewer reproducing D3 trees than B (direction only). Scored when P2 is ready.

## Apparatus (0259's, with named changes)

Unchanged from 0259: image and its ID check, the B package and integrity, D3/F10 task inputs and the task override,
`cell.py` lifecycle, routes, assessors, prompts, usage accounting, credentials and renewal rules, fault rules, the
probe and the witness, the probe rerun rule, the two-pass witness rule, 0257's amendments 1–3, the B-equals-0257
installer and Claude-form checks, caps 95/95 from the first dispatch and the deadline 14 days after the first SMOKE
dispatch.

0259's two amendments are part of the apparatus from the start, frozen before SMOKE, and apply to both arms alike:

- **Amendment 1:** `quota.py`'s retry-only authentication shape. A cell whose execution shows it ends STOP as a
  shared account fault during the run, and the driver archives it and reruns it in the same slot. 0259's
  `reclassify.py` is not copied: with the shape in the classifier from the start, it has nothing to reclassify.
- **Amendment 2:** `judge.py` mounts its snapshot copies and a sha256-checked witness copy (always the only file in
  `/witness`) from `NX01_0260_JUDGE_SCRATCH` when that variable is set, an absolute path under `/private/tmp`.
  Docker's `/Users` bind mounts worked again on 2026-10-27, so the variable is set only if the hang returns; the
  result says which grading calls used it.
- **A container that never starts is not an attempt.** In 0259 a hung create was stored as an unassessable probe
  and spent the rerun. `judge.py` now creates each probe and witness container with `docker create` (60 s limit)
  and runs it with `docker start -a` under 0259's run limits, then reads the container's state from Docker. A
  create that fails or exceeds its limit, a container Docker reports as never started, or a state that cannot be
  read stops the call before that attempt is recorded, and names the cell; the operator fixes Docker or sets the
  scratch variable and repeats the call, which runs only the missing attempts. Every completed attempt is written
  at once and never replaced. Every stopped call is reported. For a started container, the exit code is the one
  Docker records for the process; a failure or timeout after the start keeps 0259's meaning (probe
  `unassessable`, witness exit 2).

Changes:

1. **Edit** in `control.py` and `instructions.py`: the two ordered C edits above instead of 0259's seven. The
   package-diff test and the qualification checks (Claude forms differ only by the edit; installed `AGENTS.md` by the
   edit plus the managed-block digest; both installed `runtime-principles.md` copies only by the edit) use it
   unchanged otherwise.
2. **Names:** experiment `0260`, runtime root `~/.local/share/nx01/0260-live`, runtime variables `NX01_0260_RUNTIME`
   and `NX01_0260_JUDGE_SCRATCH`, the token prefix and the headlines above.
3. **Witness and probe files** copied from 0259 byte for byte; a test pins both sha256 values. 0259's severe-finding
   witnesses are not copied; severe findings get witnesses written for the claim on the cell's own tree.

## Grading

0259's: public checks, hidden oracle rows, dual blinded assessors, the final-report audit for false completion, scope
and user-data harm on every attempt (0233 m24 line), and severe findings dispositioned with witnesses on the cell's
own tree. Root prepares judgments; Astra ultra and Grok 4.7 verify them read-only. Two 0259 lessons are binding:

- The audit reads every report in full for mechanism claims and also searches every report broadly for claim words
  (for example "JSON object", "single process", "atomic", "guarantee"), because a delegated audit and a narrow search
  both missed c014.
- A witness checks every acknowledged item in every round it drives, so a mixed round of successes and failures
  cannot hide a lost write.

## Qualification (before SMOKE)

- 0259's unit tests, adapted to the new edit and names, all passing; 0259's and 0258's suites still pass, run
  separately.
- The B→C package diff is exactly the edit in the three files; a B missing any source text of the edit, or holding one
  twice, fails.
- The witness, unchanged, run twice each in the cell image on 0257 trees: exit 1 on d241 and d049, exit 0 on d002 and
  d017. The probe classifies 0256 c01 as JSON 400 and c02 as HTML 400. These trees qualify the instruments only.
- SMOKE for both arms; `seal-forms` records qualification PASS.

## Interpretation limits

- Two exposed tasks; one rule; claude only. A positive result implicates the Saint-Exupéry line as a whole, as one
  cause of the F10 behavior, not the only one; it does not say which of the line's sentences matters (the aphorism
  or the definition of done), and says nothing about Codex or other tasks. P1 and P2 measure behavior,
  not the model's reasons.
- A negative result does not clear the rule: power is limited. The other lines that favor small changes stay in both
  arms (the No-overengineering principle, and First-principles' "push back when a simpler path is genuinely better"),
  as do the delivery text, the skill listings and the settings. If those lines substitute for each other, every
  single-line deletion can read NOT_IMPLICATED; this experiment cannot detect that, and a joint deletion would be a
  separate design.
- Model drift since 0257 is not controlled; there is no concurrent bare arm. B's P1 count was 0/16 in 0258 and 2/16
  in 0259.
