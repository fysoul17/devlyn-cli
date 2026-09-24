# Work packet T1b-packaging-vocab-delivery

Generated 2026-09-24 against main @466aa25 by a read-only scoping agent, then checked by an adversarial verifier (verdict: **READY_WITH_FIXES**). **Verifier corrections below override the packet body where they conflict.** Line numbers drift: re-check every location against the session's base SHA before editing. Registration: [0221](../../../iterations/0221-subtraction-direction.md).

**Used in:** Session 1: items c1, c2, b3 (+ the lint pins b3 needs, mirror). Session 2: items a1–a5 (+ mirror). Session 8, only if the intent candidate is NOT adopted: items b1, b2, b4, b5. Item b-keep stays untouched until intent removes resolve.

## 0221 overrides (authoritative; they replace conflicting body text)

- **c1 migration is replaced.** Under `pr`, `complete` must leave no auto-merge request on a PR it owns. The owned PR is the exact repository/head/base PR bound to the receipt. If that PR carries an auto-merge request, from an earlier default-`auto` attempt or a reused receipt `mode_override`, disable it (`gh pr merge --disable-auto <pr>`). Re-read the PR and verify `autoMergeRequest == null`, then return `PR`. Do not touch PRs the receipt does not own. When ownership cannot be proven, report it and leave the PR unchanged. Add self-test cases for three situations: absent policy → no merge request; a receipt with a stored `auto` override under explicit `--mode pr` → the reservation is removed and verified; a foreign PR → no change. Release note: the default is now PR-only, and `auto` is opt-in via `git config --local devlyn.completionMode auto` or `--mode auto`.
- **Session 1 uses only items c1, c2, b3 and the lint pins b3 needs, plus the mirror.** Items a1–a5 belong to Session 2. Items b1, b2, b4 and b5 are deferred to Session 8 and apply only if intent is NOT adopted.

## Summary

