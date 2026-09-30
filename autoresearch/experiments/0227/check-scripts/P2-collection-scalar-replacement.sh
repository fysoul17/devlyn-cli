#!/bin/sh
# Clause (spec Req 3/4): a nested list replaced by a scalar is emitted without traversal; a nested scalar replaced by a list has its children visited.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, sys
import attr
import attrs

assert os.path.realpath(attr.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attr.__file__


@attrs.define
class Child:
    x: int


@attrs.define
class Root:
    payload: list


failures = []

# Field [[1]]: the serializer replaces the nested list [1] with 0 -> [0], and 1 is never visited.
inner = [1]
calls = []


def list_to_int(inst, attribute, value):
    calls.append((inst, attribute, value))
    return 0 if inst is None and value is inner else value


try:
    out = attr.asdict(Root([inner]), value_serializer=list_to_int)
    if out != {"payload": [0]}:
        failures.append(f"list->int: got {out!r}, expected {{'payload': [0]}}")
    elif any(v == 1 and type(v) is int for _, _, v in calls):
        failures.append("list->int: original list traversed")
except Exception as e:  # noqa: BLE001 - any exception violates the clause
    failures.append(f"list->int: raised {type(e).__name__}: {e}")

# Field [7]: the serializer replaces the nested 7 with [Child(1), 3]; the replacement's children get callbacks and recursion.
repl_child = Child(1)
calls = []


def int_to_list(inst, attribute, value):
    calls.append((inst, attribute, value))
    if inst is None and type(value) is int and value == 7:
        return [repl_child, 3]
    return value


try:
    out = attr.asdict(Root([7]), value_serializer=int_to_list)
    if out != {"payload": [[{"x": 1}, 3]]}:
        failures.append(f"int->list: got {out!r}, expected {{'payload': [[{{'x': 1}}, 3]]}}")
    child_events = [c for c in calls if c[0] is None and c[2] is repl_child]
    scalar_events = [c for c in calls if c[0] is None and type(c[2]) is int and c[2] == 3]
    field_events = [c for c in calls if c[0] is repl_child]
    if not (child_events and scalar_events and field_events):
        failures.append("int->list: replacement children skipped their callbacks")
except Exception as e:  # noqa: BLE001 - any exception violates the clause
    failures.append(f"int->list: raised {type(e).__name__}: {e}")

if failures:
    sys.exit("violated:\n" + "\n".join(failures))
print("holds")
PY
