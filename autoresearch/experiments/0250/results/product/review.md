# Comment-prefixed import: independent product review

2026-10-11. **SHIP — zero CRITICAL or HIGH findings.** One review round is
sufficient for this narrow, source-supported installer correction.

Scope: the current diff in `bin/instructions.js` and
`scripts/test-windows-portability.py`, plus retained evidence in
`.devlyn/comment-import-v1`. This review does not change or reopen research 0250.

## Source and behavior

The preserved `native-loader-excerpt.js` explicitly excludes code/codespan
tokens. For an HTML token whose trimmed raw text begins with `<!--` and contains
`-->`, it removes complete comments using `/<!--[\s\S]*?-->/g` and applies the
native import-path matcher to the remaining raw text. Ordinary HTML tokens are
otherwise skipped. The new branch follows precisely that boundary; it does not
globally strip HTML/comments or reinterpret the remainder as Markdown.

The extracted `matchesImport` retains the prior complete-token regex and removes
only an optional fragment before exact comparison with `AGENTS.md` or
`./AGENTS.md`. Escaped spaces remain part of the captured filename, so they cannot
turn a different path into the adjacent filename. A backslash directly before
`@` still prevents the whitespace/start prefix match. Suffixes, punctuation,
other directories and quoted paths remain excluded. No new broad path
normalization or unsupported stripping is introduced.

Complete comments followed by an import, multiple comments, and a valid import
before a trailing unclosed comment follow the retained native rule. A lone
unclosed comment without a complete comment terminator does not enter this
branch. Comment-only tokens lose their apparent imports when complete comments
are removed. Raw HTML that does not start with a comment remains excluded;
fenced and inline code are rejected before the new branch. These are native
token semantics, not a promise to suppress every apparent import inside all
possible trailing raw markup.

Only recognition changes. Existing ownership, self-import, backup and managed
default-removal logic remains intact. The added installer cases assert exact
CLAUDE prose preservation, one managed copy for real imports, retention for
comment-only examples, exact backups on migration and stable repeated installs.
This fixes the demonstrated duplicate at its parser boundary (**No workaround**)
without adding a new parser, dependency or instruction (**No overengineering**,
**Best practice**, **Optimized**).

## Retained verification

- `prediction-v1.json` predates implementation and identifies the native loader
  version/path, hash and extracted byte interval. The claim is source-aligned
  deduplication; no live model expansion or token/time improvement is claimed.
- `pre-fix-v1-apparatus.json` explicitly rejects the first installer probe:
  fixture placement below a common Git directory broke Git ownership discovery.
  That failed setup is not credited as product evidence.
- Corrected `pre-fix-v2` reproduces the parser failure and the specific fresh
  install/upgrade duplicate cases. `post-fix-targeted` passes all three tests.
- The completed packed/offline-installed package suite passes all 72 tests.
  `verification-summary.json` reports the installed detector hash equal to the
  reviewed source, unchanged package metadata/lockfile hashes, and passing
  scoped diff whitespace checks. This reviewer read the retained results and
  did not rerun tests.

Reviewed SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `bin/instructions.js` | `217b59bd1152de46ac8c84325edb5217d53604267b80e6215b6b5824ca764c75` |
| `scripts/test-windows-portability.py` | `c81d28a17dbf4a59dd4054875e2fe7cfd60cbe494663b330657bc2fa36aeb300` |
| `.devlyn/comment-import-v1/native-loader-excerpt.js` | `79665b907ecad6702a5e6cd65d5b9d72f409b6c670dd361c1201b59a0fc3f357` |

No additional implementation, regression expansion or review round is required
by this diff. Only this report was written; no native, authentication or test
operation was launched by the reviewer.
