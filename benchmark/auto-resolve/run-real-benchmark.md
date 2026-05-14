# Running Real Pair/Solo Benchmarks

This document is for benchmark runs that spend real model calls and produce
judge scores. Use it when a change claims `solo_claude < pair`.

For wiring checks that must not invoke providers, use `npx devlyn-cli benchmark
--dry-run` or the shell tests listed in `README.md`.

## Current Score Harness

The current full-pipeline comparison has three evidence arms:

| Arm | Meaning |
|---|---|
| `bare` | control without the devlyn skills |
| `solo_claude` | Claude-only `/devlyn:resolve` path |
| `l2_risk_probes` | current measured pair path: Claude implement plus Codex-derived risk probes / pair VERIFY |

`l2_gated` is diagnostic replay only. `l2_forced` is retired and rejected by the
runner because it leaks pair-awareness before IMPLEMENT.

The score artifacts that matter are:

- `benchmark/auto-resolve/results/<run-id>/<fixture>/judge.json`
- `benchmark/auto-resolve/results/<run-id>/<fixture>/<arm>/result.json`
- `benchmark/auto-resolve/results/<run-id>/<fixture>/<arm>/verify.json`
- `benchmark/auto-resolve/results/<run-id>/full-pipeline-pair-gate.md`
- `benchmark/auto-resolve/results/<run-id>/full-pipeline-pair-gate.json`

Do not treat a score as evidence if the matching arm has a deterministic
failure, judge disqualifier, missing `diff.patch`, blocked resolve verdict,
failed verify score, provider invocation failure, or an invalid judge axis cell.
The matching arms must also appear in `judge.json` `_blind_mapping`; a
`scores_by_arm` value without the blind slot mapping is not score evidence.

## Headroom First

Before spending new provider calls, check the active frontier:

```bash
python3 benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  --out-md /tmp/devlyn-pair-frontier.md
npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md
```

Only `candidate_unmeasured` fixtures need fresh headroom. Fixtures marked
`pair_evidence_passed` already have local passing full-pipeline complete pair evidence rows,
and fixtures marked `rejected` need rework before pair arms. The frontier command
prints existing complete `bare`, `solo_claude`, `pair`, margin, wall ratio, and run id rows to
stdout, plus average/minimum pair margin and wall ratio, even when `--out-md`
or `--out-json` writes an artifact.
Gate-3 pair-eligible manifests carry both `rejected_excluded` and
`rejected_excluded_reasons`, so excluded solo-ceiling controls keep their
registry reason inside the manifest artifact.
After a headroom failure, run
`npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json`
which invokes `audit-headroom-rejections.py` to ensure no active failed fixture
remains outside both the rejected registry and passing pair evidence, and that
each active rejected-registry reason is backed by a matching local headroom
artifact unless it is an explicit calibration/known-limit fixture.
For release/handoff checks, add `--fail-on-unmeasured` to the frontier command
to fail when active pair candidates still need headroom measurement.
Or run the composite provider-free guard:

```bash
npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit
npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict
```

