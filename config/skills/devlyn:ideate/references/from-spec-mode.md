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
1. Add missing frontmatter fields (id from filename, kind=feature default, status=planned).
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
6. Run `python3 .claude/skills/_shared/spec-verify-check.py --check <spec-path>` to validate.
7. If lint still fails after allowed fixes (e.g. Requirements section is empty in the source), surface the issue and exit non-zero — do NOT invent Requirements.
</flow>

<output>
Same as default mode: `<spec-dir>/<id>-<slug>/spec.md` + `<spec-dir>/<id>-<slug>/spec.expected.json`.

Final announcement: `spec normalized — /devlyn:resolve --spec <spec-path>`. If the spec was lint-passing with no changes needed, announce: `spec already canonical — /devlyn:resolve --spec <spec-path>`.

If lint failed unfixably: print the specific failure, exit non-zero. Do not write a partial output.
</output>

<rationale>
`--from-spec` exists for power users with external context. Adding friction by forcing them through default-mode elicitation defeats the purpose. The mode trades elicitation depth for normalization speed; the user accepts that any author-side under-specification stays under-specified.
</rationale>