This packet makes three installed-product policy changes, all measured against main@466aa25 in /Users/aipalm/.local/share/nx01/core-continuation-20260912. (a) The benchmark leaves the npm package. It currently makes up 383 of 519 packed files and 1.65 of 4.24 MB unpacked. The `npx devlyn-cli benchmark` dispatcher (~211 lines of bin/devlyn.js) is deleted, not repointed. Benchmark users run the seven underlying scripts directly from a git checkout. (b) The solo-headroom / solo-ceiling / pair-evidence vocabulary is removed from the runtime entry points (free-form classifier halts, ideate elicitation, spec-verify-check validators, probe/judge anchors, README). Benchmark fixture authoring already has its own checkers (pair_evidence_contract.py, solo-headroom-hypothesis.py, solo-ceiling-avoidance.py), so it keeps working. The one runtime↔benchmark interface (verify-merge's `spec.solo_headroom_hypothesis` telemetry reason) and the env-keyed BENCH_WORKDIR / CODEX_BLOCKED hooks are kept until /devlyn:intent deletes resolve. (c) The completion default flips from `auto` to `pr` (push + PR, no merge request). `auto` stays an explicit opt-in, with matching self-test, doc and managed-instruction edits. Net effect is roughly −2,600 lines including the tracked .agents mirror, with zero new files, flags or abstractions.

## Items

### 0. (c1) Flip the delivery default from auto to pr in task-complete.py. Keep `auto` as an explicit opt-in (`git config --local devlyn.completionMode auto` or `compl

**Change.** (c1) Flip the delivery default from auto to pr in task-complete.py. Keep `auto` as an explicit opt-in (`git config --local devlyn.completionMode auto` or `complete --mode auto`). Fix the self-tests that relied on the implicit auto default.

**Files / lines.** config/skills/_shared/task-complete.py:175 (`return override or value or "auto"` → `"pr"`). Self-tests that must pass `--mode auto` on their first complete call: :990 (test_scratch_refusal_reports_delivery_separately), :1165 (test_in_place_retains_ignored_data), :1179 (test_linked_custody_and_interrupted_removal), :1229 (test_interrupted_external_effects), :1244 (test_retains_unknown_dirty_locked_and_active_tree), :1264 args list (test_concurrent_completions), :1293 (test_actual_foreign_writer_and_registration), :1310 (test_remote_compare_delete_race), :1374 (test_in_place_resume_does_not_overwrite_ignored_collision). Rewrite :1317-1320 (test_policy_and_local_only_persist) to assert that absent policy with merge_allowed=False gives status PR, pushs=1, merges=0; then `--mode auto` fails on disallowed merge commits. Mirror byte-identically to .agents/skills/_shared/task-complete.py (tracked full mirror; Check 6a).

**Current behavior.** When devlyn.completionMode is absent, `policy()` returns 'auto'. `complete` then checks mergeCommitAllowed (:640-641), runs `gh pr merge --auto --merge --match-head-commit` (:674-675) and cleans owned resources after MERGED (:680-682).

**Target behavior.** When config is absent, `complete` pushes the exact accepted ref, creates/reuses the PR and returns status `PR` with its URL. The workspace is retained, no merge is requested, and the mergeCommitAllowed gate is skipped. `auto` behaves as before, but only when configured or passed with --mode. The mode_override persistence at :623-625 is unchanged, so only the first `complete` call in a test needs the flag.

**Tests.** `python3 config/skills/_shared/task-complete.py --self-test` (also run by scripts/lint-skills.sh:408-414 Check 6b loop). New assertion: absent policy → PR without a merge request. docs/specs/task-completion/spec.expected.json runs the same self-test plus lint. scripts/test-windows-portability.py has no delivery-mode assertion (grep 'auto'/'--mode' empty).

**Migration.** Projects without devlyn.completionMode now stop at PR: no auto-merge request and no post-merge cleanup. Projects that explicitly set `auto` are unchanged. Receipts from earlier default-auto runs have no mode_override, so an earlier PENDING auto run now resumes as pr and returns PR without cleanup. [0221 override] Under `pr`, an owned PR's existing auto-merge request is disabled and verified (see overrides above); resume old auto receipts with `--mode pr` unless the owner explicitly wants `--mode auto`. Needs a release note.

**Risk.** MEDIUM. With in-place allocation, the anchor checkout stays on the task branch after a PR. The next `allocate` refuses ('allocate from the retained base checkout', task-complete.py:192). A manual `git switch <base>` makes a later `complete` fail closed with 'foreign worktree branch' (:404). Queue drains therefore stop after the first in-place item. This is the designed stop in queue SKILL.md:38 / CLAUDE.md:65, but it is new in practice now that PR is the default. See open question 2.

**Net lines.** +12 (1 code line, ~11 test lines) ×2 with the .agents mirror ≈ +24

### 1. (c2) Update delivery wording in the reference, the managed instructions, the README and the task-completion spec.

**Change.** (c2) Update delivery wording in the reference, the managed instructions, the README and the task-completion spec.

**Files / lines.** config/skills/devlyn:resolve/references/task-completion.md:95-106 (+ .agents mirror): 'absent means `auto`' → 'absent means `pr`'; describe `pr` as the default and `auto` as the opt-in that also requests `gh pr merge --auto --merge --match-head-commit`. CLAUDE.md:54 and AGENTS.md:41: replace 'then PR/merge and recoverable owned-resource cleanup after required archive/queue commits' with 'then push + PR after required archive/queue commits'. Keep the substring 'Default to direct execution when inspection makes', which scripts/test-windows-portability.py:394 asserts. README.md:100-103: 'Accepted tasks default to scoped commit → push → PR; the task branch is retained for review. Set `git config --local devlyn.completionMode auto` to also request a normal protected merge and recoverable cleanup after it merges; `task-complete.py complete --mode auto|pr` overrides one task.' Keep README.md:104-111. docs/specs/task-completion/spec.md:36-41: amend 'absent means auto' → 'absent means pr' and record the dated amendment. bin/instruction-templates.json: NO manual edit. .github/workflows/publish.yml:29 runs scripts/update-instruction-templates.js, which fingerprints every first-parent historical paragraph (update-instruction-templates.js:13-21), so the old sentence migrates on reinstall. No change needed in config/skills/devlyn:queue/SKILL.md:38, references/outer-loop.md:15-24 or CLAUDE.md:65 (already mode-neutral).

**Current behavior.** The docs say absent config means auto and that completion goes through PR/merge and cleanup.

**Target behavior.** The docs say the default is push + PR and that merge/cleanup happen only when a project opts into `auto`. The managed paragraph gets shorter.

**Tests.** `bash scripts/lint-skills.sh` (no lint pin on this wording; grep 'PR/merge|completionMode' in lint is empty). Portability test_instruction_legacy_hash_migration_preserves_prefix_suffix (test-windows-portability.py:376-396) in CI.

**Migration.** Reinstall rewrites the managed block in users' CLAUDE.md/AGENTS.md through the existing fingerprint migration (README.md:230-251).

**Risk.** LOW. CLAUDE.md and AGENTS.md must get the identical phrase.

**Net lines.** ≈ −4 (mirror included)

### 2. (a1) Drop every benchmark entry and every repo-dev script from package.json files[].

**Change.** (a1) Drop every benchmark entry and every repo-dev script from package.json files[].

**Files / lines.** package.json:21-72: delete all benchmark/** entries (3 docs, fixtures F*/retired/shadow/test-repo globs, 44 results files, scripts/**). package.json:76-79: delete scripts/lint-fixtures.sh and scripts/lint-shadow-fixtures.sh (benchmark fixture lints). Also delete scripts/lint-skills.sh and scripts/test-owner-phases.py. A packaged lint-skills.sh cannot run because it needs .agents/ (Check 6a) and benchmark/. test-owner-phases.py was packaged only because lint Check 6c1 (lint-skills.sh:572-577) runs it (commit f2ab8f8). KEEP package.json:73-75 (the __pycache__/.pyc excludes still guard config/skills/_shared/*.py).

**Current behavior.** `npm pack --dry-run --json` at 466aa25: 519 entries, 4,239,485 B unpacked. benchmark/ = 383 files / 1,650,296 B; scripts/ = 4 files / 369,869 B.

**Target behavior.** The pack contains only AGENTS.md, CLAUDE.md, README.md, package.json, bin/**, config/** and optional-skills/**: ≈132 entries, ≈2.22 MB unpacked.

**Tests.** The rewritten npm-pack assertion in item a5. portability.yml posix/windows only consume config/skills/_shared from the installed package (test-windows-portability.py:57, 900, 1096, 1857) plus `bin/devlyn.js -y` (portability.yml:170-177), so both are unaffected. publish.yml:32 `npm pack --dry-run` is unaffected.

**Migration.** NONE for users. Benchmark/research use requires a git checkout.

**Risk.** LOW. Nothing at runtime reads benchmark/ from the package.

**Net lines.** −56

### 3. (a2) Delete the `benchmark`/`bench` subcommand and its help from the shipped CLI. No stub: the existing default branch already fails explicitly.

**Change.** (a2) Delete the `benchmark`/`bench` subcommand and its help from the shipped CLI. No stub: the existing default branch already fails explicitly.

**Files / lines.** bin/devlyn.js:1025-1033 (help lines), :1054-1217 (showBenchmarkHelp + showBenchmarkModeHelp), :1237-1275 (case 'benchmark'/'bench' incl. benchmarkScripts map and spawnSync). The top-level `execSync` import at :7 stays; spawnSync was a local require at :1269.

**Current behavior.** `npx devlyn-cli --help` lists 9 benchmark lines with research vocabulary ('Score bare vs solo_claude headroom', 'pair evidence'). `benchmark <mode>` dispatches to benchmark/auto-resolve/scripts/* and prints 'runner missing' when those files are absent.

**Target behavior.** `npx devlyn-cli benchmark` or `bench` hits the default case at bin/devlyn.js:1313-1316: 'Unknown command: benchmark', then help, then exit 1. Help contains no benchmark/solo_claude/pair vocabulary.

**Tests.** `node bin/devlyn.js --help | grep -ci benchmark` → 0. `node bin/devlyn.js benchmark; echo $?` → 'Unknown command: benchmark', 1. The bin-help assertions in test-benchmark-arg-parsing.sh are removed in a3, and the lint pins in a5.

**Migration.** Release note: run the benchmark from a devlyn-cli git checkout with the direct scripts (mapping in a3).

**Risk.** LOW-MEDIUM. External scripts calling `npx devlyn-cli benchmark` break loudly. No active research lane uses it: autoresearch/ has one historical mention (iterations/0068-discriminating-corpus.md). Merge-conflict risk with the separate packet that edits bin/devlyn.js:932-933 (CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING), so sequence the two.

**Net lines.** −211

### 4. (a3) Point the benchmark runners and their tests at direct script invocation and delete the DEVLYN_BENCHMARK_CLI_SUBCOMMAND replay branch. Mapping, from bin/dev

**Change.** (a3) Point the benchmark runners and their tests at direct script invocation and delete the DEVLYN_BENCHMARK_CLI_SUBCOMMAND replay branch. Mapping, from bin/devlyn.js:1239-1247 and :1271: suite→`bash benchmark/auto-resolve/scripts/run-suite.sh`; recent→`python3 benchmark/auto-resolve/scripts/recent-benchmark-summary.py`; frontier→`python3 .../pair-candidate-frontier.py`; audit→`python3 .../audit-pair-evidence.py`; audit-headroom→`python3 .../audit-headroom-rejections.py`; headroom→`bash .../run-headroom-candidate.sh`; pair→`bash .../run-full-pipeline-pair-candidate.sh`. Arguments are identical because bin only forwarded them. Only the two .sh runners read the env var.

**Files / lines.** benchmark/auto-resolve/scripts/run-headroom-candidate.sh:106-111 → keep only `cmd=(bash "$0" --run-id "$RUN_ID")`. run-full-pipeline-pair-candidate.sh:142-147 gets the same edit. run-full-pipeline-pair-candidate.sh:458: the release-audit echo becomes `python3 benchmark/auto-resolve/scripts/audit-pair-evidence.py --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict`. test-run-headroom-candidate.sh:43-44 and :207-210 (cli-replay-command case): delete. test-run-full-pipeline-pair-candidate.sh:41-42 and :228-233: delete; :441: match the new echo. test-benchmark-arg-parsing.sh: delete the bin help assertions at :337-414 (--help blocks only) and :741-769, and the CLI-replay cases at :771-783. Repoint the functional `node "$ROOT/bin/devlyn.js" benchmark …` calls at :329, :416, :428, :460, :574, :616, :642, :678, :705, :736 and :785-837 through the mapping. Where test-run-headroom-candidate.sh (:204-222) or test-run-full-pipeline-pair-candidate.sh (:235-245) already cover a case (smoke-only S1, dry-run min-fixtures), delete it instead. Replay asserts `Command: npx devlyn-cli benchmark X --run-id Y` become `Command: ` plus `--run-id Y`.

**Current behavior.** When launched through bin, the runners print the replay line `Command: npx devlyn-cli benchmark headroom|pair --run-id …`. test-benchmark-arg-parsing.sh drives most cases through `node bin/devlyn.js benchmark …`.

**Target behavior.** The replay is always `Command: bash <runner> --run-id …`, a branch that already exists. All tests call the scripts directly.

**Tests.** `bash benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh`, `test-run-headroom-candidate.sh`, `test-run-full-pipeline-pair-candidate.sh` (all three are also run by lint Check 10e, lint-skills.sh:3804-3849).

**Migration.** NONE (research-only).

**Risk.** MEDIUM (mechanical churn in a 1,015-line test). No behavior change beyond the replay string.

**Net lines.** ≈ −130

### 5. (a4) Remove the root README benchmark section and rewrite the operational benchmark docs to use the direct scripts (same mapping). Delete the 'When launched thr

**Change.** (a4) Remove the root README benchmark section and rewrite the operational benchmark docs to use the direct scripts (same mapping). Delete the 'When launched through `npx devlyn-cli benchmark …`, the replay uses the same package CLI path' sentences. Leave historical and frozen documents untouched.

**Files / lines.** README.md:160-227 (delete '### Benchmark score runs' through 'ids.'). benchmark/README.md:26-42. benchmark/auto-resolve/README.md:8-14, 46, 146, 155-156, 177-179, 203, 212-213, 289, 301-303, 680, 683. benchmark/auto-resolve/run-real-benchmark.md:6-7, 43, 56, 66-67, 111, 121-123, 148, 171-172, 268-269. benchmark/auto-resolve/BENCHMARK-RESULTS.md:60-61. benchmark/auto-resolve/shadow-fixtures/README.md:61-62. benchmark/auto-resolve/BENCHMARK-DESIGN.md:26, 146-148, 282. Comments: run-suite.sh:5, compile-report.py:13, measure-static.py:8. DO NOT EDIT: dated reports BENCHMARK-RESULTS-v3.md:6, PILOT-RESULTS-v3.2.md:5, PILOT-RESULTS-STRICT-v3.2.md:5, v3.6-ab-plan.md:5, results/**, and the frozen corpus benchmark/ceiling/corpus/copycat-doc.md (a README copy used as corpus input; 8 mentions).

**Current behavior.** README.md:160-227 advertises `npx devlyn-cli benchmark …`. Seven operational benchmark docs/comments reference the npx CLI.

**Target behavior.** The npm README has no benchmark section (optionally one line pointing to benchmark/README.md in the repository). Benchmark docs show directly runnable commands from a checkout.

**Tests.** Check 10e's stale-wording regex (lint-skills.sh:1903-1911) must still pass; avoid the forbidden phrases, e.g. 'both arms'. The doc pins are repointed in a5.

**Migration.** NONE

**Risk.** LOW

**Net lines.** ≈ −90

### 6. (a5) Update lint Check 10e: delete the packaging, bin-help and root-README pins; repoint the kept benchmark-doc pins through the mapping; shrink the npm-pack ch

**Change.** (a5) Update lint Check 10e: delete the packaging, bin-help and root-README pins; repoint the kept benchmark-doc pins through the mapping; shrink the npm-pack check to a 'nothing from benchmark/ or scripts/ ships' guard. Edit by content, not by line number, because deletions shift lines. All numbers below are at 466aa25.

**Files / lines.** scripts/lint-skills.sh. Delete package.json pins at :2070-2071 and :3543-3548. Delete the packaged-evidence subset audit at :3562-3671. At :3672-3775, delete the `required` list and its missing check inside the NODE heredoc; keep `npm pack --dry-run --json` and the forbidden filter, extend the filter to /^(benchmark|scripts)\//, and reword the messages at :3766-3772. In the block at :2401-2423, delete the conditions at :2401-2403 and :2416-2421 and reword :2422. Delete the README-only block at :2424-2433. In :2435-2453, delete :2435-2436 and :2449. Delete the block at :2454-2457. Delete :2892. In the block at :2985-3027, delete the root-README pins (:2988, :2991, :3019), the bin pins (:2994, :2996, :2998, :3000, :3002, :3004, :3006, :3008, :3010, :3012, :3014, :3016, :3022, :3024, :3026) and the test-file help-copy pins (:2995, :2997, :2999, :3009, :3023, :3025). Delete :3423 and :3437 (bin). Delete the root-README pins at :3033, :3280-3281, :3289-3315, :3345-3348, :3358, :3365, :3407-3409, :3472 and :3526-3530. Repoint through the mapping: :2885, :2986-2987, :2989-2990, :2992-2993, :3020-3021, :3090-3091. Keep :2103 (a negative grep that still passes) and :3549-3561 (committed result-artifact schema; optionally drop the word 'packaged' from the message).

**Current behavior.** Check 10e (lint-skills.sh:1902-3967) requires benchmark files in package.json and in npm pack, the benchmark help text in bin/devlyn.js, and ~50 benchmark sentences in the root README.

**Target behavior.** Check 10e guards only benchmark internals, plus 'npm pack contains no benchmark/ or scripts/ path and no __pycache__/.pyc'.

**Tests.** `bash scripts/lint-skills.sh` exits 0 and Check 10e prints 'ok benchmark docs use current bare / solo_claude / pair-arm topology'.

**Migration.** NONE

**Risk.** MEDIUM (large lint edit). Mitigated by running the full lint.

**Net lines.** ≈ −330

### 7. (b1) Remove the research halts and branching from the runtime entry (free-form classifier, resolve SKILL.md, state-schema, README).

**Change.** (b1) Remove the research halts and branching from the runtime entry (free-form classifier, resolve SKILL.md, state-schema, README).

**Files / lines.** config/skills/devlyn:resolve/references/free-form-mode.md:16-23 (signals 6-9), :58-59 (Large conditions), :64-65 (two exceptions), :80-81 (mini-spec preservation bullets). config/skills/devlyn:resolve/SKILL.md: :88 clause 'and any present actionable solo-headroom hypothesis, matching its command to `spec.expected.json.verification_commands[].cmd` or the inline `## Verification` JSON carrier'; :94 the two halt clauses after `BLOCKED:large-needs-ideation`; :175-184 (first-probe rule plus the stale pair-trigger claim); :197-198 'makes the benchmark run invalid' → 'makes the run invalid'; :331 the sentence 'If the spec includes a solo-headroom hypothesis, one targeted review … object).'; :359 the two `/devlyn:ideate` guidance clauses for BLOCKED:solo-*. config/skills/devlyn:resolve/references/state-schema.md:138: the matching two guidance clauses. README.md:87-98. Mirror every config/skills file into .agents/skills.

**Current behavior.** A free-form goal that asks for 'benchmark evidence, pair-evidence, risk-probe measurement…' is classified Large and halts with BLOCKED:solo-headroom-hypothesis-required or BLOCKED:solo-ceiling-avoidance-required. SKILL.md:181-184 also claims such specs cannot finish on solo VERIFY. That claim is stale: verify-merge-findings.py:974-989 lets any automatic trigger skip to solo when OTHER is unavailable.

**Target behavior.** The free-form classifier uses only the generic signals 1-5. No research BLOCKED verdicts remain; git grep shows no code recognizes them, only prose. Entry text carries no solo_claude / solo-headroom / S2-S6 vocabulary.

**Tests.** Lint pins removed in b5. `python3 config/skills/_shared/resolve-bootstrap.py --self-test` (CI; it has no solo references).

**Migration.** NONE (removes a false halt for real users).

**Risk.** LOW. Lane A fixtures use --spec, not free-form.

**Net lines.** ≈ −35 ×2 (mirror) + README −12 ≈ −82

### 8. (b2) Remove benchmark-candidate authoring rules from ideate. Fixture authoring stays enforced by the benchmark-only checkers: benchmark/auto-resolve/scripts/pai

**Change.** (b2) Remove benchmark-candidate authoring rules from ideate. Fixture authoring stays enforced by the benchmark-only checkers: benchmark/auto-resolve/scripts/pair_evidence_contract.py:149-164, solo-headroom-hypothesis.py and solo-ceiling-avoidance.py, called from scripts/lint-fixtures.sh:13,304 and scripts/lint-shadow-fixtures.sh:15,20.

**Files / lines.** config/skills/devlyn:ideate/SKILL.md: :113 clause '; any present actionable solo-headroom hypothesis command must match that carrier's `verification_commands[].cmd`'; :114 the solo clauses; :126 (delete step 6); :139 (delete the last sentence). references/elicitation.md: :43-63 (items 8-9), :97-98 (solo clauses), :123-133 (quick-mode exception paragraph). references/from-spec-mode.md: :40-41 (solo clauses), :49-63 (steps 10-11), :69 (the two appended announcements for steps 10/11; keep the step-9 warning). references/project-mode.md: :18-32 (rules 6-7), :85 (solo clauses). references/spec-template.md:121-122. Mirror everything to .agents/skills.

**Current behavior.** Every ideate mode asks for a solo-headroom hypothesis and a solo-ceiling note for benchmark / risk-probe / pair-evidence goals, and exits 'spec not ready — …' without them.

**Target behavior.** Ideate never asks for or requires solo_claude / solo-ceiling notes. Compound-verification guidance (elicitation.md:37-42, spec-template.md:120, project-mode.md:14-17, from-spec-mode.md step 9) is preserved.

**Tests.** Lint pins removed in b5. `bash scripts/lint-fixtures.sh && bash scripts/lint-shadow-fixtures.sh` still enforce fixture hypotheses.

**Migration.** NONE

**Risk.** LOW. Future benchmark candidates must follow benchmark/auto-resolve/fixtures/SCHEMA.md and the shadow-fixtures README instead of ideate.

**Net lines.** ≈ −60 ×2 ≈ −120

### 9. (b3) Remove the solo-headroom and solo-ceiling validators from spec-verify-check.py (the runtime copy). Besides the vocabulary, this removes a false block that 

**Change.** (b3) Remove the solo-headroom and solo-ceiling validators from spec-verify-check.py (the runtime copy). Besides the vocabulary, this removes a false block that can hit real users: the probe validator fires on any Verification line containing `miss`, one of command/observable/expose, and a command-like backtick (:446-455, :543-570), for example '`npm test` exposes the cache miss'. It then rejects risk probes whose derived_from lacks the literal 'solo-headroom hypothesis', so BUILD_GATE blocks whenever risk probes are enabled.

**Files / lines.** config/skills/_shared/spec-verify-check.py:247-278: BACKTICKED_TEXT_RE, OBSERVABLE_COMMAND_MARKERS, RESERVED_BACKTICK_TERMS, SOLO_CEILING_CONTROL_RE, SOLO_CEILING_DIFFERENCE_RE and COMMAND_PREFIXES, which are used only by the solo helpers. :445-570: backticked_observable_miss_commands, is_command_like_backtick, has_backticked_observable_miss_command, validate_present_solo_headroom_hypothesis, validate_present_solo_ceiling_avoidance, validate_solo_headroom_commands_against_expected, command_contains_expected, validate_risk_probes_cover_solo_headroom_hypothesis. Call sites: :875-888 (keep the rest of validate_expected_against_sibling_spec), :1102-1107, :1910-1917, :1952-1959. Self-tests: :2618-2780, :3021-3194, :3210-3326; keep the expected_json setup at :3196-3209, which :3328+ reuses. Fix the docstring if it mentions these checks. Mirror to .agents/skills/_shared/spec-verify-check.py. benchmark/auto-resolve/scripts/test-lint-fixtures.sh:275 grepped the runtime message 'solo-headroom hypothesis must include'. Change it to the benchmark checker message from scripts/lint-shadow-fixtures.sh:48 ('must document a solo-headroom hypothesis'), or drop it; the status assertion at :274 remains. External importers stay intact: benchmark/ceiling/scripts/f7-carrier-gate.py:349-355 (extract_authorized_surface_block, loads_strict_json, validate_authorized_surface_shape, validate_scope_only_plan_text), resolve-bootstrap.py:283-293 (stage_from_expected, stage_from_source, --check), state-phase-write.py:1914 (load_untracked_baseline, current_untracked_files).

**Current behavior.** --check / --check-expected reject specs that mention the hypothesis or ceiling words in weak form, and --validate-risk-probes forces probes[0] to cover the hypothesis command.

**Target behavior.** spec-verify-check validates only product contract shape. Preserved: carrier precedence (sibling spec.expected.json > inline > generated fail-closed), pure-design, risk-probe tags/evidence, authorized surface, untracked baseline, process evidence, BENCH_WORKDIR branch.

**Tests.** `python3 config/skills/_shared/spec-verify-check.py --self-test` (lint Check 6d, :658). `bash benchmark/auto-resolve/scripts/test-lint-fixtures.sh`. `bash scripts/lint-fixtures.sh`. `bash scripts/lint-shadow-fixtures.sh`.

**Migration.** NONE for users.

**Risk.** MEDIUM (≈620-line deletion in a 5,736-line file). Mitigated by the self-test and the fixture lints. Lane A runs whose fixture specs carry hypotheses are no longer forced to anchor probe #1 on the hypothesis. That changes measurement semantics, so new Lane A pair evidence is not comparable with archived evidence; record this in the PR body.

**Net lines.** ≈ −620 ×2 ≈ −1,240

### 10. (b4) Remove the solo-headroom anchors from the probe and judge prompts and from the grok adapter.

**Change.** (b4) Remove the solo-headroom anchors from the probe and judge prompts and from the grok adapter.

**Files / lines.** config/skills/devlyn:resolve/references/phases/probe-derive.md:51-58 (paragraph), :183-184 ('Solo-headroom hypothesis probes keep…' sentence), :214-217 (quality-bar bullet). references/phases/verify.md:203 through 'run a neighboring edge case.' on :207. Keep the telemetry list at :135-139. config/skills/_shared/adapters/grok.md:69-71: drop 'the solo-headroom hypothesis's backticked observable command when present; otherwise'. Mirror all of these to .agents/skills.

**Current behavior.** When the spec contains a hypothesis, the probe-derive prompt, the pair-judge prompt and grok's allow-list precedence anchor on it.

**Target behavior.** Probes and judges anchor on the visible `## Verification` bullets only. Grok's allow-list precedence becomes the backticked Verification commands, then the repo's test/CLI runner.

**Tests.** Lint pins removed in b5. Check 6a mirror parity.

**Migration.** NONE

**Risk.** LOW

**Net lines.** ≈ −16 ×2 ≈ −32

### 11. (b5) Delete the lint pins that required the research vocabulary in runtime files. Keep the pins for the preserved verify-merge telemetry.

**Change.** (b5) Delete the lint pins that required the research vocabulary in runtime files. Keep the pins for the preserved verify-merge telemetry.

**Files / lines.** scripts/lint-skills.sh. Delete the blocks at :698-743, :983-990, :991-1026, :1027-1034, :1035-1052, :1084-1094, :1101-1107, :1108-1121, :1123-1134, :1135-1146, :1147-1166, :1240-1274 and :1275-1291. Partial edits: in :758-775 drop the spec-verify-check paths (:758-759, :767-768); in the parity heredoc drop :783-784 and keep the verify-merge ↔ pair_evidence_contract parity; in :913-940 delete :913-920 and :929-936, keep :921-928 (carrier precedence) and reword the messages; in :941-969 keep :941-943 (validate_expected_against_sibling_spec, runtime-empty and pure-design), delete :944-967 and reword :968; in :1196-1239 delete only :1234-1235 (the SKILL.md trigger sentence). KEEP :1180-1195 and :1196-1233 (verify-merge `spec.solo_headroom_hypothesis` telemetry, verify.md and state-schema reason lists) and Check 10e :2830-2860 (runtime KNOWN_PAIR_TRIGGER_REASONS == benchmark canonical).

**Current behavior.** Checks 6d/6f require the solo-headroom text and functions in ideate, resolve and spec-verify-check.

**Target behavior.** No lint check requires research vocabulary in config/skills except the kept verify-merge telemetry pins.

**Tests.** `bash scripts/lint-skills.sh` exits 0.

**Migration.** NONE

**Risk.** LOW

**Net lines.** ≈ −230

### 12. (b-keep) Preserve list: NO EDIT in this PR. These are env-keyed or spec-literal-keyed hooks that are inert for real users. They form the runtime↔benchmark inter

**Change.** (b-keep) Preserve list: NO EDIT in this PR. These are env-keyed or spec-literal-keyed hooks that are inert for real users. They form the runtime↔benchmark interface, and /devlyn:intent deletes them together with resolve.

**Files / lines.** config/skills/_shared/verify-merge-findings.py:60, 68-90, 810-845 and 878-879 (reason `spec.solo_headroom_hypothesis`; requires both literals, so it is inert for real users), with self-tests :2434-2562. SKILL.md:329, verify.md:135-139 and state-schema.md:71 (reason lists). spec-verify-check.py:5224-5412 BENCH_WORKDIR pre-staged trust (set by benchmark/auto-resolve/scripts/run-fixture.sh:568 and run-frozen-verify-pair.sh:451). Removing it would need run-fixture.sh to deliver the fixture contract through the sibling spec.expected.json path and re-prove F9 (iter-0019.9). spec-verify-check.py:233-235 FORBIDDEN_RISK_PROBE_CMD_RE, SKILL.md:137-139 and probe-derive.md:25-28 (hidden-blind inputs). codex-monitored.sh:65-75 CODEX_BLOCKED (research word only in a comment/message). Fixture-shaped examples: probe-derive.md:96-111 (FEFO/warehouse compound), :143-144, :187-189, :194-198 (cart/pricing); SKILL.md:168-169 (Cart/pricing); SKILL.md:331 and verify.md:72, 215 ('inside a warehouse'). These are behavior-bearing, and there is no measurement to justify editing them twice.

**Current behavior.** Unchanged

**Target behavior.** Unchanged. When /devlyn:intent replaces resolve, Lane A must retire `--require-hypothesis-trigger` (audit-pair-evidence.py:258-261,771,1088-1092; full-pipeline-pair-gate.py:159-160,326,384; frozen-verify-gate.py:269-273,371-387; pair_evidence_contract.py:20,217-218).

**Tests.** Unchanged checks keep passing: lint :1180-1233 and :2830-2860, `python3 config/skills/_shared/verify-merge-findings.py --self-test`.

**Migration.** NONE

**Risk.** Known hazard left in place: FORBIDDEN_RISK_PROBE_CMD_RE rejects any probe cmd containing 'verifiers/', which is a false positive for real repos with such a directory. It disappears with the probe phase under intent.

**Net lines.** 0

### 13. (mirror) Sync the tracked .agents mirror and any local installed mirror after all config/skills edits.

**Change.** (mirror) Sync the tracked .agents mirror and any local installed mirror after all config/skills edits.

**Files / lines.** .agents/skills/_shared/{task-complete.py, spec-verify-check.py, adapters/grok.md}, .agents/skills/devlyn:ideate/{SKILL.md, references/elicitation.md, from-spec-mode.md, project-mode.md, spec-template.md}, .agents/skills/devlyn:resolve/{SKILL.md, references/free-form-mode.md, task-completion.md, state-schema.md, phases/probe-derive.md, phases/verify.md}. Work in a fresh linked worktree/branch (no .claude/skills, so Check 6 skips), or copy the changed critical-path files into .claude/skills. Do NOT run `node bin/devlyn.js -y` to refresh: it writes ~/.claude settings (bin/devlyn.js:932-933).

**Current behavior.** .agents/skills is a byte-identical full mirror of config/skills (59 tracked files, 0 differences at 466aa25). The workspace also has a gitignored .claude/skills that Check 6 compares when present.

**Target behavior.** `diff -r config/skills .agents/skills` is empty. Check 6 either passes or is skipped because the fresh worktree has no .claude/skills.

**Tests.** Lint Check 6 and 6a (lint-skills.sh:386-404).

**Migration.** NONE

**Risk.** The codex workspace-write sandbox cannot write .agents/. The orchestrating session must do the sync, not a codex worker.

**Net lines.** counted in the items above

## Acceptance checks

- cd /Users/aipalm/.local/share/nx01/core-continuation-20260912 (fresh task branch/worktree from main@466aa25 or newer)
- python3 config/skills/_shared/task-complete.py --self-test  # exit 0; includes the new absent-policy → status PR, merges 0 assertion
- grep -n 'return override or value or "pr"' config/skills/_shared/task-complete.py .agents/skills/_shared/task-complete.py  # 2 hits
- python3 config/skills/_shared/spec-verify-check.py --self-test && python3 config/skills/_shared/verify-merge-findings.py --self-test && python3 config/skills/_shared/resolve-bootstrap.py --self-test && python3 scripts/test-owner-phases.py
- bash scripts/lint-skills.sh  # exit 0 (covers Checks 6/6a parity, 6d, 6f, 10e incl. all benchmark test-*.sh runs)
- bash benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh && bash benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh && bash benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh && bash benchmark/auto-resolve/scripts/test-lint-fixtures.sh && bash scripts/lint-fixtures.sh && bash scripts/lint-shadow-fixtures.sh
- npm_config_cache="$(mktemp -d)" npm pack --dry-run --json | node -e 'const p=JSON.parse(require("fs").readFileSync(0))[0];const bad=p.files.map(f=>f.path).filter(f=>/^(benchmark|scripts)\//.test(f)||f.includes("__pycache__")||f.endsWith(".pyc"));if(bad.length){console.error(bad.join("\n"));process.exit(1)}console.log(p.entryCount)'  # exit 0, prints ~132 (was 519)
- node bin/devlyn.js --help | grep -ci benchmark  # prints 0
- node bin/devlyn.js benchmark >/tmp/b.out 2>&1; echo $?; grep -F 'Unknown command: benchmark' /tmp/b.out  # 1, and the line is present
- git grep -n -E 'solo-headroom|solo_claude|solo ceiling|pair-evidence|BLOCKED:solo' -- config .agents README.md CLAUDE.md AGENTS.md  # only hits: _shared/verify-merge-findings.py and _shared/codex-monitored.sh (and their .agents mirrors)
- git grep -n 'devlyn-cli benchmark' -- README.md bin benchmark/README.md benchmark/auto-resolve/README.md benchmark/auto-resolve/run-real-benchmark.md benchmark/auto-resolve/BENCHMARK-RESULTS.md benchmark/auto-resolve/shadow-fixtures/README.md benchmark/auto-resolve/scripts scripts  # no output
- git grep -n 'absent means' -- config/skills/devlyn:resolve/references/task-completion.md docs/specs/task-completion/spec.md  # both say pr
- grep -c 'then push + PR after required archive/queue commits' CLAUDE.md AGENTS.md  # 1 each; grep -c 'Default to direct execution when inspection makes' CLAUDE.md AGENTS.md  # 1 each
- diff -r config/skills .agents/skills  # no output
- git diff --check  # exit 0
- GitHub: PR opened against main with CI 'Windows portability' (posix + windows jobs) green; PR is NOT merged (delivery = push + PR only)

## Dependencies

- Workspace is the research checkout /Users/aipalm/.local/share/nx01/core-continuation-20260912 at main 466aa25. Do not touch the user's primary checkout /Users/aipalm/Documents/GitHub/devlyn-cli, which has uncommitted CLAUDE.md/AGENTS.md/.gitignore edits.
- Sequencing with the /devlyn:intent replacement packet: this packet assumes it lands BEFORE intent. If intent lands first, drop the resolve-side parts of b1/b4/b5 (free-form-mode.md, resolve SKILL.md, probe-derive.md, verify.md, state-schema.md pins). The ideate, spec-verify-check --check/--check-expected and README parts are still needed because ideate and spec-verify-check are expected to survive into intent (0201-harness-transformation-plan.md:169-173).
- File overlap with sibling packets: bin/devlyn.js (CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING at :932-933), README.md, CLAUDE.md/AGENTS.md managed text and scripts/lint-skills.sh. Merge sequentially and rebase by content, not line numbers.
- No model CLI runs are required; every check is deterministic. The orchestrating session, not a codex sandbox, must write the .agents/ mirror.
- bin/instruction-templates.json is refreshed at publish (.github/workflows/publish.yml:29), not in this PR.

## Open questions

- 1. Delete the `auto` completion mode entirely instead of keeping it as opt-in? Deletion would remove task-complete.py:640-641, :670-681, the `auto` choice at :699, the mergeCommitAllowed query and ~6 self-tests. But post-merge cleanup currently runs only on the auto path (a pr-mode `complete` returns PR at :668-669 even after MERGED). Recommendation: keep `auto` opt-in in this PR, because the user asked for a new default, not a capability removal.
- 2. HIGH operational consequence of the PR default: an in-place allocation leaves the anchor checkout on the task branch. The next `allocate` refuses (task-complete.py:192). Switching back to base makes a later `complete` fail closed (task-complete.py:404). Unattended queue drains therefore stop after the first in-place item (the designed stop in queue SKILL.md:38). Options: (i) doc-only, queue drains allocate every item with `--worktree` (edit queue SKILL.md:38 and task-completion.md:19-20); (ii) let pr mode clean up after an observed MERGED on resume by moving the `if mode == "pr": return` inside the not-MERGED branch at :668; cleanup still requires merge-commit ancestry (:523-525), so squash merges stay retained; (iii) accept a manual switch. Recommendation: (i) now, (ii) as a follow-up. Needs the user's or astra's decision.
- 3. Should the whole benchmark lint (Check 10e, lint-skills.sh:1902-3967, ≈2,060 lines that run 17 benchmark test scripts) move out of the product lint into a benchmark-lane lint? That would be a separate subtraction PR; this packet only removes the packaging, bin and README coupling.
- 4. BENCH_WORKDIR pre-staged-trust branch (spec-verify-check.py:5224-5412): delete it only after run-fixture.sh:563-568 and run-frozen-verify-pair.sh:451 deliver the fixture contract through the product's sibling spec.expected.json path and F9 is re-proved. Defer to the intent PR or a Lane A PR?
- 5. Adjacent research residue that was not in the listed scope (mention only): README.md:158 ('Historical record: iter-0020 … PLAN-pair remains research-only: iter-0033g + iter-0034') and config/skills/_shared/pair-plan-schema.md (an archived iter-0022 schema full of benchmark/ paths that still ships in the npm package; lint Check 6 lists it at lint-skills.sh:103). Delete them in a follow-up?
- 6. Is the generic 'Unknown command: benchmark' (exit 1) enough, or does the user want a dedicated one-line message pointing to the git-checkout scripts? A dedicated message would add ~4 lines, so it has to be requested explicitly.
- 7. Removing the probe/judge hypothesis anchors (b3/b4) changes Lane A measurement semantics for new runs. Confirm that Lane A continuity is not required (current research uses the ceiling lane; Lane A is effectively frozen per benchmark/README.md:62-64).

## Verifier corrections (authoritative over the body)

- **CORRECTED** — c1: rewrite :1317-1320 so absent policy with merge_allowed=False gives PR and pushs=1, then `--mode auto` fails
  - The rewrite works (tested), but it drops the only assertion that auto mode rejects a merge-commit-disallowed repo before any push. The current test asserts pushs==0 at :1318-1320. Smaller alternative: keep :1318 as `self.complete("--mode","auto",success=False)` with pushs==0, and cover absent→PR by removing `"--mode","pr"` from test_same_repository_transport_alias (:1111). That test already asserts status PR and pushs==1.
- **CORRECTED** — a1: package.json:21-72 holds '44 results files'
  - Lines 32-71 list 40 results files, not 44. The −56 line estimate is still right (52 + 4).
- **CORRECTED** — a3: runner replay branches at run-headroom-candidate.sh:106-111 and run-full-pipeline-pair-candidate.sh:142-147; only the two .sh runners read DEVLYN_BENCHMARK_CLI_SUBCOMMAND
  - The env-var claim is confirmed. The ranges are off by one: :106 and :142 are `local cmd` and must stay. The if/else blocks to collapse are :107-111 and :143-147.
- **CORRECTED** — a3: where test-run-headroom/pair-candidate already cover a case (smoke-only S1, dry-run min-fixtures), delete it from test-benchmark-arg-parsing.sh instead of repointing
  - Lint :2140-2141 require the literals 'smoke-only-s1-cli-headroom' and 'smoke-only-s1-cli-pair' in test-benchmark-arg-parsing.sh (:804, :831). Deleting those cases fails Check 10e unless :2140-2141 are also deleted. Either repoint those two cases or add :2140-2141 to the a5 deletions.
- **CORRECTED** — a5: test-file help-copy pins to delete are :2995, :2997, :2999, :3009, :3023, :3025
  - I pruned test-benchmark-arg-parsing.sh :337-414, :741-769 and :771-784 in a copy. These pins then also fail because their strings exist only in the deleted help blocks: :3001, :3003, :3005, :3007, :3011, :3013, :3015. :3018 survives because the functional audit calls keep the string, and :2455 is already covered by the :2454-2457 deletion.
- **CORRECTED** — a5: delete root-README pins at :3289-3315
  - Wrong as a range. :3290 pins README '`--pair-verify` and `--no-pair` are mutually exclusive' (README:86, outside the benchmark section; must stay). :3291-3292, :3294-3295, :3297-3298 and :3300-3301 pin benchmark/auto-resolve docs. The README-only lines in that span are :3289, :3293, :3296, :3299 and :3302-3315. The other README pin lists (:2424-2433, :2988, :2991, :3019, :3033, :3280-3281, :3345-3348, :3358, :3365, :3407-3409, :3472, :3526-3530) are exact; confirmed by simulating README with :87-98 and :160-227 removed.
- **CORRECTED** — a4: benchmark doc edit locations
  - The listed lines are accurate but miss benchmark/auto-resolve/README.md:209 ('The package CLI exposes that release/handoff guard as one command:'), which becomes false. BENCHMARK-DESIGN.md:280-282 is one Q&A, not just :282. When deleting the 'When launched through' sentence on benchmark/auto-resolve/README.md:301, keep 'then that pair evidence was accepted', which lint :2412 pins (unlisted).
- **CORRECTED** — b5: in :913-940 keep :921-928 (carrier precedence)
  - This contradicts b1/b2. The only occurrence of 'inline `## Verification` JSON carrier' in resolve SKILL.md is inside the :88 clause b1 deletes, so :927-928 fail. The only occurrence of 'legacy inline `## Verification` JSON carrier' in elicitation.md is inside the :97 solo clause b2 deletes, so :923-924 fail unless that sentence is rewritten to keep the precedence phrase. Keep only :921-922 and :925-926 (ideate SKILL.md:113 and from-spec-mode.md:40 keep the phrase), or reword the docs so the phrase survives.
- **CORRECTED** — b5: delete the whole block :1240-1274
  - The block also holds non-research pins, :1244-1253. They cover state.source.type = "generated" (SKILL.md), state.source.criteria_path and criteria_sha256 (free-form-mode.md), criteria_sha256 for generated free-form mode (verify.md), and 'Free-form sets `type: "generated"`' (state-schema.md). These are the only lint guards for the generated-source contract (grep finds no duplicates). Keep :1244-1253 as their own check and delete only :1240-1243 and :1254-1270.
- **CORRECTED** — b3: delete :875-888 (keeping the rest of validate_expected_against_sibling_spec) and self-tests :3210-3326, keeping setup :3196-3209
  - Both ranges break the file. :881 `commands = data.get("verification_commands", [])` sits inside :875-888 and is used at :890; deleting it made the self-test crash with NameError (tested). Delete :875-880 and :882-888 only. The expected_json setup ends at :3211, so deleting from :3210 leaves broken syntax; delete :3212-3326. Also delete the function block through :573. With the corrected ranges: self-test exits 0, no 'solo' string remains, the file shrinks by about 649 lines, and test-lint-fixtures.sh (with :275 changed to 'must document a solo-headroom hypothesis'), lint-fixtures.sh and lint-shadow-fixtures.sh all pass (tested in a scratch copy).
- **CORRECTED** — Open question 2: recommendation (i), queue drains allocating each item with --worktree, handles the PR default
  - Not enough. Only auto-mode cleanup advances the local base (task-complete.py:557 `update-ref base_ref base_sha` after an observed merge). Under the pr default, each item's terminal queue commit ([x]/[F], task-completion.md:80-86) stays on an unmerged task branch. The next item then branches from a base without the earlier transitions (task-completion.md:141-144, outer-loop.md:21-23), so the drain reads a stale docs/specs/queue.md. This needs a design decision (astra review) before or alongside the flip, not a doc-only fix.
- **CORRECTED** — Open question 5 cites README.md:158 for 'Historical record: iter-0020'
  - It is README.md:152. The pair-plan-schema.md listing at lint-skills.sh:103 is confirmed.
- **CORRECTED** — Open question 7: Lane A is effectively frozen per benchmark/README.md:62-64
  - The statement is at benchmark/README.md:57 and reads 'Lane A is frozen on the solo arm'. :62-64 are Lane B fixture bullets. The claim is narrower than 'Lane A frozen'.
- **CORRECTED** — Dependency: 0201-harness-transformation-plan.md:169-173 says ideate and spec-verify-check survive into intent
  - :169 does recommend `/devlyn:intent`, and the next lines say ideate's requirement alignment is reused. Nothing there mentions spec-verify-check surviving.

## Missed references found by the verifier

- scripts/lint-skills.sh:3001,3003,3005,3007,3011,3013,3015 — help-copy pins on test-benchmark-arg-parsing.sh that fail once :337-414 are deleted
- scripts/lint-skills.sh:2140-2141 — pin 'smoke-only-s1-cli-headroom'/'smoke-only-s1-cli-pair' in test-benchmark-arg-parsing.sh (:804, :831); conflicts with a3's 'delete it instead'
- scripts/lint-skills.sh:923-924 and :927-928 — packet says keep, but b1 (SKILL.md:88 clause) and b2 (elicitation.md:97 clause) remove the only occurrences of the pinned carrier phrases
- scripts/lint-skills.sh:1244-1253 — generic generated-source contract pins inside the :1240-1274 block that must survive
- scripts/lint-skills.sh:3290-3292,3294-3295,3297-3298,3300-3301 — non-root-README pins inside the '3289-3315' range that must be kept
- scripts/lint-skills.sh:2412 — pins 'then that pair evidence was accepted' on benchmark/auto-resolve/README.md:301, the line a4 edits
- config/skills/_shared/spec-verify-check.py:881 — `commands = ...` must be kept inside the :875-888 deletion; setup ends at :3211, not :3209
- benchmark/auto-resolve/README.md:209 — 'The package CLI exposes that release/handoff guard as one command:' becomes false
- benchmark/auto-resolve/BENCHMARK-DESIGN.md:280-281 — the rest of the bin/devlyn.js benchmark Q&A that :282 belongs to
- config/skills/_shared/codex-config.md:57 — runtime doc with research vocabulary (benchmark variant arm, scripts/codex-shim, iter-0006/0008, autoresearch path); mention only
- config/skills/devlyn:resolve/references/phases/build-gate.md:54 ('benchmark-prestaged') and probe-derive.md:177 (BENCH_FIXTURE_DIR/verifiers) — tied to the BENCH_WORKDIR/FORBIDDEN_RISK_PROBE hooks; should be on the b-keep list
- config/skills/devlyn:resolve/SKILL.md:325 — another 'inside a warehouse' fixture-shaped example missing from the b-keep list
- docs/specs/package-evidence-self-contained/spec.md:17-20,26-29 — historical spec whose invariant ('every file package.json promises to publish' incl. benchmark evidence) is superseded; no CI gate, mention only
- docs/specs/task-completion/spec.md:3,7 (title 'through PR merge and recoverable workspace cleanup') and :63 — go stale-ish alongside the :36-41 amendment
- scripts/test-windows-portability.py:351,582 — also assert 'Default to direct execution when inspection makes'
- config/skills/_shared/task-complete.py:557 with config/skills/devlyn:resolve/references/task-completion.md:80-86,141-144 and outer-loop.md:21-23 — queue-state propagation under the PR default (base never advances)
- benchmark/instruction-sensitivity/README.md:103 — '`devlyn-cli benchmark instruction` | not wired' row becomes permanently moot; mention only

## Acceptance checks the verifier could not run as written

- GitHub: PR opened against main with 'Windows portability' posix+windows green and not merged — needs push and GitHub CI; cannot be run in a read-only verification
- `bash scripts/lint-skills.sh # exit 0` — runnable (baseline passes in a fresh tree), but will FAIL if the packet is followed literally: the missed pins :3001-3015 (odd lines), :2140-2141 (if S1 cases are deleted) and :923-924/:927-928 break it. Run it in a fresh worktree; in the research checkout Check 6 compares the gitignored .claude/skills
- `python3 config/skills/_shared/spec-verify-check.py --self-test` — will crash (NameError on `commands`) or hit a SyntaxError if the literal :875-888 and :3210-3326 ranges are used; passes with the corrected ranges
- `git grep -n 'absent means' -- task-completion.md docs/specs/task-completion/spec.md # both say pr` — ambiguous if the dated amendment in spec.md quotes the old 'absent means auto' wording
- `git grep -n 'devlyn-cli benchmark' -- ... # no output` — the path list omits BENCHMARK-DESIGN.md and benchmark/auto-resolve/measure-static.py, which a4 edits, so it cannot confirm those edits
