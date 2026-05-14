# devlyn-cli resolve Benchmark Suite

One-command resolve benchmark that gates every harness change with a ship/rollback decision.

## Quick start

```bash
npx devlyn-cli benchmark                 # n=1 smoke, all fixtures × 3 arms, judge, report, ship-gate
npx devlyn-cli benchmark F2              # specific fixture only
npx devlyn-cli benchmark headroom F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
npx devlyn-cli benchmark --dry-run       # validate suite wiring without model invocation
npx devlyn-cli benchmark --bless         # if ship-gate PASSes, promote this run as the shipped baseline
npx devlyn-cli benchmark --judge-only --run-id <ID>   # re-judge an existing run's artifacts
```

Exit code 0 = PASS, 1 = FAIL.

## What it does

1. For every fixture × arm (`variant` / `solo_claude` / `bare`):
   - Prepare a fresh temp copy of `fixtures/test-repo/`.
   - Commit baseline + apply `setup.sh` + commit bench scaffolding.
   - Invoke the arm via an isolated `claude -p` subprocess.
   - Capture `diff.patch`, `transcript.txt`, `timing.json`, run `expected.json::verification_commands`.
2. For every fixture, invoke isolated Codex as a blind judge with randomized slots using the 4-axis rubric in `RUBRIC.md`.
3. Aggregate into `results/<run-id>/report.md` + `summary.json`.
4. Apply ship-gate thresholds (`scripts/ship-gate.py`). Print verdict.
5. Append immutable record to `history/runs/<run-id>.json`.

## Directory layout

```
benchmark/auto-resolve/
├── BENCHMARK-DESIGN.md       # full design rationale
├── README.md                 # this file
├── RUBRIC.md                 # 4-axis scoring + ship gates
│
├── fixtures/
│   ├── SCHEMA.md             # fixture file format
│   ├── test-repo/            # bootstrap Node project — base for all arms
│   ├── F2-cli-medium-subcommand/
│   └── F1,F3-F9/             # add per Stage 2-3
│
├── scripts/
│   ├── run-suite.sh          # single entry — called by `npx devlyn-cli benchmark`
│   ├── run-fixture.sh        # one fixture × one arm, self-contained
│   ├── judge.sh              # Codex blind judge for one fixture
│   ├── compile-report.py     # aggregates into report.md + summary.json
│   ├── ship-gate.py          # applies thresholds + writes history record
│   ├── test-benchmark-arg-parsing.sh
│   ├── test-ship-gate.sh
│   ├── run-headroom-candidate.sh
│   ├── headroom-gate.py      # blocks pair measurement without headroom set
│   ├── test-headroom-gate.sh
│   ├── test-run-headroom-candidate.sh
│   ├── run-full-pipeline-pair-candidate.sh
│   ├── test-run-full-pipeline-pair-candidate.sh
│   ├── full-pipeline-pair-gate.py
│   ├── test-full-pipeline-pair-gate.sh
│   ├── pair-candidate-frontier.py
│   ├── test-pair-candidate-frontier.sh
│   ├── audit-pair-evidence.py
│   ├── test-audit-pair-evidence.sh
│   ├── audit-headroom-rejections.py
│   ├── test-audit-headroom-rejections.sh
│   ├── test-check-f9-artifacts.sh
│   ├── iter-0033c-l1-summary.py
│   ├── test-iter-0033c-l1-summary.sh
│   ├── run-frozen-verify-pair.sh
│   ├── fetch-swebench-instances.py
│   ├── collect-swebench-predictions.py
│   ├── run-swebench-solver-batch.sh
│   ├── test-run-swebench-solver-batch.sh
│   ├── prepare-swebench-frozen-case.py
│   ├── prepare-swebench-frozen-corpus.py
│   ├── run-swebench-frozen-corpus.sh
│   ├── swebench-frozen-matrix.py
│   ├── test-swebench-frozen-case.sh
│   ├── frozen-verify-gate.py # gates frozen VERIFY pair-lift evidence
│   └── test-frozen-verify-gate.sh
│
├── external/swebench/        # ignored local imports of SWE-bench cases/repos
├── results/<run-id>/         # per-run artifacts (overwritten)
└── history/
    ├── runs/                 # append-only, one JSON per run
    ├── latest.json           # pointer to most recent run
    └── baselines/shipped.json   # last blessed version, used for regression floor
```

