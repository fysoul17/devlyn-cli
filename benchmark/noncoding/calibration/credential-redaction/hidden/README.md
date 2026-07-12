# Freeze rationale

Why packet-decisive: the code change is one set member in a recursive sanitizer.
The difficulty is locating ownership and retaining the exact-match constraint, not
implementing recursion.

- Dependency defect: reverses shared-sanitizer/adaptor ownership and directs the
  change into the CLI adapter, leaving direct API callers exposed.
- Evidence/constraint defect: changes complete-key matching to prefix matching,
  over-redacting two explicitly preserved fields.

These bytes are frozen before T0; results must not be used to retune them.
