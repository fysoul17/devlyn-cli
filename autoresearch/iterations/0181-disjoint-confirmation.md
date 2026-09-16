# 0181 — disjoint minimal-direct confirmation

2026-09-16 KST. Root direct, no resolve. This continues0180's positive development
screen using the unchanged355-word0179 candidate on fresh configuration-overlay
and bounded-async-map tasks. The [protocol](../experiments/0181/PROTOCOL.md) was
committed as `b389c2b` before quality execution. Customer instructions are unchanged.

## Admission evidence

These two root-authored synthetic tasks are disjoint from candidate tuning and
0180's selection-parser/SQLite-JSON inbox cases. They are not representative
workload sampling or independently authored tasks. References use recursive versus
iterative overlay, and rolling task windows versus fixed async consumer pools.
Preserved legacy tests/NOTICE, observable checks and isolated defect mutations
constrain admission without requiring a particular implementation strategy.

Final calibration **27/27**: four valid products pass and23 expected rejects
include both seeds. Initial preparation failures remain in `.devlyn/0181/`:

- An initial syntax check caught an extra brace in the small oracle before calibration.
- The pool reference initially cancelled a worker twice, interrupting its async
  cleanup. Calibration1 caught it. Shielding the initial gather gave cancellation
  ownership to the outer cleanup block.
- Root then predicted and reproduced a shared miss: a single caller cancellation
  during worker-error cleanup interrupted both allegedly valid implementations.
  Both returned with `cleanup_finished=False`. Final drain shielding plus awaiting
  that drain on cancellation repairs this. The oracle now covers this existing
  task requirement and rejects unshielded cleanup and double-cancel variants.

Initial Fable high-effort advice timed out at605.126s without a verdict. Grok
completed in588.354s with NEEDS_WORK, but its blanket claim that CPython3.11+
re-injects cancellation on every await is contradicted by actual3.14.6 reference
checks and inspected CPython source. Its version-explicitness advice was accepted;
the frozen runtime was also already recorded by the launcher registration.

Final independent medium-effort Fable/Grok advice both **ADMIT** the repaired
sources (160.468s/319.287s), with no tool calls. Root adjudicated each claim;
these reviewers saw root-supplied calibration and disputed-evidence dispositions,
so their agreement is validation, not independent discovery of the root defects.
A tautological event assertion was then deleted; exact final calibration4 still
passes27/27. No candidate tuning or quality draws occurred during these repairs.

Actual A/B edit/test probes pass, with normalized rendered-context parity after
removing exactly B's candidate. Root inspected commands and outputs: A tested
ancestor AGENTS paths, which were absent; no foreign instruction reads were
observed. Neutral participant Git roots live outside the research repository.
This is observational confinement, not OS read isolation, provider-request capture
or attested server-model identity.

Freeze: `2026-09-16T04:59:36.562685Z`,32 file hashes, registration SHA-256
`77bcb4e8d9e334eb62cfd7c3ab0bb64c7e7203fcb1ecbbfcd87ee40514560dcf`.
Native Codex0.154.0, requested Astra/high, CPython3.14.6; small ABBA/hard BAAB,
two repeats per arm with300/600-second native budgets. Raw argv, config/render
evidence, native events and source seals remain under `.devlyn/0181/`.

## Observed result

All eight native calls exit0, with no rerolls, timeouts, substitution or changed
inputs. Mechanical and root-adjudicated complete success agree: **A2/4, B3/4**.
There is no matched A-success/B-failure. Both independent label-withheld advisors
agree on the same five complete products and three requirement misses.

| Task / repeat | A native seconds | A complete | B native seconds | B complete |
| --- | ---: | --- | ---: | --- |
| small1 | 71.829 | PASS | 79.613 | PASS |
| small2 | 72.595 | PASS | 75.041 | PASS |
| hard1 | 108.655 | FAIL: cleanup interrupted | 135.751 | FAIL: cleanup interrupted |
| hard2 | 120.063 | FAIL: cleanup interrupted | 173.446 | PASS |

The frozen event-controlled check reproduces one boundary in all three failures:
worker0 fails; worker1 enters async cleanup; the caller cancels the outer map once.
Their unshielded cleanup gather re-cancels worker1 and returns before cleanup
finishes. `cleanup_finished` remains false. This is the existing single-caller-
cancellation requirement, not a post-dispatch expansion or repeated caller cancel.
Sealed source locations: `.devlyn/0181/products/product-3/async_map.py:43`,
`product-1/async_map.py:44`, and `product-6/async_map.py:43`; the protected drain is
`product-4/async_map.py:41`. The raw mapping and failing checks are retained.

B hard2 shields the cleanup gather and awaits it after caller cancellation.
Its native command history shows its own regression fail before the in-session
repair. No operator feedback or oracle access was supplied or observed. All eight
participant-authored suites pass (9–12 tests), including the three incomplete
products; test quantity is not a product-quality measure.

Final Fable/Grok source reviews received mechanical outcomes and task/seed/final
sources with arm labels, AGENTS and timing removed. They validate exposed findings,
not independent discovery. Fable calls the defect medium and Grok high; root counts
the explicit requirement miss regardless of severity agreement. No additional
blocking finding remains on the five successful products. Root remains unblinded.
All actual commands were inspected: hard2 A's ancestor AGENTS scan was empty;
no foreign instruction, hidden-assessment read or publication was observed.

**POSITIVE_CONFIRMATION_ONLY; no promotion.** The registered B>A/no-paired-regression
rule is met on disjoint tasks, but the incremental gain is one successful draw,
not reliable success across both hard repeats. This supports retaining the candidate
for broader registered comparison; it does not establish representative superiority
or justify replacing current instructions. Neither task nor candidate was retuned.

Consumed native time: **A373.142s / B463.852s**. Matched complete small products:
A144.424s / B154.654s. No hard pair has two complete products, so its incomplete
A timings cannot establish faster verified completion. External mechanical
assessment adds0.756s/0.725s. Four final source-review calls consumed233.089s in
sum,82.884s shared wall interval; no per-arm allocation is invented. Preparation,
root authoring/adjudication and inactive conversation intervals are separate;
root labor is not precisely metered. No speed or equivalence claim follows.

Native output fields total10,619/12,804; reasoning-output fields1,410/2,379 are
reported separately, not added twice. Input fields257,827/402,993. Actual native
cost is UNKNOWN. These are observed within-screen fields, not a causal efficiency
comparison with0180 or a whole-program cost estimate.

## Scope and custody

The primary gate is complete requirements with no unresolved HIGH/CRITICAL
finding. B must exceed A successes with no paired A-success/B-failure; a tie is
NO_LIFT, not equivalence. Neither this two-case screen nor0180 justifies replacing
installed instructions; there is no installed-contract arm. Independent review
and repair as an execution treatment remains a separate comparison.

Research files are excluded from the npm package; full source lint passed.
Source verification is complete. PR/merge delivery and owned-resource cleanup
are tracked separately in `.devlyn/0181-delivery/FINAL.md`, under receipt
`fc6753e210af09115442f8a9`. Participant roots under `~/.local/share/nx01/0181-participants/`
are source/recovery evidence; exact final product bytes are also in
`.devlyn/0181/products/`. Frozen inputs and all raw failures remain in custody.
Original workspace WIP, prior frozen experiments and A16 remain preserved.
Mission1 remains active; no npm release.
