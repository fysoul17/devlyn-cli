# iter-0110 apparatus

This cell measures whether serialized, real corpus work at a verified session
horizon changes the **relative** late-minus-early manifestation-fail rate of
opus-5 versus opus-4-8. It does not claim absolute opus-5 degradation.

The gate chain is: G0 frozen crossover schedule/power reachability; G1
task-balanced EARLY transport against the published anchors; G2 request-level
custody and horizon attestation for each deciding LATE row; then G3 paired
estimand support. The scorer uses the G0 shared complete-replicate interaction,
bootstrap, and terminal path. Its normal terminals exit 0; transport refusal
exits 2; unscored structural or infrastructure input exits 3.

G0 evaluates every criterion at each correlation-envelope member (ρ = 0,
0.25, 0.5); the empirical worst member decides. The smallest passing scale is
five independently stageable sweeps: 120 sessions and 960 task attempts total
(24 and 192 per sweep). Sweeps 2–5 are fired into the SAME `--out` and `--run-id` as sweep 1 — the launcher resumes that manifest and the scorer reads one manifest for all 120 sessions. Phase A runs the first sweep-1 block alone, one
session at a time in schedule order, and persists A5 after each clean matrix
session. A5 requires unbroken custody plus the registered 64,000-token horizon threshold (AMENDMENT 3: re-derived from the opus-5 gate-session ledger + per-engine overhead; boundary-4 PEAK) by boundary
4 (strictly before the first LATE position 5); a clean subject below threshold writes `FAIL_FAST_THRESHOLD_UNREACHED`; a completed gate block lacking a clean matrix subject writes `A5_SUBJECT_UNAVAILABLE`. Once both
matrix engines have passing A5 records, Phase B runs the remaining block work:
each block stays serial on one lane to preserve its ABBA matrix unit, while
distinct blocks may occupy parallel lanes. Three consecutive sessions with any
`infra_invalid` row write `INFRA_ABORT`; abort terminals are sticky, so
continuation requires a fresh run root and run id.

Every launch requires an operator-authored `--window-attestation` JSON that
re-attests the three recorded 1,000,000-token measured planning windows, records its exact
bytes in the manifest, and verifies the complete `scripts.sha256` inventory
before a session starts. Build artifacts (`__pycache__`) are not fixture bytes
— remove them before preflight; the pin refuses trees that carry them. The
scorer requires that manifest and verifies the recorded `rows.jsonl` and
`boundary-ledger.json` digests before scoring.

G3 requires at least **47 non-tied early/late pairs per matrix engine** and all
20 complete crossover replicates. The S=5 G0 receipt,
`/tmp/iter0110-t3/g0-grid-final.json`, has 160 pairs per engine and yields
`ceil(46.975) = 47`: 46.975 is the conservative
2.5th-percentile lower support bound in the S-null, ρ = 0.5, opus-5 cell, the
smallest bound across the registered scenario/correlation-envelope/matrix-engine
grid.
