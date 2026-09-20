# 0193 — invalid optional engine configuration

2026-09-20. Mission1. Root direct; zero resolve invocations, including controls.
Source verification and delivery evidence: `.devlyn/0193/FINAL.md`.

## Why this iteration exists

A dangling project `.devlyn/engines.json` was treated as absent: status selected
its default engine and an edit replaced the unresolved link. The maintainer
selected this real source defect after no independent external request was
available. It does not satisfy Mission1 independent field gate15.

Why did defaults win? `read_config` used `Path.exists()` to infer absence.
Why was that inference invalid? The predicate follows the leaf link and loses
filesystem failure information. The invariant is that only genuine optional
absence may use defaults; an existing invalid entry or read error must block.

## Registered comparison and actual result

Preregistered `ed698f3`, frozen `.devlyn/0193/REGISTRATION.json`: unchanged0179
minimal B versus native A, requested Astra/high, serial ABBA, two draws each.
Same original source, callers, adapters, request/public tests and0191 transport;
1800s ceiling, no rerolls, participant repair or oracle changes after exposure.
Prediction: both B complete, at least one A misses a requirement. **Falsified.**

| Draw | Arm | External checks | Full completion | Wrapper-return seconds |
|---|---|---|---|---|
|01-A|native|35/35|PASS|155.623|
|02-B|minimal|35/35|PASS|150.435|
|03-B|minimal|35/35|PASS|142.754|
|04-A|native|35/35|PASS|143.934|

Every returned artifact passed the public suite (7 tests) and original self-test.
All53 completed tool/file events, final messages and complete diffs/tests were
reviewed. Protected inputs and sealed workspaces are unchanged; only allowed
source/tests changed. No outside task operation, pipeline invocation, network
publication or remaining task debris was found. `.devlyn/task-inputs` contains
only the launcher's unchanged native-options input. No runtime-debris exemption
was needed. One B used an equally valid read-first formulation.

Totals: native299.557s, minimal293.189s. Completion saturates2/2 in each arm:
**NON_DISCRIMINATING; no operational adoption or added minimal quality claim.**
Two draws on one selected task, with independent reviews overlapping early draws,
cannot establish general speed superiority. Native output counters total8167 A,
8047 B (reasoning1129/1149 is included, not added again); invoice dollars and
provider-internal weights are unverified. This is not a resolve/full-workflow
comparison. Preserve0187 NO-GO and0190–0192 non-adoption.

## Instrument correction before exposure

Original calibration failed because Python3.14 `Path.exists` and `Path.lstat`
bypassed the patched `Path.stat`. Actual source/controlled calls confirmed that
prediction. Injection now targets stat/lstat/open seams. Original15/35,
reference35/35 and an equivalent builtins.open positive35/35; follows-links27/35,
catch-all28/35, rejects-links34/35, requires-optional33/35 match exact frozen
failure sets. Original public FAIL, positive public PASS, both self-tests PASS.
The initial calibration failure and an incorrectly constructed open-positive
IndentationError remain recorded. No expected failure labels were weakened.

Opus protocol advice found no blocker; its method-specific injection concern
was corrected before freezing, with the second positive proving equivalence.
Unexpected checker exceptions now produce visible failing rows, missing required
registry inputs block, and stopped draws are explicitly assessed NOT_RUN or
INCOMPLETE. Grok supplementary protocol advice returned no blocker after launch;
it reviewed the earlier packet, not the final open-seam refinement.

## Production repair and verification

Replace the lossy absence predicate with `lstat` inside the shared reader's error
boundary. Catch only `FileNotFoundError` from that entry inspection for optional
defaults; failed reads reach the existing path-bearing BLOCKED error. All callers,
API, policy, required-file behavior, valid-link binding/edit semantics and custom
fields remain unchanged. Canonical source and repository mirrors are synchronized.

Two package-driver regressions exercise bad entries/errors and valid-link
preservation. The actual npm installation passes19 PackageTests and the existing
role self-test; the external oracle also passes35/35 against packed bytes.
Original-source controls fail19 subcases with5 errors; replacing lstat with stat
fails5 subcases with1 error, so the guard cannot simply be removed or weakened.
Full required lint passes in325.487s. Symlink cases intentionally skip on Windows;
other cases run there. Native CI, final acceptance and delivery are recorded in
the FINAL pointer.

Actual Opus5 and Grok4.6 source reviews report zero CRITICAL/HIGH/MEDIUM. Fable5.1
was unavailable due quota; Grok4.7 rejected its model ID. Both failures remain.
Grok reported4.6-build and advertised tools/MCP/skills despite flags, but emitted
zero tool calls: treat it as static supplied-packet advice, not proof of isolation.
Concurrent swaps, dangling directory ancestors, crash durability and general
filesystem confinement remain outside the repair. No npm release.

## Principles check

- Preflight0 / Mission-bound: fixes a real default-routing/destructive-edit defect;
  Mission1 stays open, independent field gate15 is not closed.
- No workaround: distinguish absence at the shared reader; preserve visible errors.
- No overengineering: replace one predicate, no new product API/helper/flag.
- No guesswork: pre-registered prediction rejected; raw failures and tie retained.
- Worldclass / Production ready: independent source reviews and package negatives;
  final required gates and delivery status stay explicit in FINAL.
- Best practice: standard lstat/FileNotFoundError and existing error boundary.
- Optimized: no new runtime machinery or duplicated caller fixes; no speed claim.
- Subtractive-first: removed the old predicate; guard-deletion control regresses.
