# 0139 — Post-release Mission 1 validation

2026-09-09 KST. **PREPARATION; NO TRIAL OR COMPARISON LAUNCHED.** The user
authorizes finishing the remaining gates sequentially. Root decides; requested
read-only advisors are Fable 5.1 and Grok 4.7, with temporary Opus 5 / Grok 4.6
substitution only for a usage limit or unsupported requested version. This is
the research team preference, not a change to installed product defaults.

## Evidence and next action

The release is complete ([0138](0138-v3-release.md)); all Mission 1 gates remain
binding ([MISSIONS](../MISSIONS.md)).
[0137](0137-public-issue-execution.md#successor-completion--2026-09-08) supplies
functional Click evidence with repairs and reporting handoff. Its root-selected
task does not satisfy NORTH-STAR operational test 15.

First obtain an independent developer's selection and execution of a fresh
real-codebase task. Required prelaunch record: developer's relationship to the
harness, repository and exact base revision, original goal/issue, executable
acceptance conditions, existing project gates, chosen CLI/model/roles and total
completion-time budget. These fields are **PENDING**; a root-selected issue or
a fresh AI reviewer does not substitute for that developer. The developer
input request is pending. No upstream contact or publication is authorized by
this preparation.

## Sequence and admission

1. **Independent real-project trial.** Install the published `devlyn-cli@3.0.0`
   through the ordinary installer, retain package/source/config identities and
   unchanged customer baseline checks, then let the independent developer run
   the normal installed resolve entry on the original goal or spec. Resolve
   owns its normal repair rounds, report and archive. Apply [NORTH-STAR test
   15](../NORTH-STAR.md#real-project-trial-gate-codex-r2-2026-04-28): existing
   suite and developer acceptance pass within the agreed budget, with no
   manual prompt edits or phase reruns. A reporting handoff or post-run repair
   leaves the uninterrupted-completion claim unmet. Preserve a failed row;
   any later repair/attempt is separately identified.
2. **Quality and completion-time comparison.** After trial acceptance, freeze
   a separate prospective registration for Claude and Codex, each with L0
   direct use, L1 solo harness and L2 paired harness. Match the task, base,
   visible acceptance, model/version/settings and budget within each contrast;
   record actual dispatch identity. Hold probes and other settings constant
   for a judge-only ablation, and report default-product comparisons separately.
   Measure correct resolution and missed requirements first; include review,
   repair, reporting and independent acceptance in completion time. Retain
   failures, timeouts and infrastructure invalidity as distinct outcomes.
   Predefine repetition count, order, best-of-N/M selection cost, loss rules
   and the independent confirmation population before launch. Apply the
   [three-layer contract](../NORTH-STAR.md#the-3-layer-performance-contract);
   unknown provider OUTPUT/cost stays unknown, with reasoning counted once.
3. **Ceiling comparison.** Only after the prior gates pass, use the same frozen
   candidate in devlyn / bare-best-of-N / copycat-best-of-N comparisons under
   the [ceiling contract](../NORTH-STAR.md#the-ceiling-contract-added-2026-07-06).
   The copycat gets public docs and the same frontier models. Freeze objective
   acceptance, calibrated blind cross-vendor grading, matched wall budgets,
   population/sample size and losable thresholds before results. Confirmation
   excludes every task exposed during tuning, including the new trial.

These are preparation requirements, not a frozen executable registration or
permission to infer superiority from a small pilot. The existing layer runner
accepts only `claude-*` models (`benchmark/layer-lift/run-lift-panel.py:1479`);
its registered Astra pair and the historical ceiling runner's fixed stack
cannot establish the requested new model comparisons unchanged. Reuse their
mechanisms only in a separately registered candidate. Frozen A16 stays parked;
its partial collection is NOT_INSPECTED, not assumed NOT_RUN. Preserve closed
negative experiments. Exposed Click3362, F23/F25 and historical reviewer packets
remain development evidence, excluded from fresh confirmation.

## Current execution blockers

Actual availability-only calls retained in
`.devlyn/0139-mission1-continuation-r0/` used the installed Claude 2.1.263 and
Grok 1.0.13, without changing credentials, product settings or sandbox policy.
Neither call reached model verification:

- Requested `claude-fable-5-1`: native exit 1 in 0.589s; result says
  `Not logged in · Please run /login`, `terminal_reason=api_error`, empty
  `modelUsage`, zero input/output. The user subsequently confirmed that Claude
  is logged in in the adjacent normal terminal. This is an authentication
  visibility difference in the agent environment, not a demonstrated account
  logout. Native direct `auth status` also failed inside the current sandbox;
  Keychain lookup failed there. Earlier successful0136 execution required a
  host launch (`fable/review.py:29` under its advice artifact directory).
  Keychain access restriction remains the leading explanation; the user's
  host report does not itself attest the exact failing OS operation.
- Requested `grok-4.7`: native exit 1 in 4.812s;
  `FS_PERMISSION_DENIED`, `Couldn't create session`, `Operation not permitted`.
  `grok models` listed 4.6/4.5 but also reported
  settings-fetch failures; that does not establish live 4.7 availability.

Neither result establishes the authorized model-fallback condition. No Opus
or Grok 4.6 replacement was invoked; an auth/filesystem failure is not resolved
by silently changing models. Pair review and all measured runs remain pending
a runtime that can authenticate and create native sessions under its allowed
permissions, plus the independent developer's task record above.

Internal Codex review checked this preparation against the source contracts
and retained native receipts; local link and whitespace checks passed. That
review is not the requested Fable/Grok pair review or measured task acceptance.

Principles: **No guesswork** preserves actual failures and scoped claims;
**No workaround** preserves execution boundaries; **No overengineering** reuses
existing measurement mechanisms.
