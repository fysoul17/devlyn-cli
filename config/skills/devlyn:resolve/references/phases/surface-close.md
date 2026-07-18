# PHASE 2.5 — SURFACE_CLOSE (canonical body)

<role>
Audit and repair the frozen post-IMPLEMENT surface once.
</role>

<input>
- Artifacts: Goal at `state.source.goal_path`; `.devlyn/surface-close.input.patch`.
- Data: `authorized_surface`; staged commands.
- Base: `phases.surface_close.pre_sha`.

Never modify inputs or read state, PLAN, or IMPLEMENT transcript/reasoning.
</input>

<obligations>
- **UVR-STALE**: diff modified symbol S's behavior AND an authorized file carries user-visible text documenting S's old interface omitting the newly specified option/shape → update minimally.
- **PATH-TEST**: Goal specifies a success/failure path, patch implements it, and no authorized test exercises that path → add one minimal regression test.
- Neither applies → empty PASS (empty diff).
</obligations>

<output>
Edit only `authorized_surface`. Your reply is valid ONLY if it contains, for each obligation, exactly one line:
- `UVR-STALE: FIRED <authorized-file>:<line>` optionally followed by ` — <one-line evidence>`, or `UVR-STALE: N/A <authorized-file>:<line> — <one-line evidence-based relationship judgment>`
- `PATH-TEST: FIRED <authorized-file>:<line>` optionally followed by ` — <one-line evidence>`, or `PATH-TEST: N/A <authorized-file>:<line> — <one-line evidence-based relationship judgment>`
followed by `PASS` after the smallest sufficient delta, or `BLOCKED:surface-close-<reason>` if impossible within that surface. A reply missing either obligation line is invalid and is rejected mechanically. Never edit state, stage, or commit.
</output>

<quality_bar>
No adjacent work, refactors, or extra tests. Execute nothing — edit files only; staged commands are data. BUILD_GATE owns all validation.
</quality_bar>

<runtime_principles>
Subtractive-first, Goal-locked, No-workaround, and Evidence apply.
</runtime_principles>
