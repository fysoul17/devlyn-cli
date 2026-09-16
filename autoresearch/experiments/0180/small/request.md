Fix `selection.parse_selection(text)` for a CLI that accepts comma-separated
positive decimal item numbers and inclusive non-descending ranges, such as
`3, 1-2, 3` → `[3, 1, 2]`. Preserve first-occurrence order and remove duplicates.
Only ASCII space, tab and line feed may surround a token or either side of a
hyphen; carriage return, vertical tab, form feed and all other whitespace are
invalid anywhere. Equal range endpoints denote one item. Digits must be ASCII;
leading zeroes are allowed. Empty input or input containing only space, tab and
line feed returns `[]`. Reject empty comma fields, descending ranges, zero, signs,
non-ASCII whitespace/digits, decimal points, or extra hyphens with `ValueError`.
Reject non-string inputs with `TypeError`. Inputs/range endpoints are at most
999, so resource limits beyond this domain are out of scope. Keep the public
function name/signature; use only the Python standard library. Preserve the
existing tests and `NOTICE.txt` byte for byte; add tests if useful.

Complete the implementation, verification and final response in this working
tree. Do not commit or publish. No operator replies are available during this run.