It invokes `pair-candidate-frontier.py --fail-on-unmeasured` and
`audit-headroom-rejections.py`, writes `audit.json` with the frontier summary, artifact map,
`frontier.json`, `frontier.stdout`, `frontier.stderr`,
and compact trigger-backed verdict-bearing `pair_evidence_rows` (each row carries
`pair_trigger_eligible: true`, non-empty `pair_trigger_reasons`, `pair_trigger_has_canonical_reason: true`, and `pair_trigger_has_hypothesis_reason`; the audit fails rows missing trigger reasons or missing actionable solo-headroom hypotheses in fixture `spec.md` whose observable command matches `expected.json`), plus both child JSON reports and child stdout/stderr logs, and prints the existing complete pair score rows
with pair arm, verdict, and trigger reasons from the frontier step. By default it revalidates frontier `verdict: PASS`, zero unmeasured candidates,
requires at least four active fixtures with passing pair evidence, and revalidates `pair_mode: true`,
the default 5-point pair margin, and 3x pair/solo wall ratio. The audit stdout
also prints `headroom_rejections=...`, `pair_evidence_quality=...`,
`pair_trigger_reasons=...`, `pair_evidence_hypotheses=...`, and `pair_evidence_hypothesis_triggers=...` handoff rows, plus
`pair_trigger_historical_aliases=...` when archived evidence includes legacy
trigger aliases and `pair_evidence_hypothesis_trigger_gaps=...` when documented
hypotheses have not yet propagated into trigger reasons, with rejected-fixture
coverage counts, actual minimum pair margin, maximum pair/solo wall ratio, and
canonical trigger reason coverage plus row-match status. The compact evidence row count must match the frontier evidence count, so incomplete local score artifacts cannot inflate
the claim. `checks.frontier_stdout` records summary, aggregate, final-verdict, expected, printed score-row, trigger-visible row, and hypothesis-trigger-visible row counts, `checks.headroom_rejections` records child verdict plus unrecorded/unsupported counts, `checks.pair_evidence_quality` records the same quality thresholds from the compact rows, `checks.pair_trigger_reasons` records canonical/historical-alias/exposed/total trigger-reason row counts, fixture-level historical alias details, summary count, and row-match status for handoff review, `checks.pair_evidence_hypotheses` records documented/total pair-evidence hypothesis row counts, and `checks.pair_evidence_hypothesis_triggers` records whether documented hypotheses also appear as `spec.solo_headroom_hypothesis` trigger reasons plus fixture-level gap details. The markdown frontier
artifact includes the overall verdict plus row-level verdict, pair-arm, and trigger-reason columns.
Full-pipeline pair gate artifacts record `require_hypothesis_trigger` in JSON
and include a Markdown `Hypothesis trigger` column, so strict regenerated
evidence shows whether each row carried `spec.solo_headroom_hypothesis`.
Add `--require-hypothesis-trigger` to turn those hypothesis-trigger gaps from
archived-evidence WARN rows into release-blocking FAIL rows for newly
regenerated pair evidence.
Historical trigger aliases are only reported for archived artifact review; new
current pair-evidence gates fail historical-only or unknown trigger reasons and
require at least one canonical `pair_trigger.reasons` entry.

Pair lift is not measurable when `bare` or `solo_claude` is already near the
ceiling. Calibrate candidate fixtures first:

```bash
bash benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  --bare-max 60 \
  --solo-max 80 \
  --min-fixtures 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

Equivalent CLI entrypoint:

```bash
npx devlyn-cli benchmark headroom \
  --bare-max 60 \
  --solo-max 80 \
  --min-fixtures 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

The runner prints a startup `Gate:` line, the replay `Command:`, and the
headroom markdown report with `bare`/`solo_claude` scores and remaining headroom against
the configured thresholds, including average and minimum headroom for the
candidate set plus fixture pass count. When launched through
`npx devlyn-cli benchmark headroom`, the replay command uses that same package
CLI path. Count a fixture only when `headroom-gate.py` reports
evidence-complete `bare <= 60` and `solo_claude <= 80` with the default minimum 5-point `bare`/`solo_claude` headroom margin. Add `--dry-run` only to validate args,
fixture ids, minimum fixture count, and the replay command; it does not produce
scores. When showing scores, include `bare` headroom and `solo_claude` headroom. A real
headroom run explicitly reports whether the candidate set was accepted or rejected.
Known rejected or ceiling-saturated fixtures are refused by default; use
`--allow-rejected-fixtures` only for diagnostics of still active rejected
fixtures, not for new pair-evidence candidate selection. Retired fixtures are
preserved for historical artifact replay and are not rerun by the pair-candidate
runners.

## Full Pair Measurement

Run the selected pair arm only after headroom passes:

```bash
bash benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  --min-fixtures 3 \
  --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

Equivalent CLI entrypoint:

```bash
npx devlyn-cli benchmark pair \
  --min-fixtures 3 \
  --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

For prompt-only pair changes, reuse an evidence-complete calibration run to avoid
re-spending `bare` and `solo_claude`:

