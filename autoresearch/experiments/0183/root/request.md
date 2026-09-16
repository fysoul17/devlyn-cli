Add `--root PATH` to scripts/skill-token-gauge.py so a developer can measure a
different checkout without copying the script there. Use that directory for all
skill bases, shared files, root documents and relative report paths in JSON and
table output. Relative PATH is relative to the invoking process's working
directory. Paths with spaces and Unicode work. When omitted, retain the existing
script-location root and output behavior exactly. A missing path or a regular file
must exit with argparse-style exit 2, a useful stderr diagnostic and no report on
stdout. An existing empty directory is valid and produces empty file groups and
zero totals. Preserve all existing measurement formulas, ordering, roles, schema
and dependency-free operation. Document the option in the script's usage text and
`--help`. Only this script and optional tests/test_regression.py may change.
