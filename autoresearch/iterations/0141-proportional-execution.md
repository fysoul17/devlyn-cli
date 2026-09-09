# 0141 — Proportional conversational execution

2026-09-09. User reports v3.0.0 takes too long for small work, still misses
requirements, and asks root to investigate with actual Fable 5.1 and continue
0140. Priority remains correctness/completeness, verified completion time, then
output/cost. This is a bounded development improvement, not Mission 1 closure.

## Evidence and why-chain

0140 remains CLOSED_NEGATIVE_SUPERIORITY_SCREEN: H2 706.187s, bare Fable
142.589s, H1 821.702s with a missed prohibition, bare Astra 105.341s.
The exposed security/API task is not eligible for a low-risk direct shortcut.

| Archived phase | H2 seconds | H1 seconds |
| --- | ---: | ---: |
| PLAN | 142.013 | 217.535 |
| IMPLEMENT | 91.433 | 141.503 |
| BUILD_GATE | 106.893 | 123.006 |
| CLEANUP | 57.723 | 64.647 |
| VERIFY | 208.133 | 200.077 |
| FINAL_REPORT | 23.293 | 5.019 |

BUILD's eight sealed commands took 5.396s/3.760s; VERIFY's eight took
5.261s/5.258s. H2 judges took 36.834s and 34.986s concurrently; H1's judge
57.173s. Phase spans include dispatch/collection and unsealed commands; residual
time is not all model inference. Different H1/H2 patches do not identify causal
pair contribution or prove zero pair cost. Raw states and the derivation are
under `.devlyn/0141-proportional-execution/historical-timing.json`.

Why does tiny work enter the whole pipeline? CLAUDE.md's original line 54
explicitly says small tasks invoke resolve, and resolve's description triggers
on every ordinary fix/implement request. Why doesn't the trivial classifier
help? It reduces mini-spec depth, not worker count or phase graph. This conflicts
with the existing conversational implementation permission in DECISIONS 0069.1.
The executor paragraph already permits direct delegation; the pin is not the
root cause and remains binding. Principles: No guesswork, Optimized,
No overengineering, Goal-locked execution.

Why did the Any prohibition pass? The eight executable checks did not encode
that clause, while native primary and a separate blind Fable review missed it.
The spec template misleadingly maps semantic “no any types” and “no silent
catches” to regex; the existing kernel searches whole diffs including deleted
and context lines. Scope-aware, suitable checks and known-bad/allowed controls
are the repair at authoring time, not another generic judge instruction. The
0140 spec was owner-authored; use of this template in that omission is not
established. The template defect is a separate recurrence risk.

## Actual Fable discussion and root decision

Fable 5.1 R0 completed in 113.585s. It identified fixed phase costs and proposed
removing direct-route ambiguity, skipping trivial BUILD/CLEANUP, consolidating
VERIFY and mechanizing prohibitions. Root rejected unproven claims that
finish-gate replaces semantic cleanup/CI gates or that a one-test small-task
classification protects quality. Root also corrected the pin attribution and
whole-diff regex assumptions using opened source.

R1 timed out at 180.596s with no result; it is not a completed consultation.
A smaller R2 with the named counterevidence completed in 26.488s on actual
Fable 5.1. It accepted the narrowed change: classify after inspection, default
full when inconclusive, retain explicit full/pinned routes, and replace wrong
regex advice only with appropriate existing carriers. Native output also
reports ancillary Haiku usage; no whole-provider cost claim follows.

Root chose the existing conversational route for clear, local, reversible,
low-risk edits with decisive checks and final diff review. Security, public API,
data/state/concurrency, unclear scope, formal specs/queues and explicit resolve
keep the full machinery. No new router, flag, state schema, global language
scanner or omitted full-run worker/judge. Source work is governed by
`docs/specs/proportional-conversational-execution/` (owner commit f8e5374).

## Development controls and registration

