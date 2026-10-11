# Direct AGENTS import dedup — source review v1

2026-10-10. REVISE. One HIGH finding: an import-looking string inside native-stripped YAML frontmatter can remove CLAUDE.md's sole effective defaults block. Review scope is only bin/instructions.js, package.json/package-lock.json and scripts/test-windows-portability.py. No product edits, models, authentication, native CLI or Docker calls were made. A local Node invocation exercised the installed detector/lexer, not Claude.

## HIGH — omit native-stripped frontmatter before import detection

The new importsAgentsMd sends the complete BOM-stripped source to Marked. Native Claude memory parsing strips frontmatter first. Thus this valid frontmatter-only mention is detected as an actual import:

```markdown
---
note: "Read @AGENTS.md for team rules."
---

# Actual instructions
Use pnpm.
```

Observed local result from `require('./bin/instructions').importsAgentsMd(input)`: `true`. Marked tokens were `hr`, a depth-2 `heading` containing the note, then the actual body heading/paragraph. Its leaf text token matches the import regex.

If adjacent AGENTS.md holds defaults, the unchanged importsAgentsDefaults gate therefore reports imported=true. Existing updateInstructions then removes CLAUDE.md's own managed defaults even though the native parser never sees this import mention. The self-import check does not protect distinct files. This is a loss of effective instructions, not merely an extra duplicate. The new tests omit frontmatter and therefore do not cover this path. The example was discovered during static review, then checked locally; no retroactive experiment prediction is claimed.

Pinned host evidence (binary SHA256 c9b5341637becbd423ddffc5b254afb645682a3868cb708bbc6cc0e7bb419937):

- Byte191541381: `Gb` removes a leading BOM.
- Byte191545777: `Pv=/^---\s*\n([\s\S]*?)---\s*\n?/`.
- Byte191545890: `si` applies Gb, checks for a subsequent delimiter, matches Pv and computes `a=e.slice(i[0].length)`. It returns `content:a` even on YAML parse failure; without a match it returns the original content.
- Byte195890803: `OZn` obtains frontmatter/content through `si` and returns the stripped content.
- Byte195891055: `YNe` passes OZn's content to `new EA({gfm:false}).lex(...)`, then to BZn's import walker.

The host/Linux runtime identity limitation from import-parser-audit.md remains. However this is direct source evidence in the specifically pinned host version, and it demonstrates why Markdown lexing alone is not a conservative subset of the native memory pipeline.

Smallest correction: exclude the same native frontmatter prefix from the detector's temporary parsing input before Marked, without altering the persisted source or ownership/update code. No YAML interpretation is needed. Marked's standard Lexer does not supply native memory-frontmatter extraction; its observed output above demonstrates that. A new YAML package or frontmatter extension would add unnecessary semantics and might differ on malformed YAML. Preserve the native boundary rather than assume a stricter closing-line grammar.

Targeted cases: frontmatter-only exact/relative/inline mention must be false; a real body import after that frontmatter must be true; BOM/CRLF; malformed YAML with the same matched boundary must still be excluded; missing closing delimiter follows ordinary native Markdown behavior. Add an installer case proving frontmatter-only mention retains CLAUDE defaults and prose, while a real body import deduplicates and preserves the existing backup/reinstall behavior.

## Other reviewed properties

Marked15.0.12 is pinned consistently in manifest and lock, included in bundleDependencies/inBundle, provides a CJS entrypoint, requires Node>=18 and has no runtime dependency tree. The current Node floor is unchanged. The lock integrity matches the metadata checked during design. Actual new tarball installation/bundle inspection is not claimed by this source review.

The leaf-only text walker is intentionally narrower than native's parent-text traversal, skips code/codespan/html tokens, traverses nested tokens/items, and compares full native-style path tokens against the two adjacent spellings after fragment removal. It does not add punctuation stripping or broad basename matching. Existing self-import, stale-AGENTS and ownership flows remain outside the patch. Added tests cover meaningful inline/relative installation, nested literals, backups and repeated self-alias updates. No further actionable finding was established in this bounded round.

## Exact reviewed source hashes

- `bin/instructions.js`: `c2ef3fda7714efab8e1569a4d08ec17abc1a10469133b11b159d0884f7bb2532`
- `package.json`: `ffaaffe502f9c77faa7c0e3dfa2c261373e15ff907d15acf16e96bc604919c07`
- `package-lock.json`: `673daed9c547a038027950cfd31a1fa2144639982a8299a37184d5f0d2c7ae8d`
- `scripts/test-windows-portability.py`: `8497a6a228fd7f1bc1bdd3fc63121b1eb6e902879f3d64ac8c1d7fd367b0b6a7`
