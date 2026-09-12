# HANDOFF — current continuation

Updated 2026-09-12 18:51 KST — **0153 source accepted; CI/delivery next.**
Read this file, [NORTH-STAR](NORTH-STAR.md), then the current source and iteration.
Current user instructions supersede older records. [PRINCIPLES](PRINCIPLES.md),
[MISSIONS](MISSIONS.md) and [DECISIONS](DECISIONS.md) retain enduring constraints.
Inspect Git state and live runs; do not replay unrelated cold-start suites.

## START-HERE — 0153 benchmark pre-staged validation

Latest owner instruction, 2026-09-12: **“오케이 그러면 1번부터 하나씩 검증해가며 진행해줘.”**
The agreed sequence is benchmark pre-staged validation → ordinary small-request
routing → full-route overhead → semantic constraint coverage → matched quality
and pair-value comparison. Complete and verify each bounded change before
advancing. Earlier direct-implementation/native-review authorization continues.

Root implements directly; **no resolve invocation**. Review uses actual native
`claude-fable-5-1` and `grok-4.6`, independently and read-only. Opus 5 is only a
substitute when Fable is unavailable. Root decides after evidence, without a
unanimity requirement. No source or model-performance claim follows from advice.

### 0153 source ACCEPTED — delivery pending

[0153](iterations/0153-benchmark-validation.md) adds strict existing carrier
validation to pre-staged commands. All 36 before/after controls pass: 14 invalid
cases now stop before execution/results refresh, 22 outcomes stay unchanged.
Existing 35 nonempty benchmark carriers (144 full / 94 visible commands) retain
validation. Checker self-test, guard-deletion regression, full lint (349.922s),
mirror/scope checks pass. Native Fable 5.1 **PASS_WITH_ISSUES**, Grok 4.6 **PASS**;
no in-scope CRITICAL/HIGH. Existing general carrier fix-hint LOW remains.

Active checkout: `/Users/aipalm/.local/share/nx01/core-continuation-20260912`.
Receipt `f9d7c95fac90f43c8b4e3830`; `.devlyn/0153-evidence.tar.gz` owns source
acceptance, `.devlyn/0153-delivery/` owns CI/merge. Finish matching-source hosted
checks and delivery before moving to the ordinary-request routing investigation.
The earlier research clone's HANDOFF WIP and original checkout remain preserved.

### 0149 delivery COMPLETE

