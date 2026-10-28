I'll review the amendment and the blind-packet change only, without editing anything or opening the credential store.The change is correct and minimal. It closes the FIFO stop without blocking, reading a credential path, following a link, or leaking the arm. No measured outcome or decision code changes.

1. `copy_tree` now `lstat`s each entry and, for a FIFO, records `{relative path: "fifo"}` in `special-files.json` and skips it (`blind.py:130-132`, `140-141`). `os.lstat` does not open the pipe, so an unread FIFO cannot block. The same basename exclusions run first (`117-118`); `private.key` and `AGENTS.md` are neither recorded nor opened. `os.walk(..., followlinks=False)` and the existing symlink branch (`114`, `121-127`) still run before the FIFO check, so a symlink to a FIFO is recorded as link text and not followed. Any other non-regular file still raises (`133-134`); the socket test covers that. The known pipe's relative path is `pytest-of-participant/pytest-1/test_lazy_read_fifo_direct_Fal0/fifo`. `relative_to(tmp)` drops `d021-D4-claude-B-r11.stop-1`. `redact` still strips cell ids, `install [BC]`, and the inserted sentence (`65-71`). The fixture asserts the manifest is absent when the tree has no FIFO (`test_apparatus.py:1389`).

2. The diff is `copy_tree`, its docstring, and one README sentence. Verdicts, witnesses, transcripts, checks, prompts, and `decide.py` are unchanged. The manifest is packet metadata for a tree that actually contains a FIFO. The label-map hash is still only the map, printed after every packet (`blind.py:217-218`).

3. The timing matches the frozen design: 64 slots in `cells.tsv`, this amendment after amendment 1's single archived STOP, and the hash printed only after a finished run. The traceback raises inside `copy_tree` on that tmp FIFO, so the first run's hash was never printed. The "32 packets" figure is root's count of a deleted prefix; the code writes one packet per slot in label order and stops on d021, and it neither confirms nor contradicts 32. The blinding note matches amendment 1: one two-attempt slot, arm B, and the manifest does not name the arm.

No HIGH, MEDIUM, or LOW findings.

VERDICT: SHIP
