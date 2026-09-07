# 0123 — Explicit worker and independent judge controls

## Problem and outcome

Users can pin an engine, but IMPLEMENT/CLEANUP and primary VERIFY share that executor; model and effort selection are scattered across native routes. Provide explicit project and per-run choices while retaining unconfigured behavior, canonical phases and independent OTHER review.

Named scheduling change: 0120 direction:22 deferred a primary-judge key pending evidence of allocation benefit. The user's explicit manual-control request supplies a separate acceptance criterion: reliable choice. Automatic defaults and promotion still require comparative evidence. This feature makes no performance claim.

## Requirements

1. **One project configuration.** Extend `.devlyn/engines.json` with optional `roles`, preserving `executor` and `pair_judge_priority`. Role names are `worker`, `primary_judge`, `pair_judge`. Each entry has required nonempty `engine`, optional nonempty exact model ID `model`, optional nonempty `effort`. Reject unknown fields inside `roles`, duplicate JSON keys, unknown roles and null/empty/wrong-type values. Preserve unrelated existing top-level keys when editing. No parent/global devlyn configuration search.

```json
{
  "executor": "codex",
  "pair_judge_priority": ["claude"],
  "roles": {
    "worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "xhigh"},
    "primary_judge": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"},
    "pair_judge": {"engine": "claude", "model": "claude-fable-5-1", "effort": "medium"}
  }
}
```

This is an example, not a new default or ranking.

2. **One per-run override.** Add `--role-config <path>`, accepting the same `{"roles": {...}}` object with no other top-level fields. Reject repeated/missing/unreadable inputs. A role entry replaces the lower-precedence entry as a unit; never inherit another engine's model/effort through field merging. Worker and primary precedence: per-run role entry > explicit `--engine` legacy selection > project role entry > existing executor/default. At its precedence level, `--engine` supplies an engine-only entry, clearing lower-profile model/effort. Pair precedence: per-run pair entry > project pair entry > existing pair priority/complement. Absent primary profile follows the legacy executor, not the opt-in worker profile. Missing model/effort uses that selected route's current default, displayed honestly. `--no-pair` retains explicit solo behavior; unused pair settings do not force dispatch. Freeze resolved choices, provenance and input digests in state before affected dispatch; no mid-run configuration reread or copying user auth/config files into archives.

3. **Preserve role boundaries.** `worker` applies to IMPLEMENT/CLEANUP and repair rounds. PLAN remains orchestrator-fixed; BUILD_GATE retains its existing route and CI-equivalent capabilities. PROBE_DERIVE, SURFACE_CLOSE and deterministic MECHANICAL remain unchanged. Primary and pair settings apply only to VERIFY; risk-probe derivation keeps its existing pair-resolution rule. OTHER must differ from primary by engine; explicit same-engine pair is invalid, not same-provider peer support. Keep fresh contexts, frozen evidence, judge tool restrictions, bounds, findings merge, report→complete→archive order and existing round limits. No new phase, voting, bypass or replay route.

4. **Honor explicit settings or fail visibly.** Check adapter eligibility and actual spawn-channel capability before affected dispatch. Worker requires executor eligibility; judges require judge eligibility. Existing engine/config errors remain fail-closed; unconfigured automatic OTHER retains reported solo selection when unavailable. Model/effort are argv/native-input values, never prompt instructions or shell interpolation. Preserve exact model spelling. No model fallback, effort clamp, silent unsupported-value default or retry with weaker settings. Unsupported fields report `BLOCKED:unsupported-role-option` with role/engine/field and actionable guidance. Explicit unavailable engine retains `BLOCKED:<engine>-unavailable`; native rejection remains raw BLOCKED evidence.

5. **Engine-specific capability and initial supported routes.** Codex CLI worker/primary/pair routes accept `-m` and `-c model_reasoning_effort=...`; Claude CLI primary/pair routes accept `--model`, `--effort`, and `--output-format json`. Keep the existing native Agent worker route for Claude. If that native interface cannot carry a requested exact model/effort with evidence, reject those explicit worker fields with `BLOCKED:unsupported-role-option` and identify the supported Codex worker or native-Claude engine-only route; do not silently substitute a new Claude CLI worker. This is a supported-route boundary, not a claim that Claude cannot implement. Other adapters preserve engine-only eligibility and reject an explicit field unless their existing route has a validated mapping/evidence contract. No guessed universal model support.

   Validate effort against the selected route/model capability evidence, never a universal numeric ranking. Codex may read its current native model-capability cache, with explicit model/version/source provenance and actionable failure when unavailable or inconsistent; do not invent a permanent model registry. Claude CLI's help/capability source, not its narrower persisted-settings schema, governs CLI option spelling. Validate advertised values before dispatch; if model-specific support cannot be established, report unsupported rather than allowing native warn-and-ignore. Native warnings/rejections that say a requested option was ignored must remain a failed explicit promise even at exit0. Missing fields retain existing defaults and truthful inherited/unknown labels.

   Explicit Claude judges use only `Read,Grep,Glob` tools and the existing dontAsk/network route with the600s bound, project-only settings and empty MCP configuration; remove the contradictory Bash allowlist in the adapter. Retain raw JSON stdout. Validate actual exit0, `type=result`, `subtype=success`, `is_error=false`, `stop_reason=end_turn`, nonempty `session_id` and string `result` before deriving the exact `result` string for the unchanged findings collector. Reuse `select_claude_primary_model` for modelUsage identity; preserve raw/derived hashes and never treat wrapper bytes as finding text.

   Explicit isolated Codex judges retain read-only, isolation and the600s bound. A small read-only evidence path may validate the first directly captured native header's model/workdir/sandbox/session and requested effort against the dispatched argv plus exit/raw hashes. That is native CLI configuration evidence, not provider-internal attestation. Reject missing, malformed, duplicate/conflicting fields or a header occurring only inside echoed prompt/result text. Do not relax the existing mutation receipt or its JSONL-only model parser; do not disable ephemeral isolation to obtain logs.

