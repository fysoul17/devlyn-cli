# 0149 — Preserve explicit agent-target intent

2026-09-11. Mission 1, intent fidelity. Baseline `67e85a1` contains 0148's
inline-carrier repair. This iteration uses a fresh actual CLI defect to inspect
natural-language constraint authoring and ship a root-owned correction without
invoking resolve. Frozen experiments and A16 remain unchanged.

## Concrete task and prediction

`agents <cli>` selects one agent (`README.md:30`), but the dispatch at
`bin/devlyn.js:1317` treated an unknown target like an omitted target and entered
automatic installation. Its ordinary object lookup also accepted inherited
names such as `constructor`. Why did a typo install something else? Missing and
invalid explicit input shared the auto-detection branch; target membership was
not limited to the declared keys.

Before reproduction, `.devlyn/0149-authoring/registration.json` fixed the task:
reject an unsupported explicit target with its value, supported choices and a
nonzero exit, without changing project/agent-home entries, bytes or modes.
Preserve no-argument detection, supported targets and `all`. Predicted baseline
failures were observed: `cdoex` and an explicit empty string exited 0 and wrote
project/home files when `.codex` was detectable; `constructor` reported success.
The no-detection typo also exited 0. All installations used isolated test homes.

## Smallest product repair

Dispatch now matches only declared target keys and rejects any remaining explicit
argument before detection/installation. Only an omitted argument auto-detects.
The diagnostic JSON-quotes the invalid string, making empty/control characters
visible, and lists supported targets. No flag, parser or installer redesign.

The existing native package-test driver supplies temporary projects and a
child-only `os.homedir` preload; the process's real HOME is unchanged. Added
regressions cover five invalid values with/without detection (10 cases), exact
entry/content/mode preservation, and seven allowed selection/detection cases.
Baseline fails all 10 invalid cases; the repair passes all five PackageTests
against an actual locally packed/installed artifact (3.556s, macOS).
A separately registered partial fix installs first and then emits the same
invalid-target diagnostic/nonzero exit. The owner's filesystem checks reject
all five detectable cases of that partial fix, so exit-code-only coverage cannot
explain this regression's success. Native Windows execution is not claimed.

## Bounded authoring observation

The pre-registered question is whether current generated-authoring guidance
retains the no-write clause and proposes an executable check that distinguishes
correct early rejection from the late-rejection control. One independent native
Fable 5.1/high and Grok 4.6/high proposal receives the same baseline source and
current free-form/template references. Verification-only file proposals are
allowed so dependencies on new tests are explicit. Original terminal outputs
are retained; one whole-response JSON fence is an accepted presentation wrapper.

This is a static proposal extraction, with tools disabled. It cannot establish
production PHASE 0 behavior, where the orchestrator reads files and runs guard
controls, or the ordinary conversational route, which need not generate criteria.
The registered baseline/correct/late-rejection copies contain the same original
tests; the new owner regressions are excluded from authored-check scoring.
Their Git IDs identify isolated control-copy commits, not the main baseline
commit. Raw case label `typo-empty` means `cdoex` in an undetected project;
the separate `empty` case supplies an actual empty string.
Only an observed filesystem assertion failure supports no-write coverage;
failure on extra installation logs alone does not. One task provides no general
model/pair advantage or harness-prompt promotion evidence.

Both proposals complete with no observed tool calls and valid inline carriers:
Fable 5.1 in 316.308s; Grok 4.6 (emitted `grok-4.6-build`) in 353.875s. Both
retain the no-write clause and propose entry/content/mode snapshots. Fable's
four unchanged verification commands run through the actual generated-carrier
checker: correct 0, baseline 1, late rejection 1. The pre-existing PackageTests
pass in all three copies, so they do not explain detection. Allowed target and
auto-detection cases pass within the proposed test on the correct copy.

Failure attribution matters: the registered late-rejection case first fails
Fable's installation-log assertion, before the filesystem assertion. A separate
**post-observation diagnostic**, predicted before execution, silences only the
late install's logs. Unchanged verification then fails at
`self.assertEqual(before, case.snapshots())`. That supports this snapshot's
sensitivity to the observed late-write fault; it is not a confirmation sample
or independent proof of mode-only detection.

Grok's proposed file explicitly assigns child `HOME` and `USERPROFILE` in
addition to the supplied homedir preload. The owner's execution instructions
prohibit repurposing HOME, so that proposal is **NOT_RUN_RESERVED_ENV_OVERRIDE**,
not a pass or a model failure rate. Its original bytes are preserved, without
repair for scoring. Static inspection also finds `re.I` passed as `assertRegex`'s
message argument rather than regex flags; no full execution result is claimed.

Root adopts no authoring instruction change: the one executable proposal
retains the constraint and detects the observed fault; the other is unexecuted.
This does not establish authoring completeness or production guard-validation
reliability. Full `bash scripts/lint-skills.sh` passes in 242.152s. Fresh
independent source reviews complete: Fable 5.1 **PASS_WITH_ISSUES** (83.028s),
Grok 4.6 **PASS** (140.623s), no CRITICAL/HIGH or in-scope product defect.
Root retains the CLI's existing stdout diagnostic convention; LOW test-token
matching advice is nonblocking. Label/commit distinctions are clarified above;
the raw regression stderr supplies the per-subtest failures omitted from the
review packet's compact result JSON. Source acceptance is scoped to this repair.

## Hosted-check boundary

While checking delivery, the owner found a pre-existing Windows CI failure on
0148: [PR job](https://github.com/fysoul17/devlyn-cli/actions/runs/34609270179/job/103296947146)
fails two NativeOwnershipTests expecting two Job Object PIDs but observing three.
The [push job](https://github.com/fysoul17/devlyn-cli/actions/runs/34609264386/job/103297016986)
passes with identical package/driver bytes. Installer tests pass in both.
0149 leaves those ownership tests and implementation unchanged. The third PID's
identity is absent from the logs, so this is not certified harmless infrastructure.
Preserve that failure and inspect 0149's own hosted checks before merging;
do not loosen assertions or rerun until green. Its delivery status/evidence
is recorded separately from this committed local source acceptance.

## Principles and custody

**No workaround / Production ready:** distinguish invalid input from omission
before any installation side effect. **No overengineering / Best practice:**
replace the inherited-property lookup with declared-key membership and reuse
the package-test isolation. Removing the explicit-error branch restores typo
auto-installation; removing key membership restores prototype-name acceptance.
**No guesswork / Worldclass:** registered predictions, real failing controls,
packed-artifact tests and independent reviews bound the acceptance claim.
**Optimized:** no model-speed, whole-run efficiency or broad recall gain claimed.

Raw evidence lives in the retained research checkout's `.devlyn/0149-authoring/`.
Task receipt `04c8d7f4ab67f53f7e57352d` owns source acceptance, delivery and
recoverable evidence custody separately. No npm release or global engine change.
