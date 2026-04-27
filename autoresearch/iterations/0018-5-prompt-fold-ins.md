# iter-0018.5 — BUILD/EVAL prompt fold-ins for F5 / F9 failure modes

**Status**: SHIPPED 2026-04-27.
**Risk**: low (text-only edits to two phase prompts; no skill orchestrator logic, no benchmark schema, no arm change).
**Cost**: 0 paid runs ($0).

## Why this is iter-0018.5 and not part of iter-0019

Codex GPT-5.5 R0 explicit pushback (Q7): bundling prompt edits + new arm + schema change in iter-0019 would muddy attribution — F5 / F6 / F9 movement could come from prompt fix or from arm definition, with no way to disentangle. Splitting into a text-only iter-0018.5 (prompt fold-ins) followed by iter-0019 (arm + schema) keeps each iter's hypothesis clean.

## Hypothesis

iter-0016 surfaced two distinct failure modes that are *prompt-fixable*, not pair-vs-solo evidence:

1. **F5 −1 on scope** because variant added `completed=` to roadmap frontmatter beyond the lifecycle status flip. BUILD's `quality_bar` did not explicitly forbid spec-frontmatter edits.
2. **F9 both arms verify=0.4 spec=16/13** because BUILD declared PASS without literally executing every `verification_command` in `expected.json` and comparing output character-for-character. BUILD's `quality_bar` did not require literal verification; EVAL's `quality_bar` did not require a literal-match checklist.

Predicted change (filled BEFORE):
- No suite-margin movement in this iter (no benchmark run).
- iter-0019 should land F5 with scope=25 on variant arm (no `completed=` field), and F9 with spec≥22 on variant arm (`Error:` prefix, exit 2, JSON top-level keys all literal-matched).
- Bare arm scoring should also improve on F9 because the spec-match enforcement runs at BUILD prompt level which `--engine claude` mode (= L1 arm in iter-0019) inherits.

## Mechanism

Two surgical edits, both inside `<quality_bar>` blocks of phase prompts:

### 1. `phase-1-build.md` — two new bullets

**Bullet A (spec-frontmatter ban)**:

> Spec frontmatter is read-only to BUILD. The only legitimate lifecycle frontmatter change is the DOCS phase status flip after EVAL. BUILD must not add `completed`/`date` metadata, reorder YAML keys, reformat frontmatter, or introduce new metadata fields. Touch the spec frontmatter and EVAL will flag it as a `scope.out-of-scope-violation` HIGH.

Codex Q4 wording adopted (rejected my draft because mine implied BUILD might do the status flip). Locks the rule + names the EVAL-side enforcement.

**Bullet B (literal verification)**:

> Verification commands are literal. Before declaring PASS, re-read the source's Verification section (or `expected.json.verification_commands` for benchmark fixtures). Run every command exactly as listed and compare output to the spec character-for-character: every `stdout_contains` substring must appear verbatim in stdout, every `exit_code` must match exactly (exit 2 means exit 2, not 1), every `Error:` prefix must be the literal string the spec quotes, every JSON top-level key listed must be present at the top level (not nested or renamed). Paraphrasing the error message, choosing a "close" exit code, or restructuring the JSON shape is a verification failure — record it as such and fix BEFORE returning PASS.

Codex Q5 verdict: lands at BUILD `quality_bar`, not in shared `engine-routing.md`. Engine-routing is the wrong layer (it controls which engine, not what engine does). The "passive" weakness Codex flagged in my draft is fixed by saying "re-read spec → run every command → compare literally → fix before PASS" instead of just "match the spec."

### 2. `phase-2-evaluate.md` — two new bullets in `<quality_bar>`

**Bullet C (frontmatter-edit detection)**:

> Spec-frontmatter edits by BUILD are scope violations: the only legitimate frontmatter change is the DOCS phase status flip. If BUILD added fields (`completed`, `date`, etc.), reordered YAML keys, reformatted, or introduced metadata, emit `rule_id: "scope.frontmatter-edit"`, `severity: HIGH`, `criterion_ref: "spec://out-of-scope"`, `fix_hint` naming the offending keys.

Concrete `rule_id` so the finding is greppable in future analysis.

**Bullet D (literal-verification checklist)**:

> Verification-command literal-match is mandatory: for every command in the source's Verification section (or `expected.json.verification_commands` for benchmark fixtures), execute the command against the post-BUILD code and compare output literally. For each mismatch, emit a finding:
> - exit code differs from spec → `rule_id: "correctness.exit-code-mismatch"`, severity HIGH.
> - stdout/stderr missing a required substring → `rule_id: "correctness.spec-string-mismatch"`, severity HIGH.
> - JSON top-level shape differs → `rule_id: "correctness.json-shape-mismatch"`, severity HIGH.
> - Output format ordering differs → `rule_id: "correctness.format-mismatch"`, severity MEDIUM if cosmetic / HIGH if blocks the verification grep.
> Paraphrased error messages, "close" exit codes, and restructured JSON are not acceptable.