6. **Truthful status and evidence.** `/devlyn:engines` shows role, engine, requested model/effort, source and dispatch channel; pre-execution inherited/unresolved values stay labeled. Show effective model only with its evidence basis. Effective effort stays unknown unless native evidence establishes it: invocation arguments prove dispatch, not hidden provider reasoning. Explicit model mismatch or absent required attestation blocks. Keep `state.engine` as legacy executor; use explicit `phases.verify.engine` consistently for primary spawn, timeout-marker writes/authentication, stdout naming/exclusion and pair resolution, falling back only when absent, never malformed/null. Preserve separate judge identities and bound raw/receipts so executor changes cannot misclassify primary stdout as OTHER or authenticate the wrong timeout. Historical states remain readable.

7. **Reuse the utility.** Add `/devlyn:engines role <worker|primary_judge|pair_judge> <JSON object>` and `role <name> clear`. Existing `executor` and `pair` retain meaning; `clear` removes all role/legacy pins while preserving unrelated keys. Reuse one small deterministic resolver/validator for status, config writes and resolve. It returns data and never calls models, ranks them or owns lifecycle. Customer entries point to canonical skills without maintainer research instructions.

## Smallest implementation boundary

Canonical files below plus exact `.agents/skills` mirrors; local generated `.claude` parity follows normal installation/lint. No research launcher becomes product code.

- New `_shared/role-config.py`: shared resolution, validation and atomic role writes, with focused tests; no registry or dispatcher. `_shared/judge-role-evidence.py` validates explicit read-only native identity/transport without relaxing mutation receipts.
- `_shared/engine-preflight.md`, `devlyn:engines/SKILL.md`, `devlyn:resolve/SKILL.md`: call the helper and replace coupled dispatch instructions only. `_shared/resolve-bootstrap.py:22-26,114-150` must admit/store the new flag without changing existing admission/duplicate/unknown-flag checks.
- `_shared/state-phase-write.py`, `devlyn:resolve/references/state-schema.md`: bind resolved choices and phase/judge evidence; reuse existing engine/model fields (state writer:1543-1662), history and worker attestation.
- `_shared/verify-merge-findings.py`: validated primary accessor at all current uses, notably303,475,686,1206; includes timeout, stdout and pair exclusion. Never overwrite executor temporarily to make merge work.
- `_shared/codex-config.md`, relevant `_shared/adapters/{claude,codex,README}.md`: explicit-selection/capability contracts only, not unrelated prompt or default-effort cleanup.
- `_shared/invocation-receipt.py` and `_shared/archive_run.py` only as needed for explicit judge evidence. Current receipt PHASES:19 excludes VERIFY and line170 requires workspace-write: isolated judge attestation needs a distinct fixed read-only contract, not relaxed mutation receipts. Wrapper changes only if authenticated dispatch actually requires them.
- `AGENTS.md`/`CLAUDE.md`: replace stale coupled-role descriptions and link to the utility. Add the product spec and required validation coverage; no other entry expansion.

## Acceptance and stop

The verification below gates explicit control, compatibility, identity, independent review and package installation. Allocation benchmarks gate automatic policy/default changes, not manual control delivery. No automatic router, version registry, new platform, universal-model-support or complete-usage claim. Root adopts the supported routes and separate read-only evidence boundary above after actual Fable/Grok advice. Grok completed every source read but failed its extra-context isolation check; only source-confirmed design suggestions inform this decision. No advisor consensus or performance claim is required for manual choice.

## Verification

### Observed inspection-contract repair (2026-09-07)

The ordinary installed `8de469d` run's first VERIFY round supplied the Codex judge with file paths and required README line citations while forbidding all command execution. The attested Astra/high call returned only `BLOCKED`; no successful source read was observed. Dispatch identity passed, but the unchanged merge correctly blocked the missing canonical finding. This is an input/access-contract defect, not evidence of a filesystem denial. The inherited wording came from iter0111 (`53f1436`): its observed failure was duplicate lint execution and a false sandbox-based product finding, not read-only source inspection. In `devlyn:resolve/SKILL.md` and `references/phases/verify.md`, replace the blanket prohibition with native read/search tools or non-mutating shell inspection of the authorized source, diff and sealed evidence. Preserve no mutation, no verification/lint/test/build/probe or invented-scenario execution, the existing sandbox/isolation, independent contexts, review bounds, parser and verdict floors. Update only the affected existing lint contract and mirrors. Keep the active installed run and historical evidence unchanged; validate the repaired source through a separate ordinary installation/run. This repair makes the existing review contract executable across engines; it makes no accuracy or speed superiority claim.

