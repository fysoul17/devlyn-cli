# Work packet E1-comparison-apparatus-v2

Generated 2026-09-24 against main @466aa25 by a read-only scoping agent, then checked by an adversarial verifier (verdict: **READY_WITH_FIXES**). **Verifier corrections below override the packet body where they conflict.** Line numbers drift: re-check every location against the session's base SHA before editing. Registration: [0221](../../../iterations/0221-subtraction-direction.md).

**Used in:** Session 3. Arm F = published devlyn-cli@3.2.1 full resolve; verify tarball integrity, install manifest and actual role/pair behavior in-container. The B' product-arm install path is completed in Session 5.

## Summary

This packet collapses the six-level wrapper chain (0220→0219→0218→0211→0210→0208: 25 files, 1,744 lines) into one self-contained experiment directory. The evaluators, calibration, accounting and container isolation are imported unchanged. Every budget mechanism is deleted: the live token/call interrupts, the stop-all on first breach and on reviewer timeout, the meter/reserve/wait prompt text, the per-cell token targets, the 2-review/4-descendant pool and the zero-retry provider override. What remains is one uniform hang wall timeout, post-hoc usage recording (UNKNOWN when missing, never zero) and a screen stop only on shared-infrastructure defects: a container that survives teardown, a control/source hash mismatch, or an evaluator that cannot produce a verdict. The runner gains Claude owners (opus-5-5, sonnet-5), Codex astra/sol owner routes, cross-engine reviewer/assessor routes, and a product-arm mechanism. That mechanism runs the published devlyn-cli@3.2.1 full /devlyn:resolve (arm E) and later the /devlyn:intent candidate (B′) inside the same container; the recipe is the host-side one 0185/launch.py:48-123 already proved. It also fixes the evaluator defects found so far: D3.6 and public suites run in-image rather than on the loaded host; less is baked into the image so the owner and evaluator see the same PATH; and D2/D4 allowed test paths that break pytest collection (reproduced today) are corrected. The packet also adds the packet base-diff fix that committing product arms need. No product location changes (verified: nothing in bin/, config/, scripts/, .github/ or package.json files references autoresearch/experiments), so managed CLAUDE.md/AGENTS.md text, instruction-templates.json, lint pins, the .agents mirror and CI are unaffected (NONE).

## Items

### 0. (a) Reuse as-is, import by path, zero edits: task material, evaluators, calibration, accounting, packet compaction, isolation/teardown, format gates, identity b

**Change.** (a) Reuse as-is, import by path, zero edits: task material, evaluators, calibration, accounting, packet compaction, isolation/teardown, format gates, identity binding, image.

**Files / lines.** 0206/tasks.json:84-124 (D3) and :125-167 (D4) as the source of the v2 copies. Issue snapshots .devlyn/0206/D3-issue.json and D4-issue.json are sha-bound at tasks.json issue_snapshot_sha256. Pinned clones .devlyn/0206/commander @ba6d13d and click @3cbaa76 were verified today; they are gitignored local state. 0206/baseline-probes.py:1-96. 0207/calibrate.py reference() :23-37, MUTANTS :40-70 and evaluate() :90-111; 0207/commander.mjs:1-87; 0207/click_checks.py:1-165. 0208/accounting.py Rollouts, reused with math.inf limits exactly as 0218/usage.py:23-24 already does. 0210/native_accounting.py:1-56 (fork boundary). 0211/packet.py compact_tap :12-38 and checks() :41-60; 0211/test_packet.py. 0210/native_cell.py create argv :67-80, isolation asserts :99-116 and teardown :187-211 (copied into cell.py). 0218/prepare.py FORMAT :10-16 (Prettier 3.8.3 / Ruff 0.15.9), with controls .devlyn/0219-screen/format-controls.txt (4 pristine pass, 4 mutants rejected). 0217/review.py argparse fix. 0218/run_cell.py snapshot_auth :28-57. Image sha256:4f2080e5d128… (docker image inspect OK: created 2026-09-22T11:43:34Z, user 501:501, Codex 0.155.1 / Claude 2.1.278 / Node 22.23.2 / Py 3.12 / pytest 9.0.3); its archived models_cache already lists gpt-6-sol.

**Current behavior.** These pieces are sound but are reached only through a chain of 5 wrapper levels, each of which adds prompt/budget text.

**Target behavior.** v2 imports these modules unchanged. Archives stay byte-identical, so historical seals remain verifiable. Calibration set for D3/D4 is 15 variants: D3 baseline + reference + 6 mutants, D4 baseline + reference + 5 mutants; the full 29/29 set was 0207's.

**Tests.** Existing unit tests are unchanged: 0208 has 21, 0210 has 7, 0211 has 5. All pass at 466aa25 (run today). `git diff origin/main -- autoresearch/experiments/02{04,06,07,08,10,11,14,17,18,19,20}` must be empty.

**Migration.** NONE (research-only; autoresearch is not in package.json files)

**Risk.** The image cannot be rebuilt as-is: the COPY inputs of 0210/Dockerfile:3,5,6 (node tarball, codex vendor dir, claude binary) are not present anywhere under ~/.local/share/nx01 (searched). See the image item.

**Net lines.** 0

### 1. Registration/contract doc for v2. It supersedes the budget and stop-all clauses and records the user decisions of 2026-09-24. It also replaces the stale HANDOFF

**Change.** Registration/contract doc for v2. It supersedes the budget and stop-all clauses and records the user decisions of 2026-09-24. It also replaces the stale HANDOFF block and adds one DECISIONS row.

**Files / lines.** NEW autoresearch/experiments/<ID>/DESIGN.md. It explicitly supersedes (archives unedited): 0206/PROTOCOL.md:58-67 (4-descendant/2-review pool), :77-120 (finite budget, live whole-tree observation, BUDGET_EXCEEDED stop, assessment 240s/8,000/400,000 caps); 0210/AMENDMENT.md:18-21 (thresholds as observed stop rules), :26-36 (UNKNOWN stops ENTIRE screen incl. 240s reviewer timeout at :31-32; first-breach stop-all at :33-36), :37-41, :47-57 (assessment allowances, descriptive-only). It cites the user lift of 0201 rule 5 at autoresearch/iterations/0201-harness-transformation-plan.md:153-155 (quote: 'full 교체도 고려하고 있어. 너무 비효율적이라서'); do not edit 0201. autoresearch/DECISIONS.md: append one row after :406. autoresearch/HANDOFF.md:41-71: replace the stale 0206-0209 admission narrative with an 8-line pointer to <ID>.

**Current behavior.** The live contract is 0206 PROTOCOL plus the 0210 AMENDMENT: observed token/call targets, first-breach stop-all, 240s reviewer timeout that halts the whole screen when usage is missing, assessment caps, and descriptive-only results. autoresearch/HANDOFF.md still narrates 0206-0209 as BLOCKED.

**Target behavior.** One live contract. Wall = hang protection only; usage is recorded, never gated. A per-cell failure is a result row and the screen continues. The screen stops only on (1) a container survivor or teardown failure, (2) a control/source/prompt hash mismatch against the seal, or (3) an evaluator that cannot produce a verdict. No descriptive-only clause: decision rules are registered prospectively per 0221 Track 3. Delivery is push + PR only, no auto-merge.

**Tests.** `grep -nE 'descriptive only|BUDGET_EXCEEDED|first.breach' autoresearch/experiments/<ID>/DESIGN.md` hits only inside the supersession list. HANDOFF net lines shrink.

**Migration.** NONE

**Risk.** Ambiguity over which old clause still applies. Mitigation: DESIGN.md lists superseded file:line ranges explicitly and states that everything else in 0206 (scope, protected files, blind assessment) stays.

**Net lines.** +80 DESIGN.md, +1 DECISIONS, HANDOFF -31/+8

### 2. tasks.json v2 for D3 and D4 (D2 optional). Budget fields are gone, allowed test paths that break collection are fixed, and every declared check (color parity, f

**Change.** tasks.json v2 for D3 and D4 (D2 optional). Budget fields are gone, allowed test paths that break collection are fixed, and every declared check (color parity, format gate, focused path) is folded into public_checks. This deletes the 0215/0216/0218/0219 prepare wrappers.

**Files / lines.** NEW autoresearch/experiments/<ID>/tasks.json, copied from 0206/tasks.json:84-167 minus the budget fields. D3 public_checks = ['env -u NO_COLOR node --test tests/command.executableSubcommand.test.js tests/args.literal.test.js', 'env -u NO_COLOR node --test', FORMAT['D3'] from 0218/prepare.py:14]. D4 allowed: replace :135-136 with 'tests/test_utils/**' and 'tests/test_types/**'; public_checks = ['python -m pytest tests/test_basic.py', 'python -m pytest', FORMAT['D4'] from 0218/prepare.py:15]. With less baked into the image, the 0219 PATH prefix is not needed. If D2 is kept: allowed :53 becomes 'tests/test_exceptions/**' and check :69 becomes 'python -m pytest tests/test_exceptions/ tests/test_basic.py'. One top-level 'wall_seconds' hang value replaces the per-task budgets.

