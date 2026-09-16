# Treat --patch-name as one literal filename

In benchmark/auto-resolve/scripts/collect-swebench-predictions.py, --patch-name is
a literal filename within each immediate instance directory, not a glob or path.
Accept names containing *, ?, brackets, Unicode, whitespace and leading dashes
(use --patch-name=NAME for dash-leading argv). Reject empty names, . and .., and
any name containing / or backslash using argparse exit2 with an actionable stderr
diagnostic and empty stdout before touching --out. Do not strip valid whitespace.

Inspect immediate child directories of --patch-root, in the existing lexicographic
instance-id order, and include only the exact named regular file in each. A matching
directory is not a patch. Do not recurse into nested directories or interpret glob
syntax. Ordinary pathlib is_dir/is_file symlink-following semantics are acceptable;
this is not a new security boundary. Retain instance filtering/missing-id reporting,
default patch.diff behavior, JSONL/report shapes, model/patch contents, and empty
handling. Output atomicity and unrelated existing error presentation are outside
this request. No new flags or unrelated refactor.

Change only the collector and optional tests/test_regression.py. Preserve supplied
checks and dependency source. Use /opt/homebrew/bin/python3 -B -m unittest discover
-s tests -v. Standard library only; no network. Verify and remove your temporary debris.