EVAL is now forced to *execute* the verification commands and produce file-anchored findings, not just *opine* on whether the implementation looks right. The four `rule_id`s are deliberately distinct so iter-0019 / 0020 can attribute movement.

## Diff plan

- `config/skills/devlyn:auto-resolve/references/phases/phase-1-build.md`: +2 bullets in `<quality_bar>`, no other change.
- `config/skills/devlyn:auto-resolve/references/phases/phase-2-evaluate.md`: +2 bullets in `<quality_bar>`, no other change.
- `autoresearch/iterations/0018-5-prompt-fold-ins.md` (this file).
- `autoresearch/HANDOFF.md` — collab log + Current state + Lessons cumulative entry.
- `autoresearch/DECISIONS.md` — iter-0018.5 SHIPPED entry.

No skill code, no Python, no schema, no arm work, no benchmark behavior change, no run.

## Falsification gate

Local checks only (no paid run):

1. `bash scripts/lint-skills.sh` → 10/10 ✓.
2. `bash benchmark/auto-resolve/scripts/run-suite.sh --dry-run F2-cli-medium-subcommand` → mirror runs successfully (`[suite] mirrored 26 committed skill(s)`), confirming the edited prompts copy from `config/skills/` to `.claude/skills/` cleanly.
3. `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` → silent.

The empirical falsification of the hypothesis happens in iter-0019's paid 5-fixture smoke run — that is when we read whether F5 variant scope returns to 25 and F9 variant spec ≥ 22. iter-0018.5's claim is bounded: "the new prompts are syntactically present and lint-clean." The behavior claim is iter-0019's job.

## Principles check (per `autoresearch/PRINCIPLES.md` 1–6)

1. **No overengineering** ✅ — 4 bullets total across 2 files, no new abstraction, no helper, no tool, no schema. Each bullet points at a specific iter-0016 failure mode.
2. **No guesswork** ✅ — predictions filled in BEFORE (no margin movement in this iter; iter-0019 should show F5 variant scope=25 and F9 variant spec≥22). Claims explicitly bounded ("syntactically present and lint-clean here, behavior verified in iter-0019").
3. **No workaround** ✅ — fix lands at the BUILD/EVAL prompt level, which is where the failure mode lived (BUILD's `quality_bar` had no spec-frontmatter ban; EVAL's `quality_bar` had no literal-match checklist). Why-chain: F5 lost scope point → because variant added `completed=` → because BUILD didn't forbid it → because `quality_bar` didn't enumerate spec-frontmatter as out-of-scope. Fix at the deepest level.
4. **Worldclass production-ready** ✅ — diagnostic-only landing, no shipped runtime mutation. Doc commit only.
5. **Best practice** ✅ — bullets follow existing `quality_bar` voice + reference existing `criterion_ref` / `rule_id` taxonomy from `findings-schema.md`. No new vocabulary invented.
6. **Layer-cost-justified** ✅ — text-only iter, zero added L1 / L2 cost. Closes a known scope/correctness gap that affects all layers identically; if the fix works, L0/L1/L2 all benefit, which is consistent with NORTH-STAR.md's "harness solo must beat bare" contract (L1 needs the same prompt discipline L2 has).

## Codex collaboration

R0 cached. R0 verdicts on this iter (Q4, Q5, Q7) adopted verbatim:

- Q4 wording: my draft implied BUILD might do the status flip. Codex's wording correctly says only DOCS does the flip after EVAL. Adopted.
- Q5 location: phase-1-build.md `<quality_bar>` + phase-2-evaluate.md `<quality_bar>`, **not** shared `engine-routing.md`. Adopted.
- Q5 active enforcement: my draft was passive ("must match the spec"). Codex wanted "EVAL forced to execute the verification commands and produce findings." Adopted via the four `rule_id`-anchored bullets in EVAL.
- Q7 split: iter-0018.5 (prompt-only) + iter-0019 (arm + schema) keeps attribution clean. Adopted as the iter sequence.

## Lessons (cumulative add)

- **Prompt-level fixes can be split from arm/schema fixes** for attribution clarity. Codex R0 Q7 framing — "if you ship both in one iter, any movement is muddy" — is the operational rule: **change one variable per iter** when measurement matters.
- **`quality_bar` is the right surface** for cross-cutting BUILD/EVAL contracts that previously lived implicitly. Bullets there get re-read every phase invocation; bullets in `references/findings-schema.md` are reference material that the orchestrator may not load at action time (iter-0014 lesson: "References are docs; SKILL.md PHASE sections are scripts").
- **EVAL must be forced to *execute*, not just *opine*.** F9 in iter-0016 had spec=16 because EVAL didn't run the verification commands; it just inspected the diff. Literal-match-by-execution is a different discipline and now lives in EVAL `quality_bar`.