**Current behavior.** 0206/tasks.json carries per-task wall/output/input targets at :18-20, :56-58, :96-98, :139-141, totals at :291-297 and budget launch_blockers at :298-302. D4 allowed lists tests/test_utils.py and tests/test_types.py (:135-136). D2 lists tests/test_exceptions.py (:53) and its focused check at :69 collects nothing. Those files are ABSENT at base while same-name packages tests/test_utils/, tests/test_types/ and tests/test_exceptions/ exist. execution_scope (:123/:166) invites 'Named test paths may be created if absent'. Creating tests/test_exceptions.py or tests/test_utils.py in a click@3cbaa76 copy makes pytest 9.0.3 fail collection with 'import file mismatch' (reproduced today on host in scratch). NO_COLOR/format/less fixes live in wrapper code: 0215/prepare.py, 0216/prepare.py, 0218/prepare.py:45-48, 0219/prepare.py:9-15.

**Target behavior.** Owner and evaluator run byte-identical declared checks. No task contract sends an owner toward a path that breaks the suite. No token field exists.

**Tests.** Two model-free collection controls in the image: click base + tests/test_utils.py gives pytest exit 2 'import file mismatch'; click base + tests/test_utils/test_fifo_regression.py collects cleanly. Host-side scope logic accepts a new file under tests/test_utils/ (pathlib '**' matches files on host Python 3.14, verified today). The format controls from .devlyn/0219-screen/format-controls.txt are re-run for D3/D4.

**Migration.** NONE

**Risk.** Changing D4 allowed paths is a task-contract amendment and must be stated in DESIGN.md; obligations are unchanged. '**' also permits edits to existing tests in those dirs; the existing 'cannot weaken unrelated tests' rule and blind assessment still apply.

**Net lines.** +95

### 3. (c) Owner prompts. Replace the 398-word 0211 common contract and its add-ons with a ~75-word neutral task frame so that arm A is genuinely native; arm-specific 

**Change.** (c) Owner prompts. Replace the 398-word 0211 common contract and its add-ons with a ~75-word neutral task frame so that arm A is genuinely native; arm-specific text is added only for C, B′ and E. Proposed common.txt: 'Complete the development request in /work/.devlyn/caller.json for the repository at /work. Change only the allowed paths it lists; keep existing tests and caller.json unchanged. Run its public checks. Do not look up upstream fixes or use the network except for your own model calls, and do not change Git configuration, dependencies or installed tools. There is no later repair turn. Finish with what you changed, what you verified and anything unresolved.' C adds: 'Before finishing, obtain an independent review with python3 /control/review.py; it sends the request, allowed files, your diff and any files you put under /work/.devlyn/checks-final to a reviewer without tools. Reproduce and repair actionable findings, rerun affected checks, and obtain a fresh review after any source change.'

**Files / lines.** NEW autoresearch/experiments/<ID>/common.txt. C/B′/E text lives in <ID>/prepare.py. Stop using 0211/common.txt:1-9, 0214/common-wait.txt, 0218/prepare.py:17-20/:50, 0220/prepare.py:9-15/:26-29, 0211/prepare.py:44-46/:52-56. B is supplied as a candidate (path+sha, or an installed package; see the product-arms item), never 0204/owner.md.

**Current behavior.** 0211/common.txt:1-9 contains: an engine-specific identity line; slot counting ('at most four descendant … two reviews', :3); a 240-second reviewer target and 2-review PRODUCT_INCOMPLETE rule (:5); a whole telemetry/targets paragraph (:7); and the raw-log retention duty 'Retain exact test commands, exit codes, stdout and stderr under .devlyn/checks-final', TAP transport notes, Click metadata and 'Do not commit' (:9). The retention duty produced the 0218 D2-1-A 1,104,757 B review packet (466 KB baseline-pager stdout). Prompt add-ons: the per-cell targets line (0211/prepare.py:44-46), the C pool clause (:55-56), the 0214 wait text with Codex-only yield_time_ms (inserted by 0218/prepare.py:50), METER (0218/prepare.py:17-20) and RESERVE (0220/prepare.py:9-15). B = 0204/owner.md (447 words), which also carries budget/usage duties (:5-6 'total budget', :33-34 'Stop at the supplied budget', :46-48 usage reporting). Those audit/report duties caused the 0219 D1-B post-completion wrap-up of 34,141 + 35,134 input.

**Target behavior.** A receives only the task frame: no review tool is advertised, and native subagents remain available. The reviewer packet includes checks-final only if an owner chooses to write it; no retention duty. 'Do not commit' is deleted because the evaluator diffs against base_sha. No budget, telemetry, meter, wait, invocation or 240s wording appears in any prompt.

**Tests.** For every dry cell, `grep -ciE 'budget|target|telemetry|invocation|cache-inclusive|240|yield_time_ms|OUTPUT' prompt.txt` returns 0. prompt.txt == plan.argv[-1] and baseline.prompt_sha256 matches, following the 0214-0220 binding pattern.

**Migration.** NONE

**Risk.** This is a real arm redefinition: A no longer sees the review tool (0206 PROTOCOL:39-41 equal-capability intent) and C loses its 2-review cap. Both need the explicit registration decision recorded as open questions. Removing retention means reviewers may see no check logs; packet.checks() already emits 'NO CHECKS SUPPLIED; report this limitation.' (0211/packet.py:60).

**Net lines.** +3 (common.txt); arm text counted in prepare.py

### 4. (d) prepare.py, flattened and route-driven. One materializer replaces 5 wrapper levels. Routes: Codex {gpt-6-astra, gpt-6-sol} owner with a configurable child m

**Change.** (d) prepare.py, flattened and route-driven. One materializer replaces 5 wrapper levels. Routes: Codex {gpt-6-astra, gpt-6-sol} owner with a configurable child model; Claude {claude-opus-5-5, claude-sonnet-5} owner. Budget plan fields are deleted.

**Files / lines.** NEW autoresearch/experiments/<ID>/prepare.py, keeping the core of 0211/prepare.py:15-72: clone/checkout/remote removal :25-29, issue sha check :31-33, caller :34-39, baseline hashes :67-71. caller.json gains 'base_sha' for packet.py. Codex argv: `env PYTHONPATH=/work/src:/control/python codex exec --strict-config --json --skip-git-repo-check -C /work <prompt>`, deleting the PATH=/control/less… entry (:59) and '--ignore-rules'. Claude argv: `env PYTHONPATH=… DISABLE_AUTOUPDATER=1 claude -p --model <m> --effort <e> --permission-mode bypassPermissions --output-format stream-json --verbose <prompt>`. Claude credentials are a per-cell writable copy in runtime scratch, bind-mounted at /home/participant/.claude/.credentials.json, so evidence keeps only an empty mount point as it does for codex auth.json today (size 0 in all nine 0218/0219 cells, verified). codex.toml template derived from 0211/codex.toml: keep :1 and :3 (route model/effort), :7, :11 rollout_budget=false, :12-14, :18-24 (child model/effort from route) and :38-39. DELETE :2 model_provider and :26-36 [model_providers.observed-openai]; that block existed only to force zero retries per 0211/CONTINUATION.md:10-15. DELETE :6 project_doc_max_bytes=0 and :15-16 skill_search/skip_host_skill_discovery: upstream commander/click have no AGENTS.md, CLAUDE.md or .claude (verified), and product arms need them. Sandbox is decided in open questions. Plan = {engine, model, effort, child_model, wall_seconds, argv, image, mounts}.

**Current behavior.** The runner can launch only Codex owners. Evidence: 0211/prepare.py:58-61 argv is `codex exec`; :65 hardcodes model='gpt-6-astra', effort='high'; 0211/codex.toml:1,22 pin astra. The chain 0220/prepare.py → 0219/prepare.py → 0218/prepare.py → 0211/prepare.py re-parses and rebinds prompt, argv and hashes at every level; the pilot.json stamp chain comes from 0214, 0218, 0219 and 0220. Plan fields input_tokens, output_tokens and model_calls=5 are at 0211/prepare.py:63-65.

**Target behavior.** One prepare call per cell. A single prepare_sha256 in baseline.json. Identical config for A/B′/C within an engine. Model and effort come from the route, never code constants.

**Tests.** Dry materialization for every registered cell checks prompt/argv/caller/hash bindings. Also: codex.toml for a sol route contains model='gpt-6-sol' and nothing named observed-openai; the Claude plan argv contains --model claude-opus-5-5. A unit test covers route → argv for both engines.

**Migration.** NONE

**Risk.** Deleting the zero-retry provider means native retries happen. Usage of failed attempts may then be under-reported, which is acceptable under record-only rules; DESIGN.md must state it. The '--effort' vocabulary differs per engine, so routes store engine-native values.

**Net lines.** +110

### 5. (b) cell.py: trimmed copy of 0210/native_cell.py. The live budget interrupt, the terminal breach check, the error-event kill and the budget classes are deleted.

**Change.** (b) cell.py: trimmed copy of 0210/native_cell.py. The live budget interrupt, the terminal breach check, the error-event kill and the budget classes are deleted. Owner termination is engine-generic, and the only kill is a hang wall.

