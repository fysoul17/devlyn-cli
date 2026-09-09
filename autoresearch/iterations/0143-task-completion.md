# 0143 — Owned task delivery and recoverable worktree cleanup

2026-09-10 KST. **Legacy housekeeping complete; implementation present, required acceptance BLOCKED, draft PR open, merge and release pending.**
The user requests truthful remaining-work handoff, removal of stale worktrees,
and a completion boundary through commit/push/PR/main merge before owned-resource
cleanup, with automatic completion or a configurable stop at PR. This record
separates the completed one-time cleanup from the not-yet-verified product change.

## Cause and responsibility

The audit found 40 registered worktrees: the active checkout, 29 existing inactive
roots and 10 already-missing registrations. Twelve `r5b/*`, `m95/*`, `m96/*` and
`m97/*` arms were created by frozen 0094–0097 benchmark drivers. `wt-control` was
closed 0088 Stage B; three `wt-arm-*` roots belonged to closed 0099. Other `codex/*`
roots were isolated implementation candidates or validation attempts. Creation
commands were recovered for the benchmark arms; ownership documentation, not a
fabricated shell transcript, attributes the manually isolated work.

Production resolve did not allocate these task worktrees. Its CLEANUP phase
removes scoped source/tooling leftovers before VERIFY, and archive stores run
evidence inside the same checkout. Neither was the missing Git shipping and
workspace-finalization boundary. The outer research/controller workflow created
and retained these roots without completing their lifecycle. Deleting after
local archive alone would lose that evidence; moving destruction into pre-VERIFY
CLEANUP would invalidate verification. The correction therefore belongs after
successful verification and archival, under the creating task owner's authority.

Evidence: `.devlyn/0143-worktree-shipping/findings.md`, `worktrees.json` and
`shipping-audit.md` retain per-root provenance and the current-source searches.
This is an observed ownership/finalization defect, not evidence that the harness
spontaneously spawned all names in the screenshot.

## Completed one-time cleanup

Local cleanup began 2026-09-09T15:40:56Z and finished 15:42:52Z. A subsequent
authorized audit completed the seven matching remote-branch deletions:

| Operation | Result |
| --- | ---: |
| Existing inactive worktrees removed | 29 |
| Missing registrations pruned | 10 |
| Covered local branches removed | 33 |
| Registered checkouts remaining | 1 |
| Covered remote branches removed | 7 |

Recovery: `/Users/aipalm/.local/share/nx01/worktree-cleanup/0143-20260909T154056Z/`.
The cleanup receipt binds per-tree archives/manifests, Git administrative archive
and a verified repository bundle retaining 39 recovery heads. Existing filesystem
snapshots preserve regular files, modes, symlink targets and ignored evidence;
274,330 filesystem entries were archived. Ten absent roots had no filesystem to
archive retrospectively; their Git administration and recoverable commits were
retained. The exact receipt is `.devlyn/0143-worktree-shipping/cleanup-result.json`.

The active checkout, parked A16, unregistered roots and live processes were
excluded. The seven remote branches were initially retained, then deleted in one
atomic deletion-only push after exact live-head/recovery matches and no open PRs
were verified. Each deletion used its expected-SHA lease; fresh remote enumeration
confirmed absence, and all 39 recovery refs remained unchanged. Raw commands and
results are in durable `remote-cleanup/`, bound by the cleanup JSON. Main, current
0143 and unrelated remote branches were excluded from that operation.

No old candidate was merged merely to clean its branch. In particular 0115/0116,
0125 and 0128 remain unadopted histories recoverable from custody. Removal does not
reclassify their rejected/invalid/partial experiments. Process observations are
point-in-time evidence, not a universal future writer lock.

## Authorized product change — acceptance pending

Owner-input commit `5e85f99` contains `docs/specs/task-completion/spec.md` and its
expected file, the original HANDOFF WIP and byte-identical historical 0139. Current
branch is `codex/0143-task-completion` in the retained checkout. The original run
`rs-20260909T153949Z-e67a90ebc237` is archived **BLOCKED before IMPLEMENT**. Its
PLAN native invocation took 400.047 seconds; the recorded PLAN phase was 452.632
seconds including orchestration. Automatic Claude probe selection actually used
`claude-opus-5`, not Fable. That probe read the explicitly forbidden installed
`.claude/skills/devlyn:resolve/SKILL.md`; root terminated it at 432.088 seconds,
wrapper exit 143, and accepted no probe artifact. The original observed model, input violation
and blocked result are preserved, not relabeled as successful advice or execution.

