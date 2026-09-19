# Incremental NDJSON parser

Implement `Decoder(max_line_bytes=1048576)` in stream.py with `feed(chunk)` and
`finish()` returning lists of decoded JSON values. Only stream.py and optional
tests/test_regression.py may change. Preserve the existing ParseError public API.
Use the standard library; no new dependencies or unrelated features.

1. feed accepts bytes (including empty bytes), retaining incomplete physical lines
between calls. Split on LF bytes. Decode each completed line as strict UTF-8, then
parse one JSON value; JSON's standard leading/trailing whitespace and CRLF work.
Blank lines containing only ASCII space, tab or CR are ignored but still increment
the physical 1-based line number. UTF-8 characters may span chunks. JSON null,
booleans, numbers, strings, arrays and objects are all valid outputs. Reject JSON
NaN, Infinity and -Infinity; do not reject ordinary JSON strings with those words.
2. max_line_bytes must be a positive int, excluding bool; invalid type raises
TypeError, nonpositive value raises ValueError. The limit counts all bytes before
LF, including a CR and whitespace. Reject over-limit input as soon as a physical
line exceeds the limit even without LF. Bound retained incomplete-line storage
by this limit; do not retain already processed lines or whole prior chunks.
3. Malformed UTF-8, malformed/nonstandard JSON and length violations raise
ParseError(line, reason), with reason respectively `utf8`, `json`, or `limit`.
For a physical line exceeding the limit, `limit` takes precedence over parsing.
For multiple bad physical lines, report the earliest line. The failing call
returns no partial values. The decoder becomes permanently failed: every later
feed or finish re-raises the exact same exception object, including empty feed.
Already returned values are unaffected. Do not silently skip malformed records.
4. Before failure/closure, a non-bytes feed raises TypeError without consuming
input or poisoning the decoder. After failure, the saved ParseError has precedence
over argument validation. After successful finish, feed always raises RuntimeError.
5. finish parses a final nonempty line without LF under the same rules, then closes
successfully; subsequent finish returns []. Empty input and trailing LF return [].
Failure during finish has the same sticky-failure behavior. Instances must not
share state. Never mutate input or previously returned mutable JSON values.

Run `python3 -B -m unittest discover -s tests -v`. Preserve supplied tests, spec.md,
spec.expected.json and .gitignore. Add focused regressions as needed; inspect every
requirement, scope and task-created debris before finishing. Local commits only;
the outer owner handles delivery. State actual checks and remaining limitations.
