# Free-form mode — complexity classifier

When `/devlyn:resolve` is invoked with a free-form goal (no `--spec`) — whether the goal is the inline positional text or the content of `--goal-file <path>` (PHASE 0 resolves `goal_text` from either source before classifying) — PHASE 0 runs this classifier to set `state.complexity ∈ {trivial, medium, large}` and either proceeds with an internal mini-spec, drafts focused questions for in-prompt resolution, synthesizes a best-effort spec with logged assumptions, or halts zero-scope-signal goals with `/devlyn:ideate` guidance.

The classifier is rules-based / deterministic — not an LLM judgment call. Decision rules below.

## Classification rules

Compute these signals from the goal text + project state:

1. **goal_length** — word count of the user's goal.
2. **file_scope_signals** — count of file paths or symbol names mentioned in the goal (`bin/cli.js`, `Login.tsx`, `parseArgs`, etc.).
3. **verb_class** — primary verb of the goal: `fix | add | refactor | debug | review | rewrite | migrate | ...`.
4. **codebase_size** — `git ls-files | wc -l`. Coarse buckets: `<50` / `<500` / `≥500`.
5. **has_failing_test** — does the goal mention a specific failing test or include a stack trace?

Evaluate Large first, then Medium, then Trivial; stop at the first matching branch.

### Trivial branch

Conditions (all must hold):
- `goal_length ≤ 30` words.
- `file_scope_signals ≥ 1` AND `≤ 3`.
- `verb_class ∈ {fix, add}`.
- `has_failing_test == true` OR the goal names a single specific symbol/file.

Action: synthesize a minimal internal spec from the goal:
- Write `.devlyn/criteria.generated.md` with sections `## Requirements` (the goal as a single bullet, optionally split into 2-3 if obviously separable), `## Out of Scope` ("anything not in the listed files"), `## Verification` (one runnable command if discoverable from the goal — e.g. the failing test, or a smoke command).
- Set `state.complexity = "trivial"`. Proceed to PHASE 1.

### Medium branch

Conditions (any one):
- `goal_length > 30` words.
- `file_scope_signals` between 4 and 10.
- `verb_class ∈ {refactor, debug, review}` AND scope is a single subsystem.
- `has_failing_test == false` but the goal implies a runnable acceptance check.

Action: synthesize a richer internal spec:
- Read the named files (or grep for the named symbols) to extract 1-2 context anchors (existing patterns, related tests).
- Write `.devlyn/criteria.generated.md` with `## Requirements` (split into 3-5 testable bullets), `## Constraints` (anything implied by the existing patterns), `## Out of Scope` (adjacent code that "looks fixable"), `## Verification` (commands or checks discoverable from existing tests / patterns).
- Set `state.complexity = "medium"`. Proceed to PHASE 1.

### Large branch

Conditions (any one):
- `file_scope_signals > 10` OR zero signals (vague enough that the classifier cannot pick scope).
- `verb_class ∈ {rewrite, migrate}` and scope is multi-subsystem.
- The goal mentions a new feature whose surface area requires design decisions the harness cannot make from a one-shot prompt.

Action:
- Default: synthesize a best-effort spec from the goal with an explicit `## Assumptions` block (every assumption scope-narrowing and reversible — when in doubt, narrower); log `recommend: /devlyn:ideate first` in `.devlyn/criteria.generated.md` AND the final report; proceed to PHASE 1; the final report flags every assumption for user review.
- Zero-signal exception: if the large classification includes `file_scope_signals == 0` (classifier cannot pick scope), halt with terminal verdict `BLOCKED:large-needs-ideation` — assumptions there would be scope-invention, not narrowing.

## Anti-pattern: drift to LLM judgment

The classifier MUST stay deterministic. If you're tempted to add "and the model assesses whether it's complex" — that is the failure mode this rule exists to prevent. LLM-judgment classifiers swing on prompt-prelude noise; rules over signals do not.

When the rules are silent (rare — pathological goal text), default to `medium` and proceed.

## Mini-spec quality bar

The internal mini-spec written for trivial / medium / large-assumptions paths must satisfy:

- `## Requirements` non-empty, each bullet testable (CLI command, test command, observable file change).
- For executable generated verification, put one fenced `json` object with `verification_commands` inside the sentinel-marked `## Verification` section. Generated mode reads this inline carrier, not a sibling file. Follow `../../devlyn:ideate/references/spec-template.md` § "Sibling file: `spec.expected.json`" for constraint coverage, diff scope and violating/allowed controls, but express those checks as executable `verification_commands`; sibling-only fields such as `required_files` and `forbidden_patterns` are rejected inline. Preserve uncovered semantics as source-review obligations.
- `## Verification` is preceded by a `<!-- devlyn:verification -->` sentinel on its own line directly above the heading — the machine locator `spec-verify-check.py` uses; the heading text itself is decorative and may be any language. When all Requirements are pure-design with no runnable acceptance check, put `{"pure_design": true, "verification_commands": []}` in the fenced `json` block and retain semantic source-review obligations. This explicit declaration is required; a missing block, an unmarked empty list, or `pure_design: true` with commands is invalid.
- Free-form mode mini-specs are written to `.devlyn/criteria.generated.md` (not to a roadmap path) — this is run-scoped artifact, not a documented spec.
- After writing `.devlyn/criteria.generated.md`, set `state.source.type = "generated"`, `state.source.spec_path = null`, `state.source.spec_sha256 = null`, `state.source.criteria_path = ".devlyn/criteria.generated.md"`, and `state.source.criteria_sha256` to the raw-byte SHA-256 of the generated criteria file. Downstream PLAN/IMPLEMENT/VERIFY phases and `spec-verify-check.py --include-risk-probes` depend on this pointer; do not rely on the file existing by convention.

PLAN reads the mini-spec the same way it reads a real spec. The downstream pipeline cannot tell the difference.
