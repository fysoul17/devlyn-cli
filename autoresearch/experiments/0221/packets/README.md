# 0221 work packets

Session-ready scoping for the [0221](../../../iterations/0221-subtraction-direction.md) plan. Each packet was produced read-only against main @466aa25 and adversarially verified; every packet is READY_WITH_FIXES, meaning its verifier section must be applied. Raw JSON: `.devlyn/0221/packets/`.

| Packet | Verifier | Used in |
|---|---|---|
| [E1-comparison-apparatus-v2](E1-comparison-apparatus-v2.md) | READY_WITH_FIXES | Session 3. Arm F = published devlyn-cli@3.2.1 full resolve; verify tarball integrity, install manifest and actual role/pair behavior in-container. The B' product-arm install path is completed in Session 5. |
| [E2-instruction-layer-instrument](E2-instruction-layer-instrument.md) | READY_WITH_FIXES | Session 4, with the 0221 §4 counts: drift-bait current/slim N=4 on 4 models (192); none N=2 as a reference control excluded from the decision formula (48); EQ3 4 pre-registered tasks × 1 × 4 models × 3 variants (48). slim is frozen as a candidate; product reflection happens in Session 8. |
| [I1-resolve-responsibility-map](I1-resolve-responsibility-map.md) | READY_WITH_FIXES | Session 5 (build /devlyn:intent from the KEEP/MOVE rows; add, do not delete). Session 9 (delete helpers whose references are gone). Do not delete resolve or shared helpers in Session 5. |
| [I2-cross-surface-dependencies](I2-cross-surface-dependencies.md) | READY_WITH_FIXES | Session 5: PR-A (add intent, no default change). Session 8: PR-B (intent default at the next major; resolve/ideate become GUIDANCE-ONLY stubs for one major, not executing aliases — 0221 §3/§8). Session 9: PR-C (remove stubs after one major). |
| [T1a-small-cleanups](T1a-small-cleanups.md) | READY_WITH_FIXES | Session 1 (all items). Also in Session 1: move the four standards skills to optional-skills/ after the frontmatter fix (0221 §5). |
| [T1b-packaging-vocab-delivery](T1b-packaging-vocab-delivery.md) | READY_WITH_FIXES | Session 1: items c1, c2, b3 (+ the lint pins b3 needs, mirror). Session 2: items a1–a5 (+ mirror). Session 8, only if the intent candidate is NOT adopted: items b1, b2, b4, b5. Item b-keep stays untouched until intent removes resolve. |
