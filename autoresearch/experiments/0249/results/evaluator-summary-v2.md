# 0249 staging and evaluator calibration

PASS: all ten cases match their prospective public-check and per-oracle predictions. This is preparation evidence, not a native-model result.

| Task | Variant | Public | Oracle PASS | Oracle FAIL |
|---|---|---|---:|---:|
| OR1 | baseline | PASS | 2 | 8 |
| OR1 | gold | PASS | 10 | 0 |
| OR1 | fault | PASS | 9 | 1 |
| OR2 | baseline | PASS | 3 | 9 |
| OR2 | gold | PASS | 12 | 0 |
| OR2 | fault | PASS | 10 | 2 |
| E1 | baseline | PASS | 1 | 2 |
| E1 | gold | PASS | 3 | 0 |
| B5 | baseline | PASS | 2 | 3 |
| B5 | gold | PASS | 5 | 0 |

The unchanged native machinery has 119 execution inputs. Controls bind 64 public, 28 oracle and 969 package files. The actual pinned-image evaluator made 32 container calls; teardown and all protected inputs, controls and source copies passed.

The first calibration driver incorrectly required `AssertionError` from a JavaScript helper that throws `Error(row)`. Its original STOP and raw E1 result remain unchanged. The corrected validator requires the exact registered oracle, row, exit and assertion stack. Seven existing raw results were reused; only the three unrun cases were executed. No case was repeated.

Staging preserves the original journal and separately records the OR1/OR2 hidden-oracle extension. The earlier pre-write symlink check and unsupported old B5 route are retained as preparation observations. The reviewed 0249 adapter restores B5 through the unchanged original evaluator.

Runtime: `/Users/aipalm/.local/share/nx01/0249-live/staged-v1/runtime-measured.json`  
Runtime SHA-256: `39082b5a5b7fbdc203ec3796fa2fee2bb913f3cc3ca323ef0531f76ff48cf657`  
Tasks SHA-256: `284f7ed725033781640c9262aeeb70f0731378d7aa72f6be48260d831d1ead3d`  
Control manifest SHA-256: `1d0fa17cf35ce310b7e01ed07f4a0c31774931b53d7c63dfeef0fce348ab7f4a`  
Combined report SHA-256: `f8a830fc485e918a852e289ba9b1152ab581843456bca2a9d4214df352ee2a3c`

No authentication operation, credential copy, native model call, evaluation replay, runtime freeze or dispatch occurred. Staged auth/output/scratch directories are empty. Root review and freeze remain outstanding.
