# 0228 — limit how VERIFY judges keep-existing clauses, gate the change on 0227 replays, then re-screen on fresh tasks

2026-10-01. **Status: REGISTERED, frozen before the G commit, any replay call and any corpus authoring.** Design: fact brief (`.devlyn/0228/brief.md`); independent R0s (root, synthesized from three angle drafts with cross critiques, `.devlyn/0228/r0-root*`; Astra gpt-6-astra/ultra, read-only, `.devlyn/0228/r0-astra.out.md`); R1 converged on every policy point (`.devlyn/0228/r1-astra.out.md`); registration reviews: Astra R2 REVISE (4) + three Claude critics → R3 REVISE (1) + two Claude critics → R4 FREEZE (`.devlyn/0228/reg-*`). **User decision (2026-09-30, "1"):** fix the judging rubric where the [0227 diagnosis](../experiments/0227/diagnosis/DIAGNOSIS.md) points — a step for keep-existing clauses and the coverage vs source-review conflict — test the fix by replay on already-public 0227 material, then re-screen on fresh tasks. Standing rules are as in 0227: no resolve invocation, root works directly, Astra reviews, the strict bar, root merges research PRs after Astra SHIP, and a NOT PASS ends automatic re-screening. 0228 amends [0227](0227-verify-rescreen.md) by reference; anything not named here stays as 0227 registered it (`0227:N` means line N of that file). Raw record: `.devlyn/0228/`.

## Why this iter exists

- **Pre-flight 0:** 0227 blocked a correct J4 reference ([RESULT](../experiments/0227/RESULT.md), "Condition 2"), and the block recurs: Codex primary 7/17, Codex pair 1/12, Claude 0/29 on that span (DIAGNOSIS.md:18–20). Fixing it unblocks the go/no-go decision on held steps 2–5.
- **#7 Mission-bound:** as 0227 (`0227:8`).

The rubric tells judges that "a pre-existing defect do not excuse that violation" (`verify.md` 84–86, repeated for the pair at 103–104) but gives no step to establish the existing behavior before binding a keep-existing clause, nor a rule for a public contract the base already contradicts; its coverage mandate for high-complexity behavior (72–77) also conflicts with source-review obligations the spec retains (79) (DIAGNOSIS.md:26–30).

**0228 decides one thing:** whether 22616b57 + F + G may re-enter development of steps 2–5. Beyond 0227's limits it cannot show:
- that G caused any change (DIAGNOSIS.md:34);
- how G judges a twin that breaks behavior the base already has. No 0227 hit is such a case: 61 of 69 hit findings fail on the base, and J1's 8 concern the new `minTTL` option. The fresh corpus is not steered toward one;
- whether one seat excuses a target defect by citing base behavior while the other seat still hits. The screen counts hits per round, as 0227 did, so only gate R3 checks this per seat;
- whether G's coverage edit removes the two J2 blocks. Both read the spec's Verification text as requiring an executable false-override case; the edit's exception helps only if a seat instead treats that case as a retained source-review obligation, as the diagnosis did. Their count is reported, not gated.

## Candidate

**One commit G on `f40da73b`,** on a pushed branch `candidate/0228-fix` with no PR (main unchanged), mirrored byte for byte into `.agents/skills`. Addendum C1 names G before any replay. `V` below is `f40da73b:config/skills/devlyn:resolve/references/phases/verify.md`.

- **Preservation (insert after V:86, "... does not establish applicability.")**: "For a clause that requires an existing path's current behavior, establish that behavior from `base_sha` (the snapshot diff's base side) for the same operation, or from unchanged code on the path the clause names, and bind only a demonstrated departure from it. A public contract that this behavior already contradicts binds separately only if the task independently requires conformance or the diff introduces or changes that promise; otherwise report the conflict as advisory. This does not excuse unmet new requirements, including state that a new or failing operation must leave unchanged."
- **Pair (delete at V:103–104)**: "Apply the same mandatory-clause, applicability and evidence check above; neither impact nor pre-existing origin makes an applicable violation advisory." becomes "Apply the same mandatory-clause, applicability and evidence check above." The imported check keeps V:84–85's "a pre-existing defect do not excuse that violation" for new requirements.
- **Coverage (V:73–75)**: "...and present in the sealed MECHANICAL evidence." becomes "...and present in the sealed MECHANICAL evidence, except for explicitly retained source-review obligations that do not also require executable checks."; **(V:75–77)** "Missing coverage is a verdict-binding finding" becomes "Missing required coverage is a verdict-binding finding"; the rest of both sentences stays.
- **Obligations:** `scripts/lint-skills.sh` and the portability suite pass; a grep finds no 0227 task identifier or domain word in G's diff (dispose, evict, maxSize, noDisposeOnSet, attrs, serializer, memo, allowStale); root implements; Astra reviews `git diff f40da73b G` until SHIP.

