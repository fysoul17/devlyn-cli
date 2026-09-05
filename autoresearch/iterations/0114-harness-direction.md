# 0114 — harness direction and honest layer-lift measurement

**USER-PARKED, 2026-09-05.** Parked run
`rs-20260905T104352Z-29990a258793`: PLAN/IMPLEMENT PASS; missing-state initialization/regression and refreeze
implemented, uncommitted. Current BUILD_GATE was interrupted by user with partial
evidence; full acceptance and actual corrected-diff final trio are suspended
on user request; fresh collection is NOT LAUNCHED. PHASE0 baseline was captured
before the first worker. Prior rs100953 is archived `BLOCKED:phase0-baseline-missing`:
seven commands exit0, overall BUILD_GATE FAIL from root’s omitted baseline;
no CLEANUP/VERIFY/final trio. [Accepted correction](../../.devlyn/fix-0114-pair-stream-20260905/accepted-missing-state-design.md):
plain `pair_verdict = None` before state branching, valid-state assignment retained.
Actual Fable 5.1/Grok 4.6 design GO; Grok prose is transport-attested but
collector-rejected, not canonical JUDGE PASS.

## Checkpoint

**USER-PARKED at 2026-09-05T11:05:55.872448+00:00 (20:05:55 KST).**
[Stop proof](../../.devlyn/fix-0114-state-capture-20260905/parking-stop.json)
records actual wrapper exit 0 after SIGTERM, a completed exit-0
[invocation receipt](../../.devlyn/build_gate.invocation.0.json), no final worker
verdict and `remaining_owned_processes=[]`.
[Canonical state](../../.devlyn/pipeline.state.json) retains PLAN/IMPLEMENT PASS
(IMPLEMENT completed `2026-09-05T10:59:40.141Z`); the
[focused receipt](../../.devlyn/fix-0114-state-capture-20260905/implement-evidence.json)
records green in 58.320 seconds. Exactly five sealed BUILD_GATE commands exited 0;
lint was interrupted, command 7 and the scope gate are incomplete. BUILD_GATE
round 0 remains open with `completed_at`/`verdict` null: no overall PASS/FAIL,
exit-143 verdict, product failure or exhaustion. Preserve state, invocation,
[worker session](../../.devlyn/build_gate.worker-session.0.jsonl) and
[partial command evidence](../../.devlyn/process-evidence/rs-20260905T104352Z-29990a258793/build_gate/round-0/)
byte-exact, including explicit park-packet preservation of unbound raw evidence;
normal archive ownership must not be assumed to cover every unfinished file.
Correction/refreeze remains uncommitted WIP; no CLEANUP, independent MECHANICAL,
actual final Codex/Fable 5.1/clean Grok 4.6 trio, implementation commit or new
collection occurred. Full acceptance is suspended.

- Base: `4b5bb0a39fcf3b5122f1104ca3adfa6c58da0ec1`; keep the cumulative
  WIP uncommitted until root completes full gates and final review.
- Contract: [`spec.md`](../../docs/specs/0114-harness-direction/spec.md),
  SHA256 `e11e2b239e91d72854bb0a346094eaa17aeeee3f6c587cc56c0fa2490e8702d4`;
  sibling `spec.expected.json` owns the seven verification commands.
- Historical parking stopped run `rs-20260905T074941Z-1b68ecba41e8`
  during IMPLEMENT (wrapper exit 143); its archived `started` receipt is
  incomplete. Preserve that archive and earlier superseded PLAN-only runs.
  Durable bundle: `~/.local/share/nx01/iter0114/park-20260905/`; its manifest
  seals the parked WIP, proofs, research receipts and run archive. Prior
  preservation checks remain 116/116 proofs and 188/188 bundle entries;
  these are historical receipts, not checks rerun in this IMPLEMENT.
