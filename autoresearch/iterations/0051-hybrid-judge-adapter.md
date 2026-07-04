# iter-0051 — ollama local-backend adapter, JUDGE-ONLY role

**Status**: SHIPPED. First local/hybrid-LLM engine adapter (Gemma-class,
Ollama-hosted) wired into the role-resolution contract as a judge-only
backend. 2-round Codex convergence before implementation. Live end-to-end
VERIFY pair-judge invocation through the real adapter path, plus both
fail-closed negatives, verified on this machine.

**Trigger**: user direction — prove the hybrid-LLM (Gemma/GLM-class) engine
direction end-to-end, not just recommend it. iter-0050's engine doctor
already had placeholder `ollama`/`vllm` rows with "no `--engine` route yet
(tracked: iter-0051)".

## Design (2-round Codex convergence, `model_reasoning_effort=high` then
`medium`, read-only sandbox, `CODEX_MONITORED_ISOLATED=1`)

**Key insight, verified against `verify.md`'s pair-mode contract before
implementing**: a completion-only local model has no tools and no file
access — it cannot be the executor (IMPLEMENT/CLEANUP need file edits) but
is structurally exactly right for VERIFY pair-JUDGE, whose entire contract
is prompt-in (diff + contract) → findings-JSONL-out, read-only by design.
This makes the adapter **judge-only by construction**, not a policy choice.

**Round 1** (108s, high effort): converged on 4 named deltas, all adopted:
1. Adapter shape: adapter declares concrete backend metadata (fixed-field
   `Invocation` block); `engine-preflight.md`/the invoker owns the generic
   semantics — do not duplicate URL/timeout/parsing prose across files.
2. Judge-only enforcement: `## Role eligibility` must be a structured marker
   with fixed ASCII fields (`executor: no`, `pair_judge: yes`), not English
   prose — consistent with iter-0049's move away from prose-inferred
   decisions toward explicit, mechanically-validated declarations. Absent
   section = eligible for both roles (zero change for claude/codex/omp).
3. `engine-doctor.sh`: add a `role` column (option **a**) rather than
   overloading `pin_eligible`; require `server=yes && adapter=yes` for
   local-backend eligibility (not `binary=yes`) — the HTTP server, not the
   CLI binary, is ollama's real invocation surface.
4. Model: `gemma3:4b` (3.3GB) is a defensible default under the 8GB cap;
   `gemma3:12b` is already 8.1GB and over cap. Named fallback if the smoke
   test failed: `qwen2.5:3b` (Ollama calls out its JSON/structured-output
   strength explicitly) — not needed, see Model choice below.

**Round 2** (medium effort, ~3 min): one empirical finding from this
session's smoke test fed back for sign-off — raw JSONL-text prompting
produced a markdown-fenced, format-drifted response, while Ollama's
schema-constrained `format` field produced a clean single JSON object
matching the schema exactly. Codex signed off: *"JSONL is a transport/
storage format, not something the model should be trusted to free-form...
Test 2 moves formatting from model behavior into constrained decoding plus
deterministic serialization."* Final invocation shape: the model returns one
schema-constrained JSON object (`{"findings":[...]}`); the orchestrator
`json.loads`s it and mechanically writes one JSONL line per array element —
empty array means PASS, matching the existing Codex pair-judge empty-file
convention.

## Install (this machine, verified)

- `brew install ollama` → 0.31.1, plus deps (sqlite, python@3.14, mlx,
  mlx-c) — reversible, logged here as the assumption for user review.
- `ollama serve` backgrounded; `curl localhost:11434/api/version` → 200.
- `ollama pull gemma3:4b` → 3.3GB (`ollama list`: `a2af6cc3eb7f`, 3.3 GB).
  `du -sh ~/.ollama` → 3.1G. Well under the 8GB cap; `vllm` stays
  recommend-only (heavy env, no route) per scope.
- Smoke test (`curl` direct to `/api/generate`, no adapter/skill code
  involved yet): unconstrained JSONL prompt → markdown-fenced single object
  (fragile). Schema-constrained `format` → clean `{"findings":[...]}`,
  parses directly. This result is what drove the round-2 design question
  above; `gemma3:4b` needed no fallback.

## Shipped shape

