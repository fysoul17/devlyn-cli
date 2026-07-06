# Seat Matrix - 2026-07-07

Cells: 73

## Recommendation

```json
{
  "executor": {
    "recommendation": "recert required",
    "seat": "implement_executor"
  },
  "pair_judge_priority": {
    "recommendation": "recert required",
    "seat": "verify_pair_judge"
  }
}
```

## Cells

| Seat | Engine | Metric | Value | N | Status | Model version | Artifact |
|---|---|---|---:|---:|---|---|---|
| drift_resistance | opus | non_violation_rate | 0.500 | 24 | stale | null | `benchmark/probes/results/iter0058-base-matrix.json` |
| drift_resistance | opus | non_violation_rate | 0.000 | 4 | stale | null | `benchmark/probes/results/iter0062-a-matrix-corrected.json` |
| drift_resistance | opus | non_violation_rate | 0.500 | 4 | stale | null | `benchmark/probes/results/iter0062-b-matrix-corrected.json` |
| drift_resistance | sonnet | non_violation_rate | 0.625 | 24 | stale | null | `benchmark/probes/results/iter0058-base-matrix.json` |
| drift_resistance | sonnet | non_violation_rate | 0.625 | 24 | stale | null | `benchmark/probes/results/iter0062-a-matrix-corrected.json` |
| drift_resistance | sonnet | non_violation_rate | 0.833 | 24 | stale | null | `benchmark/probes/results/iter0062-b-matrix-corrected.json` |
| implement_executor | bare | judge_score_mean | 36.000 | 3 | stale | codex-cli unknown (version-timeout)/gpt-5.5 | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof` |
| implement_executor | bare | verify_score_mean | 0.361 | 3 | stale | codex-cli unknown (version-timeout)/gpt-5.5 | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof` |
| implement_executor | l2_risk_probes | judge_score_mean | 97.333 | 3 | stale | codex-cli unknown (version-timeout)/gpt-5.5 | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof` |
| implement_executor | l2_risk_probes | verify_score_mean | 1.000 | 3 | stale | codex-cli unknown (version-timeout)/gpt-5.5 | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof` |
| implement_executor | solo_claude | judge_score_mean | 72.000 | 3 | stale | codex-cli unknown (version-timeout)/gpt-5.5 | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof` |
| implement_executor | solo_claude | verify_score_mean | 0.722 | 3 | stale | codex-cli unknown (version-timeout)/gpt-5.5 | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof` |
| orchestrator | claude | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0042-20260704T001308Z/compliance/claude-medium/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0042-20260704T001308Z/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0044-verify-20260704T053516Z/compliance/claude-medium/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0044-verify-20260704T053516Z/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0046-verify/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0047-verify-claude-small/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0048-ko-compliance/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0049-verify-claude-small/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0052-verify-claude-small/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0054-verify-claude-small-20260704T132052Z/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0059-guard-claude/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0060-g4-claude/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0060-g4b-claude/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0062-verify-claude-small/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0063-v4c/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0063-verify-final/compliance/claude-small/compliance-check.json` |
| orchestrator | claude | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0063-verify/compliance/claude-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0042-20260704T001308Z/compliance/codex-medium/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0042-20260704T001308Z/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0046-baseline-head/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0046-baseline-with-diff/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0046-verify-v2/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0046-verify/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0047-verify-codex-small/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0052-verify-codex-small/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0059-guard-codex/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0060-g1-codex/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0060-g4b-codex/compliance/codex-small/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0061-a1/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0061-a2/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0061-a3/compliance-check.json` |
| orchestrator | codex | compliance_pass | 0.000 | 1 | stale | null | `benchmark/probes/results/iter0061-a4/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0061-b1/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0061-b2/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0061-b3/compliance-check.json` |
| orchestrator | codex | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0061-b4/compliance-check.json` |
| orchestrator | omp | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0042-20260704T001308Z/compliance/omp-medium/compliance-check.json` |
| orchestrator | omp | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0042-20260704T001308Z/compliance/omp-small/compliance-check.json` |
| orchestrator | omp | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0047-verify-omp-small/compliance/omp-small/compliance-check.json` |
| orchestrator | omp | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0048-ko-compliance/compliance/omp-small/compliance-check.json` |
| orchestrator | omp | compliance_pass | 1.000 | 1 | stale | null | `benchmark/probes/results/iter0049-verify-omp-small/compliance/omp-small/compliance-check.json` |
| plan_ideate_designer | codex | unmeasured | n/a | n/a | unmeasured | null | `none` |
| plan_ideate_designer | opus | unmeasured | n/a | n/a | unmeasured | null | `none` |
| plan_ideate_designer | sonnet | unmeasured | n/a | n/a | unmeasured | null | `none` |
| verify_pair_judge | codex | pair_gate_pass_rate | 1.000 | 3 | stale | null | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json` |
| verify_pair_judge | codex | pair_lift_rate | 1.000 | 11 | stale | null | `benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.json` |
| verify_primary_judge | ollama | false_positive_rate | 1.000 | 8 | stale | null | `benchmark/probes/judge-quality/results/ollama` |
| verify_primary_judge | ollama | parse_failure_rate | 0.000 | 24 | stale | null | `benchmark/probes/judge-quality/results/ollama` |
| verify_primary_judge | ollama | recall_rate | 0.500 | 16 | stale | null | `benchmark/probes/judge-quality/results/ollama` |
| verify_primary_judge | sonnet | false_positive_rate | 0.000 | 8 | stale | null | `benchmark/probes/judge-quality/results/sonnet` |
| verify_primary_judge | sonnet | parse_failure_rate | 0.000 | 24 | stale | null | `benchmark/probes/judge-quality/results/sonnet` |
| verify_primary_judge | sonnet | recall_rate | 1.000 | 16 | stale | null | `benchmark/probes/judge-quality/results/sonnet` |
| verify_primary_judge | variant-v1 | false_positive_rate | 1.000 | 8 | stale | null | `benchmark/probes/judge-quality/results/variant-v1` |
| verify_primary_judge | variant-v1 | parse_failure_rate | 0.000 | 24 | stale | null | `benchmark/probes/judge-quality/results/variant-v1` |
| verify_primary_judge | variant-v1 | recall_rate | 0.500 | 16 | stale | null | `benchmark/probes/judge-quality/results/variant-v1` |
| verify_primary_judge | variant-v2 | false_positive_rate | 1.000 | 8 | stale | null | `benchmark/probes/judge-quality/results/variant-v2` |
| verify_primary_judge | variant-v2 | parse_failure_rate | 0.000 | 24 | stale | null | `benchmark/probes/judge-quality/results/variant-v2` |
| verify_primary_judge | variant-v2 | recall_rate | 0.500 | 16 | stale | null | `benchmark/probes/judge-quality/results/variant-v2` |
| verify_primary_judge | variant-v3 | false_positive_rate | 0.000 | 8 | stale | null | `benchmark/probes/judge-quality/results/variant-v3` |
| verify_primary_judge | variant-v3 | parse_failure_rate | 0.000 | 24 | stale | null | `benchmark/probes/judge-quality/results/variant-v3` |
| verify_primary_judge | variant-v3 | recall_rate | 0.000 | 16 | stale | null | `benchmark/probes/judge-quality/results/variant-v3` |