## Prerequisites

- `claude` CLI on PATH (Claude Code, used to invoke each arm).
- `codex` CLI on PATH (used by the blind judge). Install from https://platform.openai.com/docs/codex.
- `python3`, `node`, `git`, `timeout`.

## Adding a fixture

Follow `fixtures/SCHEMA.md`. Six files per fixture: `metadata.json`, `spec.md`, `task.txt`, `expected.json`, `NOTES.md`, `setup.sh`. Common workflow:

1. Copy an existing fixture directory as a template.
2. Rewrite `metadata.json::intent` with the new task's plain-language intent.
3. Write `spec.md` (resolve-ready) and `task.txt` (plain prompt) both derived from the intent.
4. Fill `expected.json` with concrete verification commands and forbidden patterns.
5. Document purpose + failure mode in `NOTES.md`.
6. Add `setup.sh` if the task needs the base `test-repo` modified before either arm starts.
7. Run `bash scripts/lint-fixtures.sh`.

For draft pair candidates, start in `shadow-fixtures/S*` and run
`bash scripts/lint-shadow-fixtures.sh`. The headroom and pair candidate runners
accept explicitly named `S*` ids for dry-run checks and candidate measurement,
but shadow results are read-only signals. Promote a validated task to an active
`F*` fixture before counting it as golden pair evidence.
Use `run-suite.sh --suite shadow` only with `--dry-run`; the suite path refuses
provider and judge runs for shadow fixtures so rejected/smoke controls do not
spend benchmark budget accidentally.
Before spending provider calls, write a solo-headroom hypothesis into the
candidate's `spec.md`: name the visible behavior a capable `solo_claude`
baseline is expected to miss, and the observable command from `expected.json`
that would expose that miss. A hypothesis of only "the task is hard" is not
enough; rework the candidate before measurement. `lint-shadow-fixtures.sh` and
the candidate runners enforce this as an actionable hypothesis: the fixture
`spec.md` must contain `solo-headroom hypothesis`, `solo_claude`, `miss`, and a
backticked observable command matching `expected.json`, with the backticked line
itself containing `miss` and framed as the command/observable that exposes it.
For unmeasured high-risk shadow candidates, `NOTES.md` must also include
`## Solo ceiling avoidance` naming how the candidate differs from the
solo-saturated `S2`-`S6` controls and why that difference should preserve
`solo_claude` headroom. If that distinction is not concrete, rework the
candidate before measurement.
If a real shadow headroom run fails because the fixture is solo-saturated, record
the run and score in the fixture's `NOTES.md` and add the fixture to
`scripts/pair-rejected-fixtures.sh`; `lint-shadow-fixtures.sh` enforces that
calibrated shadow `FAIL` entries are registered before future provider spend.

For L2/pair candidate fixtures, also run:

