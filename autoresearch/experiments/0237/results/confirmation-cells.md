# Confirmation evidence ledger

As of 2026-10-10T10:16:23.660360+00:00. Final verdicts only; no regrading or admission decision.

All finalized attempts, including failures and recorded native children, remain charged. Input includes cache; output includes reasoning. Costs are not billed tokens/dollars. Use owner_seconds, not dispatcher elapsed; holds can delay FINISH. Research assessors are separate.

Recorded source/oracle checks plus matching local commit; no PR/merge or general-correctness claim.

| Block | Final / scheduled | State |
| --- | ---: | --- |
| CF-CONFIG | 5/12 | INCOMPLETE_NO_DECISION |
| CF-LEASE | 0/12 | INCOMPLETE_NO_DECISION |

| Final cell | Raw status | Source / delivery | Owner s | Input incl. cache | Output | Usage | Integrity |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| [f01-CF-CONFIG-codex-B-r1](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f01-CF-CONFIG-codex-B-r1.json) | CHECKS_PASS | PASS / PASS | 478.963 | 760,948 | 19,140 | COMPLETE | MATCH |
| [f02-CF-CONFIG-claude-C-r1-auth1](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f02-CF-CONFIG-claude-C-r1-auth1.json) | PRODUCT_INCOMPLETE | PASS / FAIL | 2,269.698 | 7,218,661 | 240,858 | COMPLETE | MATCH |
| [f03-CF-CONFIG-codex-A-r1](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f03-CF-CONFIG-codex-A-r1.json) | CHECKS_PASS | PASS / PASS | 371.906 | 305,590 | 13,357 | COMPLETE | MATCH |
| [f04-CF-CONFIG-claude-B-r1](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f04-CF-CONFIG-claude-B-r1.json) | PRODUCT_INCOMPLETE | FAIL / PASS | 3,276.344 | 44,253,577 | 400,250 | COMPLETE | MATCH |
| [f05-CF-CONFIG-codex-C-r1](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f05-CF-CONFIG-codex-C-r1.json) | CHECKS_PASS | PASS / PASS | 435.635 | 621,831 | 15,940 | COMPLETE | MATCH |

| Task / engine / arm | Final attempts / scheduled | Recorded correct | Total owner s / input / output | Per recorded correct s / input / output |
| --- | ---: | ---: | --- | --- |
| CF-CONFIG / claude / A | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |
| CF-CONFIG / claude / B | 1/2 | 0 | 3,276.344 / 44,253,577 / 400,250 | unknown / unknown / unknown |
| CF-CONFIG / claude / C | 1/2 | 0 | 2,269.698 / 7,218,661 / 240,858 | unknown / unknown / unknown |
| CF-CONFIG / codex / A | 1/2 | 1 | 371.906 / 305,590 / 13,357 | 371.906 / 305,590.000 / 13,357.000 |
| CF-CONFIG / codex / B | 1/2 | 1 | 478.963 / 760,948 / 19,140 | 478.963 / 760,948.000 / 19,140.000 |
| CF-CONFIG / codex / C | 1/2 | 1 | 435.635 / 621,831 / 15,940 | 435.635 / 621,831.000 / 15,940.000 |
| CF-LEASE / claude / A | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |
| CF-LEASE / claude / B | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |
| CF-LEASE / claude / C | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |
| CF-LEASE / codex / A | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |
| CF-LEASE / codex / B | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |
| CF-LEASE / codex / C | 0/2 | 0 | unknown / unknown / unknown | unknown / unknown / unknown |

Totals include final attempts only and are provisional until the block completes. Unknown costs and zero-success denominators stay undefined. Recorded correct means the original CHECKS_PASS status; an integrity/QA finding requires review and does not silently alter that status.

Slots without an accepted final identity:

- `f06-CF-CONFIG-claude-A-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f07-CF-CONFIG-claude-A-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f08-CF-CONFIG-codex-C-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f09-CF-CONFIG-claude-B-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f10-CF-CONFIG-codex-A-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f11-CF-CONFIG-claude-C-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f12-CF-CONFIG-codex-B-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f01-CF-LEASE-claude-B-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f02-CF-LEASE-codex-C-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f03-CF-LEASE-claude-A-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f04-CF-LEASE-codex-B-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f05-CF-LEASE-claude-C-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f06-CF-LEASE-codex-A-r1`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f07-CF-LEASE-codex-A-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f08-CF-LEASE-claude-C-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f09-CF-LEASE-codex-B-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f10-CF-LEASE-claude-A-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f11-CF-LEASE-codex-C-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.
- `f12-CF-LEASE-claude-B-r2`: NO_DISPATCH_RECORD; outcome/cost unknown.

Authentication recovery: `f02-CF-CONFIG-claude-C-r1` → `f02-CF-CONFIG-claude-C-r1-auth1`; binding MATCH. [Recovery artifact](/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0237/results/confirmation-recovery.json). The original guard stays recorded; a never-dispatched cell has no measured owner cost, not a zero-cost completion. Both final identities, if present, are charged and require review; they cannot complete one slot.

[Frozen full schedule](/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0237/results/confirmation-registration-freeze.json) · [Registration](/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0237/confirmation-registration.md) · [Detailed bindings, original verdicts, source/QA hashes and aggregates](confirmation-cells.json). Legacy baseline task hashes label sibling tasks.json; selected task identity comes from seal.inputs.

Frozen registration bindings: MATCH. Existing QA is checked byte-for-byte. Added/changed production source still requires normal source review; this ledger runs no tests.

Refresh explicitly: `python3 -B autoresearch/experiments/0237/results/refresh-confirmation-cells.py`.