- **New**: `_shared/adapters/ollama.md` — Identity (completion-only, no
  tools, judge-only), `## Role eligibility` (`executor: no` / `pair_judge:
  yes`), `## Invocation` (HTTP request shape incl. the findings-array JSON
  schema, adapter-declared availability probe, timeout), Output discipline
  (Gemma has no system role per its official prompt-structure guide — fold
  everything into `prompt`), Anti-patterns (don't trust free-form JSONL;
  don't treat this as an agentic probe-runner — the orchestrator must
  pre-select diff hunks/excerpts into the prompt since the model can't read
  files itself).
- **`_shared/adapters/README.md`**: documents the two new optional sections
  (`Role eligibility`, `Invocation`) as the general contract for role-scoped
  and non-agentic adapters — the plug-in point future local backends
  (vLLM, GLM) reuse without further skill changes.
- **`_shared/engine-preflight.md`**: role resolution now requires
  role-eligibility (not just adapter-file presence) for both executor and
  pair-judge selection; the fail-closed validation sentence gains "or an
  adapter that declares itself ineligible for the requested role" — same
  `BLOCKED:invalid-engine-config` token, no new verdict invented. New
  paragraph documents the `## Role eligibility` contract and its default.
- **`devlyn:engines/SKILL.md`**: `executor <name>` now also refuses adapters
  declaring `executor: no`; `pair <name>` symmetrically refuses `pair_judge:
  no`; step 3's "Available engines" sourcing is now role-scoped (executor
  rows need `role` to include `executor`; pair-judge rows — cli-engine or
  local-backend — need `role` to include `judge`), closing a real gap where
  a judge-only local backend would otherwise have been misreported as
  executor-available.
- **`devlyn:resolve/SKILL.md`** (PHASE 0 engine pre-flight, one line): same
  role-ineligibility clause added to the inline restatement of
  engine-preflight.md's rule, so a stale duplicate copy can't silently miss
  the new gate.
- **`engine-doctor.sh`**: new `check_role()` — greps the adapter's
  `## Role eligibility` fixed fields (`n/a` if no adapter file exists);
  new `role` column in the printed table; `pin_eligible` for `local-backend`
  kind now requires `server=yes` (not `binary=yes`); ollama's note branch
  rewritten from the iter-0050 placeholder ("no --engine route yet") to
  report the live judge-only route or an actionable "server down, start it"
  message. `vllm` (still adapter-less) keeps the old placeholder note
  automatically — no special-casing needed.
- **Mirrors**: `.agents/skills/` and `.claude/skills/` byte-identical to
  `config/skills/` for every touched/added file (verified via `diff -q`).
  Not added to `lint-skills.sh`'s `critical_path_files` manifest — that
  manifest already excludes `engine-doctor.sh` and `devlyn:engines/SKILL.md`
  from iter-0050 (a documented pre-existing gap, not this iteration's scope
  to fix); `ollama.md` follows the same precedent rather than silently
  expanding a different iteration's manifest.

## Live verification (this machine)

1. **`engine-doctor.sh` catalog, server up**: `ollama` row —
   `binary=yes server=yes adapter=yes role=judge-only pin_eligible=yes`,
   note *"judge-only route live (pair_judge_priority); server reachable"*.
   `vllm` unchanged (`adapter=no`, old placeholder note). Pair-judge
   diversity count stays 3 (cli-engine only, unaffected by design).
2. **Fail-closed negative 1 — server down**: `pkill ollama serve`; doctor
   row flips to `server=no pin_eligible=no`, note *"binary present, server
   down — start it..."*. Availability-probe curl directly:
   `curl -fsS ... /api/version` → exit 7 (`Couldn't connect`), the same
   non-zero signal `BLOCKED:ollama-unavailable` keys off — not a silent
   skip.
3. **Fail-closed negative 2 — executor pin refused**: headless
   `claude -p --model sonnet --permission-mode bypassPermissions
   "/devlyn:engines executor ollama"` → refused, citing
   `.claude/skills/_shared/adapters/ollama.md:11`'s `executor: no`, listed
   valid names (`claude`, `codex`, `omp`), suggested the pair route, and
   confirmed `.devlyn/engines.json` was not written (file absent
   afterward).
4. **Pair pin accepted**: `/devlyn:engines pair ollama` (server back up) →
   pin written (`{"pair_judge_priority": ["ollama"]}`), resolved role table
   showed `pair judge: ollama (pin) — ... ollama ✓ (judge-only)`, executor
   row unaffected (`claude`, still lists only `claude ✓ codex ✓`).
