# 0237 completed-cell evidence

As of 2026-10-10T04:25:06.929859+00:00. Derived from final verdict files only; no regrading or C admission/rejection.

UA1 is excluded as a whole because of unsupported oracle requirements. Its five raw outcomes and charged attempts remain below. AF1 rows are available diagnostics, not a claim of general correctness. Missing final verdicts have no outcome or cost assigned.

A is native CLI; B is installed 4.2.3; C adds the caller/consumer contract-discovery sentence. The separately admitted helper/docs fixes did not change these frozen measured packages.

| Cell | Raw status | Source / local delivery | Hidden rows | Owner s | Input incl. cache | Output | Usage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [d01-EQ3-UA1-claude-A-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d01-EQ3-UA1-claude-A-r1.json) | PRODUCT_INCOMPLETE | FAIL / PASS | local-a=FAIL, local-b=PASS, remote-a=PASS, remote-b=PASS, restore=PASS | 529.381 | 611,877 | 53,340 | COMPLETE |
| [d02-EQ3-UA1-claude-B-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d02-EQ3-UA1-claude-B-r1.json) | PRODUCT_INCOMPLETE | FAIL / PASS | local-a=FAIL, local-b=PASS, remote-a=PASS, remote-b=PASS, restore=PASS | 607.584 | 2,430,324 | 60,742 | COMPLETE |
| [d03-EQ3-UA1-claude-C-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d03-EQ3-UA1-claude-C-r1.json) | PRODUCT_INCOMPLETE | FAIL / PASS | local-a=FAIL, local-b=PASS, remote-a=PASS, remote-b=PASS, restore=PASS | 809.465 | 2,677,123 | 82,340 | COMPLETE |
| [d04-EQ3-UA1-codex-B-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d04-EQ3-UA1-codex-B-r1.json) | PRODUCT_INCOMPLETE | FAIL / PASS | local-a=PASS, local-b=PASS, remote-a=FAIL, remote-b=PASS, restore=PASS | 181.687 | 251,150 | 6,292 | COMPLETE |
| [d05-EQ3-UA1-codex-C-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d05-EQ3-UA1-codex-C-r1.json) | PRODUCT_INCOMPLETE | FAIL / PASS | local-a=PASS, local-b=PASS, remote-a=FAIL, remote-b=PASS, restore=PASS | 293.873 | 539,289 | 10,649 | COMPLETE |
| [d13-EQ3-AF1-claude-C-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d13-EQ3-AF1-claude-C-r1.json) | CHECKS_PASS | PASS / PASS | 5/5 PASS | 1169.674 | 3,809,320 | 116,734 | COMPLETE |
| [d14-EQ3-AF1-claude-A-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d14-EQ3-AF1-claude-A-r1.json) | CHECKS_PASS | PASS / PASS | 5/5 PASS | 855.364 | 1,305,743 | 86,558 | COMPLETE |
| [d15-EQ3-AF1-claude-B-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d15-EQ3-AF1-claude-B-r1.json) | CHECKS_PASS | PASS / PASS | 5/5 PASS | 1218.138 | 5,192,478 | 122,560 | COMPLETE |
| [d16-EQ3-AF1-codex-A-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d16-EQ3-AF1-codex-A-r1.json) | CHECKS_PASS | PASS / PASS | 5/5 PASS | 216.166 | 209,634 | 7,956 | COMPLETE |
| [d17-EQ3-AF1-codex-B-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d17-EQ3-AF1-codex-B-r1.json) | CHECKS_PASS | PASS / PASS | 5/5 PASS | 419.312 | 639,136 | 16,228 | COMPLETE |
| [d18-EQ3-AF1-codex-C-r1](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/verdict-d18-EQ3-AF1-codex-C-r1.json) | CHECKS_PASS | PASS / PASS | 5/5 PASS | 336.283 | 574,930 | 12,788 | COMPLETE |

Not finalized (excluded from the table, never inferred to pass): none.

## Source and predicate integrity

