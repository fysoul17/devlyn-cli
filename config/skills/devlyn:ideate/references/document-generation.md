# Document Generation — Phase 4 Detail

Loaded on-demand by `devlyn:ideate` during Phase 4 (DOCUMENT). Everything the phase needs to generate the three-layer planning output — templates, order, spec quality gates, expand-mode rules — lives here. The SKILL.md body keeps only the pointer and quality reminders.

## Templates

Read these templates before generating the corresponding document:

- `references/templates/vision.md` — VISION.md format
- `references/templates/roadmap.md` — ROADMAP.md index format
- `references/templates/item-spec.md` — auto-resolve-ready spec format
- `references/templates/decision.md` — architecture decision record format

## Generation Order

1. `docs/VISION.md` — from Phase 1 framing + Phase 3 decisions
2. `docs/roadmap/decisions/` — one file per architecture decision
3. `docs/roadmap/phase-N/_overview.md` — phase-level context
4. `docs/roadmap/phase-N/{id}-{name}.md` — one per roadmap item
5. `docs/ROADMAP.md` — index linking to everything above

The order matters: `decisions/` predates phase overviews because overviews reference decisions. `ROADMAP.md` comes last because it indexes everything above.

## Item Spec Quality (load-bearing)

Each Layer 3 spec is the **direct input to auto-resolve**. Its quality determines implementation quality. Miss these and auto-resolve's output quality drops in direct proportion.

<spec_quality_criteria>
**Requirements section** — becomes auto-resolve's done-criteria:
- Testable: a test can assert it OR a human can verify in under 30 seconds
- Specific: not "handles errors well" but "returns 400 with `{error: 'missing_field', field: 'email'}`"
- Scoped: tied to this item only, not aspirational

**Context section** — 2–3 sentences maximum. Just enough for auto-resolve to understand WHY without loading the full vision.

**Out of Scope** — explicitly states what this item does NOT do. This is what prevents auto-resolve from over-building, which is one of its most common failure modes. Also audited by preflight as "anti-commitments" — shipping something listed here is a scope-creep finding.

**Constraints** — technical constraints with reasoning. Auto-resolve respects constraints significantly better when it understands the motivation behind them. Prefer "must use Postgres (existing infrastructure; team already paged on pg ops)" over bare "must use Postgres".

**Verification** — newly generated specs that include observable Requirements (CLI command, test command, HTTP request, exit code, output substring) **must ship** a ` ```json ` block under `## Verification` with at least one matching entry. Schema: `{"verification_commands": [{"cmd": "...", "exit_code": int, "stdout_contains": [str], "stdout_not_contains": [str]}]}` per `templates/item-spec.md`. Block omitted entirely is allowed only when all Requirements are pure-design (e.g. "follow existing pattern X", "match the visual style of Y"). iter-0019.8: this block is the contract carrier auto-resolve's BUILD_GATE consumes mechanically — `spec-verify-check.py --check <spec.md>` runs after every spec write to validate shape. Backward compat: a missing block on a pre-carrier handwritten spec source is a silent no-op for auto-resolve (the gate stays inert, no regression for old specs); on a generated source it is a CRITICAL `correctness.spec-verify-malformed` finding (auto-resolve's PHASE 1 BUILD must always emit the block when creating `criteria.generated.md`).
</spec_quality_criteria>

If an item is too vague to write specific Requirements, it needs more exploration (revisit Phase 2 for that item) or should be split into smaller items. Do not ship a vague spec — the downstream pipeline will silently narrow scope to whatever it can actually test.

## Handling Existing Documents

In **Expand** and **Replan** modes:
- Read existing documents first.
- Merge new items into the existing phase structure.
- Preserve existing items (don't overwrite or reorder without confirmation).
- Continue numbering from existing IDs — if Phase 2 has 2.1–2.4, new items start at 2.5 (or open a Phase 3 if the new cluster is distinct).
- Update `docs/ROADMAP.md` index to include new entries — don't regenerate the whole table.
- If a new item changes the meaning of an existing item, flag this to the user rather than silently updating the older spec.

## Output Summary

After generating all documents, print the file list so the user has an immediate handle:

```
Documents created:
- docs/VISION.md
- docs/ROADMAP.md
- docs/roadmap/phase-1/_overview.md
- docs/roadmap/phase-1/1.1-xxx.md
- docs/roadmap/phase-1/1.2-yyy.md
- docs/roadmap/decisions/001-xxx.md
[total: N files]
```

This is what Phase 5 (BRIDGE) uses to produce the per-item `/devlyn:auto-resolve "Implement per spec at <path>"` handoff lines.
