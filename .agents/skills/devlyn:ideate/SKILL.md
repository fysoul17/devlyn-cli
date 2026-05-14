---
name: devlyn:ideate
description: Extract a verifiable spec from a user's idea by driving the conversation with focused questions. Output is a single-feature `spec.md` + `spec.expected.json` that `/devlyn:resolve --spec` consumes directly. Use when the user has an idea but not a spec, or wants AI to elicit the missing engineering context. Modes — default (single spec, AI drives Q&A), `--quick` (assume-and-confirm from one-line goal), `--from-spec <path>` (normalize external spec), `--project` (plan.md index + N specs). Optional in the pipeline — `/devlyn:resolve` works standalone via free-form mode for users who skip ideate.
---

Spec-elicitation surface for users who have ideas but not engineering specifications. AI drives the conversation with focused questions until a structurally-valid, verifiable spec exists. Output consumed directly by `/devlyn:resolve --spec`.

<elicit_config>
$ARGUMENTS
</elicit_config>

<orchestrator_context>
This skill is OPTIONAL. `/devlyn:resolve` is standalone-capable: free-form mode handles trivial/medium tasks without a spec, `--spec` mode accepts handwritten specs from any source. Use ideate when the user wants AI to do the elicitation work.
</orchestrator_context>

<elicitation_contract>
The user does not know context engineering. They will under-specify and over-assume. AI's job is to ask focused, specific questions that surface the missing engineering decisions.

1. Ask one or two questions per turn, not more. Multi-question lists overwhelm and produce shallow answers.
2. Questions are concrete and decision-grade — what is the input, what is the expected output, what command verifies success, what files are out of scope.
3. Do not ask design preferences the user clearly does not have. Infer the simplest reasonable default and confirm in one line.
4. Stop when the spec passes structural lint AND the user explicitly confirms or 8 turns have elapsed (whichever comes first). Eight turns is a hard ceiling — beyond that, the spec is either ready or the task is too large for ideate.
5. The output is the spec, not a transcript. Do not include the conversation in the saved files.
</elicitation_contract>

<harness_principles>
Read `_shared/runtime-principles.md` (Subtractive-first / Goal-locked / No-workaround / Evidence). The principles bind the spec content as well as your conversation. A spec that says "for future flexibility" is a Subtractive-first violation. A spec that asks for `try { ... } catch { return null }` is a No-workaround violation. AI flags these in elicitation, not after `/devlyn:resolve` has built them.
</harness_principles>

<engine_routing>
Default engine: Claude. The per-engine adapter from `_shared/adapters/<model>.md` is prepended to the elicitation prompt so the model honors its own official prompt-engineering guidance during the Q&A.
</engine_routing>

<modes>
Four modes, selected by flag:

1. **Default** (no flag) — single-spec elicitation. AI asks questions in-conversation until lint passes. Output: `<spec-dir>/<id>-<slug>/spec.md` + `<spec-dir>/<id>-<slug>/spec.expected.json`. Default spec dir: `docs/specs/` (configurable via `--spec-dir <path>`).
2. **`--quick`** — one-line goal, AI synthesizes a spec with explicit assumptions block, asks the user to confirm or correct in a single turn. Use when the user wants speed over thoroughness.
3. **`--from-spec <path>`** — external spec exists. AI lints it for the canonical structure, normalizes section names, generates a missing `spec.expected.json` if absent, fixes minor schema issues, and stops. Does NOT reshape Requirements / Out-of-Scope content; structural changes only.
4. **`--project`** — multi-feature project. AI elicits a project description, decomposes it into 3-7 feature specs, writes `<spec-dir>/plan.md` (the index) and one `<spec-dir>/<id>/spec.md` + `<spec-dir>/<id>/spec.expected.json` per feature. See `references/project-mode.md`.

`--spec-dir <path>` overrides the default output directory. `--engine <model>` selects the adapter.
</modes>

<spec_kind_escape_hatch>
The spec carries `spec.kind ∈ {feature, spike, prototype}` in its frontmatter. The kind changes downstream behavior:

- **feature** — production-quality implementation expected. `/devlyn:resolve --spec` runs the full pipeline (PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY).
- **spike** — exploratory work; deliverable is learning, evidence, or a disposable demo. `/devlyn:resolve --spec` proceeds but VERIFY's quality bar is relaxed for code that the spike says is throwaway.
- **prototype** — between feature and spike. Production-shape but not production-grade. CLEANUP runs; VERIFY's quality bar is stricter than spike, looser than feature.

The user picks the kind during elicitation. Default = feature when not specified. `--quick` infers from the goal text (verbs like "explore", "investigate", "spike" → spike; "implement", "ship", "add" → feature).
</spec_kind_escape_hatch>

## PHASE 0: PARSE + ROUTE

1. Parse flags from `<elicit_config>`:
   - `--quick`
   - `--from-spec <path>`
   - `--project`
   - `--spec-dir <path>` (default `docs/specs/`)
   - `--engine MODE` (default `claude`)
   - `--spec-id <id>` — optional explicit id; auto-generated when absent.

2. Engine pre-flight: `_shared/engine-preflight.md`.

3. Mode dispatch:
   - default → PHASE 1.
   - `--quick` → PHASE 1Q (single turn assume-and-confirm).
   - `--from-spec` → PHASE 1F (lint + normalize external).
   - `--project` → PHASE 1P (project decomposition).

