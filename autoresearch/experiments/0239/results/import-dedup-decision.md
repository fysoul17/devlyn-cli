# Direct AGENTS import correction accepted

2026-10-10, independent installer correctness work after the closed 0239 wording
comparison. This does not reopen that comparison or alter either frozen archive.
Root accepts the detector and selects it for the next prospective solo baseline.

The old installer recognized only a whole-line `@AGENTS.md`. Retained disposable
installs reproduced two defaults blocks for `@./AGENTS.md` and ordinary inline
imports, while exact-line imports had one. Native Claude 2.1.296 embedded source
and official import documentation independently support those spellings; no
model-context measurement or token-saving percentage is claimed.

The correction lexes Markdown with bundled, pinned Marked 15.0.12, scans complete
direct adjacent path tokens, and excludes code, escapes, HTML tokens and native-
bounded frontmatter. It preserves original instruction bytes, ownership checks,
exact backups, the stale-AGENTS gate and the self-import exception. It deliberately
does not follow arbitrary import graphs or promise complete native parser parity.
HTML-token remainders and native parent-text quirks can conservatively retain a
duplicate. Marked 15 preserves the installer's synchronous CommonJS/Node floor;
it has no runtime dependencies and is included in offline npm bundles.

The first review found a HIGH: a frontmatter-only mention could remove the only
effective defaults. The reproduced failure and exact first source remain in
import-frontmatter-reproduction-v1.json and import-detector-v1.js. The narrow
native-prefix correction passed the second review, import-dedup-review-v2.md.
There are no remaining HIGH/MEDIUM findings in that bounded review.

Validation:

- 37 Markdown/path/frontmatter controls and all 71 packaged installer tests pass
  in import-dedup-package-v3.json, including exact backups, repeated installation,
  self-import and published manifestless upgrades. Inputs remained unchanged.
- Clean locked dependency installation, 15 installer-menu tests and 59 loop
  tests pass in import-dedup-ci-{dependencies,installer,loop}-v1.json.
- Full lint passes in import-dedup-lint-v2.json; inputs remained unchanged.
- The failed PackageTests v2 and lint v1 remain retained. The former incorrectly
  treated the current unreleased shared tree as published history; it now seeds
  the exact published 4.1.0 fixture; the unreleased shared tree is not treated as
  published history. The latter omitted dependencies from its
  incomplete-package fixture; it now copies them. Neither repair weakens product
  ownership or incomplete-install assertions; import-fixture-review-v1.md is SHIP.
- Native Windows execution is not claimed. The new cases use the existing
  cross-platform driver and offline bundled install path.

Principles: **No workaround** fixes the installer instead of asking users to
rewrite valid imports. **Best practice** uses a Markdown lexer instead of an
expanding collection of masking regexes. **No overengineering** keeps direct
adjacent imports as the boundary. **Optimized** adds no always-loaded model
instruction. **No guesswork** limits the claim to reproduced correctness, not
unmeasured model efficiency. **Production ready** preserves the ownership and
recovery contracts; the HIGH finding was fixed before acceptance.

Next baseline: original 4.2.3 plus the two admitted delivery fixes and this
installer correction. The 0238 v2 builder records all seven copied source hashes.
Root instructions remain unchanged; 0238 S/H/P candidates are still experimental.
