# Auto-Resolve Benchmark Harness (v2.1)

Reproducible methodology for measuring auto-resolve pipeline quality and efficiency across versions. Built to answer: **does v2.1 improve over v1.14.0 without regressing quality?**

## What this harness measures

### Static properties (measured at every run — cheap, always valid)

- `SKILL.md` line count / estimated tokens (instruction surface)
- Per-route phase count (theoretical work units per task)
- Artifact file count & type (structured vs monolithic)
- Schema conformance of emitted artifacts

Script: `measure-static.py`. Runs in <1 second. No subagent calls.

### Routing trace properties (measured per test case)

- Stage A decision + reasons
- Stage B decision + reasons (post-BUILD)
- Final phase list
- Guardrails bypassed (if any)

Script: `trace-route.py`. Simulates the orchestrator's routing logic on a fixture spec. No real pipeline execution. Validates that routing logic produces the designed outcomes.

### Dynamic properties (require real pipeline runs — EXPENSIVE)

These require actual auto-resolve execution on real tasks. NOT RUN AUTOMATICALLY.

- Wall-clock time per phase
- Actual token consumption (Codex + Claude)
- Fix-round convergence (rounds used vs max_rounds)
- Final criterion verification correctness
- Pipeline verdict

To run these: follow `run-real-benchmark.md` procedure. Expect 15-45 minutes per task × version.

## Test case library

`test-cases/` contains:

- **T1-trivial/** — CLI help-text typo. Expected route: `fast`. Zero risk, 1-3 requirements, no web files.
- **T2-standard/** — Single API endpoint + error UI. Expected route: `standard`. Medium complexity, no risk keywords in spec, web files present (triggers browser validate).
- **T3-high-risk/** — Auth middleware change. Expected route: `strict`. Risk keywords in spec (`auth`, `session`, `token`), high complexity.

Each test case has:
- `task.txt` — the task description the user would pass
- `spec.md` — the ideate-format spec file (for spec-driven cases)
- `expected.json` — the expected route, stage_a reasons, phase list, guardrail bypasses

## Reproducing baseline-vs-new measurements

### Static comparison

```bash
python3 benchmark/measure-static.py --baseline 4eb7b47 --head HEAD > static-results.json
```

Compares any two git refs. `4eb7b47` is the pre-v2.1 baseline (`feat(skills): CPO lens in ideate + handoff enforcement on auto-resolve, bump to 1.14.0`).

### Route trace comparison

```bash
python3 benchmark/trace-route.py --test-case T2-standard --version head
```

Runs Stage A + Stage B logic on the test case's spec/task without actually spawning BUILD. Validates the routing decision matches `expected.json`.

### Full real-pipeline benchmark (manual, expensive)

See `run-real-benchmark.md`. Requires:
- Sandbox environment per run (so the codebase isn't polluted)
- Codex MCP available
- ~7-15 hours for 30 paired runs at statistical significance

## Honest scope of current results

This harness was created alongside v2.1 STEP 6. The current commit includes:

- ✅ Harness scripts
- ✅ 3 test cases with expected routing outcomes
- ✅ Static measurements (baseline `4eb7b47` vs v2.1 HEAD)
- ✅ Route trace simulations for all 3 test cases
- ⏳ Dynamic measurements — **not yet run**. The harness is ready; user executes on demand.

No dynamic numbers (wall-time, real tokens) are reported without actual execution. Any such numbers in prior design docs (e.g., "−50% trivial wall-time") remain labeled as **hypotheses** until real runs validate them.

## How to extend

Add a test case:
1. Create `test-cases/<name>/` with `task.txt`, `spec.md` (optional), `expected.json`
2. Run `trace-route.py --test-case <name>` to verify expectations match the routing logic
3. Run a real pipeline execution and record actuals in `test-cases/<name>/actual.json`

Update the baseline:
- The baseline git ref (`4eb7b47`) is fixed by design. When a future v3 releases, measure against v2.1 HEAD as the new baseline.
