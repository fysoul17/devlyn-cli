# P4 mechanism record

- Family: cross-field consistency.
- Mandatory clause: “When the same evolve call changes `name` and resets `alias`, derive the alias from the new name. Its `name`, `alias`, and `alias_is_default` must describe the same resulting field.”
- Trigger: one `Attribute.evolve` invocation supplies both a different `name` and `alias=None`.
- Causal code path: after copying and applying changes, the new reset branch computes the alias from `self.name` rather than `new.name`. It marks that stale alias as default. `_transform_attrs` later keeps it because it is nonempty; initializer generation and instance evolve consume it.
- Incorrect behavior: storage and field introspection use the new name while the initializer and instance copying accept the default alias of the old name.
- Executable witness: P4-O3 in `oracle.md`.
- Near-miss exclusions: dropping the default-provenance flag, failing to distinguish omitted alias from `None`, mishandling explicit aliases, failing to reject a contradictory flag, and mutating the input Attribute are different defects. Resetting and renaming in two separate evolve calls works on the twin; only the stale source name in the combined reset operation is this mechanism.
