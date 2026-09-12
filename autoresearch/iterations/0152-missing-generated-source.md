# 0152 — Missing generated source integrity

2026-09-12. Baseline `a301aa4dd57df4e0552cd51ed004fed3740a0430`.
Prospective receipt `8d5a56901c2a69c495425638`. Root implements directly without
resolve; actual native Fable 5.1 and Grok 4.6 independently reviewed design and
final source. Root accepts **PASS_WITH_ISSUES**, zero in-scope CRITICAL/HIGH.
Delivery remains receipt-owned and separate from source verification.

## Failure and minimum repair

No guesswork: `.devlyn/0152/prediction.json` preceded 38 real-CLI controls.
All baseline outcomes matched: 26 missing-generated-source cases returned 0;
ordinary stale commands were removed, while benchmark-prestaged commands ran.
Required-probe BUILD_GATE and VERIFY reuse also returned without fresh results.

Why? `read_source` preserves generated type but collapses missing/non-file paths
to `None`. `source_integrity_error` returned success for any absent path before
checking that type. Main consequently treated a declared generated contract as
optional. The repair replaces that success only for generated sources in the
existing integrity boundary. It reports the raw declared `source.criteria_path`
value and returns the existing CRITICAL malformed finding before command work.

No workaround / Production ready: declared generated criteria must exist at
verification. No overengineering: no new flags, `read_source` changes, duplicated
main guard or benchmark exemption. Existing valid benchmark command precedence
and digest validation stay intact. AST comparison limits changes to
`source_integrity_error` and `run_self_test`; canonical and both local mirrors
have SHA-256 `a8563cd4709cf172426ce8b1b2f6242fb3683d0d43a97d3ec2b11db654ca45ad`.

## Verification and review

- All 38 candidate CLI controls matched the registered prediction. All 26 missing
  sources fail with exit 1, exactly one CRITICAL `correctness.spec-verify-malformed`,
  the declared path in the diagnostic, correct state-file/phase attribution and
  no command execution or fresh results. Twelve positive/digest/legacy controls
  retain their prior behavioral outcomes.
- The shipped eight-case CLI regression covers absent/null/empty/relative/absolute/
  directory pointers, benchmark staging and VERIFY reuse with required probes
  enabled. Darwin's external matrix additionally covers dangling symlinks.
- Checker self-test and bootstrap self-test pass. Full lint passes in 269.115s.
  Its first run failed solely because the resumed diagnostic assertion omitted the
  existing ignored `.claude` mirror. Exact stale bytes were identified and synced;
  the original failed run remains preserved. No product behavior changed for that repair.
- Subtractive check: removing the new generated-only guard in a temporary copy
  makes the actual new regression fail. Receipt-owned temporary fixtures are removed.
- Native Fable `claude-fable-5-1` **PASS_WITH_ISSUES** (85.485s),
  Grok requested `grok-4.6`, usage `grok-4.6-build` **PASS**
  (165.097s). Both reviewed the same source packet independently;
  native captures attest zero observed tool calls. Reviews preceded the later
  full-lint/bootstrap/subtraction readout; root checked those results separately.

The retained LOW concerns the pre-existing generic sibling/Verification fix hint;
the error body identifies the missing declared path. Existing stale staged/results
files can remain after an explicit integrity failure, as for digest errors; they
are not executed or refreshed. Non-string pointer validation is a separate
pre-existing boundary. No speculative cleanup or schema work is bundled.

## Evidence and claim boundary

`.devlyn/0152-evidence.tar.gz` preserves registration, immutable baseline/raw
candidate controls, exact source/diff, native review receipts, failed and passing
lint, mutation evidence and root adjudication. Task acceptance binds this archive.
Hosted POSIX/native Windows integration and matching-source delivery are recorded
separately in `.devlyn/0152-delivery/` before merge acceptance.

This demonstrates the checker's early failure, not a full-pipeline false PASS.
VERIFY source/carrier review and task completion's archived-source hash binding
remain independent boundaries. The documented probe-validation caller is after
PROBE_DERIVE (`SKILL.md:208`), whose inputs include authored criteria and PLAN.
Benchmark-prestaged oracle grammar remains a separate follow-up. Four broad core
priorities stay open; A16 and frozen comparisons remain untouched. No npm release.
