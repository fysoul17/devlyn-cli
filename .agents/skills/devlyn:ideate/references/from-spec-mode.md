# `--from-spec` mode

Per-engine adapter prepended at runtime.

<role>
The user already wrote a spec (or has one from elsewhere — a teammate, a previous project, a copy-paste from a doc). Your job is to lint and normalize it to the canonical shape — without reshaping the user's substantive intent.
</role>

<input>
- `<path>` — the external spec markdown file.
- `_shared/expected.schema.json` — the schema for the sibling `spec.expected.json`.
- `references/spec-template.md` — the canonical shape.
</input>

<allowed_changes>
You may:
1. Add missing frontmatter fields (id from filename, kind=feature default, status=planned, complexity=medium default; set complexity=high only when preserved Requirements clearly combine state/order/failure/output-shape risks).
2. Rename non-canonical section headings to canonical (`## Goals` → `## Requirements`, `## Notes` ignored unless they clearly belong in Constraints).
3. Add a missing `## Out of Scope` section with `- (no explicit non-goals provided by author)`.
4. Add a missing `## Verification` section if Requirements imply observable runtime checks — best-effort one-command-per-Requirement, then surface to user for review.
5. Generate `spec.expected.json` from the `## Verification` block if the file is absent.
6. Fix structurally invalid `spec.expected.json` (malformed JSON, missing required keys per `_shared/expected.schema.json`).
</allowed_changes>

<forbidden_changes>
You must NOT:
- Reshape Requirements content. The user's substantive intent is preserved verbatim.
- Add new Constraints the user did not write.
- Move items between Requirements and Out of Scope.
- "Improve" the prose in Context. Author voice stays.
- Add `## Assumptions` or `## Open questions` sections — that is default-mode work, not normalization.
</forbidden_changes>

<flow>
1. Read `<path>`. Parse frontmatter. Identify present sections.
2. Lint structurally (same checks as default mode).
3. For each missing/malformed piece: apply the smallest allowed fix.
4. Write the normalized spec. Default location: `<spec-dir>/<id>-<slug>/spec.md`. With `--in-place` flag: write to `<path>` directly (overwrites the original).
5. Generate or fix `spec.expected.json` per the rules above. Same dir as the spec.
6. Run `python3 .claude/skills/_shared/spec-verify-check.py --check <spec-path>` to validate the spec carrier and supported `complexity` frontmatter; if the spec uses a legacy inline `## Verification` JSON carrier, any solo-headroom hypothesis command must match that carrier's `verification_commands[].cmd`.
7. Run `python3 .claude/skills/_shared/spec-verify-check.py --check-expected <expected-path>` to validate sibling `spec.expected.json` plus sibling spec `complexity` frontmatter and any present solo-headroom hypothesis command against `spec.expected.json.verification_commands[].cmd`.
8. If lint still fails after allowed fixes (e.g. Requirements section is empty in the source), surface the issue and exit non-zero — do NOT invent Requirements.
9. If the preserved Requirements combine state mutation with ordering/priority,
   idempotency, auth/error priority, or exact output shape but the Verification
   section lacks a compound end-to-end scenario, do not rewrite the author's
   content. Add a final warning that `/devlyn:resolve` may need default-mode
   ideation or a stronger Verification section before pair-relevant risks are
   measurable.
10. If the source is a benchmark, risk probe, or pair-evidence candidate and it
    lacks an actionable solo-headroom hypothesis, do not invent one. Add a final
    warning that the candidate may be solo-saturated until Context or
    Verification literally contains `solo-headroom hypothesis`, `solo_claude`,
    `miss`, and a backticked observable command while naming the visible
    behavior a capable `solo_claude` baseline is expected to miss; the
    backticked line itself must contain `miss` and be framed as the
    command/observable that exposes it. Do not call the normalized spec pair-evidence ready.
11. If the source is a new unmeasured benchmark, shadow-fixture, golden-fixture,
    risk-probe, or pair-evidence candidate and it lacks a solo ceiling avoidance
    note, do not invent one. Add a final warning that the candidate may replay
    rejected or solo-saturated controls until Context, Verification, or fixture
    `NOTES.md` literally contains `solo ceiling avoidance`, mentions
    `solo_claude`, and names a concrete difference from rejected controls such
    as `S2`-`S6`. Do not call the normalized spec pair-evidence ready.
</flow>

<output>
Same as default mode: `<spec-dir>/<id>-<slug>/spec.md` + `<spec-dir>/<id>-<slug>/spec.expected.json`.

Final announcement: `spec normalized — /devlyn:resolve --spec <spec-path>`. If the spec was lint-passing with no changes needed, announce: `spec already canonical — /devlyn:resolve --spec <spec-path>`. If step 9 applies, append: `warning: Verification may need one compound end-to-end scenario before pair-relevant risks are measurable`. If step 10 applies, append: `pair-evidence not ready — Pair-candidate headroom is unproven until the spec states a solo-headroom hypothesis`. If step 11 applies, append: `pair-evidence not ready — Pair-candidate headroom is unproven until the spec states solo ceiling avoidance`.

If lint failed unfixably: print the specific failure, exit non-zero. Do not write a partial output.
</output>

<rationale>
`--from-spec` exists for power users with external context. Adding friction by forcing them through default-mode elicitation defeats the purpose. The mode trades elicitation depth for normalization speed; the user accepts that any author-side under-specification stays under-specified.
</rationale>
