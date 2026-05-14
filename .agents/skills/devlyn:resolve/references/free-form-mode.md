# Free-form mode — complexity classifier

When `/devlyn:resolve` is invoked with a free-form goal (no `--spec`), PHASE 0 runs this classifier to set `state.complexity ∈ {trivial, medium, large}` and either proceeds with an internal mini-spec, drafts focused questions for in-prompt resolution, or recommends `/devlyn:ideate` first.

The classifier is rules-based / deterministic — not an LLM judgment call. Decision rules below.

## Classification rules

Compute these signals from the goal text + project state:

1. **goal_length** — word count of the user's goal.
2. **file_scope_signals** — count of file paths or symbol names mentioned in the goal (`bin/cli.js`, `Login.tsx`, `parseArgs`, etc.).
3. **verb_class** — primary verb of the goal: `fix | add | refactor | debug | review | rewrite | migrate | ...`.
4. **codebase_size** — `git ls-files | wc -l`. Coarse buckets: `<50` / `<500` / `≥500`.
5. **has_failing_test** — does the goal mention a specific failing test or include a stack trace?
6. **pair_evidence_intent** — does the goal ask for benchmark evidence, pair-evidence, risk-probe measurement, solo<pair proof, or solo-headroom work?
7. **has_actionable_solo_headroom** — does the goal itself include the actionable contract: literal `solo-headroom hypothesis`, `solo_claude`, `miss`, and a backticked observable command line that itself contains `miss` and is framed as the command/observable that exposes it?
8. **unmeasured_pair_candidate_intent** — does the goal ask to add, create,
   promote, or run a new unmeasured benchmark, shadow fixture, golden fixture,
   risk-probe, or pair-evidence candidate?
9. **has_solo_ceiling_avoidance** — does the goal itself include the literal
   phrase `solo ceiling avoidance`, mention `solo_claude`, and name a concrete
   difference from rejected or solo-saturated controls such as `S2`-`S6`?

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
- `goal_length` between 30 and 80 words.
- `file_scope_signals` between 4 and 10.
- `verb_class ∈ {refactor, debug, review}` AND scope is a single subsystem.
- `has_failing_test == false` but the goal implies a runnable acceptance check.

Action: synthesize a richer internal spec:
- Read the named files (or grep for the named symbols) to extract 1-2 context anchors (existing patterns, related tests).
- Write `.devlyn/criteria.generated.md` with `## Requirements` (split into 3-5 testable bullets), `## Constraints` (anything implied by the existing patterns), `## Out of Scope` (adjacent code that "looks fixable"), `## Verification` (commands or checks discoverable from existing tests / patterns).
- Set `state.complexity = "medium"`. Proceed to PHASE 1.

### Large branch

Conditions (any one):
- `goal_length > 80` words.
- `file_scope_signals > 10` OR zero signals (vague enough that the classifier cannot pick scope).
- `verb_class ∈ {rewrite, migrate}` and scope is multi-subsystem.
- The goal mentions a new feature whose surface area requires design decisions the harness cannot make from a one-shot prompt.
- `pair_evidence_intent == true` and `has_actionable_solo_headroom == false`.
- `unmeasured_pair_candidate_intent == true` and `has_solo_ceiling_avoidance == false`.

Action: log `recommend: /devlyn:ideate first` in `.devlyn/criteria.generated.md` plus the final report. Two policies:
- Default: halt with terminal verdict `BLOCKED:large-needs-ideation`.
- `--continue-on-large` flag: synthesize a best-effort spec from the goal with explicit "assumptions made" block; proceed to PHASE 1; the final report flags every assumption for user review.
- Exception: if the large classification came from pair-evidence intent without an actionable solo-headroom hypothesis, halt with `BLOCKED:solo-headroom-hypothesis-required` even when `--continue-on-large` is set. Do not invent a hypothesis; recommend `/devlyn:ideate` so the user can supply the visible behavior `solo_claude` is expected to miss.
- Exception: if the large classification came from unmeasured pair-candidate intent without solo ceiling avoidance, halt with `BLOCKED:solo-ceiling-avoidance-required` even when `--continue-on-large` is set. Do not invent the note; recommend `/devlyn:ideate` so the user can supply the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`.

## Anti-pattern: drift to LLM judgment

The classifier MUST stay deterministic. If you're tempted to add "and the model assesses whether it's complex" — that is the failure mode this rule exists to prevent. LLM-judgment classifiers swing on prompt-prelude noise; rules over signals do not.

When the rules are silent (rare — pathological goal text), default to `medium` and proceed.

## Mini-spec quality bar

The internal mini-spec written for trivial / medium / `--continue-on-large` paths must satisfy:

- `## Requirements` non-empty, each bullet testable (CLI command, test command, observable file change).
- `## Verification` non-empty if the goal implies any runnable acceptance check. Empty Verification is allowed only when all Requirements are pure-design (e.g. "follow existing pattern X").
- If a free-form goal includes pair-evidence intent and already includes an actionable solo-headroom hypothesis, preserve that literal hypothesis in `.devlyn/criteria.generated.md` unchanged enough for VERIFY to detect `solo-headroom hypothesis`, `solo_claude`, `miss`, and the backticked observable command line that itself contains `miss`, emit the canonical `spec.solo_headroom_hypothesis` pair trigger reason, and satisfy regenerated-evidence checks such as `benchmark audit --require-hypothesis-trigger`.
- If a free-form goal includes unmeasured pair-candidate intent and already includes solo ceiling avoidance, preserve that literal note in `.devlyn/criteria.generated.md` unchanged enough for reviewers to see `solo ceiling avoidance`, `solo_claude`, and the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`.
- Free-form mode mini-specs are written to `.devlyn/criteria.generated.md` (not to a roadmap path) — this is run-scoped artifact, not a documented spec.
- After writing `.devlyn/criteria.generated.md`, set `state.source.type = "generated"`, `state.source.spec_path = null`, `state.source.spec_sha256 = null`, `state.source.criteria_path = ".devlyn/criteria.generated.md"`, and `state.source.criteria_sha256` to the raw-byte SHA-256 of the generated criteria file. Downstream PLAN/IMPLEMENT/VERIFY phases and `spec-verify-check.py --include-risk-probes` depend on this pointer; do not rely on the file existing by convention.

PLAN reads the mini-spec the same way it reads a real spec. The downstream pipeline cannot tell the difference.
