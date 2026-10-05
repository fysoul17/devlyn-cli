# RETIRED — F9-e2e-ideate-to-resolve

**Retired**: 2026-10-05 (ideate loop product track)
**Source SHA**: `79076e0b` (the last commit with this fixture active).

## Why retired

Its arm prompt ran `/devlyn-ideate --quick`, waited for
`spec ready — /devlyn-resolve --spec <path>` and then ran resolve. The ideate
loop removed `--quick` (a removed flag stops with its migration instruction),
and ideate now plans loop packages that its own drain executes, so the chain
cannot run against the current tree. Its headroom had already failed in
`20260512-f9-e2e-headroom` (bare 60 / solo_claude 90, bare headroom 0, bare
judge disqualifier), so it was never pair-lift evidence.

## When to consult this archive

- Replaying a pre-ideate-loop run of the novice end-to-end flow.
- Reading historical results under `benchmark/auto-resolve/results/` that name
  this fixture.

## What lives here

The fixture files as of `79076e0b`. `run-suite.sh` does not discover retired
fixtures, and `run-fixture.sh` no longer carries the F9-only ideate→resolve
prompt; a novice flow for the ideate loop needs a newly designed fixture.
