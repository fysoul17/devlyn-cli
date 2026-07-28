# Operator artifacts excluded before scoring

The first attempted four-way launch resolved each case prompt relative to the `/tmp/l84-*` working directory instead of the repository. All four commands therefore emitted `no such file or directory` for the case prompt and launched with the canonical body only. T and K3 were interrupted; K1 and K2 returned without a valid case input. Their files were renamed `*-invalid-missing-case.*` before valid trial numbering began. No result from those calls appears in `summary.json` or in the twelve `<case>-<trial>.stdout.json` scored receipts.