```bash
bash benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  --bare-max 60 \
  --solo-max 80 \
  --min-fixtures 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

The same runner is available through `npx devlyn-cli benchmark headroom ...`.
This runs only the arms needed for calibration (`bare` and `solo_claude`),
blind-judges them, and applies `headroom-gate.py`. A candidate set is not
usable for pair measurement unless at least two fixtures pass and each fixture
has evidence-complete `bare <= 60` and `solo_claude <= 80` scores with the
default minimum 5-point `bare`/`solo_claude` headroom margin.
The runner prints the headroom gate markdown report to stdout, including the
startup `Gate:` line and the fixture score table with bare score, bare
headroom, solo_claude score, solo_claude headroom, status, and reason columns. When launched
through `npx devlyn-cli benchmark headroom`, the replay `Command:` uses the
same package CLI path.
For passing sets, the report also prints average and minimum `bare`/`solo_claude`
headroom plus the fixture pass count, so ceiling-near, threshold-fragile, or
under-count candidate sets are visible before spending pair arms.
It explicitly reports whether the candidate set was accepted or rejected.
Evidence-clean means the measured arm has complete artifacts, no deterministic
or judge disqualifier, all expected verification commands pass, and any
skill-pipeline verdict is non-blocking (`PASS` or `PASS_WITH_ISSUES`). A
one-fixture calibration run can show useful scores but does not satisfy the set
gate. Add `--dry-run` to validate args, fixture ids, minimum fixture count, and
the replay command without running arms or judges.
Known rejected or ceiling-saturated fixtures are refused by default in the
headroom runner; use `--allow-rejected-fixtures` only for diagnostics of
rejected fixtures or calibrated shadow controls, not for new pair-evidence
candidate selection. Retired fixtures are preserved for historical artifact replay
and are not rerun by the pair-candidate runners.
Before spending new provider calls, inspect the active candidate frontier:

```bash
python3 benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  --out-md /tmp/devlyn-pair-frontier.md
npx devlyn-cli benchmark recent
npx devlyn-cli benchmark recent --out-md /tmp/devlyn-recent-benchmark.md
npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md
```

`benchmark recent` is the reader-facing version of the current evidence set: it
prints a compact, wrap-safe status block, pair-lift aggregates, and one card per
passing pair-evidence fixture. Use it for PR comments and release notes when a
wide frontier table would wrap poorly.
The frontier report lists active fixtures as `rejected`,
`pair_evidence_passed`, or `candidate_unmeasured`, using the same rejected
fixture registry and local full-pipeline gate artifacts. It also prints stdout
summary rows with `bare`, `solo_claude`, `pair`, pair arm, margin, wall ratio, run id, verdict, and trigger reasons for
fixtures that already have complete pair evidence rows, plus average/minimum pair margin and wall ratio,
even when writing `--out-md` or `--out-json`. The markdown artifact also carries
the overall verdict plus row-level verdict, pair-arm, and trigger-reason columns.
Full-pipeline pair gate artifacts record `require_hypothesis_trigger` in JSON
and the report includes a Markdown `Hypothesis trigger` column, so strict regenerated
evidence shows whether each row carried `spec.solo_headroom_hypothesis`.
After a headroom run fails, audit that any active failed fixture without passing
pair evidence is either rejected or reworked before more provider spend. The
same audit also rejects active registry entries whose reason cites a run id or
score that is not backed by a matching local headroom artifact:

```bash
python3 benchmark/auto-resolve/scripts/audit-headroom-rejections.py
npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json
```

For release or handoff checks where open candidates are not acceptable, add
`--fail-on-unmeasured` to the frontier command so any active
`candidate_unmeasured` fixture becomes a nonzero exit.
The package CLI exposes that release/handoff guard as one command:

```bash
npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit
npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict
```

It writes `audit.json` with the frontier summary and an artifact map (`artifacts`), plus
`frontier.json`, `frontier.stdout`, `frontier.stderr`, `headroom-audit.json`, and child stdout/stderr logs, prints the same frontier score rows for existing complete pair
evidence rows, and embeds those compact trigger-backed verdict-bearing score rows in
`audit.json` as `pair_evidence_rows` (each row carries `pair_trigger_eligible: true`, non-empty `pair_trigger_reasons`, `pair_trigger_has_canonical_reason: true`, and `pair_trigger_has_hypothesis_reason`; the audit fails rows missing trigger reasons or missing actionable solo-headroom hypotheses in fixture `spec.md` whose observable command matches `expected.json`). It fails if either active unmeasured pair candidates or unrecorded
headroom failures remain. By default it also revalidates frontier `verdict: PASS`
and zero unmeasured candidates, requires at least four active fixtures with passing pair evidence,
and requires each counted evidence row to satisfy `pair_mode: true`, the default 5-point pair margin, and 3x pair/solo wall ratio.
The audit stdout also prints `headroom_rejections=...`,
`pair_evidence_quality=...`, `pair_trigger_reasons=...`, and
`pair_evidence_hypotheses=...` and
`pair_evidence_hypothesis_triggers=...` handoff rows, plus
`pair_trigger_historical_aliases=...` when archived evidence includes legacy
trigger aliases and `pair_evidence_hypothesis_trigger_gaps=...` when documented
hypotheses have not yet propagated into trigger reasons, with rejected-fixture
coverage counts plus actual minimum pair margin, maximum pair/solo wall ratio,
and canonical trigger reason coverage plus row-match status. The compact evidence row count must match the frontier evidence count, so incomplete local score
artifacts cannot inflate the claim. `checks.frontier_stdout` records summary,
aggregate, final-verdict, expected, printed score-row, trigger-visible row, and hypothesis-trigger-visible row counts, `checks.pair_evidence_quality`
records the same quality thresholds from the compact rows,
`checks.pair_trigger_reasons` records canonical/historical-alias/exposed/total trigger-reason row counts, fixture-level historical alias details, summary count, and row-match status
for handoff review, `checks.pair_evidence_hypotheses` records documented/total pair-evidence hypothesis row counts, and `checks.pair_evidence_hypothesis_triggers` records whether documented hypotheses also appear as `spec.solo_headroom_hypothesis` trigger reasons plus fixture-level gap details.
Add `--require-hypothesis-trigger` to turn those hypothesis-trigger gaps from
archived-evidence WARN rows into release-blocking FAIL rows for newly
regenerated pair evidence.
Historical trigger aliases are only reported for archived artifact review; new
current pair-evidence gates fail historical-only or unknown trigger reasons and
require at least one canonical `pair_trigger.reasons` entry.
`checks.headroom_rejections` records the child verdict plus unrecorded and
unsupported registry-rejection counts, so handoff review can see rejected-fixture
coverage without opening the child artifact first.
Override `--min-pair-evidence`, `--min-pair-margin`, or
`--max-pair-solo-wall-ratio` only for narrower diagnostics.

When changing the calibration/pair evidence gates, run:

```bash
bash scripts/lint-fixtures.sh
bash benchmark/auto-resolve/scripts/test-ship-gate.sh
bash benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh
bash benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh
bash benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh
bash benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh
bash benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh
bash benchmark/auto-resolve/scripts/test-headroom-gate.sh
bash benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh
bash benchmark/auto-resolve/scripts/test-check-f9-artifacts.sh
bash benchmark/auto-resolve/scripts/test-lint-fixtures.sh
bash benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh
bash benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh
bash benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh
bash benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh
bash benchmark/auto-resolve/scripts/test-run-swebench-solver-batch.sh
bash benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh
bash benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh
```

`build-pair-eligible-manifest.py` writes `selection_rule.rejected_excluded`
with the rejected fixture ids removed from Gate 3, and
`selection_rule.rejected_excluded_reasons` with the exact registry reason for
each removed id. This keeps the manifest self-explaining when F31/F32-style
solo-ceiling controls are excluded from pair-lift evidence.

After a full-pipeline pair run has the calibrated arms (`bare`, `solo_claude`,
and the selected pair arm, default `l2_risk_probes`) plus a blind `judge.json`,
gate it separately:

```bash
bash benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  --min-fixtures 3 \
  --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