Before any natural-entry comparison, `.devlyn/0141-proportional-execution/`
records REGISTRATION.json, fixed copy/label cases and the runner. Two tasks,
four sequential Fable 5.1/medium entries: copy old/new, label new/old, at most
1800s each. Same ordinary prompts, tool settings and exact native version
2.1.266; no forced resolve/direct invocation. Both use normal installed skills.
Model selection and task context are held within each pair; the instruction
change is the treatment. Old already-direct means no route-gain claim. Native
comparisons wait for source validation and risk-route controls. A candidate
quality/routing miss rejects adoption; timings are descriptive development
observations, not statistical superiority. No retry or winning-only denominator.

Existing Ruff 0.11.11 ANN401 detects the frozen H1 addition: baseline 10
findings, final 11, one new `value` diagnostic. Direct, alias and quoted Any
controls are caught; `list[Any]` is not. This establishes a bounded detector,
not the full no-Any semantic contract. A whole-file lint failure would also
incorrectly reject allowed pre-existing annotations without baseline handling.
The kernel's literal suppression guard rejects new `@ts-ignore` while accepting
deleted/context/header/allowed controls. These are diagnostic controls, not a
claim that future models always author complete guards. Raw results are retained.

## Implementation execution

The first root-tree bootstrap correctly refused pre-existing dirty HANDOFF;
no user file was changed. Work moved to the isolated
`codex/0141-proportional-execution` worktree. Full run
`rs-20260909T121108Z-a4b6f265d6fe` passed PLAN, then IMPLEMENT reported BLOCKED:
workspace-write denied the authorized tracked `.agents/skills` mirrors. No
product diff was written; original report/finish/archive completed BLOCKED.

