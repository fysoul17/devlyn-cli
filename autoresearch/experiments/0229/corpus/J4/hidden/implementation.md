# J4 implementation brief

This request applies alone to the pinned tree. Do not ship hidden oracle cases as repository tests.

## Reference design

Change exactly `src/rules_block/reference.ts` and `test/markdown-it/misc.test.mjs`.

At successful reference-definition token creation, keep the existing null-prototype metadata object and normalized `label`. Add `meta.href = href` and `meta.title = title`, using the final local values after parsing, normalization, validation, and title fallback. These values describe the occurrence at `token.map`. Do not obtain them through `env.references[label]`: that object represents the winning lookup definition and can describe a different source occurrence. Do not alias the environment entry. Update the nearby comment that currently says href/title stay in the environment to explain the additional token snapshot.

Do not change reference insertion or lookup precedence, hidden flags, maps, default stripping, or inline link/image metadata. The existing `Should strip reference definition tokens by default` test has an exact metadata assertion; update its expected null-prototype object to include `href: '/url'` and `title: ''`. Keep the existing label-only inline metadata test unchanged.

Add public coverage using only definitions with unique normalized labels and fresh environments:

1. A normalized destination with a space inside angle brackets, an entity in a title, the expected normalized label, and exact source map. Compare environment lookup and token snapshot values and default-versus-retained rendering.
2. A multiline title with decoded entities, checking its accepted map extent and rendered link title.
3. A definition followed by an apparent title line with trailing garbage, checking an empty metadata title, a one-line definition map, and the remaining paragraph output.
4. Mutation of a retained unique token's metadata does not change the environment's lookup record, and retained definitions remain hidden.

Do not assert occurrence payloads for a duplicated normalized label or a label already present in the incoming environment in public tests. Existing fixtures may include repeated definitions; they exercise rendering, which this change does not alter. No coverage threshold is configured by `npm test`; do not introduce or weaken one.

## Twin construction

Keep precisely the reference file set and byte-identical tests. Change just the source of the two new payload fields: copy `href` and `title` from `state.env.references[label]` after the existing first-definition-wins insertion, rather than from the final local `href` and `title`. Continue to allocate a separate null-prototype metadata object, retain its local label, and leave map/hidden fields alone.

Treat this as one incorrect payload-source selection, not separate defects in two fields. It is a plausible attempt to reuse the already normalized stored reference. Unique definitions receive the correct payload. A shadowed definition receives the winner's payload while its source map points to its own occurrence. No special casing or hints may be added.

The twin passes all public checks, including the updated exact-shape assertion, and fails only J4-O3 among the hidden rows.