[PR #16](https://github.com/fysoul17/devlyn-cli/pull/16) merged at
`f50ce5b9c269fc8aa8aea7ace7a5042e8aafbb72` on 2026-09-12 15:21 KST.
Accepted source `a28334f002406495b9099f52fb501bd963e520d8` and its existing
acceptance/evidence were unchanged. Receipt `04c8d7f4ab67f53f7e57352d` is
**COMPLETE**; exact owned local/remote task refs are removed.

[CI 34676753530 attempt 2](https://github.com/fysoul17/devlyn-cli/actions/runs/34676753530)
passed POSIX and native Windows. Actual log/artifact source is
`85e803e5f0999f918af971b3bc98c35fd3b72cc4`; its tree and parents matched the
then-current PR merge ref `39701df496c4ab494092396df8603b3ed4c6cd45`.
Driver SHA-256 `0fe43e1348c9dabd46d1f87e8f7844c0343406866856874401fee424b97f4f72`
matches actual downloaded bytes; POSIX/Windows package identities agree.
Source audit proves accepted 0149 PackageTests plus unchanged 0150 test classes.
Prior stale-source failure `34676403494` and cancelled attempt 1 remain preserved,
not regraded. Delivery evidence: `.devlyn/0149-resume-20260912-1515/`.

### 0150 remains COMPLETE

[0150](iterations/0150-windows-job-membership.md) / [PR #19](https://github.com/fysoul17/devlyn-cli/pull/19)
merged accepted `512d588550da6240c7f6b01421a90c27b6a4e3e3` into main
`4dfee99695702539f0ed3b1d2110c9a03a95c043`. Final push/PR checks
`34676012206` / `34676025418` passed POSIX and native Windows. Independent native
Fable/Grok source and diagnostic-delta reviews found zero CRITICAL/HIGH; full
local lint passed. Production `platform-support.py` was unchanged. Exact fixture
PID disappearance and actual OpenProcess error 87 are verified; the historical
CI reference owner remains unknown. Existing optimized-Python timeout/failure
cleanup LOW limits stay explicit. Receipt `fbe3985ee021a2112645ac15` COMPLETE;
`.devlyn/0150-evidence.tar.gz` and receipt-bound bytes remain immutable.

### 0151 delivery COMPLETE

[0151](iterations/0151-generated-pure-design.md) / [PR #20](https://github.com/fysoul17/devlyn-cli/pull/20)
merged accepted `aab93fae2ef337d6c8bf751a1cf7c84ad1f69945` into main
`a301aa4dd57df4e0552cd51ed004fed3740a0430` at 2026-09-12 16:23 KST.
Receipt `8f5f5ba32515beadb1f4ed47` is **COMPLETE**; owned local/remote refs
are removed and scratch is clean. Source evidence remains immutable.

All 21 final CLI controls, checker/bootstrap self-tests, UTF-8-disabled caller
smoke, subtraction/scope controls and full lint (333.137s) pass. Native Fable
**PASS_WITH_ISSUES** and Grok **PASS** full-source/final-delta reviews found no
established CRITICAL/HIGH in scope. [PR CI 34680286855](https://github.com/fysoul17/devlyn-cli/actions/runs/34680286855)
and push CI `34680284277` pass POSIX/native Windows. Actual PR integration
source `dbc7a90063a87a01382d625a3655b1ea8f3ecb88` and downloaded driver hash
`c8984d8501d0761a8ea0b71a19e1d0c9c81c09dae79b6f37f8d58c94bd6fc698` match;
POSIX/Windows package identities agree. Evidence: `.devlyn/0151-evidence.tar.gz`
and `.devlyn/0151-delivery/`. No npm release.

### 0152 delivery COMPLETE

[0152](iterations/0152-missing-generated-source.md) / [PR #21](https://github.com/fysoul17/devlyn-cli/pull/21)
merged accepted `e244b153558f7014ebcba38c3fcee9d15b795e61` into main
`76cb85b08e8d30275d8f20fef10837c4f68e4a30` at 2026-09-12T08:34:47Z. Receipt
`8d5a56901c2a69c495425638` is **COMPLETE**; owned local/remote refs are removed
and scratch is clean. Source acceptance/evidence remains immutable.

All 38 before/after controls, checker/bootstrap self-tests, guard-deletion/scope
checks and full lint (269.115s) pass. All 26 missing generated sources now fail
with the declared path and one CRITICAL finding before command execution or
results refresh; the other 12 outcomes remain unchanged. Native Fable 5.1
**PASS_WITH_ISSUES**, Grok 4.6 **PASS**: zero in-scope CRITICAL/HIGH. Existing generic
fix-hint LOW remains. The initial ignored-mirror lint failure is preserved.

[PR CI 34683290987](https://github.com/fysoul17/devlyn-cli/actions/runs/34683290987)
and push CI `34683288619` pass POSIX/native Windows. Actual PR integration
`a00ccd7cb8e5835a7e9533985a8629851c410d8b` has the final merge's tree/parents;
downloaded driver, package digest and packaged checker bytes match their declared
identities and the accepted source. Windows/POSIX package identities agree.
Evidence: `.devlyn/0152-evidence.tar.gz` and `.devlyn/0152-delivery/`.

Next separate frontier: benchmark-prestaged oracle validation. This repair
establishes early checker rejection; no full-pipeline false PASS or broad semantic
coverage/model-performance claim. The four broader priorities remain open.
A16 and frozen comparisons stay untouched. No npm release.

Actual research checkout is the retained standalone clone:
`/Users/aipalm/.local/share/nx01/iter0144/core-research`.
Receipts and owned scratch live under `.git/devlyn-completion/<id>/`.
Prior local-only parking checkpoint `6b3237998ed33943ee543fdcda06efc995872550`
and branch `codex/research-park-20260912-1455` remain recoverable under receipt
`b16b5000f139c4441795aa8a`; its scratch was cleaned. Preserve unrelated
`.playwright-mcp/`, user changes, other sessions, A16 and frozen comparisons.
The original checkout's intentional HANDOFF WIP is preserved in
`.devlyn/0151/original-handoff.md` with its hash before any synchronization.

0153 closes the separate benchmark-prestaged validation follow-up at source;
its delivery is pending above. All four broader priorities remain **OPEN**.
A16, 0124/0125/0128 and frozen 0140/0147 comparisons remain parked/closed.
No restart, regrade, superiority claim or npm release is implied.

## Current owner direction — independent core, optional memory

User clarification, 2026-09-11: **devlyn-cli is the independent core harness.**
It must maximize model potential, quality, problem-solving capability, verified
completion speed and whole-run efficiency/cost without requiring Pyx. Research,
validate and ship core harness improvements for all CLI users first; adding
memory is not a substitute for fixing the core's measured shortcomings.

**pyx-memory is general-purpose memory, optionally amplifying Devlyn:** carry user/project intent,
decisions and verified experience across engines and sessions to improve later
choices and strategies. This per-installation experience loop is distinct from
researching and distributing harness improvements. Storage/reinforcement alone
does not prove learning, and strategy improvement does not imply weight training.

**A core devlyn-os vision is accessible graph engineering and loop engineering**
for harnesses using devlyn-cli and optional Pyx. Make relationships (e.g. agents,
tasks and dependencies) and result-driven execution, verification and replanning
easy to design, run, observe and improve, with user intent and necessary
intervention guiding the organization. A canvas, graph database or fixed workflow
is not decided. OS expansion comes later; CLI-first development does not make it
an OS dependency or fixed default. Retain recommended-harness status and room
for other harnesses/native execution.

Evaluate core versus strong native bare first, then Pyx's incremental value over
that core, including retrieval/learning costs. Accuracy/intent completeness →
verified completion time → total cost; protect easy tasks and improve difficult
ones. Optimal performance and cumulative amplification are goals to demonstrate,
not established or per-task guarantees. This clarification supersedes the prior
conversation's Pyx-first experiment recommendation and older fixed-fleet framing.
Implementation, naming, team/learning policy and integration design remain open.
The subsequent 2026-09-11 instruction authorizes sequential core improvements
without invoking resolve. Root Codex implements and decides after independent
Fable 5.1 (or Opus 5) and Grok 4.6 review. WIP, A16 and closed/frozen experiments
retain their existing boundaries. The four core priorities below remain open.

## 0148 rejects silently discarded inline constraints

[0148](iterations/0148-inline-constraint-validation.md) reproduces a concrete
generated/legacy-inline defect: unsupported sibling fields and misspelled command
expectations could pass validation, disappear at staging/execution and produce
false success. Both authoring `--check` and runtime staging now reject them;
generated guidance names the actual commands-only inline carrier. Normal
executable guards and sibling checks retain their behavior. Twenty-four before
and twenty-four final CLI controls, source self-test and full lint pass.
Independent Fable 5.1 **PASS_WITH_ISSUES** and Grok 4.6 **PASS** source reviews
found no CRITICAL/HIGH. Root accepts the scoped repair; the task receipt owns
delivery separately. No npm release.

Compatibility is intentionally stricter: 30 historical Markdown contracts in
the 144-file comparison now reject previously ignored keys. Historical records
remain unchanged. This establishes a validation failure, not a general model
authoring-omission rate or the cause of 0140/0147 misses. Next, inspect whether
an explicit natural-language constraint becomes a suitable executable check on
a fresh ordinary task, distinguishing absent checks from malformed carriers.
0149's bounded authoring inspection is recorded in its merged iteration above.
The oracle-validation gap and generated pure-design guidance remain follow-ups;
do not reopen frozen comparisons.

## 0147 semantic review screen — no promotion

[0147](iterations/0147-constraint-review.md) registered eight fresh Fable/Grok
reviews of the frozen 0140 source under minimal/current semantic-review
instructions. All native calls completed, but only four Grok answers met the
strict research JSON format; four fenced Fable answers are excluded. Formal
result: **INCOMPLETE**. Grok's four usable answers all missed the forbidden new
Any annotation. Qualitative inspection of Fable's readable answers also found
no detection. No allowed patch was falsely blocked. This is an exposed,
single-task component screen, not full VERIFY or general model/pair evidence.

No prompt/model change is promoted; disjoint confirmation is **NOT_SELECTED /
NOT_RUN** under the registered stop rule. 0148 separately reproduces and repairs
an inline-validation defect; it does not explain this screen. The existing
template already asks for suitable checks; another generic reviewer paragraph
or universal Any scanner is not justified. Four broader priorities remain open.

## Recent verified source repairs

[0146](iterations/0146-named-spec-carriers.md) fixes the documented `X.md` plus
`spec.expected.json` path across bootstrap, process evidence and completion.
Before the fix, named-spec obligations could be missed and the canonical contract
omitted from custody. Valid/invalid source checks could inspect unrelated
`spec.md`. Six before/after controls reproduce and close those failures; full
lint (including 25 completion tests) and independent Fable/Grok source reviews
complete: **PASS_WITH_ISSUES**, no CRITICAL/HIGH. LOW diagnostic/test-depth advice
remains; one proposed dirty-contract bypass was disproved by the existing guard.

[0145](iterations/0145-verify-coverage.md) fixes pure-design/stale-inline execution
and aligns Requirements/Constraints coverage with findings-only judges.
[0144](iterations/0144-core-overhead.md) leaves priority 1 unproven and adds
bounded duplicate-check/output guidance for priority 2. These three source
repairs are verified; broad semantic recall, performance and causal pair value
are not. The 0147 screen provides no promotion evidence; 0148 closes only the
separately reproduced inline-validation mismatch.
Keep the four broader priorities below open; do not reopen frozen comparisons.

## Completed task completion — shipped in 3.1.0

[Task completion PR #4](https://github.com/fysoul17/devlyn-cli/pull/4) is
merged at `81e9ead`; [release PR #5](https://github.com/fysoul17/devlyn-cli/pull/5)
is merged at `6a5073f`. Signed [v3.1.0](https://github.com/fysoul17/devlyn-cli/releases/tag/v3.1.0)
was published as npm `latest` 3.1.0, with registry `gitHead` matching the tag.
All 515 public package members match verified local bytes/modes; fresh npm
installation and CLI help pass. Existing task branches and acceptance/release
worktrees were removed after verified custody. This final HANDOFF travels in a
separately owned documentation task; its receipt handles merge and cleanup.

Product verification is **PASS_WITH_ISSUES**, with zero CRITICAL/HIGH findings.
The sole LOW advisory concerns manual recovery when interrupted native worktree
removal leaves a prunable registration; retry retains the resource safely.
Finish gate is clean and the normal run is archived. The original delivery and
release goal is complete; the four research priorities below remain future work.

Accepted source: `491c38deaf5735dd14dc47fecdfc0a8a1c6806c6`, normal run
`rs-20260910T022458Z-3f00122a0779`. The resumed run completed BUILD_GATE,
CLEANUP, final mechanical checks and fresh Codex/Fable 5.1 review.
The first review found HIGH `VERIFY-PRIMARY-001`: Git `insteadOf` could
redirect publication to another repository. The repair validates literal,
effective fetch and effective push repository identities before allocation and
again on resume/cleanup. Four regressions preserve rejection and legitimate
same-repository aliases. An earlier owner check also repaired the actual
`gh repo view` positional argument and unsupported JSON-field query.

Current behavior: prospective task ownership, exact accepted source, PR reuse,
protected merge and recoverable owned-resource cleanup.
`git config --local devlyn.completionMode pr` stops at PR; unset/default
`auto` continues through eligible merge and cleanup. Existing branches/trees
remain owner-managed; they cannot be retroactively enrolled.
Existing project instructions are preserved by installation: reconcile them
with the bundled AGENTS/CLAUDE templates to adopt completion guidance.

Durable evidence and recovery root:
`/Users/aipalm/.local/share/nx01/iter0143/20260910T022444Z-acceptance-r2/`.
`final-custody/manifest.json` binds 398 entries and the source bundle; the accepted
archive is `final-custody/files/.devlyn/runs/rs-20260910T022458Z-3f00122a0779/`.
`feature-cleanup-result.json`, `release-workflow-result.json` and
`public-release-3.1.0/PUBLIC-CHECK.json` record actual delivery and publication.
Release receipt/custody lives under the retained checkout's
`.git/devlyn-completion/6d3ed1352a9b2baea546ffc4/`; final documentation uses
`.git/devlyn-completion/825ab2163b1d8a0823c2239f/`. Both were allocated before work.
Git recovery refs have no automatic expiry. See [0143](iterations/0143-task-completion.md).

Two September 9 runs remain historically BLOCKED. Codex availability recovered
on September 10, so the proposed engine exception was unnecessary and pins did
not change. This session's failed owner dispatch was stopped without source
changes; its corrupted capture was not accepted, and a fresh attested worker
performed the repair. Inactive/crashed-session intervals are not active model
execution time.

## Legacy worktree cleanup and recovery

**40 registrations → 1; 29 existing roots removed, 10 absent registrations pruned,
33 local and 7 remote branches deleted.** Screenshot roots came from benchmark
drivers and isolated research/validation work, not production resolve allocation.
The outer owner's missing delivery/cleanup boundary caused their retention;
source CLEANUP runs before VERIFY and existing archive stayed inside the checkout.

Exact filesystem/Git custody, 39 recovery heads and deletion evidence are under
`~/.local/share/nx01/worktree-cleanup/0143-20260909T154056Z/` and
`.devlyn/0143-worktree-shipping/cleanup-result.{md,json}`. Remote deletions used
atomic expected-SHA leases. Missing roots have Git recovery only; absent files
could not be archived retrospectively. Main/current checkout, A16, unrelated
unregistered roots and live processes were preserved. No old candidate was adopted.

## Four next improvement priorities

1. Reproduce a real small ordinary request unnecessarily entering full resolve.
   [0141](iterations/0141-proportional-execution.md) changed the entry contract,
   but its four Fable cells were already direct: no observed route/stable-speed
   gain, and 12/12 supplied-fact classifications do not prove risk discovery.
2. Reduce measured full-route context/dispatch/report overhead while retaining
   checks and independent review. 0141 took about 21 minutes and emitted an
   unnecessary 1.26 MB BUILD hash dump. 0143’s literal lint alone took 273.846s
   and its helper tests 80.906s. Measure model work, checks, repetition and repairs
   separately; exclude inactive conversation time from active execution.
3. Improve explicit-constraint coverage and semantic reviewer recall. [0140](iterations/0140-delegated-real-task.md)
   introduced forbidden `Any` in solo despite native PASS and a blind Fable miss.
   Ruff catches that example but not nested Any; authoring guidance is not complete
   semantic coverage.
4. Establish comparative quality and causal pair value on registered matched
   tasks with untouched confirmation. 0140 paired 706.187s vs bare Fable 142.589s
   remains negative; copycat NOT_RUN, independent-human test 15 and world-best
   claims remain open. [0070 aggregate/off-resolve intent closure](iterations/0070-loop-architecture-STUB.md)
   remains a designed frontier, not a shipped guarantee.

## Preserved boundaries and history

Accuracy/intent completeness → verified resolution time → OUTPUT/cost. Root
makes decisions after actual advice; obsolete model recipes, unanimity and cost
bans are superseded by [0120](iterations/0120-model-adaptation-direction.md).
Use current installed skills/pins for execution. A finished archive is not proof
of successful verification or permission to publish. Unknown telemetry stays unknown.

**A16 remains user-parked/NOT_INSPECTED.** [0118 custody](iterations/0118-concurrent-admission.md#waiter-park-and-custody)
owns `~/.local/share/nx01/iter0113/quick-a16-1`, `lift-quick-a16-1`, staged inputs,
runner/parameters and partial evidence. No restart, regrade or retuning is authorized.
Preserve closed negatives 0124/0125/0128 and frozen comparisons; no latency,
reliability, accuracy superiority or Mission 1 closure follows from this cleanup.

Original HANDOFF WIP and exact [0139 preparation](iterations/0139-mission1-validation.md)
are committed in `5e85f99`; pre-edit hashes/snapshots remain in
`.devlyn/0143-worktree-shipping/handoff-source-preservation/MANIFEST.json`.
Historical verbatim Blocks 7–11 are recoverable from that Git version; their
adopted goals remain in NORTH-STAR. 0139's old auth blockers are historical.

<a id="direction-reassessment--2026-09-05"></a>
0115/0116, 0125 and 0128 stay unadopted, with recovered source/history under the
cleanup directory above. 0115/0116 are readable from `refs/devlyn/archive/0143/wt-27`;
follow `cleanup-result.md` for restoration only if needed.

Original user directive retained verbatim; later model/authority instructions
supersede its historical model name:

> 한가지만 더. 지금 하고있는 것들이 북극성의 목표를 향해서 no xxxx, worldclass xxx 5대 원칙들을 바탕으로 계속 개선을 해나가고 있는게 맞지? 그냥 오로지 점수를 위해서 하는게 아니고 말이야? 확실하게 해주고 항상 codex cli gpt 5.5 와 함께 compenion 으로서 pair 로 논의하고 최선의 결과에 도달할 수 있도록 끝까지 연구하고 개선해줘. 산으로만 가지마. 이제는 됐다 싶을때까지 계속 돌아. 하면서 계속 docs는 업데이트 해주고, 50% 이상 context가 차면 compact 하고 handoff 를 통해서 지금 내가 얘기한것 토씨하나 틀리지 않고 그대로 각인하고 계속 진화시켜나가.