**Files / lines.** NEW autoresearch/experiments/<ID>/cell.py from 0210/native_cell.py. Keep :66-116 (create/inspect/isolation asserts) and :187-211 (kill, then inspect Running/Pid, then rm). Delete :120-122, :125-126, :129-146 (meter and interrupt), :150-151, :157-159, :164-172 and :186. Replace :212-221 with the record: owner_status ∈ {EXITED_0, EXITED_NONZERO, HANG_TIMEOUT}, identity ∈ {MATCH, MISMATCH, UNKNOWN} (Codex: turn_context model/effort and model_reroute per :173-183; Claude: result.modelUsage keys ⊇ requested, recording extra keys), usage (from record_usage.py), teardown ∈ {CLEAN, FAILED}. Exit 2 only when teardown FAILED.

**Current behavior.** 0210/native_cell.py:120-122 treats wall - 30 s as BUDGET_EXCEEDED. :125-126 and :150-151 kill on any 'error'/'turn.failed' event, which includes native retries. :129-131 and :157-159 construct Rollouts with plan input/output/call limits. :141-145 is the LIVE budget interrupt. :168-172 is the terminal breach. :186 marks TimeoutError as a budget failure. :213-221 assigns BUDGET_EXCEEDED/UNKNOWN/INFRA_INVALID classes, and any failure becomes rc 1, which becomes a screen stop. Owner identity is Codex-only: thread.started at :127, turn_context and model_reroute at :173-183.

**Target behavior.** A cell ends at owner exit or at the uniform hang wall. The product is always sealed and evaluated afterwards, even after a timeout (0219 D1-B had finished its product before the breach kill). Usage over any old target is just a number.

**Tests.** Zero-model container controls, reusing the 0208/controls.py fixture pattern: (1) a Codex-shaped emitter with 1,200,001 input (above the old hard target) gives classes without BUDGET_EXCEEDED and rc 0, usage recorded; (2) a sleeper past the wall gives owner_status HANG_TIMEOUT, container removed, rc 0; (3) a double-forked, TERM-ignoring setsid child is gone with the namespace; (4) an injected docker rm/kill failure gives rc 2. `grep -n 'BUDGET_EXCEEDED\|observed budget\|input_limit=plan' cell.py` returns nothing.

**Migration.** NONE

**Risk.** Without the error-event stop, a stuck native retry loop runs until the hang wall. The wall value (open question) bounds it.

**Net lines.** +140

### 6. record_usage.py: a post-hoc usage recorder that the owner neither sees nor mounts. The owner-visible meter is deleted.

**Change.** record_usage.py: a post-hoc usage recorder that the owner neither sees nor mounts. The owner-visible meter is deleted.

**Files / lines.** NEW autoresearch/experiments/<ID>/record_usage.py. Codex: group rollout files by exec-root lineage (session_meta parent chain), symlink each group into a temp dir, then run 0210 native_accounting.Rollouts(dir, root, math.inf, math.inf, math.inf, stale=math.inf).finish() per root and sum; the archived modules stay unchanged. Claude: the owner's terminal result.modelUsage per model. Nested claude -p calls (the resolve pair judge uses no --output-format per config/skills/_shared/adapters/claude.md:24-29) are summed from $HOME/.claude/projects/**/*.jsonl assistant usage, deduplicated by message id. Reviewer calls: Claude modelUsage or Codex turn.completed usage. Output: per-engine and per-model totals plus completeness ∈ {COMPLETE, PARTIAL, UNKNOWN}. Remove /control/usage.py from the control build.

**Current behavior.** 0218/usage.py:1-30 and 0220/usage.py:1-34 are owner-visible meters mounted at /control/usage.py. The shared accounting raises 'unrelated session' for any second exec root (0208/accounting.py:65-66). That rules out the product arms: resolve's codex-monitored children are fresh exec roots (0185 C had 'eight structured parent/worker threads per draw'). Claude usage is parsed only for the reviewer, and requires claude-fable-5-1 (0210/native_cell.py:23-60). Archived Claude result events carry per-model modelUsage (inputTokens, cacheRead, cacheCreation, outputTokens, thinkingTokens) plus a subagent_stats field (seen today in .devlyn/0219-screen/…/01-D1-1-A/work/.devlyn/reviews/call-1/stdout).

**Target behavior.** Usage is always recorded when available and UNKNOWN otherwise (never 0). It never stops anything. Cache reads/writes and reasoning are counted once, following the existing semantics in 0208/accounting.py:125-128 and native_cell.py:57-59.

**Tests.** Replay against archived cells: .devlyn/0219-screen/0219-screen-20260924/01-D1-1-A (home/.codex/sessions + work/.devlyn/reviews) must equal verdict-01.json (230,575 input / 6,472 output / 2 calls). Two synthetic exec roots are summed without error. A synthetic Claude stream-json with result.modelUsage is parsed. A truncated rollout gives PARTIAL, not a failure.

**Migration.** NONE

**Risk.** Two things are unverified. Does Claude result.modelUsage include native subagent usage? (subagent_stats is present; see open questions.) Do Claude transcripts persist for nested judges? Both are checked in the route smoke.

**Net lines.** +70

### 7. review.py: the reviewer transport becomes record-only and routed. The pool cap, the 240s stop and the zero-retry setting are deleted, and a Codex reviewer branc

**Change.** review.py: the reviewer transport becomes record-only and routed. The pool cap, the 240s stop and the zero-retry setting are deleted, and a Codex reviewer branch is added.

