# HANDOFF — current continuation

Updated 2026-09-10 KST. Read this file, [NORTH-STAR](NORTH-STAR.md), then the
current spec/source and relevant iteration. Current user instructions supersede
older records. [PRINCIPLES](PRINCIPLES.md), [MISSIONS](MISSIONS.md) and
[DECISIONS](DECISIONS.md) own enduring constraints/history. Inspect Git state and
live runs; do not replay unrelated cold-start suites.

## START-HERE — task completion accepted; delivery recorded by the owner

Product verification is **PASS_WITH_ISSUES**, with zero CRITICAL/HIGH findings.
The sole LOW advisory concerns manual recovery after an interrupted native
worktree removal leaves a prunable registration. Finish gate is clean and the
normal run is archived. PR #4 merge, current-task cleanup and release 3.1.0
remain pending outer-owner delivery; published version is still 3.0.1.

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

Durable raw evidence, failed attempts, accepted archive, source recovery and
cleanup receipts: `/Users/aipalm/.local/share/nx01/iter0143/20260910T022444Z-acceptance-r2/`
(current archive in `work/.devlyn/runs/rs-20260910T022458Z-3f00122a0779/`;
external custody must be completed before worktree removal). See [0143](iterations/0143-task-completion.md).
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