```bash
bash benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  --run-id <new-run-id> \
  --reuse-calibrated-from <prior-headroom-run-id> \
  --min-fixtures 3 \
  --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

The runner prints startup `Headroom:` and `Pair:` lines, the replay `Command:`,
and the final pair gate report with fixture pass count and average pair margin.
If headroom fails, it reports that the pair arm was not executed. If the final
pair gate fails, it reports that pair evidence was rejected. On success, it
reports that the selected pair arm is executing and then that pair evidence was
accepted. When launched through `npx devlyn-cli benchmark pair`, the replay
command uses that same package CLI path. The pair runner and full-pipeline gate
use the default 3x pair/solo wall ratio unless `--max-pair-solo-wall-ratio` is
overridden for diagnostics. The full-pipeline gate report separates the allowed pair/solo wall ratio from the maximum observed pair/solo wall ratio, records `require_hypothesis_trigger` in JSON, and includes a Markdown `Hypothesis trigger` column. Add
`--dry-run` only to validate args, fixture ids, minimum fixture count, and the
replay command; it does not produce scores. Known rejected or ceiling-saturated
fixtures are refused by default here too; use
`--allow-rejected-fixtures` only for diagnostics of still active
rejected fixtures. Retired fixtures remain historical replay artifacts and are
not rerun by this candidate runner.
When showing a real run, report at minimum:

- run id
- fixture id
- fixtures passed / total and `--min-fixtures`
- startup `Headroom:` / `Pair:` gate lines
- `bare`, `solo_claude`, and `l2_risk_probes` scores
- pair minus `solo_claude` margin
- average pair margin for the counted set
- `pair_mode`
- pair trigger eligibility, trigger reasons, canonical-trigger coverage, and `spec.solo_headroom_hypothesis` coverage when the fixture spec has an actionable solo-headroom hypothesis
- pair/solo wall-time ratio
- gate verdict and failure reasons, if any

Example reporting shape:

```text
Run: <run-id>
Fixture                         Bare  Solo_claude  Pair  Pair-Solo_claude  Pair mode  Wall pair/solo  Verdict
<fixture-a>                      42    65    86    +21        true       1.44x           PASS
<fixture-b>                      31    58    82    +24        true       1.48x           PASS
```

Do not summarize a real run as "pair improved" unless the gate passed or the
failure reason is explicitly shown next to the scores.

## Existing Evidence

The current measured pair arm is `l2_risk_probes`.

- `20260510-f16-f23-f25-combined-proof` passed the F16/F23/F25 gate with pair
  margins `+21`, `+31`, and `+24`; average pair margin was `+25.3`; average
  pair/solo wall ratio was `1.73x`.
- `20260509-f16-f25-combined-cartprobe-v2` also passes the current gate for
  the F16/F25 subset with pair margins `+21` and `+24`; average pair margin was
  `+22.5`; average pair/solo wall ratio was `1.46x`.
- `20260511-f21-current-riskprobes-v1` passed focused F21 evidence with
  `bare 33`, `solo_claude 66`, `l2_risk_probes 99`, margin `+33`, pair mode
  true, and pair/solo wall ratio `1.47x`; it is counted by `benchmark audit` as the fourth passing pair-evidence row.

F22 and F26 are not pair-lift evidence right now because existing headroom runs
put `solo_claude` near the ceiling. F27 is also rejected in its first headroom smoke:
`20260511-f27-headroom-smoke-061401` measured bare 33 / solo_claude 94, with bare
verification passing only 1 of 3 commands. Rework or rotate F27 before spending
a pair arm on it. F28 is rejected as pair-lift evidence: earlier unstable runs
`20260511-f28-headroom-smoke-085307` and `20260511-f28-pair-smoke-091021` were
superseded after a hidden-oracle bug was found. The oracle had expected a
defective item to bypass expiration, which the visible spec does not require.
After re-verifying the same provider diffs against the corrected oracle,
`20260511-f28-policy-oraclefix-reverified-pair` scored bare 50 / solo_claude 98 /
`l2_risk_probes` 96, margin -2, and failed headroom. Rework or rotate F28 before
spending more pair arms.
F30 is also rejected: `20260511-f30-headroom-v1` scored bare 33 / solo_claude 98, so
it failed the `solo_claude` headroom precondition before any pair arm should be spent.
F15 is also rejected: `20260511-f15-concurrency-headroom` scored bare 99 /
solo_claude 94, so it failed both headroom preconditions and should stay a frozen-diff
review control unless reworked. F3 is also rejected after tightening its HTTP
error-body verifier: `20260511-f3-http-error-headroom` scored bare 97 / solo_claude 99,
so it failed both headroom preconditions. F2 medium CLI is rejected by
`20260512-f2-medium-headroom`: bare 83 / solo_claude 95, so both baseline scores
exceed headroom ceilings. F4 web browser design is rejected by
`20260512-f4-web-headroom`: bare 70 / solo_claude 92 with bare disqualifiers, so it
needs rework before pair arms. F5 fix-loop is rejected by
`20260512-f5-fixloop-headroom`: bare 99 / solo_claude 99, with `bare` and `solo_claude` each
passing 5/5 verification commands. F6 dep-audit checksum is rejected by
`20260512-f6-checksum-headroom`: bare 97 / solo_claude 96, with `bare` and `solo_claude` each
passing 6/6 verification commands. F7 scope discipline is rejected by
`20260512-f7-scope-headroom`: bare 99 / solo_claude 100, with `bare` and `solo_claude` each
passing 6/6 verification commands. F9 ideate-to-resolve remains the novice-flow
anchor but is rejected as pair evidence by `20260512-f9-e2e-headroom`: bare 60 /
solo_claude 90 with bare headroom 0 and a bare judge disqualifier, despite passing F9
artifact checks. Rework it before spending pair arms. F1 and F8 are rejected by
design as calibration/known-limit controls, not pair-lift evidence candidates.
F10/F11 are also rejected by `20260507-f10-f11-tier1-full-pipeline`: F10 scored
bare 75 / solo_claude 94, and F11 scored bare 98 / solo_claude 97. F12 webhook signature/replay is rejected by
`20260511-f12-webhook-headroom`: bare 85 / solo_claude 99.
F31 seat rebalance is rejected by `20260512-f31-seat-rebalance-headroom`: bare
33 / solo_claude 98, with bare judge/result/verify disqualifiers and `solo_claude` passing 3/3
verification commands. F32 subscription renewal is rejected by
`20260512-f32-subscription-renewal-headroom`: bare 33 / solo_claude 98, so it should
not receive a pair arm unless reworked.

## Smoke Suite

The top-level benchmark command still exists for broad suite health:

```bash
npx devlyn-cli benchmark
npx devlyn-cli benchmark --judge-only --run-id <ID>
```

This path runs `variant`, `solo_claude`, and `bare` across fixtures, judges
them, compiles `summary.json`, and applies `ship-gate.py`. It is useful for
regression floors and fixture hygiene. For new `solo_claude < pair` claims,
prefer the headroom plus full-pipeline pair gate above because it names the
selected pair arm and enforces `pair_mode`.

## Runtime Perf Artifacts

Every `/devlyn:resolve` run can also archive state into
`.devlyn/runs/<run_id>/pipeline.state.json`. Use those artifacts for wall-time
and phase diagnostics, not as score evidence by themselves.

```bash
for f in .devlyn/runs/*/pipeline.state.json; do
  jq '{run_id, engine: .engine, phases: .phases, risk_profile: .risk_profile}' "$f"
done
```

When `--perf` data is present, include it as secondary cost evidence. If token
counts are absent in the environment, say so; do not infer token savings from
wall-time alone.

## Honest Reporting Rules

- Real score claims must cite the run id and fixture ids.
- A fixture counts only when all measured arms have complete artifacts.
- Headroom failures are not pair failures; they mean the fixture cannot measure
  lift.
- Provider-limit or invocation failures make the affected fixture non-evidence.
- Wall-time ratios are cost signals, not quality scores.
- Dry-runs, lint, and shell tests prove wiring only. They are not benchmark
  scores.
