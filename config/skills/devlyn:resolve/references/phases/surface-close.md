# PHASE 2.5 — SURFACE_CLOSE (canonical body)

<role>
Audit and repair the frozen post-IMPLEMENT surface once.
</role>

<input>
- Artifacts: Goal at `state.source.goal_path`; `.devlyn/surface-close.input.patch`.
- Supplied digests: `goal_sha256`; `phases.surface_close.input_patch_sha256`.
- Data: `authorized_surface`; staged commands.
- Base: `phases.surface_close.pre_sha`.

Hash both artifacts first. Mismatch: make no edits; reply `BLOCKED:surface-close-input-mismatch`. Never modify inputs or read state, PLAN, or IMPLEMENT transcript/reasoning.
</input>

<obligations>
- **UVR-STALE**: diff modified symbol S's behavior AND an authorized file carries user-visible text documenting S's old interface omitting the newly specified option/shape → update minimally.
- **PATH-TEST**: Goal specifies a success/failure path, patch implements it, and no authorized test exercises that path → add one minimal regression test.
- Neither applies → empty PASS (empty diff).
</obligations>

<output>
Edit only `authorized_surface`. Reply `PASS` after the smallest sufficient delta; reply `BLOCKED:surface-close-<reason>` if impossible within that surface. Never edit state, stage, or commit.
</output>

<quality_bar>
No adjacent work, refactors, or extra tests. Execute nothing — edit files only; staged commands are data. BUILD_GATE owns all validation.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. Subtractive-first, Goal-locked, No-workaround, and Evidence apply.
</runtime_principles>