The same run's two native Fable initial user messages also contained the sealed prompt plus an LF and the entire caller Python heredoc (558/548 extra bytes). Both dispatcher `subprocess.run` and `_shared/run-bounded.py` inherited stdin; argv/prompt digest equality therefore did not establish actual user-input equality. Close stdin in the existing bounded non-interactive command runner after confirming its production consumers pass prompts as argv. Preserve command argv, stdout/stderr, exit and timeout behavior; no new flag or launcher. Add a real inherited-input regression to the required lint checks and retain its before/after results. Supersede the early `f9041e8` run without rewriting its incomplete pipeline evidence, then verify a fresh installed run's actual native initial input against its sealed prompt as well as model/transport. Broader native project context remains separately reported.

The consumer audit found two historical stdin-based research callers, `benchmark/ceiling/probes/sc-format-0076/run-draws.sh` and `run-baseline.sh`. Preserve those scripts and their results; historical replay requires their original frozen runner. Current production prompt callers use argv.

- `python3 config/skills/_shared/role-config.py --self-test` — precedence, compatibility, validation, atomic writes, supported capabilities and no mid-run reread.
- `python3 config/skills/_shared/judge-role-evidence.py --self-test` — strict native evidence/transport, mismatch/rejection/timeout cases and retained raw identities; this helper stays separate from mutation receipts.
- `python3 config/skills/_shared/verify-merge-findings.py --self-test` — opposite worker/primary engines, primary timeout ownership and unchanged binding findings/defaults.
- `bash scripts/lint-skills.sh` — required complete installed-skill/mirror and existing runtime regressions, including bootstrap/state writer.
- `git diff --check` — no whitespace errors.

Root additionally validates real packed installation and actual ordinary-entry role behavior after source checks, using the scoped acceptance composition below. Exact model/route identities and observations are retained; unsuccessful runs remain failures without manual phase rescue. This functional acceptance does not certify allocation superiority or universal provider capability. Preserve the unchanged original pilot/A16 and closed effort comparison.

### Ordinary r2 closure and prospective customer-task clarification (2026-09-07)

Installed r2 on a7a1f01 completed all phases with canonical PASS_WITH_ISSUES and verified owned-process quiet, but is not accepted as the complete customer task. Native Fable detected the unsupported `--engine auto` on the rewritten README usage line and marked it MEDIUM/nonbinding; root retains that native judgment while rejecting the invalid customer invocation. The next fresh README task must make every flag value on affected current-usage lines agree with the implemented adapters; `auto` is not a supported engine. Requested configuration/status must also be described as a request, with actual dispatch/effective identity tied to native evidence. Preserve the historical benchmark record and distinguish it from present PLAN-pair policy. These are prospective clarifications, not revisions of the original result or prose-mirroring tests.

The same run completed and archived before emitting its final report only as assistant text; the report artifact/log binding was absent. Repair that observed lifecycle defect separately before the next ordinary entry. Retain r2's correct explicit roles, exact worker/Fable-primary input observations, successful Codex source reads, all findings and the original canonical status. Its actual foreground judge overlap is established, but both recorded120215ms values came from joining after the primary and must not be used as individual judge runtimes. No full-task success or speed-lift claim follows.

### Prospective scoped acceptance composition (2026-09-07)

The former single successful explicit-route requirement is replaced before the next run by evidence of its separate failure domains. R2 already demonstrates actual supported role resolution, dispatch, input and independent source inspection. Its two task failures concern README correctness and common final-report persistence; neither demonstrates failed role selection. Final0126 must leave explicit resolver/dispatch/identity/merge behavior unchanged. This is acceptance of supported manual role controls and compatibility, not of an automatic allocation policy or of r2's complete task.

Accept this scoped feature only when all three conditions hold: retain r2's audited explicit-role evidence; pass final-source regressions and byte-confirm the unchanged role behavior; and complete a fresh packed legacy-r3 with no project role configuration, all six amended README requirements, truthful verdicts, report→completion→archive binding and owned-process quiet. Failure of the fresh task or a change affecting explicit routing leaves acceptance open and requires a new concrete diagnosis.

R2 stays CLOSED_NOT_ACCEPTED with canonical PASS_WITH_ISSUES. A successful legacy run does not prove the explicit model allocation's README accuracy or judge severity reliability. Preserve the PLAN trailing LF, unavailable isolated-pair structured input, provider-effective effort and whole-usage limitations. No old run is repaired, rescored or reused as whole-task success. The reason for combining evidence is the demonstrated separation of functional failure domains; avoided execution time alone would not justify this amendment.
