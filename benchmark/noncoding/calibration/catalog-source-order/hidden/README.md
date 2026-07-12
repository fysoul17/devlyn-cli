# Freeze rationale

Why packet-decisive: the implementation is a two-file data regeneration, so code
difficulty is negligible. The decisive fact is the direction of the dependency:
the canonical catalog must change before its derived copy is rendered.

- Dependency defect: reverses the `source -> render` edge, causing a render of the
  old source followed by an unrendered source edit.
- Evidence/constraint defect: claims the integer is a string, contradicting the
  visible type requirement while leaving the rest of the packet intact.

These bytes are frozen before T0; results must not be used to retune them.
