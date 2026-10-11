# AF1 completed evidence through d18

Read-only audit of completed d13–d18, 2026-10-10. No model calls, reruns, fixture edits or cost subtraction. [cells.json](cells.json) and [cells.md](cells.md) retain eleven raw final outcomes: five excluded UA1 attempts and all six AF1 cells.

## d17 provenance and predicate integrity

[d17's original verdict](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d17-EQ3-AF1-codex-B-r1.json) is `CHECKS_PASS`: five oracle rows pass, assessed-source checks pass, local delivery passes, model identity matches `gpt-6-astra/max`, and usage is complete with no gaps. Raw owner cost is **419.312111791005 seconds, 639,136 processed input tokens, 16,228 output tokens**. Input includes 580,224 cached tokens; output already includes 9,745 reasoning tokens. Those subsets must not be added again. No child sessions were recorded.

The source starts at allocation `ee8e4c1a6977a95bdf3fe840b447c3ae903cc8d9` and finishes at accepted local commit `4aa8d77135db0240893907dbfe75c3e2cdc6bfe3`. The locator selected that commit via its owned, accepted, local-only receipt. [snapshot.json](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d17-EQ3-AF1-codex-B-r1/snapshot.json), [delivery.json](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d17-EQ3-AF1-codex-B-r1/delivery.json), and [checked.json](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d17-EQ3-AF1-codex-B-r1/checked.json) agree. Recomputed full snapshot tree, checks hash and delivery hash match the checked binding. Evaluated intake SHA-256 is `b1eba12f4e00c01e54ded1fb1be81031b7343e8b7f9a4a5e17056e9b0e01ffda`.

The actual baseline-to-commit diff was read. Its only changed file is [visible/intake/hold_intake.py](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d17-EQ3-AF1-codex-B-r1/snapshot/visible/intake/hold_intake.py): reservation records both unit/order links and states; expiry processing releases the matching order, quarantines the unit, records isolation once and drains processed events. It adds no predicate replacement, import hook or side effect that weakens the evaluated QA modules. All other original visible files match their baseline bytes/modes; no visible files were added.

The exact protected files below remain unchanged for **every completed AF1 cell d13–d18**:

| Protected visible file | SHA-256 |
| --- | --- |
| matching/crossmatch_reserver.py | `8f189ba40ca4e4e3231eb5823fc5fe8b55f0360b43a2a188098ae1bb184e8ea5` |
| qa/expiry_release.py | `01146fd73b2a9d2a813d7b02b4f846e5e035a70fb7de792e42ed4f50420838d5` |
| qa/run_checks.py | `7bb6fd92f38b78a89d3d91787c7433adc273a655150977e8659bc2790a5748cd` |
| qa/scenarios.txt | `24be2fe42966ed508820e98581e700fed1ae21e80810ca820bb9c072dcb1496e` |

Each baseline matches the registered visible-source hashes. The hidden AF1 oracle hash remains `3bdc42c33b48bab3168da726eb892410364024f64ad64b223f848a9c82ab46b1`, matching its immutable control manifest. All **54 sealed input-file hashes per cell** were reread and match for d13–d18, including the actual selected tasks, runtime and runner dependencies. The inherited `baseline.tasks_sha256` still refers to sibling `tasks.json`; selected-task provenance comes from `seal.inputs`, as already disclosed in the result summary.

## d18 final integrity crosscheck

[d18's original verdict](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d18-EQ3-AF1-codex-C-r1.json) is `CHECKS_PASS`, all five oracle rows pass, local delivery passes and identity matches `gpt-6-astra/max` with no recorded child sessions. Raw cost is **336.2834316249937 seconds, 574,930 processed input tokens, 12,788 output tokens**, COMPLETE with no gaps. Included subsets are 518,528 cached input and 7,183 reasoning output; do not add them again.

Allocation `659e76b4265a5698e8a634053b553fdca5a316c9` leads to accepted local commit `c81c8801997ed3244c6784e4f73dcfcef7090642`, selected by its owned local-only receipt. Snapshot, checks and delivery bindings all match. Evaluated intake SHA-256 is `181eb25955ee66b20caea3b31bc74b51c582ab6141545e1d4a90e12a40c30608`. The actual diff changes only the intake implementation and adds `visible/qa/test_hold_intake.py`; the additive tests exercise the existing matching/expiry consumers. It neither replaces nor weakens any original predicate. All other original visible source bytes/modes remain unchanged.

## d17 work after the source was verified

The retained [native Codex transcript](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d17-EQ3-AF1-codex-B-r1/home/.codex/sessions/2026/10/10/rollout-2026-10-10T04-04-46-01a123fc-17c5-7102-937f-48ad3d58247c.jsonl) distinguishes normal protocol work, a corrected owner mistake, and a retained cleanup condition:

- Product patch at line 77; successful public/lifecycle checks at 88 onward; public status at 109 says the source checks passed. The helper scan at 98 and targeted source read at 110 inspect the local completion route under the caller's restrictions. Allocation at 119, exact patch transfer/evidence at 126, local commit at 133 and acceptance/completion at 142 are ordinary frozen-B delivery work, with costs fully charged.
- Completion returns `LOCAL_ONLY` plus scratch `RETAINED: unknown process access` at 145. At 153 the owner writes a reconciliation script that assumes the persisted receipt has `receipt['status']`. It fails with `KeyError: 'status'` at 156 before performing reconciliation. The persisted receipt instead has `delivery: LOCAL_ONLY`; the returned CLI envelope has `status: LOCAL_ONLY`. The owner reads the actual receipt and relevant helper sections at 160–164, changes its assertion to `receipt['delivery']` at 168, and reconciliation succeeds at 171. This is a concrete self-authored protocol-assumption error, corrected within the run; it is not evidence that the helper violated a documented persistent `status` field contract.
- That final call also invokes the helper's internal `verify_files` and `removable` functions to check custody and whether removal is safe. `removable` reports unknown process access, so the owner retains the task worktree and reports cleanup pending at 180. d17 does not inspect the offending `/proc` entry. Its refusal message matches the earlier cleanup family, but this trace alone does not establish that its precise cause was the same zombie case or that the admitted fix would eliminate this particular refusal.

There is an observed 210.412-second interval from the public source-passed message (04:08:13.837 UTC) to the final report (04:11:44.249 UTC). That interval includes legitimate delivery, evidence custody, local reconciliation, correction of the receipt-key assumption and final reporting; it is **not** measured avoidable overhead. No token or wall-time subtraction is made. The source reads after the actual failure and cleanup condition satisfy the proposed selective-loading exception, so this trace does not support a blanket instruction to skip them. It supplies a bounded example of return-envelope versus persisted-receipt confusion; it does not itself establish a new residual solver mechanism or justify another abstraction.

## Final AF1 resource comparison

The registered caller-discovery prediction is fewer missed nonlocal contracts without resource regressions; ceiling ties do not demonstrate quality lift ([iteration:48](/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/iterations/0237-minimal-solo-harness.md:48)). All six AF1 products pass the five predicates, so there is **no observed quality lift** on this task. Ratios below are C divided by its same-engine comparator; percentages describe these single draws, not a causal savings estimate.

| Engine / comparator | Owner wall ratio | Processed input ratio | Output ratio |
| --- | ---: | ---: | ---: |
| Claude C/B | 0.960215 (**3.979% lower**) | 0.733623 (**26.638% lower**) | 0.952464 (**4.754% lower**) |
| Codex C/B | 0.801988 (**19.801% lower**) | 0.899543 (**10.046% lower**) | 0.788021 (**21.198% lower**) |
| Claude C/native A | 1.367457 (36.746% higher) | 2.917358 (191.736% higher) | 1.348622 (34.862% higher) |
| Codex C/native A | 1.555673 (55.567% higher) | 2.742542 (174.254% higher) | 1.607340 (60.734% higher) |

C is cheaper than frozen B on all three resource measures in each engine's single draw, with equal predicate outcomes; native A remains cheaper than C on all three measures in both engines. The reduced AF1 diagnostic explicitly cannot alone admit a template change ([iteration:293](/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/iterations/0237-minimal-solo-harness.md:293)). UA1's five retained attempts are excluded from admission because of oracle-contract defects; they cannot supply missing evidence of caller discovery. These results do not supply repeated confirmation, control-task regression results or untouched transfer evidence.

All helper/delivery work stays charged to its actual owner. [The helper audit](af1-helper-audit.md) explains B's real cleanup diagnosis and the limits of assigning cached-response usage to individual activities. The admitted cleanup/document fixes change the prospective baseline; neither subtracting estimated helper cost nor assuming this single C/B gap survives those fixes is justified. Root's next step is fresh confirmation of the same caller clause against the accepted fixed baseline before any pair model call. This is a decision to verify a promising resource result, **not admission of C**; no new post-hoc hypothesis or input mutation is introduced here.
