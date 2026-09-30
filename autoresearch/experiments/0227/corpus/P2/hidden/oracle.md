# P2 hidden oracle

Run rows independently with `import attr`, `import attrs`, and `import pytest`. Exactly P2-O3 is the designated witness. All other rows must pass on both implementations. Compare recorded callback objects by identity where equality could hide an incorrect argument.

## P2-O1 — field order and filtering

Setup: define an attrs `Child` with `keep` and `secret` fields and a `Root` with a list containing one child. A filter rejects fields named `secret`. An identity serializer logs `(instance, attribute.name if attribute is not None else None, value)`.

Action: call `attr.asdict(root, filter=filter_fn, value_serializer=serializer)`.

Expected: log order is the root's list-field event, `(None, None, child)`, and the child's `keep`-field event. Neither the top-level root, a field-name key, the filtered `secret`, nor its children get callback events. Output includes the converted child with only `keep`.

## P2-O2 — replacement children and dictionary ordering

Setup: a root field contains `[{"drop": 1, "keep": [2, 3]}]`. The serializer logs each event; for nested dictionaries it returns a new dict without `drop`, and for the nested list `[2, 3]` it returns `[3]`. Other inputs are returned unchanged.

Action: serialize with `attr.asdict` and the logging hook.

Expected: output is `{"payload": [{"keep": [3]}]}`. After the field callback, events are the original nested dict, key `"keep"`, original list `[2, 3]`, and scalar `3`. There are no callbacks for `"drop"`, `1`, `2`, or the replacement dict/list roots.

## P2-O3 — replacement controls dispatch (designated witness)

Setup and action, executable:

```python
@attrs.define
class Child:
    secret: str

@attrs.define
class Root:
    payload: list

child = Child("private")
root = Root([child])
calls = []

def serialize(instance, attribute, value):
    calls.append((instance, attribute, value))
    if instance is None and value is child:
        return "redacted"
    return value

assert attr.asdict(root, value_serializer=serialize) == {
    "payload": ["redacted"]
}
assert len(calls) == 2
assert calls[0][0] is root
assert calls[0][1] is attrs.fields(Root).payload
assert calls[0][2] is root.payload
assert calls[1][0] is None and calls[1][1] is None
assert calls[1][2] is child
```

Expected: the replacement string is emitted, and the child's secret is never traversed. The twin raises `NotAnAttrsClassError` while attempting to serialize the string as an attrs instance.

## P2-O4 — collection policies and occurrence count

Setup: root payload is a list containing the same tuple `(1, 2)` twice. Use a logging identity serializer. Also provide a `dict_factory` returning `collections.OrderedDict` for a separate `attr.asdict` call.

Action: call `attr.asdict`, `attr.asdict(..., retain_collection_types=True)`, and `attrs.asdict`, resetting the log each time.

Expected: default legacy output contains two lists; retained and modern output contain two tuples. Each traversal logs one root field, the tuple occurrence and its two scalars, then the second tuple occurrence and its two scalars. The factory call produces an `OrderedDict` at the root. Calls without a serializer produce the same structures.

## P2-O5 — recursion disabled

Setup: root payload is a list containing an attrs child. The field callback returns a different list containing the same child and logs its call.

Action: call `attr.asdict(root, recurse=False, value_serializer=serializer)`.

Expected: exactly one callback, with root and its field; the returned list is stored by identity without traversing the child.

## P2-O6 — callback failure

Setup: root payload contains a nested dict. An identity hook for the field raises a pre-created `RuntimeError` when called on that nested dict.

Action: serialize with the hook, catching the error.

Expected: the identical exception object propagates, and neither the dict's keys nor its values receive callbacks.
