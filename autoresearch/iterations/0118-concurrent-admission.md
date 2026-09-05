# 0118 — concurrent bootstrap admission

**USER RESUMED 2026-09-06 with exact final-spec three-seat agreement complete. Implementation, bootstrap/full resolve, test gates and final implementation trio: NOT STARTED.** Parked design was root-reconciled; the exact final-spec votes were incomplete. No product acceptance or main adoption follows.

Candidate: `/Users/aipalm/Documents/GitHub/devlyn-cli-0118-concurrent-sessions`, branch `codex/0118-concurrent-sessions-20260906`, original base `4acfc3cb6071f5c2923b3f3ceeebd03c88460a18` (`4acfc3c`). [Owner spec](/Users/aipalm/Documents/GitHub/devlyn-cli-0118-concurrent-sessions/docs/specs/0118-concurrent-admission/spec.md) and sibling `spec.expected.json` own requirements and command bounds. Root will checkpoint spec/context; consult exact receipts in the durable bundle after parent completes custody, not an assumed future commit ID. No DECISIONS entry until final implementation closure.

## Resume checkpoint — 2026-09-06

The user resumed and reaffirmed the North Star: maximum native capability/autonomy plus quality-and-efficiency `bare < solo < pair`, with root `CLAUDE.md`, `AGENTS.md` and resolve/runtime all optimization targets. 0118 remains a separate bounded ownership correction; A16 product and outcomes stay untouched. Current PID45397 observation is not-live; no waiter was restarted.

Previous custody had no spec/context commit or final manifest. Parent preserved the original uncommitted snapshot and finalized the PARK bundle with 132 SHA256-verified files; `custody-completion.json` records the missing historical commits honestly. Canonical expected validation found lint timeout900 outside the supported1..600 range; only that bound and its spec line changed to600. Raw rejection/acceptance are candidate `.devlyn/0118/resume-20260906/spec-check-r0.*` (exit2) and `spec-check-r1.*` (exit0).

Exact final spec `c0df06d92f29b8fa3f1049489e0f1e53bb041c38b84786c0b2c3c4fd012c54c7`, expected `1c31ddb9c9972cee93fbf0405fa13c0a029a2b94b3a508bd71149f8fd8dc1b76`: actual Astra `astra-spec-r1.stdout` GO, Fable5.1 `fable-spec-final-r1.txt` GO, Grok4.6 `grok-spec-r1.validation.json` canonical PASS/zero findings, all in that resume packet. Fable/Grok each used6 final reads; actual model/exit/hash evidence is retained. Earlier snapshot reviews remain unchanged and do not certify final bytes. `final-spec-acceptance.json` makes design ready; code approval remains pending. Fable corrected its own history: predicate-only/session-exception advice belonged to historical R0; historical R1 had already withdrawn both.

## Why this iteration exists

