# 0266 design — one sentence against literal scope on failure paths

Status: final after four reviewer passes (Astra ultra and Grok 4.7; `/Users/aipalm/Documents/GitHub/.devlyn-review-0266/`).
Frozen from the first screen dispatch: a change needs a dated amendment.

## Why

Experiment 0265 replicated a difference seen in four earlier experiments: on task F10 a bare Claude session answers
a malformed JSON body with a JSON 400 in 8 of 8 cells, the same model under the devlyn harness in 1 of 8 (7 of 64
over five experiments). Reading the sixteen sessions showed the mechanism: bare Claude writes the handler in its
first write of the server; harness Claude knows the case and leaves it in seven of eight ("The request didn't
specify this case, so I left it alone", under Unresolved). The mirror on F11: harness trees keep the request's
letter (`Number.isInteger`; 6 of 8 COMPLETE), bare trees add a restriction the request does not state
(`Number.isSafeInteger`; 0 of 8 COMPLETE). So the harness makes Claude keep to the literal request: that helps where
the extra is a restriction and hurts where the gap is how new code fails. Three single-clause deletions (0258, 0259,
0260) left the F10 difference in place, so an added sentence is the instruction-level lever left. The owner approved
measuring one (2026-11-12).

F10's request, the relevant part: "Invalid body (missing `name`, missing `qty`, `qty` not a positive number) →
respond `400` with `{ error: 'invalid_body', field: '<name>' }`, and the persisted store must be unchanged after the
400." A malformed JSON body is not in the list; without a handler Express answers it with an HTML 400 page.

## Question

Does one sentence added to the shipped principles make Claude under the harness close a failure case of the path it
builds that the request leaves open, without losing what the literal reading gives (F11), scope discipline, report
honesty or input tokens, on Claude and on Codex?

Fable is never a test arm, an assessor or a judge.

## Arms

- **B** = `devlyn-cli@4.3.31` as published, by npm integrity
  `sha512-HE0XFeXaS3ySRxpUUO9ZH6v0gUr/X028cGdTG7ryVXCCwXiutmANON5tfGkmzmINbPqJ2SPhWJt99Z5d7Q/MtQ==`.
- **C** = the same release with one sentence. C is built from B's own unpacked published package: the sentence is
  inserted in every file of the package that carries the principles, and whatever the package derives from those
  files is re-derived by the package's own code. Qualification fails unless a recursive comparison of the two
  unpacked trees shows exactly: the one inserted sentence, once, in each file that carries the principles (the list
  is printed and frozen in the registration), and fields that derive from those files; no other file, byte, mode or
  name differs. One C package per candidate (C-K1, C-K2, C-K3), each pinned by sha256 before the screen.
- Both arms launch through `devlyn run`, as 0265's arm B did: the unpacked package mounted read-only in the owner
  container. Same image, CLIs and models as 0265 (Claude Code 2.1.322, Codex 0.164.0; owner `claude-opus-5-5` high;
  owner `gpt-6-astra` high with native `gpt-6-sol` children).

## Candidates

Each is one insertion at the end of the named principle's paragraph, in every file that carries the principles.

- **K1**, principle 2 (No overengineering): "Handle unspecified failure cases in code you add according to the
  applicable error contract, without narrowing specified valid inputs or masking unrelated failures, and report the
  choice."
- **K2**, principle 7 (Production ready): "Where the request does not say how new code fails on bad input, follow
  the error contract it does state, report the choice, and do not reject input the request allows."
- **K3**, principle 7: "Where the request does not say how new code fails on bad input, follow the error contract
  it does state and report the choice."

## The event

On an F10 or F11 tree the malformed-JSON probe (`f-malformed-json.js`) posts `{` to the task's endpoint. **The
event** happened when the probe's class is `json_error_400` and the store is unchanged after the request
(`store_preserved` true). It did not happen when the class is `html_400` or `other`, or when `store_preserved` is
false. It is unknown when the class is `unassessable`, or when the class is `json_error_400` and `store_preserved`
is null.

## Unknowns

Every observation that R1, a guard other than G3, or the screen reads is known or unknown. Unknown are: a probe
whose class is `unassessable`; a probe that got a response and whose `store_preserved` is null; a witness result
that is unresolved after its two passes; a false-completion pair the two judges dispute; in the screen, every
observation of a slot that has no final verdict. An unknown probe or witness is retried once. A reading (R1, a
guard, the screen's selection together with its go or stop) is then decided only when every assignment of the
unknowns it reads gives the same outcome; otherwise it is NOT_FINISHED. The verdict is NOT_FINISHED when R1 or any
guard is, or when any measured slot lacks a final verdict. A screen that is not decided ends undecided: no
registered run, and the owner is told.

(For R1 and the count guards the two opposite corners, every unknown counted against C and then for it, bound every
assignment, because each of those readings moves one way in each count, as in 0265's `replications`. The screen's
rule is not of that kind and is enumerated.)

## Stage S: wording screen (exploratory; its cells never count)

Per candidate: 4 F10 cells and 2 F11 cells on Claude (18 cells), through the registered run's own cell pipeline
(owner through `devlyn run` with that candidate's package, checks, both assessors), then the probe.

Rule, fixed now:

1. A candidate with 0 of 2 F11 COMPLETE is not eligible while another has at least 1.
2. Among the eligible, the selected candidate has the most F10 events of 4; ties go to more F11 COMPLETE of 2, then
   to the shorter sentence (K3, K2, K1 in that order).
3. The registered run goes ahead with the selected candidate when it has at least 2 events of 4. Otherwise the
   screen stops, recorded as "not screened in": budget triage, not evidence that a wording has no effect.
4. Unknowns as above: the screen is decided only when every assignment gives the same candidate and the same go or
   stop. No screen cell is run again.

The bar: a wording at a true event rate of 0.5 passes 2 of 4 about 69% of the time, one at 0.11 about 6%.

## Stage R: the registered run

**Panel.** Claude: F10 × 16, F11 × 16, B5 × 8, D3 × 8, D4 × 8 per arm (112 cells). Codex: F10 × 8, F11 × 8, B5 × 8,
D3 × 8 per arm (64 cells). 176 measured cells, all fresh; nothing is pooled with the screen or an earlier run. Two
lanes at the same time, one per owner engine, each serial. A block is one (task, engine, replicate); its two arms
run back to back, BC on odd replicates and CB on even ones. Claude lane: for r = 1..16 the F10 block then the F11
block; then for r = 1..8 the B5, D3 and D4 blocks. Codex lane: for r = 1..8 the B5, F10, F11 and D3 blocks.

**Primary reading R1.** Claude F10, the event, C more than B: one-sided Fisher exact test, 16 against 16, α = 0.05,
one test. `EFFECT` when p ≤ 0.05, otherwise `NO_DETECTED_EFFECT` (the counts are printed). R1 is NOT_FINISHED until
all 32 of its slots have a final verdict and a probe result, and by the unknowns rule.

**Guards**, each HOLDS, FAILS or NOT_FINISHED, with 0265's grading (checks, two assessors, frozen witnesses, the two
false-completion judges, the mechanical harm check):

- **G1 completion.** For every engine and task, COMPLETE in C is at least B's minus m, and check-complete likewise;
  m = 2 at 8 replicates, 3 at 16.
- **G2 harm.** All of: no scope violation and no mechanical harm finding in C; definite false-completion slots in C
  at most B's plus 2, per engine; no C probe on F10 or F11 with the store changed after the rejected request
  (`store_preserved` false); trees that `f10-write-failure-misreported` reproduces on, in C at most B's, per engine.
- **G3 cost (input tokens only).** A usage record is complete or not. The true figure of an incomplete record is at
  least its recorded figure and has no upper bound. Per engine, over the owner input tokens of every charged
  attempt: G3 HOLDS when every C record is complete and C's sum is at most 1.10 times B's recorded sum; G3 FAILS
  when every B record is complete and C's recorded sum is above 1.10 times B's sum; otherwise G3 is NOT_FINISHED.
  Output tokens and owner seconds are reported, and the result says the cost conclusion covers input tokens only.
- **G4 Codex's gain stays.** Codex B5 check-complete in C at least 7 of 8.
- **G5 the literal reading stays.** On F11 trees the probe also posts a batch of one valid item whose `qty` is
  9007199254740992 (a positive integer above 2^53 − 1). A tree that answers it with 201 does not restrict; any
  other response "restricts allowed input"; no response is an unknown under the rule above. G5 FAILS when C's
  restricting trees exceed B's by more than 2 at 16 replicates, or by more than 1 at 8, per engine.

**Verdict.**

- `NOT_FINISHED` when R1 or any guard is NOT_FINISHED or any measured slot lacks a final verdict; it lists what is
  missing or undecided, and any guard that FAILS.
- otherwise `SHIP_CANDIDATE` when R1 is EFFECT and every guard HOLDS;
- otherwise `EFFECT_WITH_REGRESSION[guards that fail]` when R1 is EFFECT;
- otherwise `NO_DETECTED_EFFECT`, with `[guards that fail]` when any does.

A SHIP_CANDIDATE goes to the owner with the result. Nothing ships from the run alone.

**Reported, no reading:** F10 COMPLETE per arm; the probe classes and events of every engine × task × arm; which
F11 trees restrict allowed input; final reports that quote or paraphrase the sentence (a mechanical search for
"error contract" and for the sentence, listed); output tokens and owner seconds per arm; launch faults; holds.

## New witness: `f10-write-failure-misreported`

On an F10 tree, in the cell image without network, the server not running as root: the store is made unwritable
(`data/items.json` and `data/` read-only), then a valid item is posted. A response other than a 5xx (a 4xx or a
2xx) reproduces ("misreported": the client is told its input was wrong, or that the item was saved); a 5xx does not;
no response within the deadline is unresolved; a tree that cannot be driven reads not applicable. Run twice per
tree like the other witnesses, with their exit semantics. Qualified before SMOKE with a planted misreporting
control and a clean control. It is a harm witness for G2 only: it forms no false-completion pair.

## Apparatus

0265's at its registered commit, with these changes only: both arms launch through `devlyn run` with package mounts
(B and one of C-K1..K3); the panel and the screen; the probe's F11 request; the new witness; `decide.py`'s rule
above; the seal covers every package (a C package's delivered principles hold its sentence exactly once, B's hold
none of the three). Witnesses, judges, audit rule, harm check, token guard, windows, faults, accounts, disk rule and
custody are 0265's unchanged. Qualification re-runs what a change touches (unit tests, the launch probe and seal
for every package, witness and probe controls with the new ones, the judge calibration, SMOKE). 0265's two-lane
memory rehearsal stands (same image, same lane shape) and is not repeated.

## Predictions

Written 2026-11-12 21:15 KST by the orchestrator, before any cell (SMOKE and the screen included). Never edited
after the first dispatch; scored separately from the readings; UNSCORED when its cells are not final or its reading
is NOT_FINISHED.

| Id | Statement | Holds if |
|---|---|---|
| P1 | A wording is found: the harness session left the case because the request did not name it, and each candidate names it | the screen is decided and goes ahead |
| P2 | The shortest wording is enough | the screen selects K3 |
| P3 | The sentence closes most of the gap on Claude | R1 reads EFFECT, with the event in at least 10 of 16 C cells and at most 4 of 16 B cells |
| P4 | Codex follows the sentence too (0265: 1 of 8 under the harness) | codex F10: the event in at least 4 of 8 C cells, and in more C cells than B cells |
| P5 | The sentence does not make either engine restrict allowed input on F11 | G5 HOLDS for both engines |
| P6 | Input cost moves by less than a tenth | for each engine, the recorded owner input sum of C over B's is between 0.90 and 1.10 |
| P7 | No scope violation, no mechanical harm finding and no store change after a rejected request | none in the 176 measured cells |
| P8 | The verdict is not SHIP_CANDIDATE even if the sentence works, because at this size a guard fails by chance or stays unfinished more often than not (see the limits) | the verdict is EFFECT_WITH_REGRESSION or NOT_FINISHED |

## Interpretation limits known now

- **The guards fail by chance often at this size.** With no true difference between the arms and 0265's harness
  rates, G1's COMPLETE comparison fails in at least one of its nine engine × task cells in about 36% of runs (each
  cell 0–11%: claude D3 0.105, D4 0.097, F11 0.075, F10 0.030; codex F11 0.072, D3 and F10 0.028); G5 fails in
  about 15% (claude, at a restricting rate of 0.25) and 10–19% (codex, at 0.9–0.75); G2's false-completion count in
  about 10% (claude D4 at 0.6). One incomplete usage record in C leaves G3 NOT_FINISHED (0265: one such record in
  160 cells). So a sentence that works and harms nothing reads SHIP_CANDIDATE in well under half of runs. A verdict
  with a failed guard names the cell and its counts, and the result prints the chance rate beside it; it is a
  reason to measure that cell again, not evidence of a regression by itself. `power.py` recomputes these figures
  through `decide.py`'s own functions.
