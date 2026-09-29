# J4 implementation brief

## Reference

Apply this request alone to the pinned tree. Change exactly `lib/types/number.js`, `test/types/number.js`, and `API.md`.

The `multiple` method currently caches `baseDecimalPlace` and `pfactor` for literals, but stores `baseDecimalPlace: null` for a reference. The generic validator has already resolved and checked `base` when the rule's validate function runs. At the start of that function, before `valueDecimalPlace` is calculated, add:

```js
if (baseDecimalPlace === null) {
    baseDecimalPlace = internals.decimalPlaces(base);
    pfactor = Math.pow(10, baseDecimalPlace);
}
```

Then retain the existing value-precision rejection, scaled/rounded remainder operation, and error construction using `options.args.base`. Recompute only local parameters per invocation; do not write resolved numbers back to the schema's rule args. Keep the literal preparation, describe/build representation, numeric validation, and existing rounding algorithm.

Clarify in the `number.multiple()` documentation that a numeric reference uses the same decimal arithmetic as a literal divisor. There is no new method or declaration.

## Public tests to add

Append these tests to `test/types/number.js`. They cover fractional sibling refs, changing the divisor across validations, conversion of the sibling, negative dividends, nonmultiples, excess precision, context refs, scientific notation, original-reference error context, and invalid context values. The values used with fractional refs have at least as many decimal places as their divisors. Keep the existing literal and integer-reference tests, but do not add a fractional-reference case with a less precise dividend, including an integer or zero. Do not add J4-W.

```js
describe('decimal reference multiples', () => {

    it('uses resolved decimal divisors across validations', () => {

        const schema = Joi.object({
            step: Joi.number(),
            amount: Joi.number().multiple(Joi.ref('step'))
        });
        for (const [step, amount, valid] of [[0.25, 0.75, true], [0.25, 0.65, false], [0.25, 0.251, false], [0.2, 0.6, true], [0.25, -0.75, true], ['0.25', 0.75, true]]) {
            const result = schema.validate({ step, amount });
            expect(!result.error).to.equal(valid);
            if (!valid) {
                expect(result.error.details[0].type).to.equal('number.multiple');
            }
        }
    });

    it('supports context references and scientific notation', () => {

        const ref = Joi.ref('$step');
        const schema = Joi.number().multiple(ref);
        expect(schema.validate(0.75, { context: { step: 0.25 } }).error).to.not.exist();
        expect(schema.validate(3e-7, { context: { step: 1e-7 } }).error).to.not.exist();
        const result = schema.validate(0.65, { context: { step: 0.25 } });
        expect(result.error.details[0].type).to.equal('number.multiple');
        expect(result.error.details[0].context.multiple).to.shallow.equal(ref);
        expect(schema.validate(0.75, { context: { step: '0.25' } }).error.details[0].type).to.equal('any.ref');
    });
});
```

Both variants must pass the unchanged `npm test` with Node 22. Existing static-divisor tests exercise the precision rejection even if the twin's dynamic-divisor path does not take it. All new lines and outcomes remain covered; no coverage, lint, or type-check exemptions are necessary.

## Twin

Change only the argument of the new runtime precision computation: use `internals.decimalPlaces(value)` instead of `internals.decimalPlaces(base)` in the `baseDecimalPlace === null` block. Keep the condition, the scale computation, literal preparation, comparison and remainder code, error context, tests, and documentation identical.

This mistakenly derives reference-divisor metadata from the dividend, a plausible confusion between the two quantities used by the multiple rule. The 0.25/0.75 public cases use identical precision; the more precise nonmultiple still fails its remainder check. Integer-reference regressions remain unchanged. The hidden witness uses a whole-number dividend and a fractional divisor, causing the twin to round the divisor to zero at scale 1 and reject a valid multiple.

The twin and reference change exactly the same three files relative to the pinned tree. Add no special handling for the witness and no suggestive comments or naming.