- Accepted design/proofs: `.devlyn/direction-20260905/`; external design
  receipts also live in `~/.local/share/nx01/iter0114/design/`.
  Prior refreeze evidence: `.devlyn/resume-0114-20260905/implement-evidence.json`.
  Historical inspection: adjacent `restarted-implement-evidence.json`. Current
  [correction evidence](../../.devlyn/fix-0114-state-capture-20260905/implement-evidence.json)
  links verified missing-only root red and focused green (58.320 s), snapshot/pins
  and the rejected deletion that restores the proven failing function.
- A15 refreeze: runner
  `8694c9fdb0149b3f985398d503a559d058d42010194872063a09b293baed12f5`; apparatus
  `644fef268345b0c9a435f7a28bb825d2c14122c07efacacfecb8b97fa39881c1`,
  params `38e0761882a9e2f4d3aab32e6d2d238ffe5dcca342f00b45d6e6dd8bb2cc425b`;
  seven seals written; normalization unchanged after both pin replacements.
  Product staged digest stays
  `ee8f74d4d2a5061c36b1ad2b4459f6801f08af3b0d08d069a756532bdb8a89f1`;
  product skills/mirrors, root AGENTS/CLAUDE, corpus, panel, seats, reps,
  thresholds and drain script stay unchanged. No implementation commit/push.
- Old `quick-1` is stopped and preserved. Fresh
  `~/.local/share/nx01/iter0113/quick-a15-1` / `lift-quick-a15-1` remains
  USER-PARKED/NOT LAUNCHED until explicit user resume and full acceptance.

## Accepted direction and evidence

Keep minimal, verifiable intent closure and measured adaptive work as the
direction. Actual quality AND efficiency must establish `bare < solo < pair`;
this is a falsifiable target, not a guaranteed ordering. Under **No guesswork**
and **No workaround**, repair the measurement defects before interpreting lift.
Under **No overengineering** and **Optimized**, share existing isolation and
delete the nested deadline owner. No blanket removal of resolve or pair follows.
Conversation may authorize implementation (0069.1); once resolve is entered,
all phases remain mandatory and executor pins bind. VERIFY pair remains default
when available. The 0070 aggregate/off-resolve closure is not fully shipped.

The original direction contract is `.devlyn/direction-20260905/accepted-design.md`;
its A15 stdout rule is superseded by the [accepted correction](../../.devlyn/fix-0114-pair-stream-20260905/accepted-design.md),
the committed spec and parked `.devlyn/plan.md`. Original synthetic red proofs
established four defects without opening sealed panel outcomes:

| Defect | Raw evidence under `.devlyn/direction-20260905/` | Accepted correction |
| --- | --- | --- |
| Early product BLOCKED retained in L1 but replaced as infrastructure in L2; canonical mechanical skips also rejected | `early-blocked-proof.log`, `mechanical-blocker-proof.log`, matching proof scripts/directories | Retain product failure in both arms; strict `pair_judge_ran` separates established not-run from missing executed evidence; smoke still requires an actual pair |
| Token ratios used totals over unequal 4/1/1 repetitions: actual 8× per-run load yielded 2 | `token-rep-normalization-proof.log`, `token-rep-proof/` | Exact Fraction means per base run; retain raw totals, top-up exclusion, wall/quality arithmetic and unknown usage |
| L0 inherited HOME/ZDOTDIR/PATH/BASH_ENV/ENV while harness arms used isolation | `l0-isolation-proof/result.json` | Same existing isolation for all arms; L0 stays goal-only and unstaged; forward exact `--allowedTools`, never substitute `--tools` |
| Nested run-bounded session escaped driver group cleanup and hung collection | `l0-timeout-proof/result.json` | Driver alone owns 1800/3600 seconds including setup; remove obsolete external-wrapper registration/seal; ordinary descendants stopped and scratch cleaned |

