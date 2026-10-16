1. **HIGH — `merge_refused` can still disappear.** [smoke.py:287](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/smoke.py:287) ignores calls without literal `task-complete.py`. A synthetic current-receipt refusal from `source /tmp/helper-env; python3 "$helper" complete --receipt …`, followed by a successful literal invocation, retained only `COMPLETE` and returned `merge_refused=False`. A direct invocation with trailing `# --help` is also incorrectly ignored. This permits decisions where DESIGN requires INCONCLUSIVE.

   **Fix:** bind structured completion evidence to the receipt and native execution/continuation provenance; command spelling cannot establish absence of refusal. Handle shell comments correctly. Add refusal-then-success regressions for externally initialized variables, wrappers, and trailing comments.

2. **MEDIUM — Harmless source inspection forces STOP.** [smoke.py:326](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/smoke.py:326) rejects `rg -n "def complete|merge_refused" .agents/skills/_shared/task-complete.py` with `helper command cannot be classified`. [runner.py:254](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/runner.py:254) converts this ordinary inspection into STOP, unnecessarily invalidating a measured run.

   **Fix:** distinguish source inspection from helper execution. Test inspections interleaved with genuine completions.

Checked every round-1 finding against `git diff HEAD~1`: Claude bearer scanning, shared smoke-attempt consumption/bindings, observer exception isolation, and missing `merge_refused` rejection are fixed. Refusal detection is only partially fixed, as above. No additional material findings in arm installation, schedule/renewal rules, credential scoping, or the ordered Decision implementation.

Validation: **16 tests and 12 subtests passed**, plus eight in-memory decision assertions and targeted scanner/parser probes. The README suite could not start because the read-only sandbox has no writable temporary directory. Existing tests miss the two parser cases above. No files changed; no Docker, network, or credentials used.

VERDICT: REVISE
