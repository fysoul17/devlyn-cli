# 0153 — Benchmark pre-staged carrier validation

2026-09-12. Baseline `76cb85b08e8d30275d8f20fef10837c4f68e4a30`.
Root implements directly without resolve; native Fable 5.1 and Grok 4.6
independently review the exact source. Root accepts **PASS_WITH_ISSUES**,
zero in-scope CRITICAL/HIGH. Delivery is separately receipt-owned.

## Why and minimum repair

Pre-flight 0: this iteration removes silent acceptance of unsupported assertions
in benchmark pre-staged verification commands. Mission 1 gate 4: malformed
mechanical evidence must not count as a successful single-task check.

Before edits, `.devlyn/0153/prediction.json` registers 36 real-CLI controls.
Why can a typo pass? Benchmark precedence skips source extraction, then
`validate_shape` checks known value types without rejecting unknown keys or
malformed `contract_refs`. Execution consequently discards those assertions.
The violated invariant is that a consumed contract must validate its vocabulary.

The repair reuses `validate_inline_shape` after the existing nonempty shape
check. Removing benchmark precedence would restore F9's oracle-overwrite bug;
a new validator is unnecessary. The leading shape check remains necessary:
inline-only validation accepts explicit pure-design empty lists, but an empty
pre-staged benchmark must still fail. Runtime probes are appended afterwards
and retain their own vocabulary. No schema, flag, routing or fixture changes.

## Verification and independent review

- All 36 baseline and candidate controls match their registered exit outcomes.
  Fourteen typo/refs/ignored-field/contradictory-design cases across BUILD_GATE
  and VERIFY change from success plus execution to one CRITICAL finding before
  commands or results refresh. The other 22 outcomes stay unchanged. All staged
  bytes retain precedence; no decoy sibling command executes.
- The shipped CLI regression covers five rejection classes in both phases;
  the existing positive precedence case now includes valid `contract_refs`.
  Checker self-test and full skill lint pass; lint takes 349.922s.
- Removing just the added strict validator makes the new self-test fail on the
  first typo case, whose command executes and passes. Mutation/raw failure stays
  in `deletion.log`; temporary mutation files are removed.
- Read-only compatibility checks inspect 38 tracked benchmark oracle files,
  including all six shadow fixtures. Thirty-five nonempty normalized carriers
  preserve validation: 94 visible commands, or 144 including hidden commands.
  Both `run-fixture.sh` and `run-frozen-verify-pair.sh` stage command-only objects.
  No historical commands are executed or results regraded.
- Native Fable `claude-fable-5-1` **PASS_WITH_ISSUES** (115.308s), Grok requested
  and assistant header `grok-4.6`, usage `grok-4.6-build`, **PASS** (259.576s).
  Both observe zero tool calls. Source review is advisory, not a pipeline verdict
  or proof of complete MCP connection isolation; native sidecar usage is retained.
  The initial root audit incorrectly expected Grok's usage name in its assistant
  header; the unchanged raw capture establishes both identities, without rerun.
- AST scope is only `main` and `run_self_test`; the tracked `.agents` mirror is
  byte-identical and whitespace checks pass.

Fable's LOW generic file/fix-hint advice remains: the error message identifies
`spec-verify.json` and the offending key, while structured location/help still
uses the existing general carrier wording. Its test-depth advice is covered by
additional retained controls; shadow carrier compatibility was checked directly.
No in-scope HIGH or unidiomatic MEDIUM finding remains.

No workaround / Production ready: unsupported assertions fail before execution.
No overengineering / Best practice: reuse the existing validator; deletion of
its one call reopens the reproduced failure. Optimized / layer-cost-justified:
no extra model or phase dispatch in the product. This is source integrity repair,
not a model-performance, full-pipeline false-PASS or Mission 1 superiority claim.

## Custody and continuation

Retained checkout: `~/.local/share/nx01/core-continuation-20260912`.
Receipt `f9d7c95fac90f43c8b4e3830` was allocated before changes; the prior dirty
research checkout and original user files remain untouched. Immutable source
acceptance evidence is `.devlyn/0153-evidence.tar.gz`. CI/merge evidence goes to
`.devlyn/0153-delivery/` before final completion. No npm release.

Next is the ordinary-small-request routing investigation, then full-route
cost, semantic constraint coverage and matched comparative quality. Those four
research priorities stay open. A16 and frozen comparisons remain unchanged.