## Gates before authoring (development evidence; never a 0227 regrade)

**Replays.** A replay reruns one 0227 round's VERIFY:
- **Inputs:** the round's sealed pristine work and home tars, with both seats live.
- **Environment:** the manifest's round environment, paths relocated.
- **Binaries:** 0227's pinned `bin/` and toolchain.
- **Product, one arm per replay:** **F** = 0227's extracted product; **G** = `git archive G config/skills`.
- **Runner:** a copy, `experiments/0228/replay.py`; 0227's copy stays byte-identical. Each attempt writes to a fresh folder, `/Users/Shared/devlyn-vr-0228-dev/<arm>/<token>/rep-<i>/`, and no folder is ever reused.
- **Kept per attempt:** every seat's full stdout, envelope, transcript and effective seat verdict. Each Claude project directory is moved into its attempt folder.
- **MECHANICAL** is never re-run (it is sealed in the tar).
- **Every batch** starts by checking both tars against the committed 0227 manifest's digests and `bin/claude` against the pinned digest.

**Isolation.**

*Inventory.* A model-free inventory runs before R1 (recorded in Addendum C1) and again immediately before every batch (kept in that batch's record). It finds every location the replay user can read that holds 0227 hidden material:
- Every Git object store that contains 0227's corpus commit `8c589f2e`. A 2026-10-01 check found two, each with its worktrees: this repository's and `~/Documents/GitHub/devlyn-cli`'s. The latter serves root's working directory and the user's active worktree `devlyn-cli-skill-names`, which has the 0227 corpus on disk.
- Every file outside the allowed set and the runner that contains a marker (the 0227 root and experiment paths, and a line unique to each hidden mechanism file), under `HOME` (except `Library`), `/Users/Shared` and `/private/tmp/claude-501`.

Before R1, the 25 diagnostic Claude project directories are moved into `/Users/Shared/devlyn-vr-0227-diag`, as 0227's `move_claude_project` does, so that their names, which carry round tokens, leave `~/.claude/projects`.

*Seals.* Around every replay's judge run, the runner applies the seals with `sealed()`'s permission mechanism and `finally` restoration. The runner is staged outside every checkout. Before any change of mode it writes the original modes to a journal outside every sealed area; R1 and every batch start by restoring any journal left behind, and the runner restores on SIGTERM and SIGINT.
- **Mode 0 on directories:** the two object stores; the research repository's working tree; each `/Users/Shared/devlyn-vr-0227*` root, except the replayed round's 0227 product arm, `bin/` and toolchain; and every other 0228 attempt.
- **Mode 0200 (write-only) on every other found file,** including this root session's live transcript and other sessions' files. Opening such a file for reading fails under any name or alias, while appends still work. A 2026-10-01 probe showed this: a headless Claude CLI 2.1.286 session whose transcript was set to 0200 mid-run kept appending (103,833 → 224,300 bytes, exit 0), and a read of it was denied.
- **Root** reads no hidden material while seals are applied.
- **Other users of sealed repositories:** at each batch start, root records the processes whose working directory lies inside a sealed repository or worktree. If any is not root's own session, root asks the user to pause that work for the batch and waits for the answer. A refusal postpones the batch; it never shrinks the seals.

*Read scan.*
- **Excluded areas:** all of the above.
- **Allowed set:** the attempt's own work and home, its product arm, 0227's `bin/`, and the round's toolchain.
- **Adjudication:** ambiguous reads are adjudicated by root and audited by Astra. An excluded read fails the gate.

**Predicates.** All predicates are frozen now and applied to effective seat verdicts and the merged verdict.
- **Clean reference:** every seat is authenticated and accepted, with no BLOCKED. The merged verdict is PASS or PASS_WITH_ISSUES, or NEEDS_WORK whose rank-2 findings are all non-execution coverage findings, with at least one such finding (reported).
- **Twin hit:** the replay ends NEEDS_WORK with a merge-accepted rank-2 behavioral finding of the target mechanism.
- **Diagnosed J4 block:** a rank-2 finding of any kind, coverage included, claiming that a same-value growth with `noDisposeOnSet` leaves an evicted entry's `disposeAfter` undelivered.
- **Labeling:** root labels, against `hidden/mechanism.md`, every rank-2 replay finding. On twin replays it also labels every finding of any rank, taken from the kept stdout, by a seat that has no rank-2 behavioral target finding. Labeling works from a pool masked of arm, token and attempt, and Astra audits every label blind, as in 0227 scoring.
- **Doubt counts against the gate:** a doubtful kind is behavioral on a reference and coverage on a twin; a doubtful hit is a miss; a doubtful diagnosed J4 block counts on G and not on F; a doubtful demotion counts as one.
- **Infra faults:** classified before any judge output is read (0227 "Faults"). Only the faulted replay is rerun, into a new attempt folder, in an order fixed in C1.
- **Outcomes:** any other G or integrity failure is **FAIL**. Only a G that meets R2's first condition with too little F recurrence is **INCONCLUSIVE**. Both stop the work: root records it and reports to the user, without tuning G, adding repetitions or switching routes (`0227:26`).
- **No fresh material** is spent before R3 passes.

The gates:
- **R1 (apparatus).**
  - **Product:** G's product differs from 0227's only in `verify.md`.
  - **Prompt equality:** for all 64 tokens, G's rendered prompts, split by `prompt_frames`, equal 0227's recorded prompts except the rubric frame (= G's `verify.md`) and the relocated paths.
  - **Stub replay:** all 64 pass authentication and merge, using 0227's stubs (`dry/bin` first on `PATH`, `STUB_DIR` inside the attempt folder, `CODEX_HOME` holding a copy of `dry/codex-home`, whose models cache matches the stub's version). Its renders feed the prompt equality check.
  - **Isolation probe:**
    - From the replay environment, opening each sealed directory and each found file for reading fails by its known path. This includes the live transcript, whose path `~/.claude/session-env` discloses.
    - Root's live transcript keeps growing under the seals.
    - One live call each of the pinned Claude and Codex binaries runs under the seals, in a probe attempt folder set up as `replay.py` sets one up (`CODEX_HOME` ending in `/.codex`, with `auth.json` copied in and removed afterwards). The Claude call has the Read tool. Each call's prompt names one sealed file and asks for its first line. Each call must start, write its session, and fail to read the file.
    - The Claude probe's project directory is then moved into the probe folder.
  - Astra SHIP.
- **R2 (J4 references).** One session, interleaved: G ×10 for each of the four J4 reference rounds (40), and F ×8 for each of the two codex-orientation rounds (16).
  - **PASS** iff every G replay is a clean reference with no diagnosed J4 block, **and** at least 3 of F's 16 replays contain a diagnosed J4 block.
  - A G meeting the first condition with fewer F replays blocked is INCONCLUSIVE.
- **R3 (recall and breadth).** The remaining 60 rounds under G once each, plus two more G replays of each J3, J4, P2 and P3 twin round (32): 92 replays.
  - **PASS** iff every reference replay is clean and every twin replay is a twin hit. In addition, no twin replay may contain a demotion: a seat with no rank-2 behavioral target finding keeps a finding below rank 2 that concerns the target mechanism or a documentation clause the spec requires, giving existing or base behavior as the reason it does not bind.
  - **Reported against 0227:** per-seat hits per task, documentation hit findings, and coverage-only NEEDS_WORK on the J2 references.

Live total: 148 paired rounds (296 seats), about 2–3 hours. The replay root is deleted once its record is committed.

## Corpus

As 0227 ("Corpus", `0227:31–37`, with Addenda B2–B3), with template copies in `experiments/0228/author/`:
- **Exclusions** add python-attrs/attrs, isaacs/node-lru-cache and cthackers/adm-zip (authored against in 0227 and published in B2); installed runtimes count as in B2.
- **PHASE-B** gains one sentence and loses one phrase. It gains: "Public checks must not rewrite repository or harness files; only build or test outputs the repository ignores may be created." It loses "run from the repository root" (`0227 author/PHASE-B.md:14`), the source of P1–P4's unevidenced condition. Execution conditions stay evidence-bound. Authors are not steered toward keep-existing clauses.
- **Apparatus:** B2/B3's fixes apply by kind to the new repositories:
  - force-add the spec copy;
  - remove scratch outputs such as `.tap`;
  - disable a test loader's code cache when it crashes;
  - run suites that share caches serially.

## Rounds, apparatus, seal, freeze and witness

As 0227, with the candidate replaced by G, in a copy `experiments/0228/screen.py`:
- **Changed:** a new root `/Users/Shared/devlyn-vr-0228`; `CANDIDATE` = G; `CONTRACT` = this file; new `STAMP` and `RUN_ID_PREFIX`; fresh `SCREEN_REPOS` and `TOOLCHAINS`.
- **Reused read-only:** the pins.
- **Deleted:** development mode (its constants, `dev_stage` through `g2`, their commands and self-test cases), since the replays replace G2/G3.
- **Kept:** `MECHANICAL_ATTEMPTS` stays 8, with B2's pre-freeze classification.
- **Before SHIP:** a stub dry run of all 64 spans precedes Astra's SHIP of the driver.

## Scoring (pre-committed)

As 0227 (`0227:48–52`), plus one rule for public documentation. Before a check is chosen for a claim grounded in the repository's public documentation, root audits applicability by G's rule (Astra audits the audit):
- **Inapplicable documentation:** documentation that the established existing behavior already contradicts binds only if the task independently requires conformance or the diff introduces or changes that promise.
- **Inapplicable-only claim:** a claim resting only on documentation that is inapplicable by that rule is labeled match=false and gets a check that passes on every tree. That makes it a false alarm on a reference and an unsupported extra on a twin.
- **Other claims in the same finding** are scored as usual.
- **Every other documentation claim,** including an unchanged promise the base honors, is scored as a task claim. An applicable promise that fails on the reference is an invalid reference, even if the base fails too.

## Registered outcome

As 0227 (`0227:54–58`), for 22616b57 + F + G. **PASS:** readmits bundle development only; nothing ships. **NOT PASS:** steps 2–5 stay held, with no automatic re-screen.

## Faults

As 0227, and as "Gates" for replays.

## Predictions (before G and any call)

- **Root:** R1 0.9; R2 0.6; R3 0.6; all gates ≈ 0.32. Fresh screen given the gates: 32/32 hits 0.8, 0 false alarms 0.65, P(PASS) ≈ 0.5; median round wall ≤ 40 s.
- **Astra (registration review, `.devlyn/0228/reg-r1-astra.out.md`):** R1 0.90; R2 0.65; R3 0.70; all gates ≈ 0.41. Fresh screen given the gates ≈ 0.55; gates and screen ≈ 0.23. Point forecast: 32/32 hits, zero false alarms, unsupported extras or invalid references, 128/128 accepted seats, zero BLOCKED, median round wall ≤ 60 s.

## Principles check

- **0 / #7:** ✅ see "Why this iter exists".
- **#1 No overengineering:** ✅ three rubric edits (one insertion, one deletion, one qualified sentence), no parser, merge, lint or scorer-schema change; development mode deleted; replays reuse 0227's pristine inputs.
- **#2 No guesswork:** ✅ predicates, thresholds and predictions fixed before any call; a concurrent F arm separates G from model drift.
- **#3 No workaround:** ✅ the strict bar and exemptions stay; documentation the base already contradicts is neither enforced nor silently excused — the judge reports it as advisory and scoring audits applicability by the same rule.
- **#4 Worldclass production-ready:** ✅ strict bar, one-shot join, sealed replays.
- **#5 Best practice:** ✅ the judge compares against the base it already receives (`base_sha` and the snapshot diff).
- **#6 Layer-cost-justified:** ✅ VERIFY stays a pair; median round wall ≤ 40 s predicted.

## Work order

1. This registration: Astra FREEZE, PR, root merges.
2. G: implement, lint, portability suite, identifier grep, Astra SHIP, push.
3. Replay copy, inventory and isolation, R1, Astra SHIP. Addendum C1 names G, the replay commit, the inventory and the replay order.
4. R2 and R3, with Astra reviewing each; the replay root is then deleted.
5. Corpus: selection, blind authoring, implementation, calibration, calibration review.
6. Driver copy, stub dry run, Astra SHIP; freeze and witness, 64 rounds, masked scoring with Astra audit, join, RESULT.
