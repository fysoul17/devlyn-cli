# J1 implementation brief

## Reference

Apply this request alone to the pinned tree. Change exactly `lib/types/string.js`, `test/types/string.js`, and `API.md`.

In the string coercer's existing truncate/max block, retain reference resolution and its `any.ref` failure. After resolving the limit, recognize UTF-8 using the case-insensitive spellings `utf8` and `utf-8`. Walk the already transformed string with `for...of`, accumulating `Buffer.byteLength(character, encoding)`. Stop before the first code point that exceeds the remaining budget. Track the retained endpoint in UTF-16 code units using `character.length`, and slice the original string once at that endpoint. For other encodings and no encoding, retain the current `slice(0, limit)` path. Do not decode a cut Buffer: that could introduce replacement characters.

This preserves existing conversion order, max-reference validation, ordinary max/empty validation, and the schema's immutable configuration. Add a concise explanation of UTF-8 byte budgets to the existing `string.truncate()` API documentation. No declarations change because no signature changes.

The following replacement for the existing `value = value.slice(0, limit);` is a checked source sketch:

```js
                    const encoding = rule.args.encoding;

                    if (encoding && ['utf8', 'utf-8'].includes(encoding.toLowerCase())) {
                        let bytes = 0;
                        let end = 0;

                        for (const character of value) {
                            const size = Buffer.byteLength(character, encoding);

                            if (bytes + size > limit) {
                                break;
                            }

                            bytes += size;
                            end += character.length;
                        }

                        value = value.slice(0, end);
                    }
                    else {
                        value = value.slice(0, limit);
                    }
```

## Public tests to add

Append the following Lab tests to `test/types/string.js`, using that file's existing `describe`, `it`, `Joi`, and `expect` bindings. The tests intentionally use ASCII and BMP input only. Do not add supplementary-plane characters, paired-surrogate endpoint checks, or the designated oracle witness to the public suite. All new loop, stop, empty, encoding, and fallback paths are exercised without testing the endpoint unit distinction.

```js
describe('UTF-8 truncation', () => {

    it('honors byte budgets for ASCII and BMP text', () => {

        const cases = [
            [4, 'ééx', 'éé'],
            [3, 'éé', 'é'],
            [2, '漢x', ''],
            [5, '漢abz', '漢ab'],
            [0, 'abc', ''],
            [8, 'abc', 'abc'],
            [2, '', '']
        ];

        for (const [limit, input, output] of cases) {
            const result = Joi.string().allow('').max(limit, 'utf8').truncate().validate(input);
            expect(result.error).to.not.exist();
            expect(result.value).to.equal(output);
        }
    });

    it('supports UTF-8 aliases and resolved limits', () => {

        for (const encoding of ['utf-8', 'UTF8', 'UTF-8']) {
            expect(Joi.string().max(4, encoding).truncate().validate('ééx').value).to.equal('éé');
        }

        const schema = Joi.object({
            limit: Joi.number(),
            text: Joi.string().max(Joi.ref('limit'), 'utf8').truncate()
        });
        expect(schema.validate({ limit: '4', text: 'ééx' }).value).to.equal({ limit: 4, text: 'éé' });
        expect(schema.validate({ text: 'ééx' }).error.details[0].type).to.equal('any.ref');
    });

    it('preserves conversion preferences and earlier transforms', () => {

        const schema = Joi.string().max(3, 'utf8').truncate();
        expect(schema.validate('éé', { convert: false }).error.details[0].type).to.equal('string.max');
        expect(schema.truncate(false).validate('éé').error.details[0].type).to.equal('string.max');
        expect(schema.trim().replace(/x/g, 'é').validate(' xx ').value).to.equal('é');
        expect(Joi.string().max(2, 'latin1').truncate().validate('ééx').value).to.equal('éé');
        expect(Joi.string().max(0, 'utf8').truncate().validate('x').error.details[0].type).to.equal('string.empty');
    });
});
```

Keep all existing tests. Both variants must pass the repository's unmodified `npm test` command with Node 22, including 100% coverage, lint, and type checks. Do not weaken coverage or add ignore directives.

## Twin

Start with the complete reference. In the new UTF-8 loop only, replace `end += character.length;` with `end += 1;`. Keep the byte accounting, break condition, slicing, reference handling, documentation, and tests identical. This confuses a count of code points with the UTF-16 offset required by `slice`; it is a plausible Unicode indexing error. Add no special-case trigger, suggestive comment, or misleading identifier.

The twin changes exactly the reference's three-file set relative to the pinned tree. ASCII and BMP iterations advance the endpoint equally in both variants, so all public assertions and coverage remain satisfied. J1-W is the only hidden row that includes a retained surrogate pair.