The same attempt's baseline full lint exited 1 with four source-to-`.claude`
mirror mismatches (ideate SKILL/template and resolve SKILL/free-form reference).
Later direct comparisons matched. The installation refresh's cause/actor is
unknown; this record makes no owner repair claim. Raw evidence remains in
`.devlyn/0143-worktree-shipping/probe-r0-rejection.json`,
`probe-r0-native-transcript.jsonl`, `probe-r0-base-lint.log`, `r0-rejected/` and the
original archived run.

Distinct successor `rs-20260909T155758Z-064c8649a367` is also archived
**BLOCKED**, with 38 retained files. Its canonical record is
`.devlyn/runs/rs-20260909T155758Z-064c8649a367/final-report.md`.

| Native invocation | Result | Seconds |
| --- | --- | ---: |
| PLAN | PASS, fresh Codex | 248.315 |
| RISK_PROBES | PASS, explicit Fable 5.1 | 62.722 |
| IMPLEMENT 0 | BLOCKED on installed-mirror prerequisite | 1493.984 |
| IMPLEMENT 1 | PASS after owner mirror refresh | 185.577 |
| BUILD_GATE 0 | BLOCKED, native exit 1 usage-limit error | 436.920 |
| CLEANUP | NOT_RUN | — |
| VERIFY primary/pair | NOT_RUN | — |

Implementation checkpoint is `26f40e5e54f7c50d5fef8ef40f5b600dc7c1d8db`.
Before IMPLEMENT 1, the owner preserved and refreshed three stale installed files
and added two source-identical installed files; exact custody is
`.devlyn/0143-worktree-shipping/installed-refresh/manifest.json`. This identified
R1 owner action is distinct from the unexplained R0 mirror refresh above.

BUILD retained three sealed successful literal commands: helper self-test 80.906s,
full structural lint 273.846s and diff check 0.018s. Two focused owner regressions
passed in 6.757s. No P1 completion entry or final spec-verify results carrier was
emitted. Native `turn.failed` and invocation exit 1 prevent successful invocation
attestation. The individual checks do not establish complete BUILD acceptance.
The Fable probe checks helper self-test exit/output; it does not independently
cover every PR/deletion invariant. Fresh primary and pair VERIFY never ran.

The BUILD state span includes roughly seven hours of inactive conversation before
owner recovery. Do not call that active model execution or a measured compute
cost. The owner completed finish-gate exit 0 and archived BLOCKED honestly; neither
terminal completeness nor successful individual commands licenses delivery.
The new helper must reject this BLOCKED archive as a shipping authority.

