---
id: "0083-summary-verdict-merge"
title: "Conserve authenticated pair-judge summary verdicts"
kind: feature
status: planned
complexity: high
depends_on: ["0082-weld-recovery"]
---

# iter-0083 — conserve authenticated pair-judge summary verdicts

**Status: FROZEN, NOT BUILT. 2026-07-28.**

## Context

iter-0082 made Grok 4.5's welded review collectable, but the collector's
authenticated summary verdict still stops at `pair-judge.summary.json`.
`verify-merge-findings.py` derives `pair_judge` only from finding severities, so
a judge can explicitly return `NEEDS_WORK` while the shipped report returns
`PASS` or `PASS_WITH_ISSUES`.

This is a real user-visible loss, not a hypothetical hardening case. Against
HEAD, the same canonical pair output produced these raw results:

| Canonical summary + findings | HEAD `pair_judge` | HEAD overall |
|---|---:|---:|
| `NEEDS_WORK` + `INFO` | `PASS` | `PASS` |
| `NEEDS_WORK` + `LOW` | `PASS_WITH_ISSUES` | `PASS_WITH_ISSUES` |
| `NEEDS_WORK` + non-binding `MEDIUM` | `PASS_WITH_ISSUES` | `PASS_WITH_ISSUES` |
| `PASS` + `HIGH` | `NEEDS_WORK` | `NEEDS_WORK` |

The mechanism is concrete: the collector defaults to
`pair-judge.summary.json` (`collect-codex-findings.py:303`), while the merge
reads only the four finding files in `SOURCE_FILES`
(`verify-merge-findings.py:21-25`) and folds only those derived verdicts
(`verify-merge-findings.py:946-948`).

## Requirements

- [ ] When either canonical pair findings carrier exists, the merge reads the
  exact canonical `pair-judge.summary.json` carrier and folds its authenticated
  verdict with the finding-derived pair verdict using the existing `worse()`
  order. File existence, including an empty findings file, is the run-evidence
  gate.
- [ ] Valid summary verdicts `PASS`, `PASS_WITH_ISSUES`, `FAIL`, `NEEDS_WORK`,
  and `BLOCKED` are accepted. `FAIL` normalizes through the existing rank to
  the reported `NEEDS_WORK`; a summary can only preserve or worsen the
  finding-derived result, never down-rank it.
- [ ] A gated canonical summary that is malformed JSON, is not an object, lacks
  `verdict`, names an unknown verdict, or claims model-authored `TIMEOUT`
  produces an explicit CRITICAL pair blocker and `BLOCKED` rather than a crash,
  fallback, or silent discard. Transport-owned
  `verify.pair.timeout.json` behavior remains unchanged.
- [ ] A missing canonical summary preserves the current severity-derived
  behavior. An orphan summary without either canonical pair findings carrier
  cannot manufacture evidence that a pair judge ran.
- [ ] Primary and stale engine-specific summaries never bind the pair verdict.
  In particular, `codex-primary-judge.summary.json` remains primary-only and
  legacy `grok-judge.summary.json` is ignored.
- [ ] The Grok adapter stops overriding the collector's canonical summary path,
  so new Grok runs write `pair-judge.summary.json` through the collector default.
- [ ] Regression tests cover every frozen row below in the existing
  `verify-merge-findings.py --self-test` surface. The worker must add those rows
  and execute them against the old merge logic first, recording the expected
  RED result before changing product logic.
- [ ] All three installed surfaces (`config`, `.agents`, `.claude`) stay
  byte-identical for each changed product file.

## Constraints

- **Canonical path only.** Do not glob `*-judge.summary.json`: real archived
  runs contain both primary and pair summary files, so a glob either blocks a
  legitimate run or folds the wrong judge.
- **Delete before adding.** Remove Grok's stale `--summary-out` override; do not
  add an alias table, filename allowlist, migration fallback, new flag, or new
  product file.
- **Use existing primitives.** Strict JSON parsing, verdict rank normalization,
  and pair blocker construction already exist in `verify-merge-findings.py` and
  remain the single contracts.
- **Authorized product surface is exactly six files.** Only the merge script and
  Grok adapter in `config`, `.agents`, and `.claude` may change during the
  implementation pipeline.
- **No extra provider layer.** The implementation adds one bounded local file
  read only; it adds no model call, retry, or new phase.
- **Evidence before claim.** The frozen positives and negatives must run as
  executable self-tests; prose-only verification is insufficient.

## Out of Scope

- Certifying Grok emission reliability or changing the durable pair-engine pin.
- Solving sibling residuals such as startup selection, pair timeout transport,
  or generic judge-summary routing.
- Reading or merging primary judge summaries.
- Renaming historical archived artifacts.
- Adding a standalone test runner when the existing merge self-test can carry
  the regression matrix.

## Team adjudication and frozen bar