Among declared product BLOCKED outcomes, only exact `BLOCKED:claude-unavailable` and
`BLOCKED:codex-unavailable` are infrastructure in both harness arms. Other
product BLOCKED outcomes cannot receive free retries. Executed pair evidence
retains exact model/version/effort/stream checks. Canonical not-run requires
unopened VERIFY plus BLOCKED, or the exact mechanical-blocker shape; contradictory
captures or judge results remain invalid. Whole-driver TIMEOUT preserves the
registered unknown-usage rule: ABSENT metadata alone is allowed; present but
malformed/unreadable/wrong-identity metadata remains infrastructure.

Known limits: fixed captures from an earlier pair round beside a final
mechanical skip still reject; false engine-availability assertions are not
distinguishable from truthful ones using these observables. Attempts remain
capped. Ordinary descendant cleanup does not prove containment of explicit
session escapes; buffered isolation output may leave no partial transcript.

Real CLI debates used Fable `claude-fable-5-1`, Grok requested `grok-4.6`
(reported `grok-4.6-build`), and Codex `gpt-6-astra`. Final convergence receipts:
`fable-r2.txt` / `grok-r3.txt` (outcomes), both `*-token-review.txt`, then
`fable-timeout-reconcile.txt` / `grok-isolation-final.txt`. The Fable timeout
reconciliation supersedes its mandatory-metadata objection using the original
A6 registration as the named criterion. Grok's isolation reversal cites the
old wrapper's surviving descendants versus shared-launch timeout/interruption
cleanup, with exact allowedTools forwarding. Raw receipts are preserved. These are design reviews, not final WIP
verification. Use `--no-memory` for future Grok seats.

The resumed bounded review found one R7 gap: during launcher prep, SIGTERM
could end the leader before `communicate()` timed out, leaving descendants.
Root's `prep-interrupt-red.json` records exit 1, `ordinary descendant survived`;
`finally-placement-proof.json` records a blocking reap until external kill at
2.009 s for a 1 s bound. The correction moves interruption kill **and reap**
together into `finally`, and adds prep interruption to the existing matrix.
Fable's final placement follow-up was quota-blocked; root authorized this R7
correction, with final actual-diff trio review still pending.

## Exam validity and evidence limits

See `exam-validity-summary.md` in the receipt bundle. Iter-0068's mismatched
visible HH:MM versus hidden ISO input and identity/environment leakage invalidate
that exam; they do not prove the causal effect of leakage. Iter-0067's valid
negative result (objective ties, blind-quality loss, wall overhead) remains a
harness-improvement signal. Preserve both lessons; never ease the exam to force
the desired ordering. Quick-12 is a disjoint M screen; full-32 confirms.
Two improvements of δ=.30 need more than .60 combined headroom; a .10 saturation
cutoff alone does not establish that headroom. NULL means CI within ±.30,
not that pair is unnecessary. NULL/INCONCLUSIVE do not automatically disable it.
Token usage is a Claude-output plus Codex-total proxy; the oracle-perfect
best-of-N comparator is conservative. No universal-model superiority follows.

Baseline-only checks passed before edits (runner 26/26, scorer 16/16, drain
10/10, lint and hashes): `baseline/summary.json`. Partial implementation evidence
is in `implement-green/` and `implement-focused-captures.json` (29 captured
commands with exits/output). Some printed smoke FAIL lines are deliberate
negative fixtures. Neither these focused checks nor the old baseline establish
a full green A15 suite. Prior-run focused receipts under
`.devlyn/resume-0114-20260905/implement-focused/` record predicted synthetic
runner/scorer/option checks; runner after the prep correction exited 0 in 44.541 s with all four lifecycle
cases PASS; scorer and option checks exited 0 in 3.021 s and 0.132 s.
The false-pair smoke FAIL is an intentional negative control. Those receipts
remain historical; the current focused correction has separate raw captures.

