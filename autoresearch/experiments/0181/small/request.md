Fix `overlay.merge_layers(*layers)` for layered configuration dictionaries.

Apply layers left to right. A string replaces the previous value. A dictionary
recursively overlays an existing dictionary; if the old value is absent or a
string, start a fresh dictionary. `None` deletes that key, and deleting an absent
key is harmless. Empty dictionaries remain present, including when all their
children were deleted. No arguments returns `{}`.

Every layer must be a dictionary, all dictionary keys must be strings, and each
value must be a string, dictionary, or `None`. Invalid types raise `TypeError`,
including invalid nested values in an earlier layer that a later layer replaces
or deletes. Inputs are finite acyclic built-in dictionaries with nesting at most
30; custom mapping behavior and cycles are outside scope. Do not mutate any input.
The result and all its dictionaries must be independent of the inputs and of
other result branches, even if inputs share dictionaries. Dictionary iteration
order and exception wording are not specified.

Examples:
`merge_layers({'db': {'host': 'a', 'port': '8'}}, {'db': {'host': None}})`
returns `{'db': {'port': '8'}}`.
`merge_layers({'db': 'off'}, {'db': {'host': None}})` returns `{'db': {}}`.

Use the Python standard library only. Preserve `test_overlay.py` and `NOTICE.txt`
byte-for-byte. Add focused tests if useful and run `python3 -m unittest`.
Complete the edit and final response in this tree; do not commit or publish.
