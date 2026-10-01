# 0228 R2 — decision and check record (2026-10-01 KST)

- 21:12 first R2 batch stopped by the OS-agent quiesce after one completed replay (`batch-r2-stopped-1.log`; C2); runner fixed (PR #147, Astra SHIP) and R2 restarted from item 0 (`batch-r2.log`, batch `1790858329`, inventory `r2c`).
- 21:42:26 judge token swapped itclab.dev26 → onedatatech.dev by the devlyn-os-v1 session between items 5 and 6 (`~/.config/devlyn-vr/token-swap.txt`).
- 22:14:36 root decided, before reading any judge output, to re-dispatch items 0–5 under the new account (inherited account-drift rule); first judge output read at 22:24:33 (collection). Rerun batch: `batch-r2-rerun.log` (inventory `r2d`, `plan-r2-rerun.json`).
- Transport classification: all 56 effective replays and the 6 reruns exited 0 on both seats; the usage-limit watcher recorded no event.
- Owner baseline compare (`mode-baseline.py compare`) after R2 and the reruns: compared 643, changed 0, gone 5 (other sessions' cleanup and the two deleted npm logs).
- Credential check: both judge tokens searched in all 97,251 files under `/Users/Shared/devlyn-vr-0228-dev`: 0 hits; 0 Codex login copies.
- Labels: root and Astra's blind audit agree (`labels.json`, `audit-astra.md`); join and verdict in `result.json`.
