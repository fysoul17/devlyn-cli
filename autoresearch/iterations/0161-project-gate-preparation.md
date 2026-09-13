# 0161 — Validate project gate environments before admission

2026-09-13. User: “오케이 계속 진행”. This is preparation-only calibration
after0159, not a native model task, replay or replacement of its frozen results.
Root operates directly; actual Fable5.1/Grok4.6 supply read-only advice.

## What preparation caught

At pytest3fd8675d6d798507c06cf9c60753be6d9d7b0e17, `pytest[dev]` supplies runtime
test dependencies but not the separately configured gate environments. Installing
mypy2.3.1/Ruff0.16.6 alongside all dev dependencies was still insufficient:
mypy encountered NumPy stub `type` syntax incompatible with the project's
`python_version = "3.10"`. Both original source and behavioral gold failed there.
No tool version/config/severity was weakened to hide that failure.

The project's `.pre-commit-config.yaml` isolates mypy and its declared typing
dependencies from runtime extras. Its actual isolated mypy/Ruff interpreters pass
the original task-file checks; whole default `pre-commit run --all-files
--show-diff-on-failure` also passes on a separately owned source clone, without
changing source bytes. Whole-hook scope is recorded separately from two-file
task checks. Manual hooks and the upstream OS/Python matrix were not exercised.

The original behavioral gold still passes48/48 but fails mypy (`Config` has no
`_tmp_path_factory`) and Ruff formatting. It is rejected for new fully gated
admission; original0159's behavior-only calibration and results stay unchanged.
A separately named preparation calibration types the existing dynamic lookup
with `factory: TempPathFactory = getattr(item.config, "_tmp_path_factory")` and
uses that local value. There is no default hiding a missing attribute. This also
removes the overlong expression. No prior gold or model-produced patch is edited.

| Preparation input | Isolated type/lint/format | Existing tmpdir tests | Behavior | Default whole pre-commit |
| --- | --- | --- | --- | --- |
| Original source | PASS | 58 pass,1 skip | expected42/48 | PASS; zero diff |
| Frozen gold copy | type/format FAIL | 58 pass,1 skip | 48/48 | not run; already rejected |
| New calibration | PASS | 58 pass,1 skip | 48/48 | PASS; zero diff |

## Admission requirements for the next separate task

- Read the actual project tool tables, hook pins, extra dependencies and CI/tox
  commands. Developer extras and tool importability alone do not establish readiness.
- Preserve the project's environment separation. Record each gate's executable,
  version, resolved dependencies, cwd, source/test inputs, environment and timeout.
  Do not use the combined runtime Python for mypy here. The future task must
  receive the actual validated command routes, not infer them from PATH.
- Execute every selected required command on original source and the proposed
  calibration before model admission. Register expected defect failures separately;
  original42/48 is the known bug, not a reason to require baseline all-green.
- Run auto-fixing hooks only on owned copies. A hook failure or unexpected diff
  rejects readiness; formatting a new calibration is an explicit source change,
  never retroactive acceptance of a failed attempt. Expected no-file/manual skips
  do not substitute for required checks.
- Lock the new task's own commands/inputs and check calibration byte identity.
  These results qualify this preparation exercise, not unseen tasks, a complete
  upstream CI matrix or general speed/quality/pair superiority. Frozen0159 remains
  INCOMPLETE_INFRASTRUCTURE; no same-task rescue or winning-task search.

**Pre-flight0 / Mission1:** prevent another invalid comparison admission.
**No guesswork / No workaround:** retain combined-environment and gold failures.
**No overengineering / Optimized:** use the project's existing isolated hooks;
no installer, router or new runtime phase. **Best practice / Production ready:**
explicit tool routes, source preservation and actual checks. **Worldclass:**
independent review of the final evidence and claim limits. Removing environment
separation or calibration qualification restores a demonstrated failure.

Actual final Fable5.1/Grok4.6 reviews PASS (53.311s/90.963s). The initial
Fable design response fabricated tool markup and has INVALID_REVIEW status;
none of its purported observations is accepted. Final packets attest some
counts; root independently verifies all raw behavior rows, command exits,
test counts, tool versions and source fingerprints in `audit-preparation.json`.
Root accepts PASS_WITH_ISSUES with the stated coverage limits.

Immutable `.devlyn/0161-evidence.tar.gz`:115 byte-verified members, SHA256
`d5e6ab3e315c22780d92daad0720cb1c40d687e9d9ad511b1c7c18635e5121f9`.
Scratch CLEAN (563747391 logical bytes removed). pre-commit had placed15 hook
source/Git clones in scratch; the cleanup helper refused their deletion. Root
moved source/Git to `.devlyn/0161/hook-sources/`, kept disposable environments
in scratch and cleaned them. Future preparation must plan custody for tool
managers' Git clones separately from disposable environments. Source, resolved
versions, patch and raw evidence remain; the cleaned environment must be rebuilt
and validated before use. Delivery is separate at `.devlyn/0161-delivery/`,
receipt73d30959b3f411d8c463ec11; follow [HANDOFF](../HANDOFF.md).
