# Free-form mode — complexity classifier

When `/devlyn:resolve` is invoked with a free-form goal (no `--spec`) — whether the goal is the inline positional text or the content of `--goal-file <path>` (PHASE 0 resolves `goal_text` from either source before classifying) — PHASE 0 runs this classifier to set `state.complexity ∈ {trivial, medium, large}` and retain every terminal halt before worker dispatch. It does not inspect the repository to author criteria or write a mini-spec: the initial PLAN worker receives the raw goal, deterministic complexity, and this quality bar, then authors the mini-spec before planning.

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

Evaluate Large first, then Medium, then Trivial; stop at the first matching branch.

### Trivial branch

Conditions (all must hold):
- `goal_length ≤ 30` words.
- `file_scope_signals ≥ 1` AND `≤ 3`.
- `verb_class ∈ {fix, add}`.
- `has_failing_test == true` OR the goal names a single specific symbol/file.

Action: set `state.complexity = "trivial"`. The initial PLAN worker writes `.devlyn/criteria.generated.md` with sections `## Requirements` (the goal as a single bullet, optionally split into 2-3 if obviously separable), `## Out of Scope` ("anything not in the listed files"), and `## Verification` (one runnable command if discoverable from the goal — e.g. the failing test, or a smoke command), then plans from those exact bytes.

### Medium branch

Conditions (any one):
- `goal_length > 30` words.
- `file_scope_signals` between 4 and 10.
- `verb_class ∈ {refactor, debug, review}` AND scope is a single subsystem.
- `has_failing_test == false` but the goal implies a runnable acceptance check.

Action: set `state.complexity = "medium"`. The initial PLAN worker reads the named files (or greps for the named symbols) once to extract 1-2 context anchors (existing patterns, related tests), writes `.devlyn/criteria.generated.md` with `## Requirements` (split into 3-5 testable bullets), `## Constraints` (anything implied by the existing patterns), `## Out of Scope` (adjacent code that "looks fixable"), and `## Verification` (commands or checks discoverable from existing tests / patterns), then plans from those exact bytes.

### Large branch

Conditions (any one):
- `file_scope_signals > 10` OR zero signals (vague enough that the classifier cannot pick scope).
- `verb_class ∈ {rewrite, migrate}` and scope is multi-subsystem.
- The goal mentions a new feature whose surface area requires design decisions the harness cannot make from a one-shot prompt.
- `pair_evidence_intent == true` and `has_actionable_solo_headroom == false`.
- `unmeasured_pair_candidate_intent == true` and `has_solo_ceiling_avoidance == false`.

Action:
- Default: the initial PLAN worker synthesizes a best-effort spec from the goal with an explicit `## Assumptions` block (every assumption scope-narrowing and reversible — when in doubt, narrower); log `recommend: /devlyn:ideate first` in `.devlyn/criteria.generated.md` AND the final report; the final report flags every assumption for user review.
- Zero-signal exception: if the large classification includes `file_scope_signals == 0` (classifier cannot pick scope), halt with terminal verdict `BLOCKED:large-needs-ideation` — assumptions there would be scope-invention, not narrowing.
- Exception: if the large classification came from pair-evidence intent without an actionable solo-headroom hypothesis, halt with `BLOCKED:solo-headroom-hypothesis-required`. Do not invent a hypothesis; recommend `/devlyn:ideate` so the user can supply the visible behavior `solo_claude` is expected to miss.
- Exception: if the large classification came from unmeasured pair-candidate intent without solo ceiling avoidance, halt with `BLOCKED:solo-ceiling-avoidance-required`. Do not invent the note; recommend `/devlyn:ideate` so the user can supply the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`.

## Anti-pattern: drift to LLM judgment

The classifier MUST stay deterministic. If you're tempted to add "and the model assesses whether it's complex" — that is the failure mode this rule exists to prevent. LLM-judgment classifiers swing on prompt-prelude noise; rules over signals do not.

When the rules are silent (rare — pathological goal text), default to `medium` and proceed.

## Mini-spec quality bar

The initial PLAN worker's internal mini-spec for trivial / medium / large-assumptions paths must satisfy:

- `## Requirements` non-empty, each bullet testable (CLI command, test command, observable file change).
- `## Verification` is preceded by a `<!-- devlyn:verification -->` sentinel on its own line directly above the heading — the machine locator `spec-verify-check.py` uses; the heading text itself is decorative and may be any language. `## Verification` non-empty if the goal implies any runnable acceptance check. Empty Verification is allowed only when all Requirements are pure-design (e.g. "follow existing pattern X").
- If a free-form goal includes pair-evidence intent and already includes an actionable solo-headroom hypothesis, preserve that literal hypothesis in `.devlyn/criteria.generated.md` unchanged enough for VERIFY to detect `solo-headroom hypothesis`, `solo_claude`, `miss`, and the backticked observable command line that itself contains `miss`, emit the canonical `spec.solo_headroom_hypothesis` pair trigger reason, and satisfy regenerated-evidence checks such as `benchmark audit --require-hypothesis-trigger`.
- If a free-form goal includes unmeasured pair-candidate intent and already includes solo ceiling avoidance, preserve that literal note in `.devlyn/criteria.generated.md` unchanged enough for reviewers to see `solo ceiling avoidance`, `solo_claude`, and the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`.
- Free-form mode mini-specs are written to `.devlyn/criteria.generated.md` (not to a roadmap path) — this is run-scoped artifact, not a documented spec.

After the initial PLAN return, the parent validates the preinitialized `state.source.criteria_path` and registers only `state.source.criteria_sha256` as the raw-byte SHA-256 of the generated criteria file. Downstream IMPLEMENT/VERIFY phases and `spec-verify-check.py --include-risk-probes` depend on this pointer; do not rely on the file existing by convention.

The initial PLAN worker writes the mini-spec first and plans from those exact bytes; downstream phases read it the same way they read a real spec.
