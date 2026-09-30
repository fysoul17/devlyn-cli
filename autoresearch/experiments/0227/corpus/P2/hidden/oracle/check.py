"""Independent behavioral checks for the asdict serializer contract."""

import json
from collections import OrderedDict

import attr
import attrs
import pytest


def field_order_and_filtering():
    @attrs.define
    class Child:
        keep: int
        secret: int

    @attrs.define
    class Root:
        payload: list

    child = Child(1, 2)
    root = Root([child])
    calls = []

    def include(attribute, value):
        return attribute.name != "secret"

    def serialize(instance, attribute, value):
        calls.append((instance, attribute, value))
        return value

    assert attr.asdict(root, filter=include, value_serializer=serialize) == {
        "payload": [{"keep": 1}]
    }
    assert len(calls) == 3
    assert calls[0][0] is root
    assert calls[0][1] is attrs.fields(Root).payload
    assert calls[0][2] is root.payload
    assert calls[1][0] is None and calls[1][1] is None
    assert calls[1][2] is child
    assert calls[2][0] is child
    assert calls[2][1] is attrs.fields(Child).keep
    assert calls[2][2] == 1


def replacement_children_and_order():
    @attrs.define
    class Root:
        payload: list

    original_list = [2, 3]
    original_dict = {"drop": 1, "keep": original_list}
    root = Root([original_dict])
    calls = []

    def serialize(instance, attribute, value):
        calls.append((instance, attribute, value))
        if instance is None and value is original_dict:
            return {"keep": original_list}
        if instance is None and value is original_list:
            return [3]
        return value

    assert attr.asdict(root, value_serializer=serialize) == {"payload": [{"keep": [3]}]}
    assert len(calls) == 5
    assert calls[0][0] is root
    assert calls[0][1] is attrs.fields(Root).payload
    assert calls[0][2] is root.payload
    assert calls[1] == (None, None, original_dict)
    assert calls[1][2] is original_dict
    assert calls[2] == (None, None, "keep")
    assert calls[3] == (None, None, original_list)
    assert calls[3][2] is original_list
    assert calls[4] == (None, None, 3)


def replacement_controls_dispatch():
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

    assert attr.asdict(root, value_serializer=serialize) == {"payload": ["redacted"]}
    assert len(calls) == 2
    assert calls[0][0] is root
    assert calls[0][1] is attrs.fields(Root).payload
    assert calls[0][2] is root.payload
    assert calls[1][0] is None and calls[1][1] is None
    assert calls[1][2] is child


def collection_policies_and_occurrences():
    @attrs.define
    class Root:
        payload: list

    shared = (1, 2)
    root = Root([shared, shared])
    calls = []

    def serialize(instance, attribute, value):
        calls.append((instance, attribute, value))
        return value

    for asdict, options, expected, element_type in (
        (attr.asdict, {}, [[1, 2], [1, 2]], list),
        (
            attr.asdict,
            {"retain_collection_types": True},
            [(1, 2), (1, 2)],
            tuple,
        ),
        (attrs.asdict, {}, [(1, 2), (1, 2)], tuple),
    ):
        calls.clear()
        result = asdict(root, value_serializer=serialize, **options)
        assert result == {"payload": expected}
        assert all(type(item) is element_type for item in result["payload"])
        assert len(calls) == 7
        assert calls[0][0] is root
        assert calls[0][1] is attrs.fields(Root).payload
        assert calls[0][2] is root.payload
        for offset in (1, 4):
            assert calls[offset][0] is None
            assert calls[offset][1] is None
            assert calls[offset][2] is shared
            assert calls[offset + 1] == (None, None, 1)
            assert calls[offset + 2] == (None, None, 2)
        assert asdict(root, **options) == result

    assert type(attr.asdict(root, dict_factory=OrderedDict)) is OrderedDict


def recursion_disabled():
    @attrs.define
    class Child:
        value: int

    @attrs.define
    class Root:
        payload: list

    child = Child(1)
    root = Root([child])
    replacement = [child]
    calls = []

    def serialize(instance, attribute, value):
        calls.append((instance, attribute, value))
        return replacement

    result = attr.asdict(root, recurse=False, value_serializer=serialize)
    assert result["payload"] is replacement
    assert len(calls) == 1
    assert calls[0][0] is root
    assert calls[0][1] is attrs.fields(Root).payload
    assert calls[0][2] is root.payload


def callback_failure():
    @attrs.define
    class Root:
        payload: list

    entry = {"key": 1}
    root = Root([entry])
    error = RuntimeError("original exception")
    calls = []

    def serialize(instance, attribute, value):
        calls.append((instance, attribute, value))
        if value is entry:
            raise error
        return value

    with pytest.raises(RuntimeError) as raised:
        attr.asdict(root, value_serializer=serialize)

    assert raised.value is error
    assert len(calls) == 2
    assert calls[0][0] is root
    assert calls[0][1] is attrs.fields(Root).payload
    assert calls[0][2] is root.payload
    assert calls[1][0] is None and calls[1][1] is None
    assert calls[1][2] is entry


ROWS = {
    "P2-O1": field_order_and_filtering,
    "P2-O2": replacement_children_and_order,
    "P2-O3": replacement_controls_dispatch,
    "P2-O4": collection_policies_and_occurrences,
    "P2-O5": recursion_disabled,
    "P2-O6": callback_failure,
}


def main():
    results = {}
    for row_id, check in ROWS.items():
        try:
            check()
        except BaseException:  # noqa: BLE001
            results[row_id] = False
        else:
            results[row_id] = True
    print(json.dumps({"rows": results}))


if __name__ == "__main__":
    main()
