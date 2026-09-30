# P3 hidden oracle

Each row runs independently with `import attr`, `import attrs`, `import pytest`, and `from typing import Annotated`. Use explicit string annotations and explicit namespace dictionaries to avoid dependencies on module locals. Exactly P3-O4 is the designated witness; every other row must pass on both implementations.

## P3-O1 — force and subsequent caching

Setup: define an attrs class `C` with `value: "Token"`. Resolve it with `localns={"Token": int}`.

Action: call unforced with `Token=str`, then forced with `Token=str`, then unforced with `Token=float`.

Expected: every return is `C`; successive field types are `int`, `str`, and `str`. The class's own `__attrs_types_resolved__` is `C` after success. Repeat force with `Token=float` and expect `float`.

## P3-O2 — extras and untouched fields

Setup: use `@attr.s` with `value: "Annotated[int, 'tag']" = attr.ib()` and an unannotated `other = attr.ib(type=str)`. Supply `globalns={"Annotated": Annotated}`.

Action: resolve normally with extras included, force with `include_extras=False`, then force with `include_extras=True`.

Expected: `value.type` is `Annotated[int, "tag"]`, `int`, and `Annotated[int, "tag"]` respectively; `other.type` remains `str` throughout. Return identity and class marker are preserved.

## P3-O3 — initial failure and recovery

Setup: an unresolved attrs class has fields annotated `"int"` and `"Missing"`. Snapshot both field types and whether the class has its own resolution marker.

Action: make an ordinary call with an empty namespace, catch `NameError`, then call again with `localns={"Missing": str}`.

Expected: the failed call leaves both types and marker presence unchanged. The retry returns the class and resolves the fields to `int` and `str`, recording a successful marker. Neither call uses `force=True`.

## P3-O4 — failed refresh of a cached class (designated witness)

Setup and action, executable:

```python
@attrs.define
class C:
    value: "Token"

assert attrs.resolve_types(C, localns={"Token": int}) is C
field = attrs.fields(C).value
marker = C.__dict__["__attrs_types_resolved__"]
assert field.type is int and marker is C

with pytest.raises(NameError):
    attrs.resolve_types(C, localns={}, force=True)

assert field.type is int
assert C.__dict__["__attrs_types_resolved__"] is marker
assert attrs.resolve_types(C, localns={}) is C
assert field.type is int
```

Expected: the failed forced resolution retains the earlier successful marker and metadata; the final unforced call returns without reevaluating the missing `Token`. The twin leaves the marker as `None` and would raise again on that final call.

## P3-O5 — inherited marker

Setup: define `Base` with `value: "Token"`, resolve it with `Token=int`, then define `Child(Base)` with an additional `extra: "Token"` field.

Action: ordinarily resolve `Child` with `Token=str`, then force it with `Token=float`.

Expected: both child fields first resolve to `str` and then `float`; the child's own marker is `Child`. The base's field remains `int` and its own marker remains `Base`.

## P3-O6 — explicit fields before class decoration

Setup: a field transformer receives an undecorated class and its Attributes for a field `value: "Token"` and an unannotated field with `type=str`.

Action: in the transformer call `attr.resolve_types(cls, localns={"Token": int}, attribs=attribs)`, then force again with `Token=float`; return the same attributes for completion of decoration.

Expected: both calls return the input undecorated class by identity. Final field types are `float` and `str`. Constructor operation and field names are unchanged.