**Files / lines.** NEW autoresearch/experiments/<ID>/review.py, merging 0217/review.py:5 (argparse; --help never dispatches) with 0210/review.py:14-17 and :20-51. Delete :18-19, :45 and :52-53. Read the route from /control/reviewer.json {engine, model, effort, hang_seconds}, which is sealed with the control hash. Claude branch as today minus retries. Codex branch: `codex exec --json --sandbox read-only -m <model> -c model_reasoning_effort=<e> --skip-git-repo-check` with stdin prompt and a temp CODEX_HOME seeded from a copied auth.json; retain only the sessions/*.jsonl and stdout in call-N, never auth. Hang bound comes from /control/run-bounded.py.

**Current behavior.** 0210/review.py:18-19 refuses a third review ('Review pool exhausted'). :28-33 hardcodes run-bounded 230 with claude-fable-5-1/medium. :45 sets CLAUDE_CODE_MAX_RETRIES=0. :52-53 raises SystemExit on >240s. 0210/native_cell.py:32-35 and :38-39 turn a pending review over 240s or an exit of 124 into a screen-stopping TimeoutError; this is the reviewer-timeout stop-all of 0210/AMENDMENT.md:31-32. :44-46 requires identity {'claude-fable-5-1'}. 0217/review.py:1-6 is a wrapper that adds argparse.

**Target behavior.** Any number of reviews. A reviewer timeout or error is recorded on that call (usage UNKNOWN), the owner sees the failure, and the cell continues.

**Tests.** Stub-claude and stub-codex fixtures on PATH inside the image: exit 124 gives a recorded call with usage UNKNOWN and a cell record without stop; a third call is allowed; --help and unknown args allocate no call dir (0217 controls replayed); no credential file lands under /work/.devlyn/reviews.

**Migration.** NONE

**Risk.** Parity: the Codex reviewer cannot be tool-less like `claude --tools ''`; it is read-only sandboxed and told not to use tools. Record this as a limitation. Unbounded reviews could loop until the hang wall.

**Net lines.** +60

### 8. packet.py: the review/assessment diff is taken against base_sha instead of HEAD. This is required for product arms that commit, and for any owner that commits n

**Change.** packet.py: the review/assessment diff is taken against base_sha instead of HEAD. This is required for product arms that commit, and for any owner that commits now that 'Do not commit' is gone.

**Files / lines.** NEW autoresearch/experiments/<ID>/packet.py. It imports compact_tap and checks from 0211/packet.py unchanged and redefines packet(work) to use `git diff <caller['base_sha']>` in place of 0211/packet.py:80. <ID>/review.py and <ID>/assess.py import this packet.

**Current behavior.** 0211/packet.py:80 uses `git diff HEAD`. resolve commits on a task branch (task-complete.py allocate plus checkpoints), so that diff would be empty. 0185 already used `git diff <baseline>` (0185/launch.py:151).

**Target behavior.** Reviewers and assessors see the full product delta whatever the owner's commit behavior.

**Tests.** Unit test: a fixture repo with a commit after base yields a non-empty DIFF from packet(), while `git diff HEAD` is empty as the control. 0211/test_packet.py stays green.

**Migration.** NONE

**Risk.** The base must be a reachable commit in the work clone. It is: the full clone is kept by 0211/prepare.py:25-26.

**Net lines.** +25

### 9. (f) check.py: the deterministic evaluator runs entirely inside the pinned image, including the requirement oracles and D3.6. The evaluator runs the declared pub

**Change.** (f) check.py: the deterministic evaluator runs entirely inside the pinned image, including the requirement oracles and D3.6. The evaluator runs the declared public checks verbatim. The 'stop screen' raises are deleted except when no verdict is possible.

**Files / lines.** NEW autoresearch/experiments/<ID>/check.py, merging 0211/check_cell.py:21-93 and 0218/check_cell.py:24-58. Scope logic 0211/check_cell.py:30-38 stays host-side. Run each tasks.json public_check via `sh -c` in `docker run --network none --read-only --tmpfs /tmp --tmpfs /cell --mount work→/cell/work:ro --mount control:ro`. Run the oracle in the same container: `python3 -B -c` importing /control/autoresearch/experiments/0207/calibrate.py (evaluate(Path('/cell/work'), task, SimpleNamespace(node='/usr/local/bin/node', python310=None), Path('/tmp/fixtures'))). The /cell tmpfs lets 0207/calibrate.py:74 create /cell/native-tmp without edits. The control build must add 0206/tasks.json and 0207/{calibrate.py,commander.mjs,click_checks.py}, because calibrate imports TASKS at :16. Delete the host PATH and less entries (:53). Timeouts become hang protection that records EVALUATOR_TIMEOUT; only 'no verdict produced' returns rc 2.

**Current behavior.** 0211/check_cell.py:58-65 runs 0207 calibrate.evaluate on the HOST with runtime node/python310. That includes 0207/calibrate.py:104-110, D3.6: host `node --test …signals/mock/lookup` with timeout=15. Per 0219/PREPARED.md:62-64 it can mark a correct D3 incomplete under host load; the host repro hung 2/8 runs at load 39-91, while in-image runs were 8/8. :48 special-cases `node --test` or pytest instead of the declared checks. :46 alarm(110), :69-70, :90-91 and 0218/check_cell.py:29-31, :54-55 raise 'stop screen' on the 120s combined limit. :53 PATH carries /control/less.

**Target behavior.** Owner, evaluator and calibration share one environment. Host load cannot flip D3.6. The format gate is just another declared check, not a separate wrapper container.

**Tests.** In-image D3 reference run repeated 20× with the host loadavg recorded: D3.6 passes 20/20. Prediction, stated before running: each D3.6 run completes in <15 s in-image. All 15 D3/D4 variants reproduce their expected pass/fail in-image.

**Migration.** NONE

**Risk.** D2.6 needs native Python 3.10, which is absent from the image (0207/calibrate.py:96-97). D2 therefore stays host-only for D2.6, or is excluded from the first screen (open question). The public-suite timing budget inside the container is unmeasured for D4 under 2 CPUs.

**Net lines.** +90

### 10. calibrate.py (in-image) plus admission controls, replacing host-side calibration.

**Change.** calibrate.py (in-image) plus admission controls, replacing host-side calibration.

**Files / lines.** NEW autoresearch/experiments/<ID>/calibrate.py. It imports reference(), MUTANTS and evaluate from 0207/calibrate.py unchanged, restricts to --tasks (D3,D4) and runs each variant plus its declared public checks via the same in-image argv as check.py. It writes summary.json, supports --repeat N and records `sysctl -n vm.loadavg` per run.

**Current behavior.** 0207/calibrate.py:113-158 main() runs all four tasks host-side, requires python310 (:115) and runs the public suites on the host (:144-151). 0219 admission reached 28/29 and then 27/29 because the host `node --test` hung (.devlyn/0219-screen/admission-notes.txt); launch then relied on a separate in-image substitute (inimage-public-controls.txt).

**Target behavior.** Calibration is one in-image command with the same environment as grading. Load is recorded, not controlled.

**Tests.** `calibrate.py --tasks D3,D4 --repeat 5` gives all 15 variants expected in every repeat, fixture_cleanup true, and 0 D3.6 timeouts.

**Migration.** NONE

**Risk.** Pure reuse of the mutant definitions, so the 0207 coverage limits remain as documented in 0207/README.md:41-43.

**Net lines.** +45

### 11. assess.py: blinded assessment becomes record-only and routed, with the owner final report retained.

**Change.** assess.py: blinded assessment becomes record-only and routed, with the owner final report retained.

**Files / lines.** NEW autoresearch/experiments/<ID>/assess.py from 0211/assess.py:23-73. Delete :65-68 and :59. The route comes from runtime.json (assessor engine/model/effort). run-bounded comes from the control copy, not ROOT/config/skills/_shared. cell.py saves the owner's final message (Codex: last agent_message; Claude: result.result) to <cell>/final.txt for root claim-versus-verdict audit.

**Current behavior.** 0211/assess.py:65-68 stops the screen if assessor input exceeds 400,000 or output exceeds 8,000. :42-47 hardcodes run-bounded 230 with claude-fable-5-1. :59 sets zero retries. :42 depends on the product file ROOT/config/skills/_shared/run-bounded.py. The owner's final message is never captured, so 0206 PROTOCOL:127-129 'truthful claims' has no measurement.

**Target behavior.** Assessment always runs on a sealed product, including after a timeout. Usage is recorded. Missing usage never stops the screen.

**Tests.** A stub-assessor fixture with oversized usage produces a recorded assessment and a continuing screen. Output parsing uses 0218/run_cell.py:108-110, unchanged.

**Migration.** NONE

**Risk.** If the assessor is also shown final.txt, blinding breaks: resolve and intent reports reveal the arm. The recommendation is root-side claim audit instead (open question).

**Net lines.** +55

### 12. run_cell.py plus a tracked screen.sh: per-cell failures continue, and a stop happens only on shared-infrastructure defects.

**Change.** run_cell.py plus a tracked screen.sh: per-cell failures continue, and a stop happens only on shared-infrastructure defects.

**Files / lines.** NEW autoresearch/experiments/<ID>/run_cell.py from 0218/run_cell.py: keep :28-57 snapshot_auth (ACCOUNT from runtime.json), :69-76 seal, :81-87 NOT_DISPATCHED handling. Delete :91-95. Always run check.py then assess.py. Status = product {COMPLETE, PRODUCT_INCOMPLETE} × owner_status × identity × usage completeness. Set MIN_TOKEN_SECONDS ≥ wall_seconds + 900. Return 0 for any verdict, 3 when not dispatched, 2 only for teardown failure, control/source hash mismatch or no evaluator verdict. NEW <ID>/screen.sh: a tracked 15-line version of the launch.sh loop with the same rc semantics.

**Current behavior.** 0218/run_cell.py:91-95 maps any nonzero owner return to BUDGET_EXCEEDED/INFRA_INVALID and return 2 (stop screen), skipping checks and assessment. :96-106 returns 2 on any check/assessment error. :16 ACCOUNT is a code constant, overridden in 0219/run_cell.py:12. :17 MIN_TOKEN_SECONDS=3600 is shorter than a long product-arm cell. The loop exists only in untracked .devlyn/0219-screen/launch.sh (rc 2 stops; rc 3 retries up to 12 times, 5 min apart). Under that rule the 0218 screen stopped at cell 7 and the 0219 screen at cell 2: 84 cells truncated across four screens (0221 evidence-digest D).

**Target behavior.** The screen runs every registered cell unless shared infrastructure is broken. Every row is published.

**Tests.** Fixture-driven unit tests: owner HANG_TIMEOUT gives status recorded and rc 0; a check-container survivor gives rc 2; an account mismatch gives rc 3 with no dispatch.

**Migration.** NONE

**Risk.** If a provider account limit is hit mid-screen, later cells fail quickly with 429. The policy is an open question.

**Net lines.** +95

### 13. Image v2, reproducible and with less baked in: pinned CLIs (current Codex/Claude; grok optional) and tracked build inputs.

**Change.** Image v2, reproducible and with less baked in: pinned CLIs (current Codex/Claude; grok optional) and tracked build inputs.

**Files / lines.** NEW autoresearch/experiments/<ID>/Dockerfile, from 0210/Dockerfile:1-11 with 'less' added to the :2 apt line. NEW <ID>/BUILD.md with pinned download URLs and sha256 for node-v22.23.2-linux-arm64, the @openai/codex linux-arm64 vendor, the claude linux-arm64 binary and, optionally, a grok linux-aarch64 binary. Delete /control/less and all PATH prefixes (above).

**Current behavior.** 0210/Dockerfile:2 installs git, ca-certificates, xz-utils and procps, but not less. The pager lives at /control/less, and owner login-bash /etc/profile resets PATH (0219/DESIGN.md:14-17). That was fixed only with PATH prefixes (0219/prepare.py:9-15, 0211/prepare.py:59, 0211/check_cell.py:53). The COPY inputs of 0210/Dockerfile:3,5,6 are not retained. The host now has Codex 0.156.1 and Claude 2.1.281 against 0.155.1 and 2.1.278 in the image. Grok exists only as a macOS build (~/.grok/downloads/grok-1.0.41-macos-aarch64).

**Target behavior.** `bash -lc 'command -v less'` succeeds in the image. The image is rebuildable from tracked text plus pinned artifacts.

**Tests.** `docker run --rm --network none <img> bash -lc 'command -v less && codex --version && claude --version && node --version && python -m pytest --version'`. Under login bash, D4 full pytest gives the same result as the evaluator; 0219 precheck: 2,099 passed.

**Migration.** NONE

**Risk.** A new image invalidates prior calibration and in-image controls. Rerun them; they are model-free and cheap. Newer CLI versions change native behavior relative to past cells, so do not pool with 0213-0219 rows.

**Net lines.** +14 Dockerfile, +30 BUILD.md

### 14. (e) Product arms inside the same container. E = published devlyn-cli@3.2.1 full /devlyn:resolve; B′ = the /devlyn:intent candidate package later, via the same m

**Change.** (e) Product arms inside the same container. E = published devlyn-cli@3.2.1 full /devlyn:resolve; B′ = the /devlyn:intent candidate package later, via the same mechanism. Install runs in-image before the baseline snapshot.

**Files / lines.** In <ID>/prepare.py, arms 'E' and 'B′'. (1) Clone at base on branch main instead of detached (replacing the 0211/prepare.py:26 behavior); remote origin = bare repo at /home/participant/origin.git (host <cell>/home/origin.git); repo-local user.name/email. (2) The control carries the npm registry tarball devlyn-cli-3.2.1.tgz with its dist.integrity pinned (tag v3.2.1 exists locally). (3) An in-image install step (`docker run --rm --network none`, same mounts, HOME=/home/participant, cwd /work): Claude E runs `node /control/devlyn-cli/package/bin/devlyn.js -y` (bin/devlyn.js:958-960 → installClaudeCore: .claude/, CLAUDE.md, .gitignore '.devlyn/' at :820-833, ~/.claude/settings.json env incl. CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1 at :932-933, recorded as shipped 3.2.1 behavior). Codex E runs `… agents codex` (AGENTS.md + ~/.codex/skills stamped with container paths). (4) Commit the install output as the baseline, then write baseline.json. .devlyn/ is ignored, so caller.json and goal.txt keep the tree clean. (5) /work/.devlyn/goal.txt = request + requirements + allowed + public checks + the common constraints + 'Local-only: do not push or open a PR.' Prompt: Claude `/devlyn:resolve --goal-file .devlyn/goal.txt`; Codex 'Read ~/.codex/skills/devlyn:resolve/SKILL.md and execute /devlyn:resolve --goal-file .devlyn/goal.txt' with shipped defaults (no --no-pair). (6) The cell home ~/.claude/settings.json model is claude-opus-5-5 (the pair judge omits --model per adapters/claude.md:36-37), and codex.toml defaults to astra (codex-config 'omit -m'). (7) The Codex parent uses sandbox danger-full-access (0185/launch.py:113,122 precedent); keep seccomp=unconfined (0210/native_cell.py:69) for the children's sandboxes.

**Current behavior.** No product arm exists: 0201 rule 5 (…/0201-harness-transformation-plan.md:153-155) is lifted by the user. The only precedent is host-side 0185/launch.py:48-87 and :112-123: skills copied into .agents/skills, the __DEVLYN_SKILL_DIR__ stamp, git init with an origin remote, user.name/email, task-complete.py allocate, codex danger-full-access, and a prompt naming SKILL.md. Resolve took 840-2263 s per hard task on the host (0185/0187/0191/0192). Allocation requires the base branch checked out and a clean tracked/untracked tree (config/skills/_shared/task-complete.py:193-194), but 0211/prepare.py:26 detaches HEAD and :27 removes origin. GIT_CONFIG_GLOBAL=/dev/null (0210/native_cell.py:79) leaves no commit identity. resolve's codex children run `-s workspace-write` (config/skills/_shared/codex-config.md:81) and need a writable CODEX_HOME plus seccomp for nested sandboxes.

**Target behavior.** E measures exactly what a 3.2.1 user runs, with the pair judge on by default when available, in the same image, tasks and evaluator as A/B′/C. B′ plugs in by swapping the tarball and entry command only.

**Tests.** Model-free install control per engine. After the baseline commit, `git status --porcelain --untracked-files=all` is empty. Codex SKILL.md has no '__DEVLYN_SKILL_DIR__' and names the /home/participant/.codex/skills path. In a throwaway copy, `python3 <shared>/task-complete.py allocate --repo /work --task t --branch task/t --repository local/fixture --remote origin --base main` returns ALLOCATED. The install succeeds with --network none. Scope check: installed files are baseline-unchanged, so they are not violations, and .devlyn/runs/** is excluded.

**Migration.** NONE (the installed product is untouched; it runs from the registry tarball)

**Risk.** The container limits (0210/native_cell.py:70: pids 256, 4g, 2 CPUs) may throttle nested claude/codex/node. OAuth expiry during long cells is covered by the MIN_TOKEN_SECONDS change. Shipped instructions include the managed CLAUDE.md, so E conflates skill and instruction layer; that is intended because it measures the product. Usage for the plain-text claude judges depends on transcripts.

**Net lines.** +45 (inside prepare.py)

### 15. Model-free test suite for v2, including the counterexamples listed in 0221 Track 3 preconditions: stale PASS, failing exit, scope violation, model mismatch, uno

**Change.** Model-free test suite for v2, including the counterexamples listed in 0221 Track 3 preconditions: stale PASS, failing exit, scope violation, model mismatch, unowned file.

**Files / lines.** NEW autoresearch/experiments/<ID>/test_apparatus.py. Pure-Python cases: route → argv; prompt vocabulary absence; packet base-diff; record_usage replay and multi-root; verdict mapping, where an owner claim of PASS with a failing root check gives PRODUCT_INCOMPLETE and final.txt is kept; scope violation; model mismatch gives identity MISMATCH, recorded, rc 0; review --help/unknown args. Container cases, gated on the APPARATUS_IMAGE env: over-old-target usage, hang timeout, setsid survivor contained, reviewer 124, teardown-failure rc 2, D4/D2 path collision, in-image D3.6.

**Current behavior.** The v2 behaviors are untested. Existing unit tests cover only accounting (21 + 7) and packet compaction (5).

**Target behavior.** Every deleted budget path has a test showing its absence. Every kept stop condition has a test showing it fires.

**Tests.** `python3 -B -m unittest discover -s autoresearch/experiments/<ID> -p 'test_*.py' -v` passes. With APPARATUS_IMAGE set, the container cases pass too.

**Migration.** NONE

**Risk.** Container tests need Docker Desktop and the local image; they skip cleanly otherwise and must be run before any model call.

**Net lines.** +150

### 16. Route smoke: a gated, minimal model step run only after all model-free checks pass. One trivial-fixture cell per route not previously exercised, modeled on the 

**Change.** Route smoke: a gated, minimal model step run only after all model-free checks pass. One trivial-fixture cell per route not previously exercised, modeled on the 0210 preflight prompt (/control/prompt.txt).

**Files / lines.** Fixture and prompts go in <ID>/smoke/ (reuse the 0210 PREFLIGHT pattern: add_one + one native child + one review). Results are recorded in <ID>/SMOKE.md.

**Current behavior.** Only Codex astra owner + Fable reviewer routes have ever run in the container (0211/RESULT.md:3-9, 0213).

**Target behavior.** Predictions, stated in DESIGN.md before running: (1) Claude opus-5-5 owner: modelUsage contains claude-opus-5-5, subagent usage is either included or reported in subagent_stats, the transcript sum matches result totals, teardown is clean. (2) Codex sol owner: turn_context model is gpt-6-sol, no model_reroute. (3) Reviewer astra (Claude owner) and opus-5-5 (Codex owner): usage is recorded. (4) E-claude and E-codex: install, allocate, PLAN and archive complete on the trivial fixture, and pair-judge usage is recorded or explicitly UNKNOWN. (5) Grok is run only if a linux binary was sealed.

**Tests.** Each smoke row passes the cell.py identity, usage and teardown record checks. A failure is a recorded row; fix the apparatus before registration, never mid-screen.

**Migration.** NONE

**Risk.** This spends model calls (≈6-8 cells, E ≈ 15 min each), in line with the user guidance 'not excessive, enough to get results'.

**Net lines.** +40 (fixture+SMOKE.md)

### 17. (g) Record the candidate additional hard tasks and their oracle status in DESIGN.md. No code in this PR.

**Change.** (g) Record the candidate additional hard tasks and their oracle status in DESIGN.md. No code in this PR.

**Files / lines.** DESIGN.md section 'Confirmation candidates'. (1) 0185 installer transaction (autoresearch/experiments/0185/{request.md,acceptance.js,heldout.js,support.js}; source/reference under untracked .devlyn/0185/source): discriminating (native 0/2, direct 0/2, full 1/2 root-complete per iterations/0185:11-18). Its frozen checks passed all 6 products, and the reference shares the lock-release gap (iterations/0185:78-81). The discriminating probes are post-seal root replays (.devlyn/0185/replay-absence.js, replay-terminal.js, collect-*replays.py, untracked). They need promotion into a frozen heldout plus a repaired reference before use. (2) 0187 NDJSON decoder: frozen checks saturated (12/12). Its probes are tracked (0187/stream_supplement.py:13: 4,301-digit int, 200,000-bracket nesting), but the numeric requirement interpretation is contested (iterations/0187:109-113) and needs a request amendment first. (3) 0184 transactional publication / literal filenames: initial implementations were 2/4 complete (review→repair to 4/4), with an executable check.py; candidate medium-hard. (4) The 0102 sealed corpus has bare tier gradients (sonnet 0.49 / opus-4-8 0.475 / fable-5 0.353 / opus-5 ≈0.30) and suits tier questions. Exclude 0191/0192: all arms 2/2, saturated.

**Current behavior.** Only D1-D4 are wired. D1 is saturated and exposed: 19 of 20 prior owner cells were D1.

**Target behavior.** The next confirmation step can pick tasks with known oracle gaps listed up front.

**Tests.** None (documentation only).

**Migration.** NONE

**Risk.** None in this PR.

**Net lines.** +15 (inside DESIGN.md)

## Acceptance checks

- cd ~/.local/share/nx01/core-continuation-20260912 && for d in 0208 0210 0211; do python3 -B -m unittest discover -s autoresearch/experiments/$d -p 'test_*.py' || exit 1; done   # 21/7/5 OK; verified passing at 466aa25 on 2026-09-24
- python3 -B -m unittest discover -s autoresearch/experiments/<ID> -p 'test_*.py' -v   # new pure-Python cases pass
- APPARATUS_IMAGE=<v2 image id> python3 -B -m unittest discover -s autoresearch/experiments/<ID> -p 'test_*.py' -v   # container cases: 1,200,001-input emitter recorded rc0, hang -> HANG_TIMEOUT rc0 container removed, setsid TERM-ignoring child gone, reviewer exit 124 -> call usage UNKNOWN and cell continues, forced teardown failure -> rc2
- git diff --quiet origin/main -- autoresearch/experiments/0204 autoresearch/experiments/0206 autoresearch/experiments/0207 autoresearch/experiments/0208 autoresearch/experiments/0210 autoresearch/experiments/0211 autoresearch/experiments/0214 autoresearch/experiments/0217 autoresearch/experiments/0218 autoresearch/experiments/0219 autoresearch/experiments/0220   # archives byte-identical
- ! grep -rnE 'BUDGET_EXCEEDED|observed budget|/control/usage.py|yield_time_ms|cache-inclusive|request_max_retries|CLAUDE_CODE_MAX_RETRIES|observed-openai|number > 2|input_limit=plan' autoresearch/experiments/<ID> --include='*.py' --include='*.txt' --include='*.toml' --include='*.json' --include='*.sh'
- for i in $(seq 0 $((N-1))); do python3 -B autoresearch/experiments/<ID>/prepare.py $i <dry-runtime.json> || exit 1; done; ! grep -liE 'budget|target|telemetry|invocation|cache-inclusive|240|yield_time_ms|OUTPUT' <dry-output>/*/prompt.txt; python3 -c "import json,hashlib,pathlib,sys; [sys.exit(1) for c in pathlib.Path('<dry-output>').iterdir() if c.is_dir() and (json.loads((c/'plan.json').read_text())['argv'][-1]!=(c/'prompt.txt').read_text() or json.loads((c/'baseline.json').read_text())['prompt_sha256']!=hashlib.sha256((c/'prompt.txt').read_bytes()).hexdigest())]"
- docker build -t devlyn-apparatus-v2 -f autoresearch/experiments/<ID>/Dockerfile <pinned-context> && docker run --rm --network none devlyn-apparatus-v2 bash -lc 'command -v less && codex --version && claude --version && node --version && python -m pytest --version'
- python3 -B autoresearch/experiments/<ID>/calibrate.py --runtime <runtime.json> --tasks D3,D4 --repeat 5 --output <new-dir>   # 15 variants x5 all expected, fixture_cleanup true, zero D3.6 timeouts, loadavg recorded
- In-image click@3cbaa76 copy: touch tests/test_utils.py -> `python -m pytest -q -p no:cacheprovider --collect-only` exits 2 with 'import file mismatch' (reproduced on host today, pytest 9.0.3); a new tests/test_utils/test_fifo_regression.py collects cleanly
- python3 -B autoresearch/experiments/<ID>/record_usage.py --codex-home .devlyn/0219-screen/0219-screen-20260924/01-D1-1-A/home/.codex --reviews .devlyn/0219-screen/0219-screen-20260924/01-D1-1-A/work/.devlyn/reviews   # equals verdict-01.json: 230,575 input / 6,472 output / 2 calls
- Product-arm install control (E-claude and E-codex dry cells): `git -C <cell>/work status --porcelain --untracked-files=all` is empty after the baseline commit; `grep -c __DEVLYN_SKILL_DIR__ <cell>/home/.codex/skills/devlyn:resolve/SKILL.md` = 0; throwaway-copy `task-complete.py allocate ... --remote origin --base main` prints ALLOCATED; the install container ran with --network none
- Route smoke (model calls, only after every check above passes): each <ID>/SMOKE.md row shows the requested identity (Claude modelUsage key or Codex turn_context model), usage COMPLETE or explicitly UNKNOWN (never 0) and teardown CLEAN
- gh pr create --base main --head <apparatus-v2 branch> (no --auto); then `gh pr view --json autoMergeRequest -q .autoMergeRequest` prints null   # push + PR only, no merge, per user item 5

