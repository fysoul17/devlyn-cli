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

## Addendum C1 (2026-10-01, before any replay call)

- **G** = `607c3cf7` on `candidate/0228-fix` (pushed, no PR). Astra SHIP (`.devlyn/0228/g-r0-astra.out.md`); lint, the portability suite and the identifier grep pass (`.devlyn/0228/g-checks.log`).
- **Replay runner** = [`experiments/0228/replay.py`](../experiments/0228/replay.py) at this commit, staged to `/Users/Shared/devlyn-vr-0228-dev/runner/` with G's skills archive and 0227's stubs. Astra reviewed it over eight rounds and gave R1 SHIP (`.devlyn/0228/runner-r*`, `.devlyn/0228/r1-ship*`). What those rounds settled:
  - seats get regular files, never pipes;
  - signals are only recorded, so neither launch nor restoration can be interrupted;
  - seals are restored only after every owned process has ended. Owned means descendants by pid and start time, plus any process whose cwd is inside the attempt, joined across bracketing snapshots. If that cannot be confirmed, seals and journal stay, and recovery needs `restore --confirmed`;
  - the journal and the unsafe marker live in the runner folder;
  - restoration attempts every target;
  - the 0227 manifest is anchored to `git show 1a6f026e:…`;
  - every required tar is checked before the first live call.