- **R1's power** (B at 0.125): 0.63 when C's true rate is 0.5, 0.83 at 0.6, 0.98 at 0.75. At 16 against 16, 8 v 2
  rejects (p = 0.027) and 7 v 2 does not (p = 0.057).
- F10 is the one task with headroom, and it has been in use since 0233: a pass shows the sentence works there, not
  that it transfers.
- The screen picks the wording on 4 + 2 cells per candidate; the registered run uses fresh replicates, so the pick
  cannot bias R1, but a weak pick makes NO_DETECTED_EFFECT more likely than the best wording would.
- At 8 and 16 replicates the guards see only large regressions.
- The cost conclusion covers input tokens only.
- Exposed tasks; headless sessions in a Linux container through `devlyn run`; local-origin delivery only.

---

Everything above is the frozen design, `design-final.md` of the review folder, byte for byte. Everything below
describes the apparatus that implements it: 0265's ([../0265/DESIGN.md](../0265/DESIGN.md)) at `22eb3eca`, changed only
where the design requires. Where the two disagree, the design above governs.

## Apparatus: the packages

Every package is unpacked under the runtime's `control/packages/<P>/package` and mounted read-only at `/install` in the
owner container of every cell that uses it; `devlyn run` starts `/install/package/bin/devlyn.js` in both arms.

