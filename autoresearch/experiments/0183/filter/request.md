Add optional `--skill NAME` to scripts/skill-token-gauge.py so a developer can
inspect one exact skill name. Filter the skills list across both existing skill
bases: if the same exact name occurs in both, retain both in their existing order.
Matching is case-sensitive and exact, not substring matching. With no option,
retain existing output behavior exactly. Shared and root document groups remain
present and unchanged, and grand totals sum only the retained skill files plus
those shared/root files. Both JSON and table output obey the filter. No matching
skill must exit with argparse-style exit 2, a useful stderr diagnostic and no
report on stdout. Keep all measurement formulas, relative paths, roles, schema,
ordering and dependency-free operation. Document the option in the script's
usage text and `--help`. Only this script and optional tests/test_regression.py may
change.