- `d13-EQ3-AF1-claude-C-r1`: original QA files and `matching/crossmatch_reserver.py`: **UNCHANGED**. Changed existing visible files: visible/intake/hold_intake.py. Added: none. Evaluated snapshot/check/delivery binding: {'snapshot_matches': True, 'checks_match': True, 'delivery_match': True}. Baseline matches registered source: True; hidden oracle matches control: True.
- `d14-EQ3-AF1-claude-A-r1`: original QA files and `matching/crossmatch_reserver.py`: **UNCHANGED**. Changed existing visible files: visible/intake/hold_intake.py. Added: visible/qa/run_expiry_checks.py. Evaluated snapshot/check/delivery binding: {'snapshot_matches': True, 'checks_match': True, 'delivery_match': True}. Baseline matches registered source: True; hidden oracle matches control: True.
- `d15-EQ3-AF1-claude-B-r1`: original QA files and `matching/crossmatch_reserver.py`: **UNCHANGED**. Changed existing visible files: visible/intake/hold_intake.py. Added: none. Evaluated snapshot/check/delivery binding: {'snapshot_matches': True, 'checks_match': True, 'delivery_match': True}. Baseline matches registered source: True; hidden oracle matches control: True.
- `d16-EQ3-AF1-codex-A-r1`: original QA files and `matching/crossmatch_reserver.py`: **UNCHANGED**. Changed existing visible files: visible/intake/hold_intake.py. Added: visible/qa/test_hold_intake.py. Evaluated snapshot/check/delivery binding: {'snapshot_matches': True, 'checks_match': True, 'delivery_match': True}. Baseline matches registered source: True; hidden oracle matches control: True.
- `d17-EQ3-AF1-codex-B-r1`: original QA files and `matching/crossmatch_reserver.py`: **UNCHANGED**. Changed existing visible files: visible/intake/hold_intake.py. Added: none. Evaluated snapshot/check/delivery binding: {'snapshot_matches': True, 'checks_match': True, 'delivery_match': True}. Baseline matches registered source: True; hidden oracle matches control: True.
- `d18-EQ3-AF1-codex-C-r1`: original QA files and `matching/crossmatch_reserver.py`: **UNCHANGED**. Changed existing visible files: visible/intake/hold_intake.py. Added: visible/qa/test_hold_intake.py. Evaluated snapshot/check/delivery binding: {'snapshot_matches': True, 'checks_match': True, 'delivery_match': True}. Baseline matches registered source: True; hidden oracle matches control: True.

The d13 through d18 source diffs were also read: all implement hold recording and expiry reconciliation; none replaces or changes the evaluated predicates. d14 adds `qa/run_expiry_checks.py`; d16 and d18 add `qa/test_hold_intake.py`. These assert behavior through the original consumers. Any later modified predicate requires independent review before using its result. See [AF1 source audit](af1-source-audit.md) for final resource ratios and [helper accounting audit](af1-helper-audit.md) for bounded interpretation.

## Accounting and provenance

Input is processed input inclusive of cache; output already includes reasoning. Not billed tokens or dollars. Owner totals include recorded native children; research assessors are separate. Missing costs remain unknown.

Source checks plus local commit matching the assessed source; not PR/merge or full North Star delivery.

Dispatcher timestamps can include parent holds. The recorded d14 review hold began 03:22:29 UTC and resumed 03:40:42 UTC; its owner_seconds comes from the completed child run and does not include the subsequent dispatcher wait. Do not substitute dispatcher elapsed time.

[Runtime](/Users/aipalm/.local/share/nx01/0237-live/runtime-discovery-max.json), [selected tasks](/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0237/tasks-discovery-max.json), [control manifest](/Users/aipalm/.local/share/nx01/0237-live/control-discovery.manifest.json), [review hold/resume](/Users/aipalm/.local/share/nx01/0237-live/review-boundary.jsonl), [UA1 exclusion](eq3-contract-audit-ua1.md). [cells.json](cells.json) retains per-cell source, oracle, usage breakdown, delivery, seal/checked hashes and raw evidence links. The inherited baseline tasks_sha256 labels sibling tasks.json; selected-task identity is taken from seal.inputs, not that field.

This report excludes smoke/advice costs from measured-cell comparisons; their separate retained outcomes, including ultra cancellation/partial usage, remain unchanged. No cross-engine aggregate or candidate decision is computed.

Refresh after later final verdicts: `python3 -B autoresearch/experiments/0237/results/refresh-cells.py`. It reads completed evidence and writes only cells.json/cells.md.
