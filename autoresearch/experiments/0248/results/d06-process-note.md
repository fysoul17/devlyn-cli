# 0248 d06 Codex/B process note

Read-only inspection of `0248-live/out-measured/d06-f23-codex-b`, under effective 0248 registration-v2/freeze-measured-v2. No new tests, models, authentication calls, source changes, or evaluator replays.

The original outcome remains **PRODUCT_INCOMPLETE / COMPLETE**: **473,694 input / 18,835 output tokens, 343.83193679200485 seconds**, public **53 PASS**, delivery PASS, cleanup CLEAN. Priority rollback and single-warehouse FEFO pass; submillisecond ordering and offset-equivalence fail. The source and raw failures explain both failures without a new experiment.

The actual owner is **Codex gpt-6-astra/max**, session `01a127c0-49e3-7610-b4c0-557c7100d9c4` (native rollout turn context LF 8). Native multi-agent v2 capability is present, but the archive has one owner trace/session, no launched child sessions, and no peer turns; peer activation is false. This is B, not a pair cell.

**Proven implementation mechanism.** In bin/cli.js:44, validation admits arbitrary fractional-second digits. At lines 98–99, ordering subtracts `Date.parse(a.submitted_at)` and `Date.parse(b.submitted_at)`, then breaks equal values by ID. This comparison retains millisecond precision, so different accepted submillisecond instants become ties. The retained evaluator's actual CLI output then shows the ID fallback consuming stock in the wrong order:

| Frozen case | Expected accepted IDs | Actual accepted IDs |
| --- | --- | --- |
| `submillisecond-order`: `a-later=.0002Z`, `z-earlier=.0001Z`, stock 1 | z-earlier | a-later |
| `offset-equivalence`: add `b-equivalent=01:00:00.000100+01:00`, stock 2 | b-equivalent, z-earlier | a-later, b-equivalent |

Both actual commands exit 0 with empty stderr, but reject the wrong order. The second failure is **not evidence that offsets are ignored**: Date.parse normalizes offsets, and the equivalent instant is correctly representable at the same millisecond. The failure is that the later .0002 instant also collapses into that tie, allowing a-later to precede the earlier/equivalent orders. The raw precision result binds CLI SHA `928f09a4979825510943427cdcd6d6a1edd69a1dbb309fedae49122748a6adf0`, which equals the inspected file. Both retained failures concern accepted/rejected ordering; no remaining-row interpretation is needed to explain them.

**Why public 53 misses this.** The public suite has 13 top-level tests plus 40 nested validation cases. Its ordering test at tests/cli.test.js:99–121 exercises priority, a whole-second offset crossing (`09:00+02:00` before `08:00Z`), and identical `08:00Z` timestamps resolved by IDs a/b. It contains no ordering witness with nonzero submillisecond fractions and no equivalent offset forms adjacent to a distinct submillisecond instant. A `.000Z` value used in the validation fixture adds no precision discrimination. Thus the tested whole-second behavior passes while the missing distinction survives; the large validation count does not supply that missing ordering coverage.

**Observed engineering steps.** Owner stdout LF 20 records real Date.parse probes for calendar rollover, leap days, ordinary offsets, invalid hours, and offsetless input. None probes fractional precision. Baseline public tests pass 3 at LF 22. An early added-test run reports pass 3/fail 9 at LF 28; subsequent implementation checks pass 50 at LF 35, targeted validation/non-finite checks pass 42 at LF 40, and final public tests pass 53 at LF 45. The owner also runs diff checks and commits only the allowed files at LF 49. These are real validation and delivery steps, but their observed examples do not challenge the lossy timestamp comparison. The owner's final “No unresolved issues” is therefore broader than the later frozen evaluation supports.

The local commit is `37482de3974effd2fdfb086a2f5f91ccc202192c`, baseline `1b58ba50e737adb5607430e81ce63a562a8507ca`, modifying only bin/cli.js and tests/cli.test.js. Delivery PASS and CLEAN are preserved. This note does not infer that a peer, another model, or a particular guide would have prevented the miss, and makes no general harness-performance claim.

**Integrity.** All **154 protected files** match before/after (raw verdict/results, source, owner logs/trace/rollout, effective registration/freeze). The SHA-256 of the sorted compact JSON path→hash inventory is `40df165a1913caeedebcd94b83448b06ce2f517744d745c634af469bfcc0cfba`. Key unchanged hashes:

| File | SHA-256 |
| --- | --- |
| sibling verdict | `462530dd619068d80153dc553421d33e283e0534f30698c952b93c3faa6fe5af` |
| checks-raw.json | `dcb3bf70f5db5f9b9611d03cc07452f8f7b49d13cd3e1a64a84e7fbf85c2d8e5` |
| run/stdout | `717d7fead7b03310b160a2327e3a240b24f90e3cb5ec7955f0973c89518d97fb` |
| bin/cli.js | `928f09a4979825510943427cdcd6d6a1edd69a1dbb309fedae49122748a6adf0` |
| tests/cli.test.js | `f1a80edf22edb3cb681429fe3c32381e0fde9933e4988984b6690f1377c9b35f` |
| registration-v2.md | `866b4384dd32f891b8539ba93a6dd645e2010d85d2fa02966d3203e1fb27e91f` |
| freeze-measured-v2.json | `16b49370e62922eed63aa3396102f89cfb258c7cc001503a407d6bf6045e00d3` |
