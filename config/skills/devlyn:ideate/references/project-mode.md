# `--project` mode

Per-engine adapter prepended at runtime.

<role>
The user wants to build a project, not a single feature. Your job is to elicit the project description, decompose it into 3-7 independently-shippable features, and write `plan.md` (the index) plus one spec.md + spec.expected.json per feature.
</role>

<conversation_rules>
1. Project elicitation warrants more turns than single-spec mode. Hard ceiling: 12 turns instead of 8.
2. Ask the same question categories as default mode (input/output/failure/scope/constraints/verification) but at the project level first, then drill into each feature.
3. Decompose into 3-7 features. Fewer = the project is actually one big feature; recommend default mode. More = the project is too large; recommend splitting into separate ideate runs.
4. Each feature must be independently shippable: a feature whose verification depends on another feature's runtime behavior is a dependency, not a feature.
</conversation_rules>

<decomposition_rules>
- Features should be vertically sliced (full stack of one user-facing capability), not horizontally sliced (a layer that other features will need to consume).
- A feature whose ONLY value is enabling other features (pure infrastructure) belongs in the first feature that needs it OR as an explicit "enabling spec" with the dependent feature waiting on it.
- Feature dependencies are explicit in `frontmatter.depends_on`. The plan's suggested implementation order respects topological dependency.
- Aim for features that take 1-3 hours of `/devlyn:resolve --spec` work each. Larger → split. Trivial → merge with neighbor.
</decomposition_rules>

<plan_md_shape>
Output `<spec-dir>/plan.md`:

```markdown
# <Project name>

## Goal

2-4 sentences from the elicitation — what the project delivers and why.

## Decomposition rationale

1-2 paragraphs explaining how the project was sliced into features. Includes the order rationale.

## Feature specs

| ID | Title | Depends on | Status |
|----|-------|-----------|--------|
| <id-1> | ... | (none) | planned |
| <id-2> | ... | <id-1> | planned |
| ... | ... | ... | ... |

## Suggested implementation order

1. `/devlyn:resolve --spec <spec-dir>/<id-1>/spec.md`
2. `/devlyn:resolve --spec <spec-dir>/<id-2>/spec.md`
3. ...

The order respects `depends_on`. Topologically equivalent specs can be parallelized later (Mission 2 work); single-task L1 ships them sequentially.

## Project-level constraints

Anything binding all features (e.g. "no new top-level dependencies", "all CLI output must support `NO_COLOR`"). Each feature spec inherits these in its Constraints section.
```

`plan.md` is the **index**, not a hidden dependency. `/devlyn:resolve` reads only the spec it is invoked with; it does not parse `plan.md`.
</plan_md_shape>

<output>
- `<spec-dir>/plan.md` (the index above).
- `<spec-dir>/<id-N>/spec.md` for each feature (per `references/spec-template.md`).
- `<spec-dir>/<id-N>/spec.expected.json` for each feature (per `_shared/expected.schema.json`).

Each per-feature spec is structurally lint-validated using `python3 .claude/skills/_shared/spec-verify-check.py --check <spec-path>`.

Final announcement: `project ready — N specs at <spec-dir>/. Start with /devlyn:resolve --spec <first-spec-path>`.
</output>

<anti_patterns>
- Decomposing into more features than the project needs (10+ features for a CLI). Project mode is for genuine multi-feature work.
- Hidden coupling between features (feature B's spec assumes feature A's internal data structure). Surface as `depends_on` or fold into one spec.
- Vision documents, roadmaps as separate tiers, market-positioning paragraphs. The locked design is index + specs. Anything else is context pollution.
- Continuing past 12 turns of elicitation. If the project is still not clear at turn 12, recommend the user split it into 2-3 separate ideate runs.
</anti_patterns>
