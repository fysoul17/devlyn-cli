# Five Principles — operational, not aspirational

Every iteration must be checked against these five before it ships. Each principle has a concrete operational test — not a vibe, not a slogan. If a principle has no operational test in this file, it is decoration and gets cut on the next pass.

These principles live HERE (referenced from iteration files) rather than in CLAUDE.md because they are the contract for *evolving* the harness, not for *executing* it. CLAUDE.md is the doctrine the harness reads at run time; this file is the doctrine the iteration loop reads at change time. Different cadence, different audience.

These five principles serve the **outer goal** in [`NORTH-STAR.md`](NORTH-STAR.md). Read NORTH-STAR.md first if you are picking this up cold — it tells you what "passes" actually means in terms of the L0 / L1 / L2 layer contracts.

---

## 1. No overengineering

> **Surface assumptions; touch only what the goal requires.**

The smallest change that closes the hypothesis is the right change. Infrastructure built for a hypothetical future need is cost without value.

**Operational test (per iteration):**

- Diff size in lines is bounded by the hypothesis. If your change touches 200 lines but the hypothesis would be falsifiable with 30, justify the surplus or cut it.
- New abstractions (helper file, new schema field, new oracle script) require an explicit "this prevents which learned failure mode?" answer in the iteration file. If the answer is "future flexibility", reject.
- A skill prompt edit that adds a new bullet must point to a concrete, observed failure mode in a previous iteration. Speculative bullets are noise that bleeds attention.

**Failure mode this catches:** Karpathy's classic — the loop keeps adding mechanisms instead of measuring whether the existing ones are doing their job. We saw this ourselves with the steps 3+4 oracles built before the skill changes had a chance to demonstrate the simpler oracles were enough.

---

## 2. No guesswork

> **The hypothesis is falsifiable BEFORE the experiment runs. The decision is data-driven AFTER.**

If you can't write down what would refute the hypothesis, you don't have a hypothesis — you have a vibe.

**Operational test (per iteration):**

- The iteration file's "Hypothesis" section names the metric and the direction. Example: "F3 margin will move from −10 to ≥0 because the test-fidelity rule will catch the mock-swap pattern at EVAL." Direction + metric + mechanism. All three required.
- The "Predicted change" section is filled in BEFORE the benchmark re-runs.
- The "Actual change" section is filled in immediately after the run, raw numbers, no interpretation. Interpretation lives in "Lessons".
- A surprise outcome (predicted +5, got −2; or predicted +5, got +18) is itself data. Record it. Do not retroactively re-write the prediction.

**Failure mode this catches:** Cargo-cult iteration. "I'll change this because it feels cleaner" is not a hypothesis. The benchmark will agree with you sometimes by coincidence, and the harness drifts toward whatever the most recent person thought was clean.

---

## 3. No workaround

> **Fix root causes, even when a workaround is faster. Use the why-chain to find the level where the fix prevents recurrence.**

When a bug is non-trivial — recurring, cross-module, or a workaround is being considered — walk "why?" back until you reach the invariant being violated. Fix at that level.

**Operational test (per iteration):**

- For any iteration triggered by a bug or regression: the iteration file documents at least three "why?" steps in the Mechanism section.
- The fix lands at the deepest level the why-chain reached, not at the symptom level.
- An LLM-side workaround (silent catch, `any`, `@ts-ignore`, hardcoded fallback) appearing in the diff is a hard reject — even if the benchmark margin would improve with it.
- A configuration workaround in the benchmark harness (e.g. "skip phase X for fixture Y") is also a hard reject for skill-level iterations. It is acceptable only as a benchmark-infrastructure fix that the iteration explicitly scopes itself to.

**Failure mode this catches:** Quick wins that pile up and turn the harness into a patch quilt. The F6/F7 spec annotation iteration is a borderline case worth studying — we annotated the spec, which IS a "configuration change" — but it landed at the right level (the benchmark was measuring the wrong thing because the spec was unclear about lifecycle). Documented as a benchmark-design bug, not a skill workaround.

---

## 4. Worldclass production-ready

