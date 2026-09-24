# 0219 — parity apparatus implemented; launch awaits user authorization

2026-09-24. Root direct, no resolve. Implements [DESIGN](DESIGN.md) steps 2–3.
Nothing dispatched. Astra, Fable and Grok all returned FREEZE after one revision.

## Apparatus

- [prepare.py](prepare.py) wraps [0218 preparation](../0218/prepare.py). For D2/D4
  it requires the caller's pytest commands to match the registered list exactly,
  then replaces each one by exact string (less-PATH prefix; D2 focused
  `tests/test_exceptions/`). It rebinds caller, prompt, argv and hashes, and stamps
  `parity_prepare_sha256` on all 24 cells. D1/D3 bytes are unchanged.
- [run_cell.py](run_cell.py) is the 0218 runner with 0219 preparation. It uses a
  behavior-preserving `PREPARE` seam in [0218/run_cell.py](../0218/run_cell.py);
  a direct 0218 run still uses 0218 preparation.

## Model-free evidence (`.devlyn/0219-dry/`)

- Bindings: all 24 prepared cells pass prompt/argv/caller/hash binding. Prompts
  match across repetitions. Compared with 0218 cell 07, only the two D2 pytest
  lines differ; D1 is byte-identical. A weakened D4 command set is rejected.
- Parity: the prepared D2/D4 checks ran in the pinned image under login bash, with
  the owner's argv PATH and tmpfs (`exec`). Focused checks passed 110 (D2) and
  109 (D4). The full suite passed 2,099, the same as the evaluator. Ruff was
  clean. A first probe with a `noexec` /tmp gave 3 pager-detection failures. That
  was a probe artifact: the owner mount is `exec`
  ([native_cell.py](../0210/native_cell.py)).
- Packet replay (step 3), on the 0218 cell 07 packet of 1,104,757 B: 776,016 B of
  it are logs caused by the owner-only pager gap. The post-parity estimate is
  331,248 B. At most about 11 KB (3.4%) is mechanically removable while keeping
  every test identity, outcome and distinct diagnostic: the duplicate 8,639 B diff
  plus progress lines. That does not meet the "substantial" criterion, so this run
  adds no pytest compaction and no duplicate-diff removal. The 331 KB figure is an
  estimate, not a measured post-parity packet.

## Before launch (unchanged from DESIGN)

1. New user authorization for a fresh registered 24-cell screen. It must
   acknowledge that 0218 already used the 0206 single-redesign allowance.
2. Reseal all admission checks against the committed source: bindings, parity,
   format gates, calibration, meter, accounting and teardown. Dry-cell hashes
   are stale by design.
3. Run a fail-closed launch through `run_cell.py`.