The implementation adds a native Git/gh completion helper and policy documentation
for prospective ownership, exact accepted source, PR reuse, protected merge,
external evidence custody and owned-resource removal. Local policy is
`devlyn.completionMode=auto|pr`, absent=`auto`; local-only instructions win.
These are implemented candidate behaviors, not independently accepted guarantees.
The candidate branch was pushed at `26f40e5` and draft [PR #4](https://github.com/fysoul17/devlyn-cli/pull/4)
is open. Main merge, current task-branch deletion and new release have not completed.

A release source audit found an installed-boundary defect: AGENTS.md and CLAUDE.md
pointed to repository-only `config/skills/devlyn:resolve/references/task-completion.md`.
The actual fresh Claude/Codex install reproduced it: both copied root documents
retained that absent path while the reference existed in their respective installed
skill directories. Installer commands exited 0 and source/reference hashes matched;
user-global settings were unchanged. Evidence is
`.devlyn/0143-worktree-shipping/install-pointer-repro.md` and its raw result directory.

After the BLOCKED run was archived, the owner made a bounded direct documentation
follow-up: replace exactly those two pointers with `references/task-completion.md`
relative to the installed `devlyn:resolve` skill's directory. This uses the current
Codex orchestrator for an inspected, reversible local documentation edit and changes
no configured engine or product Python code. The repeated fresh-install smoke passed on Claude and Codex: installed root
documents equal the new source, and their skill-relative reference exists with
matching source bytes. Evidence: `.devlyn/0143-worktree-shipping/install-pointer-after.md`
and `install-pointer-after/result.json`. An extra collector stamp assumption failed
after successful installs; its error is preserved and the same installation was
collected through the actual SKILL.md parent. No installer retry was hidden. This
proves the two documentation pointers, not full product acceptance.

The pinned Codex CLI route is quota-blocked. Root has a pending user question for
a task-local exception using Fable CLI workers and a fresh in-app Codex reviewer;
no answer or authorization is recorded. Do not silently change persistent pins
or infer consent from elapsed time. Required acceptance must finish via an
available authorized route; retain both original BLOCKED archives.

Final fields for the owner to replace from actual evidence:

- Candidate implementation: `26f40e5`; two-line install-pointer correction applied as an owner follow-up; Claude/Codex installation regression **PASS**.
- Complete BUILD, CLEANUP, independent VERIFY and accepted product result:
  **PENDING**. Both previous full runs remain archived BLOCKED.
- Draft [PR #4](https://github.com/fysoul17/devlyn-cli/pull/4): pushed head `26f40e5`.
  Accepted review, observed main merge SHA and current branch cleanup **PENDING**.
- Follow-up publication: planned under the user's prior deployment authorization
  after acceptance/delivery; version/tag/publication **UNCONFIRMED**. Last released
  baseline remains 3.0.1. Product phase workers do not publish.

## Handoff subtraction and remaining frontier

The prepared replacement removes obsolete closed-story startup chains, historical
model mandates, cost bans and unrelated cold-start suites. Current goals, the
original verbatim directive, A16 parking and negative results remain. Commit
`5e85f99` and `.devlyn/0143-worktree-shipping/handoff-source-preservation/` preserve
old WIP; 0139 is historical preparation, not a current model-auth blocker. The implementation adopted a shorter handoff; its terminal status still needs
this quota-blocked checkpoint before final delivery.

After lifecycle completion, four improvements remain:

1. Reproduce a real small ordinary request unnecessarily entering full resolve.
   0141's four native cells were all already direct, so they measured no route
   gain or stable speed advantage. Record actual installed instructions/model and
   commands before proposing another routing change.
2. Reduce measured full-route context/dispatch/report overhead while retaining
   required checks and independent review. 0141's development run took about 21
   minutes; an unnecessary 1,266,266-byte BUILD capture is a concrete starting
   point. Measure verified resolution, including repairs, instead of first response.
3. Improve explicit-constraint coverage and semantic reviewer recall. 0140's solo
   harness introduced forbidden `Any` despite native PASS and a blind Fable miss.
   Ruff catches that specific addition with baseline handling but does not cover
   nested Any; 0141's authoring guidance is not general completeness proof.
4. Establish broad quality and causal pair value with prospectively registered,
   matched comparisons and untouched confirmation; keep external-human test 15
   open. 0140 paired 706.187s vs bare Fable 142.589s was a negative superiority screen;
   copycat stays NOT_RUN and A16 stays user-parked/NOT_INSPECTED. The designed 0070
   aggregate/off-resolve intent-closure frontier also remains open.

No simple latency or reliability advantage, general accuracy/performance superiority,
or Mission 1 closure follows from housekeeping or the incomplete product attempts.
Principles: **No workaround** fixes the owner boundary; **No overengineering**
keeps native Git/gh and existing phases; **No guesswork** preserves exact provenance,
negative results, recovery receipts and the distinction between cleanup and release.

## Durable blocked checkpoint

The owner preserved this task’s raw execution/installation/cleanup audit artifacts
and both BLOCKED archives, with byte/mode verification and a verified source bundle,
at `/Users/aipalm/.local/share/nx01/iter0143/20260909T234909Z/`. `MANIFEST.json` binds retained bytes;
`RECOVERY.md` identifies the current source refs and the separate legacy-tree
custody. This checkpoint preserves an incomplete candidate; it is not release evidence.
