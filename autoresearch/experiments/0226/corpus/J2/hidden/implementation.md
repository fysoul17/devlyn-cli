# J2 implementation brief

## Reference

Apply this request alone to the pinned tree. Change exactly `lib/types/boolean.js`, `test/types/boolean.js`, and `API.md`.

Keep the early return for actual booleans and the existing trimmed, sensitivity-aware recognition of the canonical strings `true` and `false`. Replace only the subsequent custom truthy/falsy lookup. For a string, try candidates `[value, value.trim()]` in that order; for a non-string, try `[value]`. For each candidate, check truthy before falsy with the existing `Values.has(..., !schema._flags.sensitive)` comparison. Set the result to a boolean and stop on the first match. If neither candidate matches, leave the original input untouched. Do not normalize registered map values.

Document the whitespace fallback, input-match precedence, and unchanged sensitivity in the boolean truthy/falsy API sections. No new API or declaration is needed.

Use this checked replacement for the existing two-line custom mapping expression inside `if (typeof value !== 'boolean')`:

```js
            const candidates = typeof value === 'string' ? [value, value.trim()] : [value];

            for (const candidate of candidates) {
                if (schema.$_terms.truthy && schema.$_terms.truthy.has(candidate, null, null, !schema._flags.sensitive)) {
                    value = true;
                    break;
                }

                if (schema.$_terms.falsy && schema.$_terms.falsy.has(candidate, null, null, !schema._flags.sensitive)) {
                    value = false;
                    break;
                }
            }
```

## Public tests to add

Append these tests to `test/types/boolean.js` with its existing Lab bindings. They cover both candidate positions, both result booleans, no match, non-string inputs, sensitivity, canonical precedence, and truthy/falsy overlap for the same candidate. The padded registration test has no competing trimmed registration. Do not add an input whose original and trimmed spellings map to opposite booleans, and do not add J2-W to the public suite.

```js
describe('trimmed custom boolean values', () => {

    it('converts whitespace around custom strings', () => {

        const schema = Joi.boolean().truthy('yes').falsy('no');
        for (const [input, output] of [[' yes ', true], [' NO ', false], ['yes', true], ['no', false]]) {
            const result = schema.validate(input);
            expect(result.error).to.not.exist();
            expect(result.value).to.equal(output);
        }

        const result = schema.validate(' unknown ');
        expect(result.value).to.equal(' unknown ');
        expect(result.error.details[0].type).to.equal('boolean.base');
    });

    it('preserves case sensitivity and conversion preferences', () => {

        const schema = Joi.boolean().truthy('YES').falsy('NO').sensitive();
        expect(schema.validate(' YES ').value).to.equal(true);
        expect(schema.validate(' NO ').value).to.equal(false);
        expect(schema.validate(' yes ').error.details[0].type).to.equal('boolean.base');
        expect(schema.validate(' YES ', { convert: false }).error.details[0].type).to.equal('boolean.base');
    });

    it('preserves canonical booleans and custom values', () => {

        const schema = Joi.boolean().truthy('false').falsy('true');
        expect(schema.validate(' false ').value).to.equal(false);
        expect(schema.validate(' true ').value).to.equal(true);
        expect(schema.validate(true).value).to.equal(true);
        expect(schema.validate(false).value).to.equal(false);
        expect(Joi.boolean().truthy(1).falsy(0).validate(1).value).to.equal(true);
        expect(Joi.boolean().truthy(1).falsy(0).validate(0).value).to.equal(false);
        expect(Joi.boolean().truthy('x').falsy('x').validate(' x ').value).to.equal(true);
        expect(Joi.boolean().truthy(' yes ').validate(' yes ').value).to.equal(true);
        expect(Joi.boolean().truthy(' yes ').validate('yes').error.details[0].type).to.equal('boolean.base');
    });
});
```

Keep all existing tests and run the unchanged `npm test` with Node 22. No dependency, coverage-ignore, lint, or type-check exceptions are needed.

## Twin

Start from the full reference and change the string candidate array from `[value, value.trim()]` to `[value.trim(), value]`. Leave the non-string array, canonical-string handling, candidate loop, sensitivity, documentation, and tests identical.

This is a plausible normalization-first mistake: the original candidate remains available, but is tried too late when both spellings match. The reference and twin touch exactly the same three files relative to the pinned tree. The public suite runs all changed paths but never supplies conflicting mappings across the two candidates. Do not add comments or names that disclose the mistake.
