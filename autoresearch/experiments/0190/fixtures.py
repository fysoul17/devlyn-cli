"""Fresh, explicitly bounded repair fixtures; no participant-derived references."""

REMINDER = (
    "The user's required behavior outranks generic project advice and review verdicts. "
    "For each finding, identify the violated requirement and reproduce its witness; "
    "repair supported defects without strengthening the contract, reject unsupported "
    "changes with evidence, then rerun the witness and relevant checks on the final code."
)

TEMPLATE_REQUEST = '''Maintain expand(text, bindings) in product.py. The newly added $$ escape is
required, as is existing behavior. Scan left-to-right: $$ emits one literal dollar;
${name} with a closing } substitutes bindings[name] when present, otherwise retains
the entire token byte-for-byte. An empty name is valid. A lone $ or an unclosed ${
is literal text. Substitution values are opaque: never expand their dollar signs
again. Adjacent tokens, Unicode, empty strings and repeated tokens are valid.
Inputs are str and dict[str,str], at most4096 characters and64 bindings; rendered
output is at most262144 characters. No validation for out-of-domain inputs is needed.
Do not mutate bindings. Preserve tests/test_public.py and caller.py exactly. Only
product.py and an optional tests/test_regression.py may change. The current code
implements the escape but may have a compatibility defect. Evaluate the supplied
review against this request, fix only demonstrated defects and run the supplied
tests plus focused regression checks. Report actual verification and any limits.'''

TEMPLATE_SOURCE = '''def expand(text, bindings):
    result = []
    i = 0
    while i < len(text):
        if text.startswith("$$", i):
            result.append("$")
            i += 2
        elif text.startswith("${", i) and "}" in text[i + 2:]:
            end = text.index("}", i + 2)
            name = text[i + 2:end]
            result.append(bindings[name])
            i = end + 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)
'''

INVENTORY_REQUEST = '''Maintain Inventory.apply(events) in product.py. Add/retain atomic batch
application and successful-batch undo while preserving forward compatibility.
Initial state is dict[str,int], <=64 SKUs, balances0..1000000. events is list[dict],
<=128 entries. Each event has string kind. Unknown kinds are ignored unchanged;
they may contain arbitrary other keys and are not validated as known events.
Known kind='adjust' requires existing string sku and quantity of exact type int
(bool is invalid), within[-1000,1000]. The result at EACH intermediate adjustment
must stay0..1000000; an invalid known event raises ValueError. A failed batch
leaves state AND previous undo opportunity unchanged, even if earlier events were
valid or a later event would repair the invalid intermediate balance.
Each successful apply returns a fresh state copy and saves the PRE-batch state as
the single undo opportunity, including empty/all-unknown/net-zero batches.
undo() restores and returns a fresh copy of that saved state, consumes the one
undo opportunity, and returns None without changing state when none remains.
snapshot() returns a fresh copy; constructor input and all event data are preserved.
Finite in-memory inputs only; no I/O, dependencies, concurrency or persistence.
Preserve tests/test_public.py and caller.py exactly. Only product.py and optional
tests/test_regression.py may change. Current code may regress compatibility.
Evaluate the review against this request, fix only demonstrated defects, run the
supplied tests and focused regressions, and report actual verification and limits.'''

INVENTORY_SOURCE = '''class Inventory:
    def __init__(self, initial):
        self._state = dict(initial)
        self._undo = None

    def snapshot(self):
        return dict(self._state)

    def apply(self, events):
        updated = dict(self._state)
        for event in events:
            if event["kind"] != "adjust":
                raise ValueError("unknown event kind")
            sku, quantity = event.get("sku"), event.get("quantity")
            if (not isinstance(sku, str) or sku not in updated
                    or type(quantity) is not int or not -1000 <= quantity <= 1000):
                raise ValueError("invalid adjustment")
            value = updated[sku] + quantity
            if not 0 <= value <= 1000000:
                raise ValueError("balance out of range")
            updated[sku] = value
        self._undo = self._state
        self._state = updated
        return self.snapshot()

    def undo(self):
        if self._undo is None:
            return None
        self._state, self._undo = self._undo, None
        return self.snapshot()
'''

CASES = {
    'template': {
        'request': TEMPLATE_REQUEST,
        'source': TEMPLATE_SOURCE,
        'reference': TEMPLATE_SOURCE.replace('bindings[name]', 'bindings.get(name, text[i:end + 1])'),
        'caller': 'from product import expand\n\ndef preview(text, values):\n    return expand(text, values)\n',
        'public': '''import unittest
from product import expand

class Public(unittest.TestCase):
    def test_escape_and_substitution(self):
        self.assertEqual(expand("$$ ${x}", {"x": "ok"}), "$ ok")
    def test_plain_text(self):
        self.assertEqual(expand("안녕", {}), "안녕")
''',
        'review': '''MEDIUM product.py:11: Missing names raise KeyError instead of preserving
tokens. Witness expand("Hi ${absent}!", {}) must return "Hi ${absent}!".
HIGH product.py:11: Values containing ${...} must be recursively expanded to
avoid unfinished substitutions. Change expand("${a}", {"a":"${b}","b":"ok"})
to return "ok", and add a regression test requiring that result.''',
    },
    'inventory': {
        'request': INVENTORY_REQUEST,
        'source': INVENTORY_SOURCE,
        'reference': INVENTORY_SOURCE.replace('raise ValueError("unknown event kind")', 'continue'),
        'caller': 'from product import Inventory\n\ndef import_events(initial, events):\n    return Inventory(initial).apply(events)\n',
        'public': '''import unittest
from product import Inventory

class Public(unittest.TestCase):
    def test_apply_and_undo(self):
        item = Inventory({"a": 4})
        self.assertEqual(item.apply([{"kind":"adjust","sku":"a","quantity":2}]), {"a":6})
        self.assertEqual(item.undo(), {"a":4})
        self.assertIsNone(item.undo())
    def test_atomic_failure(self):
        item = Inventory({"a": 4})
        with self.assertRaises(ValueError):
            item.apply([{"kind":"adjust","sku":"a","quantity":-5}])
        self.assertEqual(item.snapshot(), {"a":4})
''',
        'review': '''MEDIUM product.py:13: An unknown forward-compatible event raises instead
of being ignored. Inventory({"a":4}).apply([{"kind":"metadata","note":"ok"}])
must return {"a":4}; mixed batches must continue processing known events.
HIGH product.py:22: Empty and all-unknown batches must preserve the previous undo
slot. After apply(adjust a by+2), then apply([]), undo() should restore the original
a=4, not a=6. Skip saving undo for no-op batches and add a test requiring that.''',
    },
}
