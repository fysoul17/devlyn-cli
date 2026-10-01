# 0229 — meet "existing … behavior" by matching the base's existing operation, then re-run the 0228 gates and the fresh re-screen

2026-10-01. **Status: REGISTERED (Astra FREEZE).** Frozen before the H commit, any replay call and any corpus authoring. Runs only after the owner approves.

Registration review: Astra R0 REVISE (3) + three Claude critics (diagnosis, recall, subtractive) → R1 FREEZE (`.devlyn/0229/reg-*`).

**Owner decision (2026-10-01, through the devlyn-os-v1 session):** after 0228's R2 FAIL, diagnose why the Codex primary still blocked the correct J4 reference, fix it and prepare a re-screen. Stop for approval before any run. Keep the judge account `_devlynjudge`, its current token and Addendum C2's isolation. No resolve invocation.

0229 amends [0228](0228-verify-rubric-rescreen.md) by reference. Anything not named here stays as 0228 registered it, with Addenda C1–C3.

## Why this iter exists

- **Pre-flight 0:** 0228's R2 failed on one G block of the correct J4 reference (C3).
  - In the [0228 diagnosis](../experiments/0228/diagnosis/DIAGNOSIS.md), that seat had the base's deferral in view. It bound the deferral as a violation of "the existing eviction disposal behavior", read as a new requirement.
  - The one G seat that compared with the base's other set-triggered evictions reported the same scenario as advisory.
  - The rubric never says that the existing-behavior part of a clause is met by matching the base's existing operation, nor that this behavior is not itself a defect under that part.
  - The cause is a hypothesis among three: scope, pre-existing-defect framing, chance.
- **#7 Mission-bound:** as 0227/0228.

**0229 decides one thing:** whether 22616b57 + F + G + H may re-enter development of steps 2–5. The limits are 0228's ("decides one thing"), plus one: the gates cannot show that H caused a change.

## Candidate

**H** is one commit on G (`607c3cf7`), on a pushed branch `candidate/0229-fix` with no PR, mirrored byte for byte into `.agents/skills`. Addendum D1 names H before any replay. `V` = `607c3cf7:config/skills/devlyn:resolve/references/phases/verify.md`.

H replaces G's preservation sentences, V:87–95 (from "For a clause that requires an existing path's current behavior" to "must leave unchanged."), with:

> For the part of a clause that requires existing behavior — an existing path's current behavior, or "the existing …" behavior a new path must receive — establish that behavior from `base_sha` (the snapshot diff's base side): for an existing path, the same operation, or unchanged code on the path the clause names; for a new path, the existing operation that performs the named behavior under the same options. That part is met by matching it: bind only a demonstrated departure, and do not treat the existing behavior itself as a defect under that part. A public contract that this behavior already contradicts binds separately only if the task independently requires conformance or the diff introduces or changes that promise; otherwise report the conflict as advisory. Agreement with `base_sha` never excuses a requirement the base does not already meet: the rest of such a clause, every other new requirement, and any state a new or failing operation must leave unchanged stay binding.

V:85–86 ("Small impact, rare inputs, or a pre-existing defect do not excuse that violation.") stays unchanged. A deviation from the base on a concrete required property remains a violation.

**Obligations, as for 0228's G:**
- lint and the portability suite pass;
- a grep finds no 0227 task word in the diff;
- Astra SHIP of `git diff 607c3cf7 H`.

## Gates (development evidence; never a 0227 regrade)

As 0228's "Gates before authoring" with C1–C3, with H in place of G and the following changes.

**Inherited from 0228 and C2:**
- replays of 0227's pristine rounds run as the judge account;
- inventory and a judge open-check before every batch;
- process control by uid, with the kernel-verified OS-agent exception;
- a credential check after every attempt;
- the owner's baseline compare after every batch;
- masked labeling with an Astra blind audit, doubt counting against the gate;
- the account-drift rule.

**Changes, all fixed in D1 before any call:**

- **Runner (D1):**
  - arms F and H, with H staged from `git archive H config/skills` as `product-H`;
  - attempt folders under `DEV/H/…`;
  - the collector pools every finding of any rank on twin replays, INFO included, so R3's demotion check sees lower-rank target findings;
  - Astra SHIP of the runner diff.