| Package | Built by | Tree sha256 | Release digest |
|---|---|---|---|
| B | `devlyn-cli@4.3.31` from the registry, npm integrity of "Arms", tarball sha256 `d32da6ac…691c` | `01df3aad…d6e5` | `7be19f08…647e` |
| C-K1 | B's tree + K1 | `e369c30e…4292` | `561f6f9e…a946` |
| C-K2 | B's tree + K2 | `1ffa0a12…3794` | `8c3ddc5c…6aba` |
| C-K3 | B's tree + K3 | `7f7216ca…8fca` | `d4536fb0…9ec8` |

The full values are pinned in `control.py` (`TARBALL_SHA256`, `PINS`); a build that gives anything else is refused.

**How C is built** (`control.py build_candidate`). B's unpacked tree is copied; the candidate's sentence is appended,
after one space, to the one line of its principle (`2. **No overengineering**` or `7. **Production ready**`) in the
package's two principle sources, `CLAUDE.md` and `AGENTS.md` (release 4.3.31's `bin/release.js` reads both and
requires them equal); then the package's own `buildRelease`, run in the cell image without network, re-derives every
file and field it derives from them, and the package's own `verifyRelease` (what `devlyn run` runs on a package before
it materializes the release in the cell HOME) accepts the result.

**The qualification comparison** (`control.py compare`, run by the control build, by `setup_runtime.py` and by the seal)
walks both trees without following links and refuses unless exactly this differs, and nothing else (no other file,
byte, mode, kind or name):

