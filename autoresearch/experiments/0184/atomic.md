# Preserve prediction output when collection fails

The existing benchmark/auto-resolve/scripts/collect-swebench-predictions.py opens
--out before validating every patch. Make publication transactional: any input,
validation, encoding/read, or output-write error before publication must preserve
an existing destination byte-for-byte, or leave a previously absent destination
absent. This includes a later invalid UTF-8/empty patch and all patches skipped by
--allow-empty. Build the complete output in a same-directory temporary file and
publish with an atomic replacement only after successful writing/closing. Remove
owned temporary files on success and failure; preserve all patch/input files.
Creating the destination's parent directories is allowed.

Expected input/validation/I/O errors must return1, give a useful stderr diagnostic,
and emit no success report or Python traceback. argparse usage errors remain2.
Successful predictions, their ordering/JSONL shape, model name/patch text, filtering,
empty-skipped accounting and summary report retain existing semantics. No new flags.
Symlink destination policy, permissions preservation, crash durability, simultaneous
writers, and unrelated patch-name behavior are outside this request.

Change only the collector and optional tests/test_regression.py. Preserve supplied
checks and dependency source. Use /opt/homebrew/bin/python3 -B -m unittest discover
-s tests -v. Standard library only; no network. Verify and remove your temporary debris.
