# Configuration format v1

A document is a JSON object with only `include` and `values` keys. Both keys are
optional. `include` is a list of nonempty path strings and `values` is an object.
An empty document means no includes and no local values. Invalid JSON, unknown
document keys, invalid include entries, or non-object values raise ConfigError.
A ConfigError identifies the failing canonical path and the root-to-failure
include chain; no arbitrary Python error is part of this API.

Each include is resolved relative to the file that declares it. Canonical
resolved paths are file identities. Merge includes in list order, then the local
values. When both values at a key are objects, merge recursively; otherwise the
later value replaces the earlier one. Lists replace, never concatenate, and
null is an ordinary value rather than a deletion marker. Do not mutate either
input while merging. Include order and local overrides apply even in diamonds:
a shared base is applied in each branch's position, not skipped globally.

A cycle exists only when a canonical file is already on the current include
stack. The same file included again after its earlier branch completed is legal.
Read each distinct document no more than once per Loader.load call: shared
includes must see the same bytes throughout that load. Dependencies contain
every distinct canonical file reached, including the root, sorted by path text.
Snapshot dependency paths are Path objects, independent of include spelling.
