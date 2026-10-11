# Package construction prediction

Registered before construction on 2026-10-10: B is a byte-identical copy of
0237's sealed two-fix baseline archive (8c4dcdfa79ba7fed8541418f09475aa9edd5bbaaa010690b26254ed42e34a6e8).
C changes exactly package/config/skills/_shared/task-completion.md by replacing
the one sentence in DRAFT.md. Every other archived regular file is identical,
including roots, helper and generated instruction fingerprints. No root template
changed, so no template generation is needed. This is a research package data
edit, not a publish. The product checkout remains unchanged.

The builder refuses an unexpected baseline or non-unique sentence, preserves
archive member metadata except the changed file size, and compares the complete
payload maps. Installation is a separate model-free check before dispatch.

First construction attempt exited 1 before creating a destination:
`ValueError: baseline sentence is not unique`. Inspection showed the existing
sentence contains a source newline between "the" and "task tree". The builder's
exact OLD string was corrected to those existing bytes. Prediction before the
second attempt is unchanged: exactly one guide payload changes. No model ran.