Prior full run `rs-20260905T083049Z-935af59bc8ad` is archived
`BLOCKED:process-evidence-invalid`; archive report:
`.devlyn/runs/rs-20260905T083049Z-935af59bc8ad/final-report.md`.
BG0 is immutable FAIL: 6/7 commands exited 0; lint hit its 600-second bound
because inherited outer `CODEX_MONITORED_TIMEOUT_SEC=1800` reached the unchanged
nested fake-wrapper self-test, leaving watchdog sleep holding stderr.
Actual Fable 5.1 and Grok 4.6 R0/R1 jointly accepted env-only recovery with
failed evidence preserved. Round1's Codex config exclusion failed its real
presence check before any commands; completion correctly refused absent
current process evidence. No fake PASS, rewritten FAIL or completed round1
is claimed. Raw receipts: `.devlyn/resume-0114-20260905/`, including
`recovery-adjudication.md` and `lint-clean-env.json`; the clean-env self-test
passed in 2.288 seconds, diagnostic only. That archive remains historical; the subsequent completed review and current
correction are distinguished below.

Completed review `rs-20260905T092108Z-8e9404a2d660` is archived NEEDS_WORK,
findings iteration 1/3: BUILD_GATE 7/7 and independent MECHANICAL 7/7 passed;
actual Codex HIGH [A15-JUDGE-001](../../.devlyn/runs/rs-20260905T092108Z-8e9404a2d660/verify-merged.findings.jsonl)
binds despite Fable PASS and Grok PASS (no majority override). Old Grok's MCP-memory
access limits freshness. Raw `codex-judge.stdout` remains beside the merged receipt.
PLAN-only `rs-20260905T095801Z-392cb0a8fb6f` is superseded: worker PASS, incomplete
lifecycle after standalone completion rejection, no code implemented. Its corrected
archive report preserves the original. Spec-only commits `495585e`, `5e98a13`,
`854e3f4` are owner amendments, not implementation shipments.

Named design delta: actual Fable R1 cited `verify.md:245–248`, confirmed by
`verify-merge-findings.py:1298–1319`; emission rejection is product BLOCKED,
so flat parse-failure→infrastructure would restore unfair retries. Actual isolated
Grok R1 also returned GO: [Fable](../../.devlyn/fix-0114-pair-stream-20260905/fable-design-r1.txt),
[Grok validated receipt](../../.devlyn/fix-0114-pair-stream-20260905/grok-design-r1.validation.json).
Fable's auxiliary Haiku envelope usage was resolved through the existing unique-primary
selector; the meter's singleton policy is unchanged. Frozen source collection now
normalizes max(summary/finding ranks), or BLOCKED on SystemExit/invalid UTF-8;
claimed pair rank cannot understate it. Root separately opened terminal acceptance
and shipping arithmetic: normalized binding output cannot accompany overall
PASS/PASS_WITH_ISSUES even when the pair sub-verdict is truthful. Truthful nonshipping
BLOCKED stays retained/nonretryable; missing captures/I/O/wrong identity stay infra.
Actual pair/driver TIMEOUT preserves incomplete-output and unknown-usage allowances.
Fresh final actual corrected-diff reviews are suspended on user request.

Observed follow-ups outside frozen A15: wrapper orphan watchdog sleep;
self-test's unpinned ambient timeout; ineffective shell exclusion on this
route; missing completion route for a pre-verification environment blocker.
These are recorded limitations, not changes implemented here.

## Resume-only continuation owned by root

While USER-PARKED, perform none of the following actions. Only an explicitly
resumed session may proceed:

1. Read HANDOFF START-HERE and this checkpoint. Preserve parked state, WIP,
   baseline, prompts, invocation/session and partial command evidence before
   any lifecycle action; compare actual HEAD/spec/source/seals to this checkpoint.
   Keep Fable 5.1/Grok 4.6 collaboration and the pinned Codex writer. Never
   overwrite round-0 evidence or rerun this packet's one-shot bootstrap/helper outputs.