Codex reproduced the HEAD matrix and searched the live/archive surface. Grok
4.5 independently executed the same probe and source inspection. Both withdrew
the initial generic-glob proposal after the named delta: real run directories
contain both `codex-primary-judge.summary.json` and a pair summary. Git history
also shows that the collector's canonical default was added after the older
Grok-specific override, making the override a superseded seam rather than a
second supported contract.

Fable 5's two tool-using seats timed out. A tool-free adjudication converged on
the canonical-only design, but falsely claimed tool execution despite tools
being disabled. Its execution claims are rejected; only reasoning independently
confirmed by Codex and Grok is admitted. This iteration therefore records Fable
as an independent design seat, not an execution-evidence source.

Frozen executable rows:

| ID | Input | Required result |
|---|---|---|
| P1 | canonical `NEEDS_WORK` + `INFO` | `NEEDS_WORK` |
| P2 | canonical `NEEDS_WORK` + `LOW` | `NEEDS_WORK` |
| P3 | canonical `NEEDS_WORK` + non-binding `MEDIUM` | `NEEDS_WORK` |
| P4 | canonical `PASS` + `HIGH` | `NEEDS_WORK` (no down-rank) |
| P5 | canonical `BLOCKED` + `INFO` | `BLOCKED` |
| P6 | canonical `FAIL` + `INFO` | `NEEDS_WORK` |
| P7 | canonical `PASS` + an existing empty pair findings file | `PASS` |
| P8 | no canonical summary + `INFO` or `LOW` | unchanged severity-only result |
| N1 | malformed JSON, non-object, or unknown verdict | explicit pair blocker + `BLOCKED` |
| N2 | missing `verdict` | explicit pair blocker + `BLOCKED`, no exception |
| N3 | canonical summary with no canonical pair findings carrier | ignored |
| N4 | primary summary plus canonical pair summary | only canonical pair summary binds |
| N5 | stale `grok-judge.summary.json` alone plus pair findings | stale summary ignored |
| N6 | only legacy `verify.pair-judge.findings.jsonl` exists | canonical fold is armed |
| N7 | canonical model-authored `TIMEOUT` | explicit pair blocker + `BLOCKED` |

The bar is all rows green, existing merge/collector self-tests green, iter-0082
collector contract green, skill lint green, and mirror parity exact. Anything
less does not ship.

## Principles check

0. **Mission-bound:** this closes one measured Mission-1 harness correctness
   loss; it does not broaden engine support or start Mission 2.
1. **No workaround:** canonicalize the producing adapter and consume the
   authenticated carrier; do not infer ownership from filenames.
2. **No overengineering:** one stale option is deleted and the existing merge
   gains the smallest required reader. No abstraction or new runner is licensed.
3. **No guesswork:** the HEAD matrix, dual-summary archive search, and Git
   supersession history were checked before freezing the design.
4. **Worldclass / Production ready:** bad authenticated carriers become visible
   blockers; they cannot crash or silently degrade to severity-only PASS.
5. **Best practice:** strict JSON and the existing verdict lattice remain the
   source of truth.
6. **Optimized:** the fix adds no provider latency and no additional phase.

<!-- devlyn:verification -->
## Verification

- The merge self-test executes all frozen positive, negative, orphan, legacy,
  and timeout rows.
- The collector and iter-0082 regression contracts remain green.
- BUILD_GATE runs skill lint directly; the literal verifier does not duplicate
  that repository-wide suite under its 60-second per-command budget. Exact
  three-surface mirror parity still passes literally.

```json
{
  "verification_commands": [
    {
      "cmd": "python3 config/skills/_shared/verify-merge-findings.py --self-test",
      "exit_code": 0
    },
    {
      "cmd": "python3 config/skills/_shared/collect-codex-findings.py --self-test",
      "exit_code": 0
    },
    {
      "cmd": "python3 benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py",
      "exit_code": 0
    },
    {
      "cmd": "cmp -s config/skills/_shared/verify-merge-findings.py .agents/skills/_shared/verify-merge-findings.py && cmp -s config/skills/_shared/verify-merge-findings.py .claude/skills/_shared/verify-merge-findings.py && cmp -s config/skills/_shared/adapters/grok.md .agents/skills/_shared/adapters/grok.md && cmp -s config/skills/_shared/adapters/grok.md .claude/skills/_shared/adapters/grok.md",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "forbidden_patterns": [
    {
      "pattern": "glob\\(.*judge\\.summary|\\*-judge\\.summary",
      "description": "Generic judge-summary discovery can fold a primary judge into the pair verdict.",
      "files": [
        "config/skills/_shared/verify-merge-findings.py",
        ".agents/skills/_shared/verify-merge-findings.py",
        ".claude/skills/_shared/verify-merge-findings.py"
      ],
      "severity": "disqualifier"
    }
  ],
  "required_files": [
    "config/skills/_shared/verify-merge-findings.py",
    "config/skills/_shared/adapters/grok.md"
  ],
  "max_deps_added": 0
}
```
