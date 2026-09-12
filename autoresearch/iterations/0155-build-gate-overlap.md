# 0155 — Canonical and literal BUILD_GATE overlap

2026-09-12. Baseline `9774517fb3b8688ea3d903100772d5419cdb4196`.
Root implements directly without resolve; actual native Fable 5.1 and Grok 4.6
review independently. Root accepts **PASS_WITH_ISSUES**, zero in-scope
CRITICAL/HIGH. No runtime speed or model-adherence claim follows.

## Why and minimum change

Pre-flight 0 / Mission 1 efficiency: the canonical BUILD_GATE body requires
type/lint/unit gates followed by every literal verification command. The parent
SKILL overview repeats that unconditional schedule. This can schedule the same
obligation twice inside one round, independently of the required later VERIFY.

Archon archive `rs-20260912T061343Z-7edfdc93e507`, round 3, records repeated
`npx tsc --noEmit`, `npm run lint` and `npm test`. All manifest raw-stream hashes
validate. Canonical captures take 1.911/3.753/3.698s; literal captures take
2.002/3.813/3.562s. Both unit captures report 318 tests with the same 600s budget.
Type/lint use 600s versus 60s: equal strings do not prove identical execution
contracts. E2E independently fails after 300.303s; repeats do not explain the
whole 692.479s phase. Historical outcomes and files remain unchanged.

No workaround / No overengineering: remove the unconditional extra scheduling
requirement at the instruction source. Exact current-contract overlap may defer
a canonical gate to its literal invocation, with the same source/test inputs,
work root, effective child environment, assertions and timeout. Unknown or
different conditions keep separate gates. Existing checker precedence/defaults
apply; omitted exit_code still means zero. The worker derives the usual precise
gate findings from current validated raw streams, including nonzero exits.

If literal execution aborts or supplies no validated exit-kind result, execute
the deferred gate normally, retaining literal failures and capability-denial
stops. This preserves error discovery within the same fix round. Every literal,
risk probe and independent post-CLEANUP VERIFY remains required. Scope checking
stays in the checker after its commands. No renderer/kernel/cache/schema/flag
changes. Only the canonical body, parent overview and tracked mirrors change.

## Evidence and review decisions

`.devlyn/0155/prediction.json` predates source changes. The first design used a
timeout partial order and a CRITICAL marker for missing deferred evidence.
Independent final review identified the lost-diagnostics case: a missing probe
file can stop literal execution before type errors are discovered, consuming an
extra fix round. Root replaced the synthetic marker with normal gate execution.

Both reviewers initially recommended literal timeout <= canonical, then changed
to >=. Root rejects >= when a canonical limit is mandatory: a 2s command passes
under a 3s literal but violates a 1s gate. The actual process-evidence runner
confirms this registered counterexample: timeout at 1.007s versus successful
exits at 2.048/2.034s under 3s limits. Root chooses exact timeout equality rather
than adding partial-order machinery. This leaves the observed 600s/60s type and
lint pairs separate; no 9.362s saving is claimed. Runtime conditions come from
opened checker/runner calls, not fields absent from the manifest.

The first full lint fails only two stale owned `.claude` mirror comparisons
after 298.924s; its output is retained. Reconciled those copies and rerun final
checks separately. Actual rendering with Claude/Codex/Grok adapters verifies the
body reaches worker prompts; renderer self-test passes. These checks establish
source delivery and unchanged mechanical regressions, not worker adherence.

Final full lint passes in **308.575s**; final actual renders and exact scope/mirror
checks pass. Fresh final-delta Fable 5.1 **PASS_WITH_ISSUES** (150.393s) and Grok
4.6 **PASS** (270.984s) find no remaining CRITICAL/HIGH; both observe zero tools.
Their full raw streams/usage and earlier NEEDS_WORK advice remain preserved.
Root retains the advisory limits: shell-mapped signal exits can reduce diagnostic
detail; environment equality is conditional; recovered gates follow an already
failed/invalid literal path; task-context obedience is not renderer-enforced.
No universal false-PASS impossibility or full connection-isolation claim follows. Removing the overlap exception
restores unconditional duplicate scheduling; removing its normal-execution
recovery reopens the demonstrated lost-diagnostics design flaw.

## Custody and continuation

Receipt `c0d5a372158bf1964fd8d14d` prospectively owns branch
`codex/0155-build-gate-overlap` in the retained continuation checkout.
Immutable source evidence is `.devlyn/0155-evidence.tar.gz`; delivery is
separately receipt-bound in `.devlyn/0155-delivery/`.
No npm release or frozen/A16 rerun. Real worker adherence, measured full-route
benefit, semantic constraint coverage and matched quality/pair value remain open.

0154's customer patches were explicitly approved and applied locally to all
three AGENTS files at 2026-09-12T10:46:36Z. Exact proposal hashes, whitespace,
unrelated diffs/index/untracked names and unchanged HEAD/branches pass. No
customer commit or push. Evidence: `.devlyn/0154-local-application-20260912/`.