## Dependencies

- User decisions relayed 2026-09-24: no budgets (usage recorded only); per-cell failures are recorded and the screen continues; full /devlyn:resolve replacement is in scope, which lifts 0201 rule 5 for arm E; models claude-opus-5-5 main, claude-sonnet-5 light, gpt-6-astra reasoning/design, gpt-6-sol implementation, grok-4.7; delivery push + PR only.
- One read-only Astra (gpt-6-astra) critique round on this packet before implementation (user item 6). Single round, per 0221 FINAL-design Track 0 ('독립 리뷰 1회').
- Work in the research checkout ~/.local/share/nx01/core-continuation-20260912 (main @466aa25, clean tree) on a new branch. The user's primary checkout /Users/aipalm/Documents/GitHub/devlyn-cli has WIP (.gitignore, AGENTS.md, CLAUDE.md modified) and must not be touched.
- Gitignored local state must be present and hash-verified: .devlyn/0206/{commander@ba6d13d,click@3cbaa76,D3-issue.json,D4-issue.json}; Prettier 3.8.3 tgz and Ruff 0.15.9 wheel (copies exist under .git/devlyn-completion/*/scratch).
- Docker Desktop running; image sha256:4f2080e5… present (verified) or rebuilt v2 image. Network access to pinned linux-arm64 artifacts (node 22.23.2, @openai/codex, claude) and to the npm registry for devlyn-cli@3.2.1 with dist.integrity pinned.
- Credentials: host Claude keychain login (snapshot_auth), ~/.codex/auth.json, and ~/.grok/auth.json + agent_id if grok is used. All kept in owned 0600 scratch, never in the evidence tree.
- B′ arm needs the /devlyn:intent candidate package from the product/kernel packet. This PR does not wait for it: E (3.2.1) validates the product-arm mechanism now.
- Parallel product packets (adaptive-thinking env removal, benchmark split, research-vocabulary removal, standards frontmatter) do not touch this apparatus. It copies run-bounded.py/platform-support.py into /control at control-build time and runs E from the published 3.2.1 tarball, not the moving repo tree.

## Open questions

- Experiment ID: 0222 is provisional. The nx01 design folder already uses 0221, and parallel packets from this workflow may claim numbers. The orchestrator should assign one.
- Arm A definition: genuinely bare native (no review tool advertised; native subagents only), as recommended by the 0221 diagnosis, or 0206 equal-capability (review.py advertised to A, PROTOCOL.md:39-41)? The recommendation is bare; C isolates the effect of review.
- Arm C: remove the 2-review cap (a call budget) and bound only by the hang wall (recommended, consistent with 'no budgets'), or keep 'after the second review → PRODUCT_INCOMPLETE'?
- Reviewer route in review.py: other engine per owner (Claude owner → gpt-6-astra high; Codex owner → claude-opus-5-5) as recommended, or one fixed reviewer for all cells? Grok-4.7 as reviewer or owner needs a linux-aarch64 build; only macOS builds exist locally (~/.grok/downloads).
- Assessor: one fixed model for every cell, or dual blinded cross-engine assessors (claude-opus-5-5 + gpt-6-astra) with disagreements surfaced (recommended)? Grok-4.7 is feasible only as a host-side assessor today (macOS binary present).
- Uniform hang wall value for all arms. 5400 s is recommended: resolve took 840-2263 s per hard task on the host in 0185/0187/0191/0192, and a timeout is a result row, not a budget.
- Codex parent sandbox: danger-full-access for all Codex arms inside the container (recommended: parity with Claude owners, and required by E's nested codex exec, as in 0185), or workspace-write for A/B′/C only? Either way the 0210 telemetry-home write protection disappears for arms that use danger-full-access.
- Container resources: keep pids 256 / 4g / 2 CPUs (0210/native_cell.py:70) or raise them uniformly before the first E cell? Decide from the E smoke rows.
- Provider rate limit or auth failure mid-cell: record INFRA_INVALID and continue (the literal user rule), or requeue that cell once after the provider window resets, applying only when no product change was produced?
- Image: rebuild with host-current Codex 0.156.1 / Claude 2.1.281 plus less (recommended; required for less and grok), or keep the proven 0.155.1/2.1.278 image and keep the PATH prefix? Does Claude 2.1.278 accept claude-opus-5-5? Unverified.
- Does Claude's result.modelUsage include native-subagent usage? Archived result events also carry subagent_stats. The smoke must decide which is authoritative.
- B′ source: install the /devlyn:intent candidate package (same mechanism as E; measures the product, including its instruction layer) or inject the kernel text as a prompt, as the old B did?
- Keep D2 (medium) in the first screen? Keeping it requires host python3.10 for D2.6 (0207/calibrate.py:96-97) or adding 3.10 to the image. Or run D3/D4 only, per 0221 Track 3.
- Truthful-claim measurement (0206 PROTOCOL:127-129): root audits final.txt against the root verdict for every non-COMPLETE cell (recommended), or show the final report to the assessor at the cost of blinding?

## Verifier corrections (authoritative over the body)

- **CORRECTED** — six-level wrapper chain ... 25 files, 1,744 lines
  - Not reproducible. The six named dirs hold 39 tracked files and 2,731 lines, or 26 non-markdown files and 2,032 lines. Cosmetic; state the counting rule or drop the number.
- **REFUTED** — Image v2 test: `docker run ... bash -lc 'command -v less && codex --version && claude --version ...'` passes once less is added to the apt line
  - Ran `bash -lc` in the pinned image: PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games. /etc/profile drops ENV PATH (0210/Dockerfile:7), so `codex: NOT FOUND`, and rg is missing too. Only claude (/usr/local/bin) survives. Adding less does not fix codex. This also breaks arm E: codex-monitored.sh (the pair judge for E-claude, and codex-routed phases) is invoked from login tool shells. The shipped contract then routes VERIFY solo with a skip, so E silently loses its pair judge. Fix: symlink /opt/codex/bin/* and codex-path into /usr/local/bin, or add an /etc/profile.d PATH entry, in the v2 Dockerfile. Assert `bash -lc 'command -v codex rg'`.
- **REFUTED** — check.py runs each tasks.json public_check verbatim via sh -c against the work mounted :ro; owner and evaluator run byte-identical declared checks (D4: 'python -m pytest tests/test_basic.py', 'python -m pytest'); calibrate --repeat 5 gives all 15 expected
  - Click pyproject.toml:83-87 sets filterwarnings=['error']. Reproduced on a read-only click@3cbaa76 copy with pytest 9.0.3: every test passes, then the session ends in PytestCacheWarning ('could not create cache path') and rc=1. The 0211 evaluator avoided this with '-p no:cacheprovider' (check_cell.py:48). The v2 D4 evaluator and calibration would mark correct products failing. Fix: set PYTEST_ADDOPTS='-p no:cacheprovider' in both the owner and evaluator env, or give the evaluator a writable copy. Also missing: the evaluator's Click PYTHONPATH must become /cell/work/src:/control/python, because the mount moves to /cell/work.
- **CORRECTED** — Scope logic 0211/check_cell.py:30-38 stays host-side unchanged (D4 new tests accepted)
  - The only real Click owner cell (.devlyn/0218-screen/.../07-D2-1-A/work) created .pytest_cache/{CACHEDIR.TAG,README.md,.gitignore,v/cache/*}. These are absent from baseline.json, so :32-36 would count them as scope violations (only .devlyn/ is excluded). D4 has never reached checks, so this is latent. It becomes load-bearing now that D3/D4 are the only tasks. Fix with the same PYTEST_ADDOPTS in the owner env, or exclude git-ignored/cache paths explicitly.
- **CORRECTED** — Host-side scope logic accepts a new file under tests/test_utils/ (pathlib '**' matches files on host Python 3.14)
  - True on host 3.14. But packet() (0211/packet.py:65-66) runs INSIDE the container for review.py, on image Python 3.12. There, Path.glob('tests/test_utils/**') matches no files (verified: 0 with python3.12). `git diff <base>` also omits untracked files. So reviewers never see new D4 test files under tests/test_utils/** or tests/test_types/**, nor new D3 files under tests/fixtures/**. Fix the file enumeration in <ID>/packet.py, e.g. use `git ls-files --others --exclude-standard` plus the diff, or rglob with fnmatch.
- **REFUTED** — Product-arm control: `grep -c __DEVLYN_SKILL_DIR__ <cell>/home/.codex/skills/devlyn:resolve/SKILL.md` = 0
  - bin/devlyn.js:438-446 deliberately stamps only the assignment default. The guard literal on config/skills/devlyn:resolve/SKILL.md:35 (`= "__DEVLYN_SKILL_DIR__"`) stays by design, so a correct install yields count 1. Check instead that `${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}` is absent and that line 34 names /home/participant/.codex/skills/devlyn:resolve.
- **CORRECTED** — .devlyn/ is ignored, so caller.json and goal.txt keep the tree clean; `git status --porcelain --untracked-files=all` is empty and allocate returns ALLOCATED (both E-claude and E-codex)
  - Only installClaudeCore adds '.devlyn/' to .gitignore (bin/devlyn.js:819-834). `agents codex` (installAgentsForCLI :721-728) writes only AGENTS.md and ~/.codex/skills. Neither upstream .gitignore lists .devlyn. So for E-codex, .devlyn/caller.json and goal.txt are untracked, and task-complete.py:194 rejects allocation. Fix: write .devlyn/ to .git/info/exclude for every arm, or commit an ignore line in the baseline, and record it as harness setup.
- **CORRECTED** — caller.json gains 'base_sha'; packet.py diffs against caller['base_sha']; for E 'Commit the install output as the baseline'
  - caller.json is written at prepare time (0211/prepare.py:39), before the E install and commit. If base_sha is the task base (ba6d13d/3cbaa76), then `git diff base_sha` for E includes the whole installed .claude/, CLAUDE.md and .gitignore. That floods the review packet and unblinds assessment (0206 PROTOCOL:133-134). The base must be the post-install baseline commit, so the ordering (caller write vs install commit) and the RO caller mount need respecifying.
- **CORRECTED** — (6) cell ~/.claude/settings.json model = claude-opus-5-5 pins the pair judge, which omits --model per adapters/claude.md:36-37
  - The omit-model text is at adapters/claude.md:34-35, not :36-37. More importantly, the judge argv (:25-30) passes `--setting-sources project`, so user-level ~/.claude/settings.json is NOT loaded and a model set there is ignored. Pin it in project .claude/settings.json (part of the committed baseline) or via ANTHROPIC_MODEL in the cell env, and record which.
- **CORRECTED** — cell.py: keep :66-116 and :187-211; delete :120-122, :125-126, :129-146, :150-151, :157-159, :164-172, :186
  - The deletion list is incomplete. :147-148 still raises on nonzero exit, which contradicts EXITED_NONZERO as a recorded status. :152-156 still raises 'missing owner telemetry' when no thread.started exists, which is always the case for Claude owners. :160-163 calls meter.finish on a None meter (AttributeError is not in the :184 except tuple) and calls reviews(), which carries the 240s TimeoutError (:32-39) and the fable-5-1-only identity check (:44-46). :224 returns 1 on any failure. Deleting :120-122 removes the only wall check, so a replacement hang-wall must be written, not just deleted. Keeping :66-116 unchanged also rejects the new Claude-owner credential mount (/home/participant/.claude/.credentials.json), because :72-80 and :104-108 have fixed mount sets.
- **CORRECTED** — Identity record: Codex turn_context model/effort per :173-183 → MATCH/MISMATCH
  - :173-183 checks EVERY rollout under home/.codex/sessions against one (model, effort). For E-codex, resolve children run with `-c model_reasoning_effort=xhigh` (codex-config.md:81). For E-claude and Claude-owner cells, the Codex pair judge and reviewer sessions share that CODEX_HOME. Every such cell would read MISMATCH. Scope the identity check to the owner root (and its native children) or record it per session.
- **CORRECTED** — review.py: merge 0217/review.py:5 with 0210/review.py:14-17 and :20-51; delete :18-19, :45, :52-53
  - 0210/review.py:54-63 is neither kept nor deleted. It holds the result parse, the fable-5-1-only identity check (:56-58), the tool_use check and the answer.txt write plus print that returns the review to the owner. Without it the owner gets no review text. The identity check must become route-driven. :11-13 must import <ID>/packet.py.
- **CORRECTED** — codex.toml template: keep :1,:3,:7,:11-14,:18-24,:38-39; delete :2,:6,:15-16,:26-36
  - The lists skip :4 approval_policy, :5 sandbox_mode, :8-9 [sandbox_workspace_write] network_access, :10 [features] header (without it :11-14 become top-level keys) and :17 shell_snapshot. Also, deleting :15-16 re-enables codex system skills seeded in the cell home. The archived 01-D1-1-A/home/.codex/skills/.system includes review-agent, which contradicts 'A receives only the task frame: no review tool'. Record this as an explicit arm decision.
- **CORRECTED** — record_usage: native_accounting.Rollouts(dir, root, math.inf, math.inf, math.inf, stale=math.inf).finish()
  - 0208/accounting.py:20-21: after (root, owner) all parameters are keyword-only and `started` is required: input_limit=, output_limit=, dispatch_limit=, stale_seconds=, started=. As written the call raises TypeError. For the Claude transcript sum, the owner's own session in ~/.claude/projects must be excluded, or it double-counts with result.modelUsage.
- **CORRECTED** — DESIGN.md supersedes 0206 PROTOCOL :58-67, :77-120 and 0210 AMENDMENT :18-21, :26-36, :37-41, :47-57; everything else in 0206 stays
  - Other retained clauses contradict v2. 0206 PROTOCOL: :45 'No new resolve invocation in any arm' (arm E); :52-56 astra-only owner, fable-5-1 240s reviewer, 'No Grok substitution'; :69-75 no access to 'installed devlyn instructions' (arm E); :79-81 24 cells, D1-D4 order; :131-132 BUDGET_EXCEEDED category; :138-171 advancement gates requiring both D1 A/B pairs COMPLETE (unsatisfiable without D1); :188 'not permission to grow a new scheduler' (screen.sh); :192 'make unavailable accounting block dispatch'. 0210 AMENDMENT: :15-17 (same tasks/arms/models, byte-identical 0204 candidate, 'No resolve') and :59-67 ('No new scheduler', equal Fable capabilities). Also register the NORTH-STAR:216 dominance-rule adjustment named in 0221 Track 3.
- **CORRECTED** — tasks.json v2 = 0206/tasks.json:84-167 minus budget fields; dry materialization for every registered cell (N)
  - prepare needs registration['cells'][index] (0211/prepare.py:18-20), as well as candidate/candidate_sha256 for B. The packet copies only the task objects and never defines the v2 cell list: arms A/C/B′/E x routes x reps and order. N in the acceptance loop is undefined. The cell registry must be specified in tasks.json or DESIGN.md.
- **CORRECTED** — Acceptance: `! grep -rnE 'BUDGET_EXCEEDED|...|yield_time_ms|cache-inclusive|...' autoresearch/experiments/<ID> --include='*.py' ...`
  - test_apparatus.py lives in <ID>. Its specified cases ('classes without BUDGET_EXCEEDED', prompt vocabulary absence) must contain these literals, so the check self-matches and fails. Exclude test_*.py or keep banned-word lists in a non-matching form.
- **CORRECTED** — resolve took 840-2263 s per hard task on the host (0185/0187/0191/0192)
  - Per-draw figures: 0191 840/1021, 0192 907/952, 0185 1379/1609. 2262.774 is the 0187 two-draw TOTAL (iterations/0187:72-79 'Total seconds'), about 1131 per draw. The range is 840-1609 s, and all were --no-pair solo; E with shipped pair defaults will run longer. The 5400 s wall recommendation still holds.
- **CORRECTED** — 0187 numeric requirement interpretation contested at iterations/0187:109-113
  - Lines :104-114 are the recursion-depth probe. The large-integer interpretation is at :99-101 and :116-125.
- **CORRECTED** — 0185/launch.py:48-123 recipe 'already proved' for E inside the same container
  - Proved host-side on macOS only (danger-full-access, seatbelt). Nested codex `-s workspace-write` sandboxes inside the Linux container (cap-drop ALL, no-new-privileges, pids 256) are unproved. The model-free install control does not exercise them. Add a model-free in-container nested-sandbox probe before the E smoke.

## Missed references found by the verifier

- Untracked control-dir build: runtime.json 'control' = .git/devlyn-completion/2b2a1f33c77c60fb546b9035/scratch/control (126 files: run-bounded.py, platform-support.py, review.py, review-0210.py, usage.py, prompt.txt, less/, prettier/, ruff, python/ (click wheel metadata), autoresearch/experiments/{0205,0208,0210,0211} copies). No tracked recipe exists (git grep review-0210 only hits 0217 docs). The packet edits this 'control build' in four items but never adds a tracked build step to <ID>.
- autoresearch/experiments/0210/native_cell.py:147-148, :152-156, :160-163, :224 (still fail-closed; missing from the cell.py delete list)
- autoresearch/experiments/0210/review.py:54-63 (answer/identity/tool_use; missing from the review.py keep/delete map) and :11-13 (packet import path)
- autoresearch/experiments/0211/codex.toml:4, :5, :8-10, :17 (missing from both keep and delete lists); :15-16 deletion exposes codex system skills incl. review-agent (archived home/.codex/skills/.system/review-agent)
- autoresearch/experiments/0211/check_cell.py:28 digests home/.codex/config.toml (absent for Claude owners) and :24-25 raises 'stop screen' on any owner failure class; both need v2 treatment
- autoresearch/experiments/0211/packet.py:65-66 runs in-container on Python 3.12, where glob('dir/**') returns no files, so new owner test files under '**' patterns are missing from review packets
- autoresearch/experiments/0206/PROTOCOL.md:45, :52-56, :69-75, :79-81, :131-132, :138-171, :188, :192 (conflict with v2 and missing from the supersession list)
- autoresearch/experiments/0210/AMENDMENT.md:15-17 and :59-67 (conflict with v2 and missing from the supersession list)
- autoresearch/experiments/0210/Dockerfile:7 ENV PATH is lost under login bash (/etc/profile). v2 Dockerfile must also expose /opt/codex/bin and /opt/codex/codex-path (rg) on the login PATH, not just add less
- Click pyproject.toml:83-87 filterwarnings=['error'] plus a read-only evaluator mount makes pytest exit 1 (PytestCacheWarning); needs PYTEST_ADDOPTS='-p no:cacheprovider' for owner and evaluator
- .devlyn/0218-screen/0218-screen-20260924/07-D2-1-A/work/.pytest_cache shows owners create cache files that the kept scope logic (0211/check_cell.py:30-36) would flag as violations
- bin/devlyn.js:438-446 plus config/skills/devlyn:resolve/SKILL.md:35: the sentinel guard literal is preserved by design (invalidates the grep=0 control)
- bin/devlyn.js:721-728 (agents codex adds no .gitignore) and task-complete.py:194: E-codex needs .git/info/exclude for .devlyn/
- config/skills/_shared/adapters/claude.md:25-30 `--setting-sources project`: the pair-judge model cannot be pinned via ~/.claude/settings.json
- autoresearch/experiments/0208/accounting.py:20-21 keyword-only Rollouts signature (started= required)
- autoresearch/HANDOFF.md:3 'Root direct, no resolve invocation' and :71 'No new resolve in any arm' (the :71 line is inside the replaced range; :3 should be reconciled with arm E wording)
- ~/.local/share/nx01/0221-direction-design/FINAL-design.md §4 Track 3 and §6.1: the lift rationale and the NORTH-STAR:216 dominance-rule adjustment should be cited in DESIGN.md
- Local reproducibility input already present: .git/devlyn-completion/2b2a1f33c77c60fb546b9035/scratch/apt/less_668-1_arm64.deb, plus ruff-0.15.9 aarch64 wheel only under .git/devlyn-completion/ceadb841f5abc39b3601b0b1/scratch/ (not every scratch dir, as the dependency implies)

## Acceptance checks the verifier could not run as written

- docker build -f <ID>/Dockerfile <pinned-context> && docker run ... bash -lc '... codex --version ...' — pinned artifacts (node linux-arm64, codex vendor, claude binary) are absent locally and need network plus the not-yet-written BUILD.md. Even when built, `codex --version` fails under bash -lc by construction (verified PATH reset) unless the Dockerfile symlinks codex onto the login PATH.
- APPARATUS_IMAGE=<v2 image id> container unit cases — need the v2 image, which cannot be built yet (above).
- calibrate.py --tasks D3,D4 --repeat 5 (15x5 all expected) — the D4 baseline/reference public suite fails by construction on a read-only mount (Click filterwarnings=error plus PytestCacheWarning, reproduced rc=1) unless -p no:cacheprovider is added.
- Product-arm install control `grep -c __DEVLYN_SKILL_DIR__ ... = 0` — fails by construction; the guard literal on SKILL.md:35 is preserved by bin/devlyn.js:438-446.
- Product-arm install control `git status --porcelain --untracked-files=all` empty / allocate ALLOCATED for E-codex — fails because `agents codex` never ignores .devlyn/ (caller.json and goal.txt untracked).
- Dry-cell loop `for i in $(seq 0 $((N-1)))` — N and the v2 cell registry are undefined in the packet.
- `! grep -rnE 'BUDGET_EXCEEDED|...'` over <ID> *.py — self-matches the required test_apparatus.py literals unless tests are excluded.
- Route smoke (SMOKE.md rows) — model calls, gated by design; not runnable read-only.
- `gh pr view --json autoMergeRequest -q .autoMergeRequest` prints null — unverified output form for a null field; `-q '.autoMergeRequest == null'` → true is unambiguous.