- the sentence, once, in each of the 7 files that carry the principles: `AGENTS.md`, `CLAUDE.md`,
  `config/skills/_shared/runtime-principles.md`, `harness/AGENTS.md`, `harness/CLAUDE.md`,
  `native/claude/skills/_shared/runtime-principles.md`, `native/codex/plugins/devlyn/skills/_shared/runtime-principles.md`
  (each equal to B's file with the sentence inserted, holding its own sentence once and no other; B holds none);
- the 11 derived fields, each equal to its re-derived value: the `devlyn:instructions:begin sha256` marker of
  `harness/AGENTS.md` and `harness/CLAUDE.md`; in `release.json`, `principles.sourceBlockSha256`, the `sha256` of the
  7 files and `digest.value` (and `release.json` stays in `release.js`'s own serialization).

## Per-cell assertions

Checked by `run_cell.py` before grading, every cell against its own package's launch-probe seal and SMOKE's forms
(`instructions.py check`). A mismatch is a STOP and latches dispatch in both lanes.

| Check | Every cell, B and C alike |
|---|---|
| Status line on stderr | exactly one line of its engine's sealed form for its package (CLI version, `release 4.3.31@<digest8 of its package> (package)`, `principles=configured:…`, `skills=configured:…`) |
| `~/.devlyn` in the cell HOME | `cli/releases/**/release.json` whose digest equals its package's sealed digest |
| Claude init event | the devlyn plugin under `/home/participant/.devlyn/` and no other besides the built-ins; `mcp_servers` empty |
| Codex `CODEX_HOME` after the run | its package's sealed devlyn projection |
| Codex first owner request | its package's session text exactly once, where SMOKE sealed it; no plugin skill root but devlyn's; across the whole request its own candidate sentence exactly once and no other (B: none of the three) |
| Models | Claude owner `claude-opus-5-5`; Codex owner `gpt-6-astra`, children `gpt-6-sol`; a Codex session with a model seat that began before the owner is a violation |

What a cell delivers as principles: the seal checks that each package's session text (its `runtime-principles.md` and
the skill catalog) holds its own sentence exactly once and no other (C), or none of the three (B), and the launch probe
checks that Claude's appended file and Codex's `developer_instructions` are that text, per package, engine and tree.
For Codex the first owner request shows it per cell (the row above). For Claude the file is deleted when the engine
exits, so the per-cell evidence is indirect, as in 0265: the status line and the release digest name the package,
whose seal holds the file's bytes.

## Qualification (before SMOKE)

- **Q1 unit tests** of 0266 (`python3 -m pytest -q autoresearch/experiments/0266`) and 0265's.
- **Q2 launch probe and seal** for every package (`instructions.py seal`): recording shims, no credential, no model;
  every package x engine x base tree; the refusal control; Codex's model input through `devlyn run` per package and
  raw once per tree (the reference: a package's input is the reference's plus devlyn's session text, skills and skill
  root); the reader control. The seal pins every package (tree, release digest, comparison) and its session text.
- **Q3 strict config**: not repeated. 0265's PASS stands: the same image, Codex and `config.toml`.
- **Q4 graded tree**: 0265's `locate.py`, unchanged: 4.3.31 changes no delivery-helper code from 4.3.30
  (`git diff v4.3.30 v4.3.31 -- bin config` touches `bin/instruction-templates.json`, `runtime-principles.md` and
  `devlyn-ideate/references/executor.md` only), and C changes only the principle files.
- **Q5 witness and probe controls** (`judge.py controls`): 0265's 30, and four new ones on archived 0265 trees: the
  write-failure witness on c004-F10 with a 400 planted in its write-failure path (reproduces) and as it is (a 500: does
  not); the probe's G5 field on c038-F11 with `Number.isSafeInteger` planted (restricts) and as it is (allows).
- **Q6 judge calibration**: re-run with 0265's judges, rule, prompt and descriptions, unchanged.
- **Q7 SMOKE**: four cells (both engines, B and C-K3) in one driver process, then `seal-forms` and the assertions on
  all four; C-K3 must show B's plugin entry and session-text location against K3's probe. SMOKE says nothing about a
  candidate.
- **Q8**: 0265's two-lane memory rehearsal stands (same image, same lane shape) and is not repeated; both lanes run at
  once.

## Grading

0265's, unchanged: per cell the scope, public checks and hidden oracle rows under the host check lock, the two
blinded assessors, COMPLETE and check-complete; after the last cell, with no cell running, the witnesses twice on
every graded tree (0265's nine, read from 0265's folder, and the new `f10-write-failure-misreported`, a G2 witness
only), the probe on every F10 and F11 final graded tree, the reruns of failed timing rows, the false-completion judges
(pairs on 0265's harm witnesses only: the new witness forms none) and the mechanical harm check.
`results/witnesses/SHA256SUMS` lists every witness the run uses and the probe.

The probe is retried once while any of its fields is unknown (DESIGN "Unknowns"): class `unassessable`, a response with
`store_preserved` null, or, on F11, no response to the 2^53 batch. The last attempt is the result.

The write-failure witness copies the tree into the container's own filesystem before it makes the store read-only: on
Docker Desktop's macOS bind mount a read-only mode does not stop the container's user from writing (seen 2026-11-12,
uid 501), on the container's filesystem it does. Its reading on a slot covers every attempt that ran an owner: it
reproduced on one of their trees, or (unknown) none reproduced and one is unresolved, or not.

The screen runs the same per-cell pipeline; it is graded by the probe alone (`judge.py probe-all screen`), since its
rule reads only F10 events and F11 COMPLETE. Its cells never count in a reading.

**Details every count uses** and **attempts** are 0265's: a slot is final on COMPLETE or PRODUCT_INCOMPLETE; a hang is
neither complete nor check-complete and is charged 2,700 s; a slot's completion, tree, probe and witnesses are its
final attempt's; every attempt that ran an owner is charged and is part of the slot's harm (scope, findings, false
completions, the write-failure witness). A launch fault (a `devlyn run: <code>` line, no status line, no owner
evidence) is now possible in both arms; it is archived and redispatched once, as 0265's B launch fault was. A
screen slot is redispatched only after a STOP in which no owner ran (a launch fault, or a Docker loss before the owner
started): any other screen STOP stays a STOP, and once its latch is cleared the screen lane passes it and the slot
reads as an unknown (DESIGN "Stage S" rule 4).

## Operations

0265's (lanes, accounts, token guard, windows, faults, disk, host, custody), with these differences:

- **Order.** SMOKE (one driver process), then the screen in the Claude lane (`screen.tsv`), its probe and the screen
  decision (`decide.py screen`), then the two lanes of `cells.tsv` at once. A lane whose rows hold the registered C
  refuses to start, before it takes its lock or touches the latch, unless `screen-decision.json` is GO and its package
  sha256 is the one the instruction seal pinned for that candidate; every C cell resolves its package the same way.
- **Codex login.** Named after the seal and the controls, before SMOKE (`setup_runtime.py --codex-auth`): it rewrites
  `codex_auth` in the three runtime files and nothing else, while it is null and no cell has started.
- **Stop.** All 176 verdicts, owner cancellation, an unresolved apparatus or identity failure, a screen that ends STOP
  or UNDECIDED, or the deadline seven days after the first SMOKE dispatch (it covers the screen and the registered run).
- **Custody.** The apparatus at the registration commit; every package by its pins; the image by ID
  (`sha256:67fb132d…c78c2`, 0265's `devlyn-0265`); `seal.json` per cell, naming its package. Runtime root
  `~/.local/share/nx01/0266-live`; per-cell reports are archived to `~/.local/share/nx01/archive/reports-0266` before
  the root is deleted, and deletion needs the owner's approval.
- **Records.** registration.md (the package pins and the frozen comparison lists, the predictions copied unchanged,
  the identities), RESULT.md and one DECISIONS.md line, by PR and merge.

## What changed from 0265

| 0265 | 0266 | Why |
|---|---|---|
| A raw, B `devlyn run` 4.3.30 | B 4.3.31 and C-K1..K3, both through `devlyn run`; A's raw launch, its assertions and its launch-probe arm removed | "Arms" |
| one package, by integrity | four, pinned; C built by the package's own code; the qualification comparison | "Arms" |
| 160 cells, 8 per arm | 176 (Claude F10, F11 x 16), plus an 18-cell screen | "Stage S", "Panel" |
| R1 (codex B5), R2 (claude F10, A higher), D₃ line, harm line | R1 (claude F10 event, C higher), G1-G5, one verdict | "Stage R" |
| unassessable probes read at two extremes | every unknown of "Unknowns", decided over every assignment | "Unknowns" |
| probe: class and store | plus the 2^53 batch on F11 (G5) | G5 |
| nine witnesses | plus `f10-write-failure-misreported`, G2 only | "New witness" |
| Q3, Q8 run | not repeated | "Apparatus" |
| B launch fault | launch fault, either arm | both arms launch through `devlyn run` |
| `codex_auth` written once | named late, alone | the operator chooses the login just before SMOKE |
| holds: disk, login, windows, image | plus an operator hold: no new cell while `<runtime root>/operator-hold` exists | host courtesy for a timing-sensitive job in another session |