[Official permissions documentation](https://learn.chatgpt.com/docs/permissions)
plus a real native probe established that
`--add-dir <exact worktree>/.agents/skills` supplies the authorized write root
while retaining workspace-write and network=false. The named-profile sandbox
probe also passed, but profiles do not compose with the required legacy
`--sandbox` route, so the successor uses the standard additional-directory
option. No user/global config was changed and no bypass was introduced.
Distinct run `rs-20260909T122634Z-4e9dcb82d21a` uses the same committed spec.

Earlier 0140/copycat and parked A16 results remain immutable. The original
main's dirty HANDOFF and untracked 0139 preparation are hash-pinned and preserved.


## Completed source acceptance

Candidate `a30acb51608ac8daaa055ac13f354d0a60945857` changes exactly the
11 licensed instruction files: 32 insertions, 22 deletions. No phase graph,
worker/judge route, runtime/schema or model change. Each retained addition
carries the explicit owner requirement: deleting inspection/decisive-check
conditions weakens the direct gate; deleting full-risk/explicit/spec/queue
exceptions licenses a bypass; deleting semantic/scope/control guidance restores
the demonstrated authoring defect. No further independent branch/helper was
needed. Canonical/mirror parity and the cumulative whitespace check passed.

The distinct full source run completed PASS through PLAN, IMPLEMENT,
BUILD_GATE, CLEANUP, VERIFY, finish gate and archive. CLEANUP changed nothing.
Both BUILD and post-CLEANUP VERIFY ran the two exact expected commands; complete
skill lint passed each time. Fresh Codex primary and Claude pair independently
returned PASS with zero findings in 60.688s and 19.432s, concurrently. The primary
native header identifies gpt-6-astra; the unconfigured Claude pair model is not
claimed from its engine name. Prior Fable design consultations and the route
probe have explicit Fable model receipts. During 3.0.1 branch cleanup, the full
worktree evidence (including both run archives) was preserved and rehashed in
`.devlyn/0141-proportional-execution/worktree-custody/ignored-evidence.tar.gz`;
the adjacent `manifest.json` records every retained file before worktree removal.

This development run itself took about 21 minutes through final report, excluding
the earlier BLOCKED run and research. It is not small-task latency or a speed
win. Phase timing includes parent work between invocations. BUILD's native
capture is 1,266,266 bytes and includes an unnecessary repository-wide hash dump;
that is an observed source of context/output overhead, not a reason to call all
phase residual time inference. Full-route context/dispatch work remains an
optimization frontier; this patch does not remove its checks on assumption.

## Natural-entry results — no demonstrated route or speed gain

All four registered entries ran exactly once and exited zero with owned
processes quiescent. Both normally installed arms exposed devlyn skills in the
native startup record. Their tracked input sets match; the only differing
installed bytes are CLAUDE.md and four changed skill/template files. The
post-v3.0.0 installer-help/README edits did not change the installed treatment.
No forced skill call or direct-route instruction was added to either task prompt.

| Task | v3.0.0 seconds | Candidate seconds | Actual route | External acceptance |
| --- | ---: | ---: | --- | --- |
| Exact README sentence | 14.751 | 14.819 | Both direct, two Bash calls | Both PASS |
| Private singular label + regression | 18.993 | 17.945 | Both direct, two Bash calls | Both PASS |

Times are the unchanged observer's wrapper-return wall seconds, including native
startup through native final response. Setup and root external acceptance are
excluded, and raw native-reported durations are also retained. No Skill/Agent
call or `.devlyn` lifecycle appeared in any cell. The old-small-task mandate
was therefore not reproduced in these Fable entries. The named delta from the
prediction is **both old runs already selected direct**: these results provide
no route-gain evidence, and n=1 per task/arm provides no stable speed advantage.
No additional trials were drawn to rescue a favorable result.

Both copy outputs matched the requested replacement byte-for-byte and preserved
all other tracked bytes. Both label outputs preserved every existing test and
`_debug_label`, passed four tests and the visible label cases, added no Any
annotations/type suppressions/dependencies/configuration, and changed only the
two licensed files. Each new regression fails against the original buggy
implementation in a separate disposable control directory. Root reviewed the
complete small diffs in addition to the bounded AST checks. This is observed
regression safety on these inputs, not a general error-free guarantee.

The separately frozen classification-only probe used actual Fable 5.1/medium
and completed in 7.368s: 12/12 expected routes (2 direct, 10 full), including
one-line security/payment/persistence/concurrency/public API changes,
inconclusive inspection, explicit resolve, queue, formal spec and mid-edit
escalation. These supplied-fact classifications do not establish real-world
risk-discovery recall or execute the full risky workflows.

Raw custody under `.devlyn/0141-proportional-execution/`:
- `REGISTRATION.json`, `cases/`, `candidate-inputs.json`,
  `installed-input-delta.json`, `case-baseline-controls.json` freeze the inputs.
- `cells/<case>-<arm>/` retains prompt, plan and pre-change hashes, native streams,
  descendant census, done result, complete diff and external acceptance.
- `native-results.json` contains timings, observed routes, caller-scoped native
  modelUsage and SHA-256s for each result/stream/diff/acceptance artifact.
- `route-controls.*` retains the separate prediction, source prompt, exact model
  output and all 12 answers. Ruff/literal control files retain earlier raw checks.

Only terminal caller modelUsage is retained as usage evidence; repeated streaming
snapshots are not summed. Whole-provider output/cost and the development/research
budget are not conflated with these four task timings.

## Decision and remaining frontier

Adopt the bounded conversational-entry correction and truthful constraint
carrier guidance. The explicit user request and contradictory mandatory text
justify the contract correction even though this Fable sample showed no route
gain. Keep **NO_DEMONSTRATED_NATIVE_SPEED_OR_GENERAL_ACCURACY_GAIN** as the result;
the new wording is not a runtime guarantee. The 0140 Any miss is reproducibly
catchable with an appropriate existing check, but this change does not prove
future authors always generate complete checks or repair every semantic miss.

Full-route dispatch/context overhead, practical risk-discovery accuracy, general
constraint-coverage recall, comparative quality and causal pair value remain
unproven/open. A useful next performance experiment must first reproduce a real
ordinary small request entering full resolve, with its actual engine, installed
contract and command traces; synthetic cases already direct cannot measure that
benefit. Do not reopen the prior copycat or parked A16 by treating this screen as
a Mission 1 win. No version bump or package publication was performed.