The same runner is available through `npx devlyn-cli benchmark pair ...`.
The runner executes `bare` + `solo_claude`, applies `headroom-gate.py`, and
only then spends the selected pair arm. Pair arms are limited to current
proof (`l2_risk_probes`) or diagnostic replay (`l2_gated`); `l2_forced` is
retired and rejected. It prints the exact replay command plus each gate's
markdown report to stdout, including startup `Headroom:` / `Pair:` lines,
fixture pass count, average pair margin, and the fixture score table with bare,
solo_claude, pair, margin, pair-mode, trigger-reason, and wall-ratio columns; if headroom or pair
evidence fails, the report is printed before the runner exits non-zero. If
headroom fails, the runner explicitly says the pair arm was not executed; if
the final pair gate fails, it explicitly says pair evidence was rejected. When
both gates pass, it explicitly says the selected pair arm is being executed and
then that pair evidence was accepted. When launched through
`npx devlyn-cli benchmark pair`, the replay `Command:` uses
the same package CLI path. Add `--dry-run` to
validate args, fixture ids, minimum fixture count, and the replay command
without running arms or judges. Known rejected or ceiling-saturated fixtures
are refused by default here too; use `--allow-rejected-fixtures` only for
diagnostics of rejected fixtures or calibrated shadow controls. Retired fixtures
remain historical replay artifacts and are not rerun by this candidate runner.
To gate already-existing artifacts:

When a prompt-only pair change needs a fresh `l2_risk_probes` measurement but
the calibrated `bare` + `solo_claude` arms are already evidence-complete, reuse
them into a new run id:

```bash
bash benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  --run-id <new-run-id> \
  --reuse-calibrated-from <prior-headroom-run-id> \
  --min-fixtures 3 \
  --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

```bash
python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  --run-id <full-pipeline-run-id> \
  --min-fixtures 3 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3 \
  --out-json benchmark/auto-resolve/results/<full-pipeline-run-id>/full-pipeline-pair-gate.json \
  --out-md benchmark/auto-resolve/results/<full-pipeline-run-id>/full-pipeline-pair-gate.md
```

This is the full-pipeline claim gate: each counted fixture must satisfy the
headroom precondition (`bare <= 60`, `solo_claude <= 80`, default 5-point `bare`/`solo_claude` headroom margins), the selected pair arm must be evidence-clean,
`pair_mode` must be true in the captured resolve state, the pair trigger must be
eligible with non-empty reasons and at least one canonical reason, fixtures with an actionable solo-headroom hypothesis must include `spec.solo_headroom_hypothesis` in the trigger reasons, the pair/solo wall-time
ratio must stay within the default 3x limit, and the blind judge must score the
pair arm at least `--min-pair-margin` above `solo_claude`. The report separates
the allowed pair/solo wall ratio from the maximum observed pair/solo wall ratio,
records `require_hypothesis_trigger` in JSON, and includes a Markdown
`Hypothesis trigger` column for each fixture row.
The judge
file must also map `bare`, `solo_claude`, and the selected pair arm in
`_blind_mapping`; `scores_by_arm` alone is not evidence.
`l2_risk_probes` is the current measured pair arm for the
F16/F23/F25 gate: `20260510-f16-f23-f25-combined-proof` passed with margins
+21, +31, and +24, average pair margin +25.3, and average pair/solo wall ratio
1.73x. Earlier F16/F25 evidence also passes the current gate in
`20260509-f16-f25-combined-cartprobe-v2`.
Additional focused F21 evidence: `20260511-f21-current-riskprobes-v1` passed
with `bare` 33, `solo_claude` 66, `l2_risk_probes` 99, margin +33, pair mode true, and
pair/solo wall ratio 1.47x, and is counted by `benchmark audit` as the fourth passing pair-evidence row. Do not count ceiling/control fixtures as pair
evidence: F22 and F26 are
currently rejected because existing headroom runs put `solo_claude` at 98. F27
subscription proration is also rejected in its first headroom smoke:
`20260511-f27-headroom-smoke-061401` measured bare 33 / solo_claude 94, with bare
verification passing only 1 of 3 commands. Rework or rotate F27 before spending
a pair arm on it. F28 return authorization is rejected as pair-lift evidence:
earlier unstable runs `20260511-f28-headroom-smoke-085307` and
`20260511-f28-pair-smoke-091021` were superseded after a hidden-oracle bug was
found. The oracle had expected a defective item to bypass expiration, which the
visible spec does not require. After re-verifying the same provider diffs
against the corrected oracle, `20260511-f28-policy-oraclefix-reverified-pair`
scored bare 50 / solo_claude 98 / `l2_risk_probes` 96, margin -2, and failed headroom.
Rework or rotate F28 before spending more pair arms.
F30 credit hold settlement is also rejected: `20260511-f30-headroom-v1` scored
bare 33 / solo_claude 98, so it failed the `solo_claude` headroom precondition before any pair
arm should be spent. F15 frozen-diff race review is now a ceiling/control
fixture too: `20260511-f15-concurrency-headroom` scored bare 99 / solo_claude 94, so
it failed both headroom preconditions. F3 backend contract risk is also
rejected after tightening its HTTP error-body verifier:
`20260511-f3-http-error-headroom` scored bare 97 / solo_claude 99. F2 medium CLI is
rejected by `20260512-f2-medium-headroom`: bare 83 / solo_claude 95, so both baseline
scores exceed headroom ceilings. F4 web browser design is rejected by
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
33 / solo_claude 98, with bare judge/result/verify disqualifiers. Rework it before
spending pair arms. F32 subscription renewal is rejected by
`20260512-f32-subscription-renewal-headroom`: bare 33 / solo_claude 98, so it is a
solo-ceiling billing rollback/shape control rather than pair-lift evidence.

Commands that reference `BENCH_FIXTURE_DIR` are hidden post-run oracles: they
are not staged into BUILD_GATE's `.devlyn/spec-verify.json`.

To compare pair VERIFY against solo VERIFY on a frozen implementation diff,
run:

```bash
bash benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  --fixture F16-cli-quote-tax-rules \
  --diff benchmark/auto-resolve/results/<run-id>/F16-cli-quote-tax-rules/solo_claude/diff.patch \
  --pair-mode gated