- **Replay orders** (generated by `replay.py plan` from 0227's mapping):
  - `plan-r2.json`, 56 replays: in every cycle, the four J4 reference rounds under G; in cycles 1–8 also the two codex-orientation rounds under F.
  - `plan-r3.json`, 92 replays: the other 60 rounds once, then the 16 J3/J4/P2/P3 twin rounds twice.
  - **Infra reruns:** a batch always runs to its end. Each faulted replay is then rerun once, into a new attempt folder, in a follow-up batch that holds the faulted items in their original plan order. Faults are classified before any judge output is read. A rerun that faults again is a recurrence, which is FAIL (0227 "Faults").
- **Inventory**, tightened beyond the registration:
  - Roots also cover all of `/private/tmp` and `$TMPDIR`, where a 2026-10-01 check found V8 code caches named after 0227 round and calibration trees, and npm debug logs.
  - The Git search prunes `node_modules` and the structural 0227/0228 roots.
  - Marker lines are the two path markers plus, per hidden mechanism file, its longest ASCII line without a quote or backslash that no non-hidden corpus file contains. They exist only in a private temporary file during the scan; only their digests are recorded.
  - Root deleted the 340 V8 cache files it had created for 0227 trees: their code-cache blobs carry no marker but pair with marked maps (`.devlyn/0228/v8-cache-removed.txt`).
  - Root moved the 25 diagnostic Claude project directories into the diag root (`.devlyn/0228/diag-projects-moved.txt`).
  - Inventory `p2`: 351 s; 14 object stores holding `8c589f2e` (this repository, `~/Documents/GitHub/devlyn-cli`, and 12 clones in another Claude session's scratchpad); 6,136 marker files outside the structural roots.
- **Residuals** (disclosed):
  - A process that both leaves the attempt folder and is orphaned by its owned parent between two 0.25 s snapshots is not owned.
  - Codex 0.156.1 can read through its built-in code-mode `exec` tool, which leaves no exec record in its plain stderr or JSON events. The probe saw this, and 6 of 0227's 64 Codex seat stderrs carry no exec record. The read scan's Codex leads are therefore incomplete; the physical seals carry isolation, as 0227's RESULT already says of the scanner.
- **R1 results**:
  - **Product:** 55 files; only `verify.md` differs.
  - **Stub:** 64/64 pass merge, authentication and parser collection. After relocation, adapter and role frames are equal, the rubric frame is G's `verify.md`, and snapshot sub-frame payloads are equal. The first stub run stopped on a comparison bug (sub-frame length headers change with the longer path) and was rerun clean after the fix.
  - **Isolation probe:** PASS on its fifth run (`probe/rep-5`), with the runner at this commit.
    - Seals: 33 paths at mode 0 (20 directories, 13 files), 4 directories at 0100, 694 files at 0200. Twelve planned mode-0 paths and most of another session's scratchpad files had been deleted by that session since the inventory. None of the sealed paths could be opened by known path from the replay environment, the live transcript included.
    - Root's transcript grew under the seals (28,018,819 → 28,019,485 bytes).
    - The pinned Claude read the control file; its Read of the live transcript failed with EACCES in its own transcript.
    - The pinned Codex (isolated flags, `--json`, a rollout kept for evidence) read the control file; its `head` of the hidden J4 file was denied in the rollout's tool output.
    - Both sessions were written, auth was removed, and modes were restored.
  - The earlier probe runs:
    - Runs 1–2 failed on apparatus and procedure only. Root polled a status file inside a sealed folder, so it made no transcript event during the wait. Codex's plain stderr and JSON events held no record of its code-mode read.
    - Run 3 passed on the previous runner version.
    - Run 4 stopped before applying any seal, because a planned path had vanished. Vanished seal targets are now skipped.
- **User:** paused their other work in the sealed repositories for the replay sessions (2026-10-01: "4.0.1 배포 끝나면 시작", then the go-ahead).

## Addendum C2 (2026-10-01): seal incident, owner decision, isolation by identity

- **Incident.** C1's seals changed paths the experiment did not own.
  - **Windows:** 13:41:36–13:52:04, 14:01:28–14:01:55, 14:03:24–14:03:48, 14:12:45–14:13:16 and 14:24:48–14:25:21 (the R2 batch, stopped by SIGTERM).
  - **What they changed:** they set `~/Documents/GitHub/devlyn-cli/.git` and the research checkout to mode 000. They set 575–6,149 marker-matched files under HOME, `/Users/Shared` and tmp to 0200. Those files included other sessions' Claude transcripts, live Devlyn terminal spools, Codex and Grok rollouts, and `/private/tmp/claude-501` scratchpads.
  - **What the owner saw in Devlyn:** live sessions vanished; panes failed with `Permission denied`; git worktree listing failed; the owner ended a live session, believing it dead.
  - **Restoration:** nothing was deleted and every mode was restored. Root checked all 610 targets of the stopped replay afterwards.
  - **Consent:** option 1 covered devlyn-cli's git becoming unavailable. It did not cover this collateral.
  - **Superseded:** the stopped replay `G/f6634cfb3793/rep-1` is not scored, and C1's R1 evidence under the old seals is superseded.
- **Owner decision (2026-10-01):** isolate by a dedicated judge account instead of toggling permissions. The owner created:
  - `_devlynjudge`: uid/gid 450, not in `staff`, shell `/usr/bin/false`, home `/var/empty`, hidden, no password;
  - a sudoers rule that lets the owner start processes as that account, passing only the environment named;
  - a separate Claude token for the account.

  The change request is `~/.config/devlyn-vr/0228-isolation-change-request.md`.
- **Invariant:** no experiment step changes the mode, ACL, owner, content or location of a path outside the three experiment-owned locations: `/Users/Shared/devlyn-vr-0227`, `/Users/Shared/devlyn-vr-0227-*` and `/Users/Shared/devlyn-vr-0228-dev`.
  - **Enforcement:** every mutation in [`replay.py`](../experiments/0228/replay.py) goes through one of 18 helpers. Each calls `owned()`, which refuses an outside target before acting: an absolute normalized path whose real parent lies inside a root, so a parent symlink that leaves the roots is refused. Tar members must be unique regular files or directories, so nothing is written through a link. Directory helpers and extraction refuse a symlink destination. After a judge process has run in an attempt, the runner opens no path there for writing; the probe's prompts and outputs live in an owner-only `results/` folder. Cleanup and transcript parsing reopen attempt files for reading only. The credential scan opens regular files only, so a FIFO cannot block it.
  - **RED/GREEN** ([`test_replay_guard.py`](../experiments/0228/test_replay_guard.py)). The test has a static part: every mutating call must sit inside a guarded helper. It has a dynamic part: every mutating primitive is intercepted, every outside target is a path that does not exist, and each helper must refuse before any primitive runs. It also covers a parent symlink, a symlink destination for directory creation and for extraction, and five escaping tar shapes; these cases also run under interception. The middle run replaces the guard with the identity function to show that the dynamic part detects a missing guard.
```
runner: replay.py at 5ad6d84a
static: 35 mutating call(s) outside the guarded helpers
  line 123: .mkdir in stage
  ... (35 static violations)
dynamic: 1 failure(s)
  no ownership guard (`owned`) in the runner
RED
exit=1

runner: replay.py (guard disabled)
static: 0 mutating call(s) outside the guarded helpers
dynamic: 22 failure(s)
  owned() allowed /private/tmp/guard-absent-0228/x
  owned() allowed /Users/aipalm/guard-absent-0228/x
  owned() allowed /Users/Shared/devlyn-vr/guard-absent/x
  owned() allowed /Users/Shared/devlyn-vr-0228-dev/../guard-absent
  owned() allowed relative/x
  dump reached a mutating primitive for an outside target: ['Path.mkdir']
  ... (22 dynamic failures)
RED
exit=1

runner: replay.py
static: 0 mutating call(s) outside the guarded helpers
dynamic: 0 failure(s)
GREEN
exit=0
```
- **Deleted:**
  - the inventory-driven seals (mode 0, write-only and search);
  - `sealed()` and restoration, with the journal and the unsafe marker;
  - the process-cwd acknowledgement gate;
  - the cwd/lsof process adoption.
- **Judges run as `_devlynjudge`.** Before anything is granted, no judge process may be alive.
  - **Command form:** `sudo -n -u _devlynjudge --preserve-env=<names> -- <argv>`. A secret never appears in argv.
  - **Process control by uid:** after each run, and on timeout or signal (TERM, INT, HUP), `pkill -TERM -U 450`, a grace period, then `-KILL`, both run as the judge. `pgrep -U 450` must then be empty. A failing sudo, or a sudo child that does not exit, stops the runner.
- **Judge access, on experiment-owned paths only:**
  - **0228 root:** mode 0700 with judge search; its own files are owner-only.
  - **0227 root:** judge search, with deny entries on every entry except `bin` and `toolchains`. Every toolchain is denied too, except the active round's for the duration of its run. Read/execute on the two pinned binaries.
  - **Attempt folders:** each is 0700, with inheritable judge and owner entries during its run. The judge entry has no `delete`, so the attempt root cannot be moved out of the roots. The entries are cleared when the attempt closes. Closing runs in a `finally` whatever failed, and every start re-closes every earlier attempt and requires that no Codex login copy is left.
  - **Products:** the arm's product is copied into the attempt, so the judge never reads either original.
- **Environment delta from the 0227 rows** (identical for F and G):
  - uid/gid 450 (was 501);
  - `HOME` and `TMPDIR` are the attempt's `judge-home` and `judge-tmp` (were `/Users/aipalm` and the owner's TMPDIR). For Codex, the pinned shim sets `HOME` to `homes/<token>` inside the attempt, as in 0227;
  - `GIT_CONFIG_PARAMETERS` trusts exactly the attempt's work tree (`safe.directory`): the tree belongs to the owner and the judge is another uid, so Git would otherwise refuse it ("detected dubious ownership").
  - `USER`/`LOGNAME` are `_devlynjudge` (set by sudo); `SHELL` stays `/bin/zsh`, passed explicitly;
  - sudo adds `SUDO_COMMAND`, `SUDO_GID`, `SUDO_HOME`, `SUDO_UID`, `SUDO_USER`, `MAIL` and `TERM=unknown`;
  - Claude authenticates with `CLAUDE_CODE_OAUTH_TOKEN`, the judge token passed only through the environment, instead of the owner's login; its config and transcripts live in the judge HOME;
  - the Codex login is a per-attempt copy readable by the judge, deleted after the run;
  - `verify-judges.py` runs from the attempt's product copy.
- **Inventory:** stays a read-only scan. Before every batch and probe the judge tries to open every hidden path; any success fails closed and is reported, and no owner path is changed to fix it. The hidden paths are:
  - every inventoried file;
  - each Git object store and its HEAD;
  - the research tree's hidden corpus files;
  - the other 0227 roots;
  - the 0227 root's hidden entries;
  - the 0228 root's own files.
- **Credentials:** after each run the runner deletes the Codex login copy. It then requires that every file in the attempt is readable and that none contains the judge token.
- **Probe (R1 again), run as the judge.** It must show:
  - the control file is readable;
  - the root transcript, the J4 hidden mechanism and `devlyn-cli/.git/HEAD` cannot be opened in the model-free check;
  - those same reads are denied in the seats' own records. In the Claude transcript, each Read has its own error result naming EACCES. In the Codex rollout, the exact prescribed `head` command has, in that same call's output, a `head: <path>: Permission denied` line for each target and the control file's line;
  - no judge process is left.

  Afterwards the owner compares the mode, owner and ACL of every non-owned path against `~/.config/devlyn-vr/baseline-modes.json`. The probe passes only if none changed.
- **npm logs:** the read-only judge check over inventory `r2` found that the judge could open two of 578 paths. Both were world-readable npm debug logs in `/private/tmp/.npm/_logs`, from the 2026-09-29 toolchain installs, naming only `SRC/toolchains` paths. The runner fails closed on them and never changes owner paths. The owner deleted them (2026-10-01).
- **R1 under the judge account (2026-10-01).** Runner as merged in PR #146, staged.
  - **Stub:** 64/64 pass as `_devlynjudge`.
  - **Probe** (`probe/05f4b0744c2a/rep-1`): pass.
    - The judge opened none of the 903 hidden paths.
    - The control file was readable.
    - Claude and Codex were each denied, with EACCES in their own records, on the live transcript, the J4 hidden mechanism and `devlyn-cli/.git/HEAD`.
    - No judge process remained afterwards.
  - **Owner's baseline compare** (`mode-baseline.py compare`, both sessions): 643 paths compared, changed 0. Four were gone, removed by the owner or other sessions: two npm logs and two worktrees' `.git`.
- **First R2 batch stopped after its first replay.** The replay itself completed: both seats exited 0, and `G/f6634cfb3793/rep-2` is kept but not scored.
  - **Cause:** after the run, the quiesce found a uid-450 process that outlived KILL. It was `/usr/sbin/distnoted agent`, a macOS per-user agent that launchd starts for any account using notifications and restarts after any signal. "`pgrep -U 450` is empty" therefore cannot hold.
  - **Fix:**
    - Process control exempts a uid-450 process only when all three hold: launchd is its parent, its command line is exactly `/usr/sbin/distnoted agent` or `/usr/sbin/cfprefsd agent`, and the kernel (`proc_pidpath`) reports that agent's executable on the read-only system volume. An exempted process is logged and never signalled; any other uid-450 process still counts. A test orphan whose argv was forged to look like the agent was counted and killed.
    - Judge processes are signalled by pid with `kill`, run as the judge, so no other uid can be signalled. The only tolerated `kill` error is "No such process" on every line.
    - KILL gets a 60 s grace.
    - Zombies count as ended.
  - **Restart:** R2 restarts from its first item.