5. **No-arg `/devlyn:engines`**: role table and detection table both
   correct with the pin live; usage lines correctly state `ollama` is
   pair-only and will be refused as executor.
6. **Real end-to-end VERIFY pair-judge invocation** (not a mock): built a
   diff introducing a real fail-open bug (`rate_limiter.py` catches
   `redis.ConnectionError` and returns `True` instead of rejecting) plus a
   one-line contract stating the fail-closed requirement. Constructed the
   bounded prompt exactly per the adapter's `Invocation` contract (contract
   + diff folded into `prompt`, no `system` field), sent via
   `curl -fsS .../api/version` (probe, 2xx) then
   `curl .../api/generate` with the findings-array `format` schema.
   Response: single clean JSON object, `json.loads` succeeded directly, one
   `CRITICAL` finding correctly identifying the exact fail-open line.
   Mechanically wrote it to a `.devlyn/verify.pair.findings.jsonl`-shaped
   file (one line per array element) — the real target-file shape, not a
   simulated one. Judge-**quality** (would a harder or adversarial diff also
   be caught) is explicitly out of scope for this iteration — a future
   probe-panel arm's job; this iteration proves the plumbing, and the one
   real sample above happened to be correct as a bonus, not a claim.
7. **Cleanup**: cleared the test pair-pin (`/devlyn:engines clear` →
   `.devlyn/engines.json` deleted, confirmed absent) so the machine is back
   at default auto-detection; left the ollama server running (the shipped
   capability should actually be usable going forward, not left stopped).
8. **`bash scripts/lint-skills.sh`**: all checks pass (`All checks passed.`
   final line; zero `✗`).

## Principles check

- **#1 No workaround**: judge-only ineligibility reuses the existing
  `BLOCKED:invalid-engine-config` token; server-down reuses the existing
  `BLOCKED:<engine>-unavailable` class via the same adapter-declared-probe
  hook `engine-preflight.md` already had. No new verdict token invented.
- **#2 No overengineering**: no new skill, no new subcommand, no wrapper
  script for ollama (unlike Codex's `codex-monitored.sh`) — a completion-only
  HTTP backend doesn't need one; the adapter's fixed-field `Invocation`
  block is the whole contract.
- **#3 No guesswork**: model size/cap verified via `ollama list` + `du -sh`,
  not vendor claims; JSON-schema-vs-raw-JSONL reliability verified via two
  real smoke-test runs, not assumed; official Gemma prompt-structure guide
  fetched and quoted (`ai.google.dev/gemma/docs/core/prompt-structure`) for
  the no-system-role citation the adapters/README standing rule requires.
- **#4 Worldclass / #7 Production ready**: both fail-closed paths
  (executor-pin refusal, server-down) were exercised live against the real
  installed skill, not just diffed; the end-to-end judge invocation ran
  against a real diff with a real bug, not a synthetic pass-through.
- **Goal-locked**: did not touch `bin/devlyn.js`, `benchmark/probes/**`
  (iter-0052), or `verify.md`/`verify-merge-findings.py` (iter-0053) —
  read `verify.md`'s pair-mode section only to confirm the judge-only
  design premise, per the coordination boundary in this iteration's brief.
  `vllm` left exactly as iter-0050 shipped it (recommend-only, no adapter).
  Judge-quality is explicitly flagged out of scope rather than silently
  assessed or claimed.

## Artifacts

- New: `config/skills/_shared/adapters/ollama.md` (+ byte-identical mirrors
  in `.agents/skills/` and `.claude/skills/`).
- Changed: `_shared/adapters/README.md`, `_shared/engine-preflight.md`,
  `_shared/engine-doctor.sh`, `devlyn:engines/SKILL.md`,
  `devlyn:resolve/SKILL.md` (+ same mirrors).
- Codex design transcripts: this file summarizes both rounds; raw stdout at
  session scratch paths `codex-r1.stdout.log` / `codex-r2.stdout.log`
  (not archived — reproducible via the same `codex-monitored.sh -s
  read-only -c model_reasoning_effort=high|medium
  CODEX_MONITORED_ISOLATED=1` invocation shape documented in
  `_shared/codex-config.md`).
- End-to-end judge sample: bug-diff/contract/prompt/response artifacts were
  session-scratch files, not committed (ephemeral verification evidence,
  reproducible from the shapes described in step 6 above).