```

This applies the diff before `/devlyn:resolve` starts, then runs verify-only
solo and pair arms against the same committed work tree. `--pair-mode gated`
tests the product trigger policy; `--pair-mode forced` adds `--pair-verify` for
diagnostics. Use non-empty diffs only; empty diffs fail fast because they are
not valid pair evidence.
Hidden verifier context is available during VERIFY, so this runner prevents
IMPLEMENT contamination but is not an oracle-blind judge setup.
The runner writes `compare.json` and `compare.md`; `pair_verdict_lift: true`
means pair VERIFY actually ran and found a verdict-binding issue that solo
VERIFY did not. It also prints a replay `Command:` block before invoking
providers and a final solo/pair summary table.
If an imported case has no deterministic `verification_commands`, the runner
does not create `.devlyn/spec-verify.json`; an empty carrier is malformed by the
normal real-user contract and must not block qualitative frozen review.

To gate a set of frozen VERIFY results mechanically:

```bash
python3 benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  --run-id 20260505T173913Z-9986cd3-frozen-verify \
  --run-id 20260505T230215Z-9986cd3-frozen-verify \
  --require-hypothesis-trigger \
  --max-pair-solo-wall-ratio 3 \
  --out-json benchmark/auto-resolve/results/frozen-verify-gate-20260505.json \
  --out-md benchmark/auto-resolve/results/frozen-verify-gate-20260505.md
```

When changing the gate itself, run its regression test:

```bash
bash benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh
```

This is deliberately narrower than `headroom-gate.py`: it does not claim
full-pipeline pair superiority. It proves only that, after the implementation
diff is frozen, gated pair VERIFY fires and returns a stricter verdict-binding
result than solo VERIFY on the same diff. Each supplied run must cover a
distinct fixture; repeated runs of the same fixture do not count as independent
evidence. For new measurements, pass `--require-hypothesis-trigger` so any
fixture spec with an actionable solo-headroom hypothesis must also expose
`spec.solo_headroom_hypothesis` in `pair_trigger.reasons`; omit it only when
re-gating historical artifacts that predate that trigger reason.
corpus growth. `--max-pair-solo-wall-ratio` is optional, but use it for
ship-style evidence so quality lift is not accepted without a reasonable
wall-time bound. The gate infers the fixture id from the runner input metadata;
artifacts without that metadata, or with a fixture id absent from
the selected `--fixtures-root`, fail instead of being counted as anonymous or
fake evidence. JSON rows expose `pair_trigger_reasons` and
`pair_trigger_has_canonical_reason`; Markdown output includes a `Triggers`
column so reviewers can see which canonical pair trigger made the evidence
eligible.

### SWE-bench fixed-diff review pilot

SWE-bench is useful here as an external, widely known corpus, but the first
measurement surface should remain frozen VERIFY rather than full-pipeline
generation. The official dataset fields include `instance_id`, `repo`,
`base_commit`, `problem_statement`, `patch`, and `test_patch`; SWE-bench Lite is
the smaller subset and SWE-bench Verified is the human-validated subset.
See:

- https://www.swebench.com/SWE-bench/guides/datasets/
- https://www.swebench.com/lite.html
- https://www.swebench.com/verified.html

Fetch a small official Lite/Verified instance file without installing the
Hugging Face Python stack:

```bash
python3 benchmark/auto-resolve/scripts/fetch-swebench-instances.py \
  --dataset lite \
  --limit 5 \
  --out benchmark/auto-resolve/external/swebench/instances-lite.jsonl
```

Prepare one case from an instance JSON and a candidate patch produced by a solo
run or another external solver:

```bash
python3 benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py \
  --instance-json /path/to/swebench-instance.json \
  --model-patch /path/to/solo-candidate.patch
```

Or prepare a small corpus from the official SWE-bench prediction JSONL shape
(`instance_id`, `model_name_or_path`, `model_patch`):

```bash
python3 benchmark/auto-resolve/scripts/collect-swebench-predictions.py \
  --patch-root /path/to/logs \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --model-name external-solo \
  --out benchmark/auto-resolve/external/swebench/solo-predictions.jsonl