> **The output ships. Zero CRITICAL, zero HIGH design or security findings.**

Code that survives review at a non-trivial codebase. No critical bugs, error states explicit and visible, security review passes.

**Operational test (per iteration):**

- A change is ship-eligible only if a full benchmark run shows zero variant-arm CRITICAL findings AND zero variant-arm HIGH `design.*` or `security.*` findings.
- A regression that introduces a single CRITICAL or HIGH on any previously-clean fixture is an automatic revert candidate, even if suite-level margin improved.
- The skill itself must not produce code that violates this bar in the variant arm. (The current `auto-resolve` SKILL.md already wires CRITIC's design + security sub-passes to enforce this; no new infrastructure required.)

**Failure mode this catches:** Optimizing aggregate margin while shipping CRITICAL bugs in some fixtures. Aggregate scores hide ship-blockers.

---

## 5. Best practice

> **Idiomatic for the language and framework. No reinvention of standard primitives.**

Distinct from #4: code can be production-ready (no critical bugs) yet hand-roll a shaped helper that the standard library already provides. That hand-roll is a maintenance and onboarding tax even if it ships.

**Operational test (per iteration):**

- Zero variant-arm MEDIUM `design.unidiomatic-pattern` findings from CRITIC. (The rule already exists in `phase-3-critic.md`: emit when hand-rolled helper logic REPLACES a standard-library primitive AND is measurably less faithful — exactly this principle's check.)
- A regression that makes the unidiomatic-pattern count rise is a quality-gate failure, separate from the ship-blocker gate of #4.

**Failure mode this catches:** Code that passes CRITICAL/HIGH review but writes a 40-line custom permission-bit checker instead of `fs.accessSync`. We had to add the calibration for that exact case in v3.5; this principle keeps it active.

**Why this is not redundant with #4:** Different severity threshold gates a different failure class. #4 is "would this break in production?" #5 is "would a senior reviewer say 'why didn't you just use X?'". Both ride on existing CRITIC findings; the operational difference is the threshold.

---

## 6. Layer-cost-justified

> **Each composition layer (L1 over L0, L2 over L1) must justify its added cost on BOTH quality and efficiency.**

`NORTH-STAR.md` defines three composition layers: L0 (bare), L1 (solo harness), L2 (pair harness). The contract is: L1 beats `bare-best-of-N`, L2 beats `L1-best-of-M`, where N and M are the respective wall-time ratios. "Slower but more thoughtful" is not free — at every layer, the alternative "just run the cheaper layer N more times" must be empirically worse.

**Operational test (per iteration):**

- An iteration that increases L2 wall-time without a measurable per-fixture quality lift on previously-tied fixtures is rejected, even if aggregate margin holds.
- An iteration that introduces or extends a pair-mode phase must specify the **short-circuit rule** (deterministic gates, not vibe confidence) and a **wall-time budget abort** for the phase. Pair budget overruns must fall back to solo, surfaced explicitly in the final report — not silently.
- An iteration that touches `auto-resolve` must declare the affected phases' decision modes (`solo` / `pair_critic` / `pair_consensus`) and confirm the change preserves the per-phase mapping in `NORTH-STAR.md`.
- An iteration on iteration-loop tooling (R0 reviews, ship-gate scripts) is exempt from auto-resolve pair gates but still subject to the layer-cost-justified check at its own scope: the meta-pair must be cheaper than running the cheaper alternative more times.

**Failure mode this catches:** "Pair always-on" creeping in because pair *feels* careful. iter-0016 partial readout (F5 17× wall at verify-tie, F6 10× wall at verify-tie) is the canary — pair without short-circuit recreates that waste pattern at every phase that gets pair-promoted without gates.

---

## How an iteration cites these

In every iteration file under `iterations/`, the "Principles check" section enumerates each of #1-#6 and writes one of:

- ✅ Passes — concrete evidence (numbers, finding counts, wall-time ratios).
- ⚠️ Borderline — explanation + judgment call.
- ❌ Fails — explicit revert reason.

Iterations with any ❌ are rejected. Iterations with ⚠️ go to user review before ship.
