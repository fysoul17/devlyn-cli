# Direct AGENTS import parser audit — design evidence

2026-10-10. Read-only static investigation, not product adoption or proof of a Linux native run. No Claude/Codex executable, model, Docker, credential or installer call was made. The host binary was read as bytes; only bounded embedded-source excerpts were inspected. Official documentation was read over the web.

## Root cause confirmed in the pinned host parser

Binary: `/Users/aipalm/.local/share/claude/versions/2.1.296`.
SHA-256: `c9b5341637becbd423ddffc5b254afb645682a3868cb708bbc6cc0e7bb419937`.

At byte 195891055, the memory parsing function `YNe` tokenizes content with `new EA({gfm:!1}).lex(y)` and passes the resulting tokens to `BZn`. At byte 195893761, `BZn` scans text tokens using:

```js
/(?:^|\s)@((?:[^\s\\]|\\ )+)/g
```

This excerpt is regex notation from embedded JavaScript, not a literal escaped string to paste into another regex. The parser then:

1. Takes the captured path and removes the first `#` and everything after it.
2. Replaces escaped spaces (`\ `) with ordinary spaces.
3. Applies its path-safety/prefix checks.
4. Resolves the path relative to `dirname(importingFile)` and deduplicates results.

The `dirname as QT` import is visible at byte 195869795. The native path resolver seen at byte 188782366 expands home paths and resolves ordinary relative paths against its passed base. The memory function uses `et(M,QT(n))` for this operation.

The token walker skips `code` and `codespan`. It also skips HTML tokens, except a comment-shaped HTML token can have complete comments stripped and remaining nonempty text scanned. Ordinary `text` tokens are scanned, and child `tokens` and list `items` are traversed. This is Markdown-aware parsing, not a whole-line import detector.

Consequently the two reproduced misses have source-grounded support:

- `@./AGENTS.md` resolves to the same adjacent AGENTS.md as `@AGENTS.md`.
- `Read @AGENTS.md for team rules.` contains the import as an ordinary text-token word.

A suffix such as `#rules` is removed before resolution. Terminal punctuation is not generally removed: plain `@AGENTS.md.` or `@AGENTS.md,` refers to that punctuated filename. Do not add punctuation trimming to make prose look nicer. `someone@AGENTS.md` lacks the required preceding whitespace/start; quoted `@"AGENTS.md"` fails the native path-prefix check. Backslash-escaped Markdown punctuation and nested constructs are affected by tokenization and cannot be decided safely by the raw import regex alone.

The current [official import documentation](https://code.claude.com/docs/en/memory#import-additional-files) independently supports inline/relative imports, escaped spaces, and skipping code spans/fences. It does not establish that the pinned Linux binary is byte-identical to this host executable. No runtime expansion, trust approval, file availability or effective model context was observed here.

## Smallest safe correction

Keep the correction inside `importsAgentsMd`. Its responsibility is recognizing a supported direct import of the adjacent file, not resolving an arbitrary import graph. Preserve `importsAgentsDefaults`, the `agentsMdIsClaudeMd` self-import exception, the AGENTS freshness gate, and the existing ownership-aware update/backups flow.

Replace the whole-line-only test with a native-boundary token test accepting exactly `AGENTS.md` and `./AGENTS.md` (optionally their native `#fragment` forms) in confidently ordinary text. Extract the full native-style path token before comparing; do not use a prefix test that accepts `AGENTS.md.bak`, punctuation or a different directory. Do not infer aliases by basename or follow arbitrary imports. The two demonstrated spellings need no filesystem resolver or new dependency.

Retain fenced-code exclusion and add exclusion for code spans before broadening the match to inline text. Correctly handle matched backtick-run lengths and multiline spans, or conservatively decline ambiguous contexts. Mask excluded content rather than deleting it and joining adjacent text into a newly valid import. HTML/comments, indented code, and nested list/blockquote fences also need negative protection: a raw whitespace regex over every non-top-level-fence line would introduce false positives that can remove the only effective defaults block.

A small conservative detector for plain prose is sufficient for the two confirmed failures; it need not promise full native Markdown equivalence. For constructs the small scanner cannot classify confidently, return no import and retain the block. Explicitly test/document that bounded scope. Supporting every heading, emphasis, link, nested list and raw-HTML edge exactly would require matching the native tokenization; that broader parser/dependency is not justified solely by these two observed misses. Existing instruction-paragraph logic may supply local fence/comment state, but is not itself a native import parser.

## Required regression matrix

Positive direct-import cases: exact line; `@./AGENTS.md`; plain inline `Read @AGENTS.md for team rules.`; the same inline relative spelling; ordinary surrounding whitespace/BOM/CRLF. If fragment support is included, test `@AGENTS.md#rules` and `@./AGENTS.md#rules` explicitly.

Negative safety cases: single and multiple-backtick code spans; multiline code spans; backtick and tilde fences, including longer delimiters; indented code; comment-only and raw HTML literal regions; a nested blockquote/list fenced example; escaped at-sign; email/non-whitespace prefix; quoted path; `@@AGENTS.md`; `@AGENTS.md.bak`; `@AGENTS.md,`; another basename; parent/subdirectory AGENTS.md. Keep mixed examples where a literal mention precedes a real ordinary-text import, ensuring exclusion does not hide or invent tokens. For conservative unsupported contexts, retaining a duplicate is safer than deleting the only defaults; do not describe those as complete native parity.

Installer assertions for both newly supported spellings should cover:

- AGENTS already holds current defaults: exactly one block overall, only AGENTS owns it, CLAUDE prose/import bytes remain unchanged.
- CLAUDE previously received its own block while AGENTS lacked one: later combined install removes only that owned duplicate, preserves prose and exact backup behavior, and repeated installs are byte-stable.
- AGENTS symlink/pointer aliases CLAUDE itself: the existing exception retains exactly one CLAUDE-owned block over repeated installs; extend the direct/inline-relative spelling coverage without changing the alias logic.
- A literal/non-import mention retains CLAUDE's own defaults; stale AGENTS behavior continues to require its own selected target and matching skills.

The current tests at scripts/test-windows-portability.py:405 onward already exercise exact-line imports, duplicate removal, reinstall stability and the symlink self-import exception. Extend those existing checks rather than create another installation framework. Root's retained disposable reproduction is causal evidence for installer duplication, not evidence of measured token savings. Do not alter frozen 0239 arm packages/results to retrofit this correction.

## Checked local source identities

- `bin/instructions.js`: `cd9802b3864509879f5a6cc6f240cd6f24366086167f88beb55b22acc7f4eb20`
- `bin/devlyn.js`: `ef61d17255c7b77cd6968285e30669e588b9ba2486fded475063649337f4171a`
- `scripts/test-windows-portability.py`: `5e0af1e8a38c54256343ad8e7b99f0ea9c26d49de02a2b4c9056a9362c6cc9de`
- `autoresearch/experiments/0239/results/import-dedup-observation.md`: `5a8e8b11766c2b73087a683b5d7fb10cfe421c8978c2b95ff29bc9f9a79f879b`
