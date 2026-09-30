# P4 hidden oracle

Run rows independently with `import attr`, `import attrs`, `import inspect`, and `import pytest`. Obtain input Attributes from `attrs.fields` rather than manually invoking their constructor. Exactly P4-O3 is the designated witness; all other rows must pass on both implementations.

## P4-O1 — complete reset result

Setup: define a class with `_value` using `field(alias="external", metadata={"tag": 1})`; retain its Attribute as `original`.

Action: call `original.evolve(alias=None, repr=False)` and inspect the result immediately, before any class builder consumes it.

Expected: result name `_value`, alias `value`, flag `True`, repr flag `False`, and metadata `{"tag": 1}`. Original alias remains `external`, default flag remains `False`, and repr flag remains `True`. Resetting an already-default `_value` field yields the same name/alias/flag triple.

## P4-O2 — sequential reset and rename

Setup: a transformer receives `_value` with explicit alias `external`.

Action: reset with `a.evolve(alias=None)`, then separately call `.evolve(name="_next")`; return that Attribute. Build with `attr.s(auto_attribs=True, slots=slots)` for each boolean `slots` setting.

Expected: the field name is `_next`, alias is `next`, and flag is `True`. `C(next=3)` stores `3` under `_next`; `attr.evolve(instance, next=4)` constructs a new instance containing `4`. The original transformer input remains unchanged.

## P4-O3 — combined reset and rename (designated witness)

Setup and action, executable:

```python
for slots in (False, True):
    originals = []

    def transform(cls, attributes):
        originals.append(attributes[0])
        return [attributes[0].evolve(name="_renamed", alias=None)]

    @attr.s(auto_attribs=True, slots=slots, field_transformer=transform)
    class C:
        _original: int = attr.ib(alias="external")

    field = attr.fields(C)._renamed
    assert field.name == "_renamed"
    assert field.alias == "renamed"
    assert field.alias_is_default is True
    assert list(inspect.signature(C).parameters) == ["renamed"]
    instance = C(renamed=3)
    assert instance._renamed == 3
    assert attr.evolve(instance, renamed=4)._renamed == 4
    assert originals[0].name == "_original"
    assert originals[0].alias == "external"
    assert originals[0].alias_is_default is False
```

Expected: field metadata, initializer, and instance copying agree on `renamed`. The twin retains alias `original` and therefore generates the wrong initializer parameter.

## P4-O4 — explicit aliases and overrides

Setup: obtain a default-aliased `_value` Attribute and an explicit-aliased `_value` Attribute with alias `external`.

Action: on the first, call `.evolve(name="_next", alias="chosen")`; on the second, call `.evolve(name="_next")`. Also call `.evolve(alias="chosen", alias_is_default=True)` without resetting.

Expected: the first has name `_next`, alias `chosen`, and flag `False`; the second keeps alias `external` and flag `False`; the explicit flag override remains `True` in the third result, as it did before this change. None of the input Attributes changes.

## P4-O5 — contradictory reset request

Setup: retain an Attribute with an explicit alias.

Action: call `.evolve(alias=None, alias_is_default=False)`, then separately `.evolve(alias=None, alias_is_default=True)`.

Expected: the first raises `ValueError` without changing the original. The second succeeds with the generated alias and flag `True`.

## P4-O6 — omission is not reset

Setup: retain an Attribute named `_value` with explicit alias `external` and metadata `{"before": 1}`.

Action: call `.evolve(metadata={"after": 2}, repr=False)` without an alias or name argument.

Expected: name, explicit alias, and default flag remain `_value`, `external`, and `False`; only the requested metadata and repr flag change. The source metadata still equals `{"before": 1}`.