```

The collector expects `/path/to/logs/<instance_id>/patch.diff`; it is useful
when another solver or a downloaded SWE-bench log bundle provides per-instance
patch files rather than prediction JSONL.

```bash
python3 benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --predictions-jsonl /path/to/solo-predictions.jsonl \
  --limit 5 \
  --out-manifest benchmark/auto-resolve/external/swebench/manifest.json
```

Then run the command written to
`benchmark/auto-resolve/external/swebench/cases/<instance_id>/run-command.txt`.
For a one-off case, the command uses:

```bash
bash benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  --fixture <instance_id> \
  --fixtures-root benchmark/auto-resolve/external/swebench/cases \
  --base-repo benchmark/auto-resolve/external/swebench/repos/<repo-cache> \
  --diff benchmark/auto-resolve/external/swebench/cases/<instance_id>/model.patch \
  --pair-mode gated
```

For a prepared corpus manifest, run the whole set and gate it:

```bash
bash benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh \
  --manifest benchmark/auto-resolve/external/swebench/manifest.json \
  --min-runs 2 \
  --max-pair-solo-wall-ratio 3 \
  --timeout-seconds 900 \
  --resume-completed-arms \
  --run-ids-out benchmark/auto-resolve/results/swebench-frozen-run-ids.txt \
  --out-json benchmark/auto-resolve/results/swebench-frozen-gate.json \
  --out-md benchmark/auto-resolve/results/swebench-frozen-gate.md
```

The corpus runner prints a replay `Command:` block before invoking providers or
gating existing run ids, so frozen VERIFY score runs can be reproduced from the
captured stdout.

To re-gate existing run ids without re-invoking providers, write one run id per
line and pass `--gate-only-run-ids <file>` with the same manifest. For large
tranches, keep `--run-ids-out` and use `--resume-completed-arms` on retries:
successful solo/pair arms are reused, while failed or provider-limited arms run
again. The run ids file is the durable handle for gate-only reruns and matrix
rendering after a bounded run finishes.

To produce local candidate patches for a bounded pilot, prepare a solver
worktree from the same instance JSONL. The generated spec contains only the
visible SWE-bench problem statement; do not read the instance's gold `patch` or
`test_patch` while solving.

```bash
python3 benchmark/auto-resolve/scripts/prepare-swebench-solver-worktree.py \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --instance-id django__django-11019 \
  --copy-devlyn-context
```

Run the prompt in `<worktree>/solve-prompt.txt`, save the resulting diff as
`<patch-root>/<instance_id>/patch.diff`, then use
`collect-swebench-predictions.py` to create prediction JSONL.

For a bounded local pilot, the batch runner performs those steps
sequentially and collects prediction JSONL. It redirects provider stdin away
from the manifest stream so later rows cannot be consumed by a child process.
The generated solver worktrees and repo caches can become large; once
`predictions-out` is written and cases are prepared, remove ignored local cache
directories such as `external/swebench/worktrees/` and
`external/swebench/repos-solver/` if disk pressure would otherwise interrupt
the frozen corpus run. Use `--timeout-seconds` and `--resume` for large
tranches; long-tail solver rows should be recorded as throughput failures
instead of letting one row hold the whole suite open.

```bash
bash benchmark/auto-resolve/scripts/run-swebench-solver-batch.sh \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --instance-id django__django-11039 \
  --instance-id django__django-11049 \
  --predictions-out benchmark/auto-resolve/external/swebench/predictions-lite.jsonl \
  --copy-devlyn-context
```

Gate a SWE-bench review pilot by pointing the existing frozen gate at the
external case root:

```bash
python3 benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  --fixtures-root benchmark/auto-resolve/external/swebench/cases \
  --run-id <swebench-frozen-run-1> \
  --run-id <swebench-frozen-run-2> \
  --run-id <swebench-frozen-run-3> \
  --min-runs 3 \
  --require-hypothesis-trigger \
  --max-pair-solo-wall-ratio 3 \
  --out-json benchmark/auto-resolve/results/swebench-frozen-gate.json \
  --out-md benchmark/auto-resolve/results/swebench-frozen-gate.md
