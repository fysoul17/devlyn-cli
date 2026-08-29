# Fable 5 final review — HX-1 external diff authority

- Reviewed at: `2026-08-29T01:01:58+00:00`
- Frozen target: `18debb4a021f92418f98e121897688f9a1fc54f0`
- Base: `a015cdfcd59c9bb5da41a9b91cabfc176620d8a3`
- Diff SHA-256: `eacccdc802aa1853230624df06c54990fa2db3a182aea878aabcc415981a0e1d`
- Exact-model evidence: `claude-haiku-4-5, claude-fable-5`
- Raw result: `/Users/aipalm/Library/Application Support/devlyn/fable-final-20260829/attempts/inference-20260829T005150Z/raw-output.json`
- Verdict: **PASS**

## Required checks

- Non-verify modes fail before patch consumption: **PASS**
- Verify-only behavior remains unchanged: **PASS**
- Checker mirrors remain identical: **PASS**
- Spec/schema/iteration evidence is consistent: **PASS**

## Findings

No actionable CRITICAL, HIGH, or MEDIUM findings.

## Summary

Reviewed a015cdf..18debb4 (patch + live target files). The mode/artifact preflight at config/skills/_shared/spec-verify-check.py:4666-4683 executes immediately after read_state() (L4665) and before source_integrity_error, carrier staging, command execution, expected_contract_findings (L5006) and authorized_surface_findings (L5017-5021). The only patch readers in the file are diff_text_for_expected (L1296-1301) and changed_files (L1339-1351), both reached only after the guard; the early-return subcommands (--print-authorized-surface L1769, --write-untracked-baseline L1795, --print-risk-probes-digest L1785, --check, --check-expected, --self-test) never touch the patch. read_state returns {} for missing/malformed/non-dict state (L1096-1104), so absent or any non-exact 'verify-only' mode fails closed with exit 1 and a CRITICAL correctness.spec-verify-malformed finding, in BUILD_GATE, VERIFY MECHANICAL (--include-risk-probes), --validate-risk-probes and bench mode alike. Verify-only is untouched: the branch is skipped for exact 'verify-only' and the new keyword-only fix_hint=None keeps every existing caller's default hint byte-identical (L1247-1252). The self-test's verify-only control is genuinely discriminating: the mechanical runner pops SPEC_VERIFY_* (L209-211) so nested runs default to build_gate, base_sha is set, and a worktree fallback would flag outside.txt as scope.out-of-scope-file CRITICAL/blocking (L1650-1671, L1734-1750) -> exit 1, so exit 0 proves patch consumption. Mirrors: both post-image blobs are 1027884 (verifier) and db46e71 (state-schema), worktree clean at 18debb4, line counts 5092/5092 and 141/141, def/subprocess.run/write_malformed_finding counts 192/192, all three hunks read identically in both copies. Docs: spec.md R1-R3 map to the implementation, spec.expected.json commands equal the iteration's Verification block, the state-schema sentence matches behavior, iteration/HANDOFF/DECISIONS cite the same commits (c9faf27 + bd9ff22), run id and claims, and the nine touched files equal the declared authorized surface. Residual notes, not findings and outside the registered scope: (a) state.mode is the authority root and pipeline.state.json is unauthenticated (no script validates mode transitions; finish-gate.py:243 and verify-merge-findings.py:835 already trust state.mode, as base_ref.sha/spec_sha256 are trusted) - a pre-existing harness-wide trust boundary this change neither introduces nor widens; (b) the archived witness run rs-20260705T015026Z-5f63cc1b7a0c lives under benchmark/probes/results/, which is gitignored (.gitignore:35), so it is not reproducible from the tracked tree; (c) docs/specs/harness-artifact-integrity-seal/spec.md:47 (R1.5 'do not add a mode branch') is superseded by the 0111 spec, which explicitly reasons past it, and the older closed spec was not amended (LOW). No actionable CRITICAL/HIGH/MEDIUM findings.