## PHASE 1: ELICITATION (default mode)

Prompt body: `references/elicitation.md`. Adapter prepended.

The elicitation agent:
1. Reads the user's initial goal from `<elicit_config>`.
2. Identifies the missing engineering decisions (input shape, output shape, success command, scope boundary, constraints).
3. Asks 1-2 focused questions per turn until each blank is filled or the user accepts an inferred default.
4. Maintains a running draft spec in `.devlyn/ideate-draft.md` (run-scoped, gitignored).
5. Stops when the structural lint passes AND user confirms, or 8 turns elapsed.

Structural lint (inline check, no script needed):
- Frontmatter has `id`, `title`, `kind`, `status: planned`, `complexity`.
- `## Context` non-empty (≥ 1 sentence).
- `## Requirements` has ≥ 1 `- [ ]` bullet.
- `## Out of Scope` present (may list "none" if truly nothing).
- `## Verification` has either ≥ 1 named command OR an explicit "all Requirements are pure-design" note.

After lint passes:
1. Write `<spec-dir>/<id>-<slug>/spec.md` (the spec).
2. Generate `<spec-dir>/<id>-<slug>/spec.expected.json` from the spec's `## Verification` block + any `forbidden_patterns` / `required_files` / `forbidden_files` / `max_deps_added` the conversation surfaced.
3. Run `python3 .claude/skills/_shared/spec-verify-check.py --check <spec-path>` to validate the verification carrier shape, supported `complexity` frontmatter, and any present actionable solo-headroom hypothesis; if the spec uses a legacy inline `## Verification` JSON carrier, any solo-headroom hypothesis command must match that carrier's `verification_commands[].cmd`. If exit 2, fix the carrier/frontmatter/hypothesis and re-run.
4. Run `python3 .claude/skills/_shared/spec-verify-check.py --check-expected <expected-path>` to validate sibling `spec.expected.json` against `_shared/expected.schema.json` plus sibling spec `complexity` frontmatter and any present actionable solo-headroom hypothesis; if the spec has a solo-headroom hypothesis, its observable command must match `spec.expected.json.verification_commands[].cmd`. If exit 2, fix the JSON/frontmatter/hypothesis and re-run.
5. Print: `spec ready — /devlyn:resolve --spec <spec-path>`.

## PHASE 1Q: QUICK MODE

Single-turn assume-and-confirm. Prompt body: see `references/elicitation.md` § "Quick mode".

1. AI synthesizes a spec from the one-line goal.
2. AI surfaces an explicit "Assumptions made" section listing every inferred decision.
3. User responds with "go" / "fix X" / "no, different".
4. On "go": write spec + spec.expected.json + lint + announce.
5. On "fix X": apply correction, re-show, ask again. Maximum 3 correction rounds before escalating to default mode.
6. Exception: for benchmark, risk-probe, or pair-evidence goals, do not infer a solo-headroom hypothesis. Ask for the actionable hypothesis first; if unavailable, exit with `spec not ready — solo-headroom hypothesis required`. For new unmeasured benchmark, shadow-fixture, golden-fixture, risk-probe, or pair-evidence candidates, also do not infer solo ceiling avoidance; ask for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`, and exit with `spec not ready — solo ceiling avoidance required` if unavailable.

## PHASE 1F: FROM-SPEC MODE

Prompt body: `references/from-spec-mode.md`.

1. Read the external spec at `<path>`.
2. Lint structure (same checks as default mode).
3. Identify missing pieces (no frontmatter, missing sections, malformed Verification block).
4. Apply structural fixes only — do NOT reshape Requirements / Out-of-Scope content. The user's substantive intent is preserved.
5. Generate `spec.expected.json` if absent (best-effort from `## Verification` block).
6. Write the normalized spec back to `<spec-dir>/<id>-<slug>/` (preserves original at `<path>` untouched unless user passes `--in-place`).
7. Run both lint checks: `--check <spec-path>` and `--check-expected <expected-path>`.
8. Lint pass → announce. Lint fail → surface the unfixable issue and exit non-zero. If the source is a pair-evidence candidate without an actionable solo-headroom hypothesis, the announcement must say `pair-evidence not ready` instead of implying measurement readiness.

## PHASE 1P: PROJECT MODE

Prompt body: `references/project-mode.md`.

1. AI elicits a project description (longer Q&A — multi-feature scope warrants more turns).
2. AI decomposes the project into 3-7 feature specs. Each feature is independently shippable; cross-feature dependencies surface explicitly in the spec frontmatter `depends_on:` field.
3. AI writes `<spec-dir>/plan.md` — index file with: project name, decomposition rationale, list of feature specs with id + title + dependency, suggested implementation order.
4. AI writes one `<spec-dir>/<id>/spec.md` + `<spec-dir>/<id>/spec.expected.json` per feature, each lint-validated.
5. Announce: `project ready — N specs at <spec-dir>/. Start with /devlyn:resolve --spec <first-spec-path>`.

`/devlyn:resolve` consumes one spec at a time; the user works through `plan.md`'s suggested order. Multi-feature parallel runs are Mission 2 work.

## State management

ideate is conversational, not pipeline-staged. State lives in:
- `.devlyn/ideate-draft.md` — current draft spec during elicitation (run-scoped, gitignored).
- `<spec-dir>/<id>-<slug>/` — final output (committed to repo by user choice).

No `pipeline.state.json` here — that's resolve's surface.
