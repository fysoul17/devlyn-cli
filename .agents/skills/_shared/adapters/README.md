# Per-engine prompt adapters

This folder is the LLM-specific delta layer. The harness's canonical phase prompts (in each skill's `references/phases/<phase>.md`) stay model-neutral and outcome-first. Each adapter file in this folder is a **small delta header** that gets injected BEFORE the canonical body when the phase runs against that specific engine.

## Why adapters exist

Anthropic and OpenAI publish official prompt-engineering guides for their flagship models. The two guides converge on outcome-first + decision rules + mechanical validation but **diverge on tactics** (XML structure vs stop-rules format, literal interpretation vs decision-rule phrasing, self-check pattern vs validation-tool primacy). A single canonical prompt can't hit both ceilings.

The split:
- **Canonical body** (in `<skill>/references/phases/`) = the contract: goal, output format, invariants, common-ground rules from both guides.
- **Adapter header** (here) = the per-engine elaboration: model-specific guidance from that engine's official guide.

This is also the load-bearing piece for **multi-LLM evolution**. When Qwen / Gemini / Gemma are added (Mission 2/3), each gets its own adapter file here. The canonical body never moves.

## Format

Each adapter is a single markdown file named `<model-id>.md` (e.g. `opus-4-7.md`, `gpt-5-5.md`). Structure:

```markdown
# <Model name> adapter

> Source: <official-prompt-engineering-guide URL>

## Identity
1-2 lines telling the model who it is + which guide governs.

## Output discipline
Verbosity, formatting, length conventions specific to this model.

## Tool-use posture
When to use tools, when to reason, parallel/sequential preferences.

## Effort and autonomy
Optional. Model-specific guidance for effort levels or autonomous-vs-interactive runs when the vendor guide calls this out.

## Validation pattern
How this model verifies its work — mechanical-first vs self-check, etc.

## Anti-patterns
Specific patterns the official guide warns about for this model.
```

Keep each section to ≤ 8 lines. Adapters are deltas, not full prompts. If an adapter grows past ~80 lines, the content probably belongs in canonical body.

## When to add a new adapter

A new adapter file ships when:
1. A new LLM is integrated into the pipeline (the engine is now invocable).
2. An official prompt-engineering guide for that LLM exists (or a vendor-recommended pattern set).
3. An empirical A/B shows the adapter's specific guidance lifts that model's performance over the canonical body alone.

Not all models need adapters. If a model performs well on the canonical body without delta, ship without one.

## What NOT to put here

- ❌ Universal rules (those go in canonical body or `_shared/runtime-principles.md`).
- ❌ Iter-history annotations (`*(iter-0020: F4 evidence...)*` style).
- ❌ Full phase prompts (defeats the decoupling).
- ❌ Per-task or per-spec content (adapters are model-scope, not task-scope).

## Runtime injection

A skill's phase invocation prepends the resolved engine's adapter file to the canonical body before sending. Mechanism is left to each skill (a `_shared/adapter-inject.sh` helper may land in a later iter); for now, skills consume the adapter file by direct read at phase-spawn time.

## Standing rule

Any iter that touches an adapter file MUST cite the corresponding official guide as part of acceptance: "guide section X.Y says Z, this change applies Z." Generic preferences ("feels cleaner") are rejected.
