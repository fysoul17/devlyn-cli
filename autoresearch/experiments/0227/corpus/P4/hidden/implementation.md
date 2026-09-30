# P4 implementation instructions

Family: cross-field consistency. Apply independently to the pinned tree.

## Reference

Change exactly `src/attr/_make.py` and `tests/test_hooks.py`.

In `Attribute.evolve`, distinguish absence of the `alias` key from an explicitly provided `None`; a `.get()` without a separate membership check would not do so. For a reset, reject an explicitly false `alias_is_default` with `ValueError`. Copy the original and apply the requested changes using the existing machinery. Normalize a reset by assigning `_default_init_alias_for(new.name)` to `new.alias` and `True` to `new.alias_is_default`, using the established object-setattr bypass for frozen metadata. The reset path takes precedence over the existing branch that marks a newly supplied non-None alias explicit. Leave the existing name-only rename and explicit override paths intact. Document the behavior in the method docstring.

Public tests in `tests/test_hooks.py` should cover resetting a custom alias on an unchanged private field name, immediately inspecting the returned concrete alias and flag, unchanged original metadata, resetting an already-default alias, unrelated metadata changes alongside a reset, rejection of the contradictory false flag, and explicit alias overrides. Add a compound transformer test that first resets an alias, then renames in a separate evolve call, and finally builds/instantiates the class and uses instance `attr.evolve` with its new initializer parameter. Parameterize slotted and dictionary-backed classes. This checks reset provenance, downstream generation, and continued default-name tracking together.

Do not add a public call that both supplies a new `name` and resets `alias=None` in one `Attribute.evolve` invocation. Existing tests already cover name-only changes and non-None alias assignment; retain them. Both implementations contain the identical tests and docstrings. Reset and non-reset branches, including the new validation failure, are exercised publicly without the combined update.

## Twin

Start from the reference and change only the input to `_default_init_alias_for` in the new explicit-reset branch: use `self.name` instead of `new.name`. Keep the assigned `alias_is_default=True`, validation, other metadata updates, and ordinary rename logic unchanged.

This is a plausible mistake when normalizing a copied Attribute: the old and new names are normally equal in reset-only calls. A simultaneous rename exposes the stale input. Later class construction sees a nonempty alias and does not repair it. Separate reset-then-rename calls continue to work because the existing default-alias rename path handles the second call. The twin changes exactly the same two files with no revealing comment or naming.