- **R1 (apparatus):**
  - H's product differs from 0227's only in `verify.md`;
  - prompt equality for all 64 tokens (rubric frame = H's `verify.md`);
  - stub replay 64/64 as the judge;
  - the isolation probe and the owner's baseline compare run again, because the runner changes;
  - Astra SHIP.
- **R2 (J4 references)** concentrates on where blocks occur: all five R2 blocks came from Codex primaries on the codex-orientation rounds.
  - **Replays, interleaved in a D1 order:**
    - H ×15 for each of the two codex-orientation J4 reference rounds (30);
    - H ×5 for each of the two claude-orientation J4 reference rounds (10);
    - F ×8 for each of the two codex-orientation rounds (16).
  - **PASS** iff every H replay is a clean reference with no diagnosed J4 block **and** at least 3 of F's 16 replays contain a diagnosed J4 block.
  - **INCONCLUSIVE:** every H replay is clean, but F has fewer blocks.
  - **FAIL:** anything else.
- **R3 (recall and breadth):** 100 replays under H, including the per-seat demotion check on twin replays.
  - The other 60 rounds once each.
  - Two more replays of each J2, J3, J4, P2 and P3 twin round (40). J2 is added because its twin, like J3's, behaves like the base in its trigger scenario while violating a required property, which is H's recall risk.

FAIL or INCONCLUSIVE stops the work and goes to the owner, as in 0228.

## Corpus, rounds, scoring, outcome

As 0228, whose corpus was never run.

- **Corpus:** a third fresh corpus by the literal selection rule. The exclusions add attrs, node-lru-cache and adm-zip.
- **Rounds:** 64, under 22616b57 + F + G + H.
- **Scoring:** the strict bar, as 0228 (including the public-documentation rule).
- **Outcome:** PASS readmits bundle development only. NOT PASS keeps steps 2–5 held, with no automatic re-screen.
- **Screen isolation**, per the owner's "keep C2's isolation":
  - the screen root is `/Users/Shared/devlyn-vr-0228-dev/screen-0229`, inside a C2-owned root;
  - the screen's judge seats run as `_devlynjudge`, with C2's grants, inventory check, process control and credential check;
  - the 0227 driver's permission-toggle `sealed()` is deleted;
  - D2 names the driver change before its Astra SHIP.

## Predictions (before H and any call)

- **"H does nothing" baseline:** at G's observed Codex-primary rate of 1 in 20 on codex-orientation rounds, P(no block in 30) ≈ 0.21. For the 10 claude-orientation replays, P(no block) ≈ 0.9 is a subjective assumption: the Codex pair raised the scenario 0 of 20 times under G, and blocked 1 of 12 in 0227.
- **Root:**
  - R1 0.9, R2 0.5, R3 0.7; gates ≈ 0.3;
  - fresh screen given the gates ≈ 0.5; overall ≈ 0.15.
- **Astra (freeze review, `.devlyn/0229/reg-r1-astra.out.md`):**
  - R1 0.90; R2 given R1 0.45; R3 given the earlier gates 0.65; all gates ≈ 0.26;
  - fresh screen given the gates 0.50; overall ≈ 0.13.

## Principles check

- **#1 No overengineering:** one rubric passage rescoped. One runner change maps the arm to H and fixes the collector, a gap Astra found in 0228's collector. The screen driver change follows the owner's isolation decision. No parser, merge or scorer change.
- **#2 No guesswork:** predicates, orders and predictions fixed before any call. The F control guards against model drift; the baseline is stated.
- **#3 No workaround:** the strict bar stays. Agreement with the base never excuses a requirement the base does not meet.
- **#4–#6:** as 0228.

## Work order

1. Diagnosis and registration PR, after Astra's FREEZE.
2. H: implement, lint, portability suite, identifier grep, Astra SHIP, push. Runner change, Astra SHIP. D1. This is preparation only: nothing is run.
3. **Owner approval** of this plan. No replay, corpus or screen work before it.
4. R1, R2, R3, with Astra reviews and the owner's baseline compares.
5. Corpus. Driver (judge account, D2). Screen, scoring, RESULT.

## Addendum D1 (2026-10-01, before any 0229 replay call)

- **H** = `3afbb18e` on `candidate/0229-fix` (pushed, no PR): one commit on G changing only `verify.md` and its `.agents` mirror. Astra SHIP (`.devlyn/0229/h-r0-astra.out.md`); lint, the portability suite (63 tests, 17 platform skips) and the identifier grep pass (`.devlyn/0229/h-checks.log`).
- **Runner** = [`replay.py`](../experiments/0228/replay.py) and [`collect.py`](../experiments/0228/collect.py) at `17c8b7b8`:
  - arms F and H. `stage <H>` extracts `git archive H config/skills` untrusted into `product-H`; attempts go to `DEV/H/<token>/rep-N` and `DEV/stub-H/…`;
  - G and stub-G stay among the attempt kinds, so 0228's attempts remain closed and inside the judge open check;
  - stub binaries are copied straight from 0227's `dry/` folder. 0228's staged copy in `DEV/stub` was byte-identical and is no longer read;
  - the collector keeps every finding of any rank, INFO included. Its pool holds every rank-2 finding plus every finding on a twin replay; labeling then applies 0228's rule, so the per-seat demotion check sees lower-rank target findings;
  - the guard test is GREEN on this runner (root's run; its fixture setup writes only inside `DEV/scratch`) and RED with the guard disabled (root and Astra). Astra SHIP (`.devlyn/0229/run-r0-astra.out.md`); two Claude reviewers, one on isolation and one on registration fidelity, found no defects.
- **Replay orders** (`replay.py plan`, committed as [`plan-r2.json`](../experiments/0229/plan-r2.json) and [`plan-r3.json`](../experiments/0229/plan-r3.json)):
  - R2, 56 replays in 15 cycles: H on both codex-orientation J4 reference rounds in every cycle (30); H on both claude-orientation rounds in cycles 1, 4, 7, 10 and 13 (10); F on both codex-orientation rounds in cycles 1, 3, …, 15 (16).
  - R3, 100 replays: the other 60 rounds once, then the 20 J2/J3/J4/P2/P3 twin rounds twice.
  - Infra reruns as C1.
- **Nothing of 0229 has run.** R1 starts only after the owner approves.