```

This gives evidence for "pair review catches solo-missed verdict-binding issues
on real SWE-bench patches." The gate accepts either external solo-vs-pair
verdict lift or internal pair lift (`pair_judge` stricter than the pair run's
primary judge), because separate solo and pair primary judges are stochastic.
For evidence intended to support shipping policy, also set a wall-ratio cap and
inspect `avg_pair_solo_wall_ratio` plus each row's `pair_solo_wall_ratio`.
For selection-bias control, render every run in the attempted pilot, not just
gate rows. The matrix reports verdict-lift rows separately from recall-only
rows where pair found additional findings but did not change the binding
verdict. It also reports pair-trigger eligibility/contract failures,
trigger reasons, canonical-trigger coverage, classification counts, gate rate,
and trailing non-gate rows. Its Markdown table includes a `Triggers` column.
For new measurements, pass `--fixtures-root` with
`--require-hypothesis-trigger` so matrix rows classify any missing
`spec.solo_headroom_hypothesis` trigger reason as a pair-trigger contract
failure instead of leaving it to the gate artifact alone.
Use the optional yield thresholds when the matrix is meant to
fail closed instead of only documenting that additional rows are adding
controls without strengthening the proof gate:

```bash
python3 benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  --title "SWE-bench Lite Frozen VERIFY Matrix" \
  --verdict MIXED_WITH_GATE_PASS \
  --fixtures-root benchmark/auto-resolve/external/swebench/cases \
  --gate-json benchmark/auto-resolve/results/swebench-frozen-gate.json \
  --run-id <swebench-frozen-run-1> \
  --run-id <swebench-frozen-run-2> \
  --require-hypothesis-trigger \
  --min-gate-rate 0.25 \
  --max-trailing-non-gate 10 \
  --out-json benchmark/auto-resolve/results/swebench-frozen-matrix.json \
  --out-md benchmark/auto-resolve/results/swebench-frozen-matrix.md
```

It does not measure official SWE-bench solve rate; run the official SWE-bench
evaluator separately for that metric. When changing the importer or
external-base runner path, run:

```bash
bash benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh
```

Do not use the retired full-pipeline `l2_forced` arm as pair evidence. It puts
`--pair-verify` in the initial prompt, so IMPLEMENT can become pair-aware before
the diff is frozen.

## LLM-upgrade resilience

- **No model hardcoding.** Judge runs Codex without `-m`, inheriting whichever flagship the CLI currently ships. The call is isolated from user config/rules/hooks so local agent instructions cannot contaminate the blind judgment. Each run captures `_judge_model` for historical provenance.
- **Margin-based gates.** Ship thresholds use pairwise margins, not absolute score. `solo_claude`-`bare` measures solo harness value; pair-`solo_claude` measures pair value on pair-eligible fixtures. As models improve, margin remains the meaningful harness-added signal.
- **Saturation rotation.** When all compared gated arms exceed 95 on a fixture for two shipped versions, rotate it (see `RUBRIC.md::Fixture Rotation Policy`).

## Ship gates (summary — see `RUBRIC.md` for full spec)

Hard floors (any one fails → block):

- Zero variant disqualifier (silent catch, fabricated verification, extra deps beyond `max_deps_added`, etc.).
- `F9-e2e-ideate-to-resolve` must PASS (novice-flow contract).
- ≥ 7 gated, headroom-available fixtures have margin ≥ +5.
- No per-fixture regression worse than −5 vs last shipped baseline.

Soft gates (warning, not block): suite-margin drop > 3, fixture losing its margin, critical-finding catch-rate regression vs last shipped variant.

## Running the full suite (real)

Full real benchmarks usually take 2-3 minutes per arm for simple fixtures and
up to 15 minutes per arm for strict-route fixtures. A full n=1 run time depends
on the selected fixture count; the historical 9-fixture core suite was roughly
45 min - 3 hrs for 3 arms, while the current extended suite can take longer.

```bash
# Smoke run before ship decisions
npx devlyn-cli benchmark

# Ship-decision run
npx devlyn-cli benchmark --label v3.7 --bless
```

## Dry-run

`--dry-run` skips model invocation. It still:

- Prepares each fresh work dir.
- Writes arm-specific prompts.
- Commits the baseline.
- Applies `setup.sh`.
- Runs verification commands (which will mostly fail since no implementation was added).

Use it to sanity-check new fixtures or runner changes before burning model tokens.
