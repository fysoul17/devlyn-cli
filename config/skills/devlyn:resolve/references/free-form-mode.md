# Free-form mode — complexity classifier

When `/devlyn:resolve` is invoked with a free-form goal (no `--spec`) — whether the goal is the inline positional text or the content of `--goal-file <path>` (PHASE 0 resolves `goal_text` from either source before classifying) — PHASE 0 sets `state.complexity ∈ {trivial, medium, large}`, writes the lossless generated contract below, or halts with `/devlyn:ideate` guidance.

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

Action: write `.devlyn/criteria.generated.md` in the common shape below without anchors, set `state.complexity = "trivial"`, and proceed to PHASE 1.

### Medium branch

Conditions (any one):
- `goal_length > 30` words.
- `file_scope_signals` between 4 and 10.
- `verb_class ∈ {refactor, debug, review}` AND scope is a single subsystem.
- `has_failing_test == false` but the goal implies a runnable acceptance check.

Action: read the named files or symbols for 1-2 context anchors, write the common shape with those non-binding anchors, set `state.complexity = "medium"`, and proceed to PHASE 1.

### Large branch

Conditions (any one):
- `file_scope_signals > 10` OR zero signals (vague enough that the classifier cannot pick scope).
- `verb_class ∈ {rewrite, migrate}` and scope is multi-subsystem.
- The goal mentions a new feature whose surface area requires design decisions the harness cannot make from a one-shot prompt.
- `pair_evidence_intent == true` and `has_actionable_solo_headroom == false`.
- `unmeasured_pair_candidate_intent == true` and `has_solo_ceiling_avoidance == false`.

Action:
- Default: write the common shape. Add `## Assumptions (non-binding)` only for true assumptions; if an assumption would materially choose scope, halt to `/devlyn:ideate`. Log `recommend: /devlyn:ideate first` and every assumption in the final report; proceed to PHASE 1.
- Zero-signal exception: if the large classification includes `file_scope_signals == 0` (classifier cannot pick scope), halt with terminal verdict `BLOCKED:large-needs-ideation` — assumptions there would be scope-invention, not narrowing.
- Exception: if the large classification came from pair-evidence intent without an actionable solo-headroom hypothesis, halt with `BLOCKED:solo-headroom-hypothesis-required`. Do not invent a hypothesis; recommend `/devlyn:ideate` so the user can supply the visible behavior `solo_claude` is expected to miss.
- Exception: if the large classification came from unmeasured pair-candidate intent without solo ceiling avoidance, halt with `BLOCKED:solo-ceiling-avoidance-required`. Do not invent the note; recommend `/devlyn:ideate` so the user can supply the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`.

## Anti-pattern: drift to LLM judgment

The classifier MUST stay deterministic. If you're tempted to add "and the model assesses whether it's complex" — that is the failure mode this rule exists to prevent. LLM-judgment classifiers swing on prompt-prelude noise; rules over signals do not.

When the rules are silent (rare — pathological goal text), default to `medium` and proceed.

## Generated-contract shape

Every proceeding branch writes `.devlyn/criteria.generated.md` in this order:

- `## Goal (verbatim)` first. Copy raw `goal_text` bytes without normalization inside a backtick fence at least three characters long and one longer than its longest backtick run; never interpret goal headings, sentinels, or fences as structure.
- Optional `## Context anchors (non-binding)` with 1-2 evidence facts, then Large-only `## Assumptions (non-binding)` for true assumptions. Neither can license, forbid, narrow, expand, or override Goal scope.
- The canonical `<!-- devlyn:verification -->` sentinel and `## Verification` section are LAST. Keep the machine JSON carrier unchanged; include a runnable command when discoverable, and leave it empty only for a pure-design Goal.

The raw Goal is the sole scoping authority. Never synthesize binding `Requirements`, `Constraints`, or `Out of Scope` sections on a free-form branch.

- Raw Goal preservation carries actionable solo-headroom hypotheses and `solo ceiling avoidance` notes unchanged; emit `spec.solo_headroom_hypothesis` when applicable and preserve the concrete difference from controls such as `S2`-`S6`.
- This is a run-scoped artifact, not a documented spec.
- After writing `.devlyn/criteria.generated.md`, set `state.source.type = "generated"`, `state.source.spec_path = null`, `state.source.spec_sha256 = null`, `state.source.criteria_path = ".devlyn/criteria.generated.md"`, and `state.source.criteria_sha256` to the raw-byte SHA-256 of the generated criteria file. Downstream PLAN/IMPLEMENT/VERIFY phases and `spec-verify-check.py --include-risk-probes` depend on this pointer; do not rely on the file existing by convention.

PLAN reads the generated contract, but treats its Goal—not anchors, assumptions, or Verification—as free-form scope law.