The user's explicit concurrent same-project tasks/sessions request supersedes Mission 2's blanket deferral only for bounded admission protection. Mission 1 floor and ceiling remain incomplete. Automatic placement, full-session writer ownership, shared resources and integration/merge verification remain open. The accepted baseline/helper receipts and 0114/0117 closures do not establish whole-product PASS. Preserve 0115/0116 candidate pointers and their separate adoption gates in [HANDOFF](../HANDOFF.md#direction-reassessment--2026-09-05).

**No workaround / No guesswork:** the observed invariant failure is admission replacing unfinished ownership or admitting two initializers. **No overengineering / Subtractive-first:** remove unconditional archive/recovery permission, share the small conservative completion predicate, and add only the short exclusion needed by the reproduced race. No new session manager or fleet substrate is accepted.

## Predictions and existing raw observations

All paths below refer to the preserved [main packet](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906). These experiments predate PARK; none was rerun for this document.

| Recorded prediction | Raw result | Limit |
| --- | --- | --- |
| [Sequential/Git prediction](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/prediction.json), 15:46:03 UTC: second bootstrap archives unfinished prior; distinct branches isolate worktrees and occupied branch refuses. | [results.json](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/results.json): second admitted, unfinished first archived byte-exact; separate-worktree HEAD/dirty isolation. [commands.json](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/commands.json): same-branch refusal exit 128. | Sequential local bootstrap and Git fixtures. |
| [Race prediction](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/race.prediction.json), 15:52:22 UTC: both synchronized first starts succeed without atomic exclusion. | [race.results.json](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/race.results.json): two actual Python processes, barrier after prior-run checks/before writes; expected 1, actual 2 admissions. Final goal/state digests agree. | No mixed bytes observed; no statistical frequency or real CLI throughput/lift claim. |
| [Follow-up prediction](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/r1-followup.prediction.json), 16:02:02 UTC: inherited Git redirects alter lock identity; exact temporary residue escapes detection. | [r1-followup.results.json](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/r1-followup.results.json): combined `GIT_DIR`/`GIT_WORK_TREE` yields same physical top with a different private Gitdir; all four exact temporary families undetected. | Detector fixtures, **not actual SIGKILL**. Process-death tests remain required. |

The synchronized race is the named delta rejecting predicate-only first-start advice. Local [CLI help receipts](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/cli-capabilities.json) also constrain future placement: Claude `-w` creates a worktree; Codex `-C` binds the working root; Grok help says headless `-p` does not create a worktree from `-w`. These are help attestations, not a native-flag equivalence guarantee or exercised CLI isolation.

## Accepted first slice

[Accepted design](/Users/aipalm/Documents/GitHub/devlyn-cli-0118-concurrent-sessions/.devlyn/0118/accepted-design.md) and [design acceptance](/Users/aipalm/Documents/GitHub/devlyn-cli-0118-concurrent-sessions/.devlyn/0118/design-acceptance.json) reconcile the following; implementation and all tests remain open:

- Canonical root realpath plus private Gitdir identity. Reject presence, including empty values, of inherited `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR` before any Git call; no silent stripping.
- Short `fcntl.flock(LOCK_EX | LOCK_NB)` at a stable private-Gitdir lock inode across admission/archive/prune/initialization in all three modes. **Inside this lock**, reject `.devlyn` and `.devlyn/runs` redirects, including dangling links, before following them or mutating owned files. No session-lifetime exclusion claim.
- Uniform unfinished/indeterminate refusal before mutation, with no same-session-ID exception. Scan all four exact families across modes: `goal.raw.txt.tmp.*`, `spec-verify.json.tmp.*`, `external-diff.patch.tmp.*`, `pipeline.state.json.tmp.*`; preserve residue.
- One completion predicate shared with prune: a real UTC calendar/time in `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS.sssZ`, plus terminal verdict `PASS`, `PASS_WITH_ISSUES`, `NEEDS_WORK` or `BLOCKED`. Preserve malformed/unfinished archives; retain valid completed autoarchive and existing retention/evidence rules.
- Manual recovery only after prior writers have stopped. A completed report does not prove all interactive writers exited. Preserve ambiguous evidence; do not autoarchive to defeat refusal.

Future verification must demonstrate byte-identical refusal, one synchronized winner with unmixed output, linked-worktree independence, alias/redirect handling, lock stability/release, actual process death before/after writes, cross-mode residue preservation and conservative prune. The spec retains all existing command bounds and installed-mirror parity obligations.

## Three-seat collaboration

Standing roles: **actual Codex `gpt-6-astra` authors and executes** product/spec/docs; **Fable 5.1 handles design, adjudication, planning and verification only**; **Grok 4.6 is the independent static judge, `executor:no` until separate recertification**. Native `direction_audit` and `seat_evidence` supplied read-only supporting audits; they do not replace actual seats. One product writer at a time. Actual final-code review by all three seats remains entirely pending.

| Actual design row | Disposition |
| --- | --- |
| [Fable R1](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/fable-design-r1.txt) | Accepted design with Git-environment finding; correction incorporated and separately reproduced. |
| [Astra R0](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/astra-design-r0.stdout) | Conditional, no source read; already proposed atomic exclusion, not blanket no-lock advice. |
| [Astra R1](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/astra-design-r1.stdout) | Source-verified NEEDS_WORK; temporary residue, strict completion/prune and pre-lock test synchronization findings incorporated. |
| [Grok R0](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/grok-design-r0.result.txt) | Misread that unfinished refusal removes completed autoarchive retracted in reconciliation; completed autoarchive remains required. |
| [Grok R1 validation](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/grok-design-r1.validation.json) | Raw process success, canonical INVALID: summary PASS with binding HIGH findings. Preserve invalid R1 unchanged. |
| [Grok R2 result](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/grok-design-r2.result.txt) / [validation](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/grok-design-r2.validation.json) | Corrected proposal canonically validated PASS, zero findings, emitted `grok-4.6` + `grok-4.6-build`. Actual 9 read calls exceeded prompt max 6: no efficiency or turn-compliance certification. |

Fable/Astra findings are incorporated design proposals, not independent final-code approvals. Design convergence neither executes gates nor substitutes for the final implementation trio.

## Prepared operator and resume

Candidate [run-resolve.py](/Users/aipalm/Documents/GitHub/devlyn-cli-0118-concurrent-sessions/.devlyn/0118/run-resolve.py) is **PREPARED, NOT EXECUTED**; `.devlyn/0118/PARKED` prevents launch. After explicit new-session continuation, first read stop/final-stop evidence and check PID identity; revalidate committed spec, HEAD, clean status, design evidence and prepared runtime/prompt. Only then remove the marker and execute the canonical full pipeline. The launch prompt's committed-spec language is a future precondition, not a current commit receipt. The design receipt's source-spec hash predates the narrow PARK/status and inside-lock clarification; parent owns the exact checkpoint/digest receipts, without rewriting historical reviews.

Operator contract: explicit `CLAUDE_SKILL_DIR=<candidate>/config/skills/devlyn:resolve`, no main fallback or global install; outer workspace-write with network=true, no isolated mode or inherited invocation variables. Fresh canonical phase receipts use network=false for PLAN/IMPLEMENT/CLEANUP and true for BUILD_GATE. Run primary Astra with actual Fable pair; parent owns final Grok and final trio acceptance. Preserve canonical routed phases, independent mechanical checks and raw failures; do not substitute an ad-hoc implementation.

Standing **no code commit before final trio** requires disclosed **inspection-only CLEANUP** with exact before/after HEAD, index and deliverable snapshots. A HEAD diff would mislabel uncommitted IMPLEMENT as cleanup delta. Preserve implementation bytes; report necessary cleanup to parent. Protected `.agents`/Gitdir permission denial remains visible; no bypass or skipped parity. This prepared adaptation does not certify an unmodified route.

## Waiter park and custody

Parent-owned [stop request](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/park-waiter-stop.json): PID **45397**, start **2026-09-05T15:29:40Z**, identity verified; SIGTERM requested **16:10:12 UTC**. Initial 15-second observation was still live during its 120-second sleep. Parent-owned [final stop receipt](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906/park-waiter-final.json) at **16:12:17 UTC** records `PID_NOT_LIVE`. This attests process liveness only. Smoke/cells/collection outcomes are **NOT_INSPECTED**; latest BLOCKED alone does not establish they never started.

No automatic restart while parked. Next session reads both receipts and checks PID identity before any continuation; never launch a duplicate. Preserve `/Users/aipalm/.local/share/nx01/iter0113/quick-a16-1`, run ID `lift-quick-a16-1`, staged product, frozen runner/params/policy and any partial artifacts. [0117/A16](0117-quiet-grok.md#post-closure-checkpoint), [0113 A16 registration](0113-layer-lift-meter-STUB.md#a-16--versioned-grok-quiet-process-detection-0117-2026-09-06) and [0114 collection policy](0114-harness-direction.md#collection-continuation-owned-by-root) retain their contracts. No hidden outcomes, corpus/oracles or scores were inspected for PARK documentation.

Durable packet: [/Users/aipalm/.local/share/nx01/iter0118/park-20260905T161107Z](/Users/aipalm/.local/share/nx01/iter0118/park-20260905T161107Z). Parent finalizes its manifest after custody, including `main-packet/`, `candidate-packet/`, `tracked/` and exact spec/context commit receipts. Working evidence is in the [main packet](/Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/concurrency-20260906) and [candidate packet](/Users/aipalm/Documents/GitHub/devlyn-cli-0118-concurrent-sessions/.devlyn/0118). Parent owns verification, final custody and commits; this document does not claim those future receipts exist. The three context documents are mirrored into the candidate for cold start from either root.

Restart line:

> autoresearch/HANDOFF.md의 START-HERE부터 이어서, 3-seat 협업 규칙을 지키며 0118을 진행해줘.