2. Reconcile actual interrupted BUILD_GATE receipts through shared state machinery.
   An open span cannot be respawned; a fresh round requires honest accepted completion
   first. Do not fabricate incomplete seven-command evidence to make completion pass.
   If completion is unavailable, preserve/archive the incomplete run through the
   existing owned-artifact archive/bootstrap route, then run a fresh normal resolve
   with the same committed owner spec and preserved WIP. Bootstrap requires a clean
   tracked baseline: use the already authorized scoped temporary stash/byte-exact
   restore route and mandatory untracked-baseline writer before any worker. User
   parking alone is not a product finding or grounds for a spec amendment/fix commit.
3. Complete full BUILD_GATE → inspection-only CLEANUP → independent MECHANICAL
   → actual Codex/Fable 5.1/clean Grok 4.6 final review on the final diff. CLEANUP
   proves no-op with WIP/index and real HEAD snapshots. Only after all gates/trio
   may root commit the implementation and launch the authorized quiet-gated fresh
   `quick-a15-1` / `lift-quick-a15-1` drain. Invoke `spec-verify-check.py` directly
   through `env -u CODEX_MONITORED_TIMEOUT_SEC`, clearing only that leaked key;
   preserve seven exact inner commands, bounds (600/120/120/120/60/600/60 seconds),
   parent 1800-second watchdog, `workspace-write` and `network=true`.
   Prediction on resume: unchanged checks finish within their bounds; record actual
   failures as well as passes. Retain quiet account, usage ≤10%, no other CLI seats,
   outside 23:00–01:00 KST, one lane, actual-pair smoke, 72 base cells (4/1/1),
   infra-only attempts 2/3 and identical digests. Never reuse old rows under new
   digests; follow exact scorer `NEEDS_TOPUP`, evaluate once and record `LIFT-0113:`.

4. Positive quality AND efficiency screens earn registered full confirmation.
   Quality lift with inefficiency drives a bounded cost reduction; valid
   quality harm/negative results drive a bounded correctness/claim change.
   NULL/INCONCLUSIVE preserve uncertainty and do not automatically remove pair.
   M′, cross-vendor bare and 0112 venue work need separate registration.

The next product candidate is design-only: extend existing SURFACE_CLOSE
rollback-and-audit recovery to exactly the observed malformed, citation-missing
and out-of-surface adjudication classes. Preserve parser rejection, input/prompt
checks, actual-mutation/execution limits, rollback, residual/transcript audits,
attestation and mandatory downstream verification. Null verdict and an honest
class-specific skip reason never grant PASS. Unknown classes still halt.
Receipts: `surface-close-candidate.md`, `fable-sc-final.txt` (GO exact three,
superseding the initial family-wide proposal), `grok-sc-design.txt` (KEEP exact
three). No candidate spec/worktree/code is part of 0114. Develop it in a
separate worktree without changing the frozen baseline; fast synthetic work
need not wait for the long panel (HANDOFF hard rule 8). Promotion still needs
its own registered comparison. A removed premature halt alone proves no lift.

## Principles check

- **Pre-flight 0:** this iter closes reproduced meter defects so 0113 can
  decide the next correctness/cost change without free failure retries or
  repetition-biased efficiency.
- **#7 Mission-bound:** serves [Mission 1](../MISSIONS.md) quality/efficiency
  gates through its existing fixed layer comparison; no fleet work.
- **#1 No overengineering / #3 No workaround:** remove unconditional pair
  evidence, redundant L0 environment and nested deadline ownership. Retain
  only the lifecycle carrier (R1/R2), exact forwarding option (R7) and
  synthetic regressions for the reproduced defects. Further deleting the
  exact allowedTools forwarding fails its option regression (R7); retain it.
- **#2 No guesswork / #5 Best practice:** preserved red/focused receipts;
  current source inspection, existing launch seams and exact Fraction means.
- **#4 Worldclass production-ready / #6 Layer-cost-justified:** full review
  and empirical quality/efficiency gates remain open; deterministic A15
  checks alone establish neither whole-harness readiness nor runtime lift.
