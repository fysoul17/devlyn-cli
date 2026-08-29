# iter-0110 apparatus
This cell measures whether serialized, real corpus work at a verified session
horizon changes the **relative** late-minus-early manifestation-fail rate of
opus-5 versus opus-4-8. It does not claim absolute opus-5 degradation.
The gate chain is: G0 frozen crossover schedule/power reachability; G1
task-balanced EARLY transport against the published anchors; G2 request-level
custody and horizon attestation for each deciding LATE row; then G3 paired
estimand support. Normal terminals exit 0; transport refusal exits 2; unscored
structural or infrastructure input exits 3.
G0 evaluates every criterion at each correlation-envelope member (ρ = 0,
0.25, 0.5); the empirical worst member decides. The smallest passing scale is
five independently stageable sweeps: 120 sessions and 960 task attempts total
(24 and 192 per sweep). Sweeps 2–5 are fired into the SAME `--out` and `--run-id` as sweep 1 — the launcher resumes that manifest and the scorer reads one manifest for all 120 sessions. Phase A runs the first sweep-1 block alone, one
session at a time in schedule order, and persists A5 after each clean matrix
session. A5 requires unbroken custody plus the registered 48,000-token horizon threshold (AMENDMENT 5: re-derived from both matrix engines' gate-session ledgers — footprints are engine-dependent; boundary-4 PEAK) by boundary
4 (strictly before the first LATE position 5); a clean subject below threshold writes `FAIL_FAST_THRESHOLD_UNREACHED`; a completed gate block lacking a clean matrix subject writes `A5_SUBJECT_UNAVAILABLE`. Launch is gated by the AMENDMENT 4 prefix attestation: immediately before the fresh run root, a fixed 2-token probe per matrix engine in the driver's exact shape must show prefix (cacheCreation+cacheRead) ≥ the derivation baseline (29,993 / 29,022); a smaller value blocks the launch. Once both
matrix engines have passing A5 records, Phase B runs the remaining block work:
each block stays serial on one lane to preserve its ABBA matrix unit, while
distinct blocks may occupy parallel lanes. AMENDMENT 6 makes only a driver's
`infra_invalid:true` 429/529 row transport-void: stop that block at its first
such row, record its unrun suffix, and keep the immutable attempt in its own
directory. Resume replays each void block whole in a fresh API-attested window,
with a fresh attempt directory and no carried session/custody/cache state. The
first complete transport-clean attempt is designated mechanically; outcomes,
catastrophic/custody fields, and position clustering never enter designation.
At most two replacement blocks are allowed per root; a third is sticky
`REPLACEMENT_CAP_EXCEEDED`, rejecting the shared-account venue: D becomes
mandatory or the iteration closes `VENUE_REJECTED`. A void gate block has void A5 records and A5 is
re-derived from its designated replacement. `LAUNCH_COMPLETE` requires exactly
one designated clean attempt for every block; the scorer joins designated rows
only.
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
