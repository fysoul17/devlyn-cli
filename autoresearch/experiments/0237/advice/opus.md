# 0237 design decision: refutable checks

## 1) Candidate: "refutable checks" (one rephrase inside No guesswork)

**Span:** `AGENTS.md:15`. Apply the same change to that sentence in `CLAUDE.md` and in both `_shared/runtime-principles.md` copies, the four files 0235 edited. The pack diff should contain this sentence only.

Old:
> State the falsifiable prediction BEFORE the experiment; record raw results AFTER.

New:
> State the falsifiable prediction BEFORE the experiment (the result that would prove you wrong) and run one able to produce it; rerun an unchanged passing check only to test a named nondeterministic failure. Record raw results AFTER.

"Retroactive prediction edits are dishonest." stays. Prediction-before, raw-results-after and hypothesis-tied repetition all survive.

**Behavior change:** before claiming a property such as bounded, exclusive or restored, the model runs the case that would break it.

**Causal prediction:**
- 0233 d09 and 0235 r03/r08 claimed "fails instead of hanging" (`0235:91`). A writer that exits before opening the FIFO refutes that, which is exactly `d4-writer-death`.
- d36's lock-before-mkdir claim (`0233:181`) is refuted by `i0185-mkdir-before-lock`.
- d40's 30 unchanged reruns should become one forced interleaving, so output and wall per success drop.

**Why this differs from 0233/0235:** both added obligations, a domain checklist and a done criterion. 0235's finals then claimed bounds they never exercised. This candidate adds no domain, scope or done rule. It changes only what counts as evidence.

**Credibility:** the mechanism is credible for the false-claim class (D4, I0185) only. I have no credible mechanism for D3/F10.

## 2) Strongest case against

0235 showed that verification wording yields verification *claims*. V may report "ran the refuting case" against a mis-built falsifier, for example a writer that dies after opening the FIFO rather than before. That produces more confident false completions, which is a REJECT condition. Other risks:
- Prediction ritual and fault-injection harnesses could raise easy-task tokens.
- Harnesses could be left behind as scratch orphans.
- The model could add test hooks to production code.
- With D3/F10 untouched, completions may not clear "> B".

**On the root's theories:**
- **Tracing non-local contracts is the weaker option.** d47-D3 was not a discovery failure: B found the override and discounted it ("no known caller relies on it", `0233:183`). 0233 C's guide named target aliases (`0233:55–56`), yet C scored terminal-alias 0/2 against B's 2/2 (`0233:178`).
- **Citation deletion** has no observed mechanism.
- **The efficiency claim** rests on one transcript (d40) and is unproven until reruns are counted.

## 3) Test

**Screening** (Claude, exposed development tasks):
- **Arms:** A native, B = current `975a01e6`, V = B + delta.
- **Cells (15):** D4 ×3 for A/B/V; I0185 ×2 and E1 ×1 for B/V.
- **Witnesses, unchanged:** `d4-writer-death`, `i0185-mkdir-before-lock`, terminal-alias.
- **Efficiency lane:** wall, input and output per correct completion, with failures charged. Also a pre-registered count of unchanged reruns after a green result, with B's baseline taken from the retained 0233/0235 transcripts.

**Reject immediately on any of:**
- a V false completion
- V completions ≤ B
- V wall, input or output per success above B
- a scope, orphan or production test-hook violation

A gain without an executed refuting case in V's transcripts is unexplained and is not admitted.

**Admit to confirmation** only if none of the reject conditions fires.

**Confirmation** uses fresh tasks, frozen with witnesses before any run:
- a bounded-wait worker that dies before rendezvous
- lock, rollback and release through a terminal alias
- a numeric boundary where the supplied tests pass and a 2\*\*53 or 10\*\*400 probe decides (`0175:52–55,73–77`)
- a public-override guard

Run B vs V ×2 on both engines, since `AGENTS.md` also reaches Codex, and A on Claude. Add the B5 (`0223:12–13`), DB-silent-catch and E1/E2 guards. Decide with `decide.py` unchanged.

## 4) Saturation and pair license

Each admitted delta becomes the new B. Solo stops for the tested hypotheses when both of these hold:
- two consecutive single deltas, each grounded in a transcript mechanism, are rejected at screening;
- the best block's completions are non-inferior to native A on Claude.

The second condition fails today. A scored 4/8 and 3/4 against B's 2/8 and 1/4 (`0233:170–171`), so instruction harm remains. When both hold, record "saturated under H1–Hn on panel P", not a model ceiling. A new transcript-observed mechanism reopens solo.

**Pair is licensed by a residual class with two properties:**
- **Blind spot, not a discount:** no solo arm, native included, ever forms the refuting hypothesis.
- **Formed elsewhere:** another engine or a fresh context did form it on matched artifacts. Existing examples:
  - Codex caught 2\*\*53 where Opus passed (`0175:52–55`).
  - 0236's Codex assessor blocked both defect-reproducing trees that Claude passed (`0236:197`).
  - A fresh VERIFY found the alias and release classes (`0185:35–46`).

The recipe must change the element that failed, which rules out finding feedback (`0236:184`) and unconditional gate+retry (`0236:211`). One that would qualify: the other engine writes refuting cases for the final report's claims, triggered only on that class.

## 5) Next change

Commit V as a child of `975a01e6` with this delta in the four files. Verify the pack diff, then run screening.

**Fallback (never combined):** delete "Most 'we have to do X' assumptions are habit, not necessity." from `AGENTS.md:24`.
- **What it targets:** that sentence licenses treating a known contract as optional, which is the D3/F10 pattern ("the request didn't ask for one", `0233:183`).
- **What stays:** the surfacing duties.
- **Why not `:25`:** its "learned failure mode" clause fits better, but 0235 closed that line (`0235:82`).