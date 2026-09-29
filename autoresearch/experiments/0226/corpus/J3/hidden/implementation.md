# J3 implementation brief

## Reference

Apply this request alone to the pinned tree. Change exactly `lib/validator.js`, `test/base.js`, and `API.md`.

Extend `internals.Mainstay.snapshot()` and `restore()`, beside the existing externals/warnings bookkeeping. Save the artifact state with:

```js
artifacts: this.artifacts && new Map([...this.artifacts].map(([id, paths]) => [id, paths.slice()]))
```

The map copy preserves key identity and insertion order; copying each accumulated path list prevents later `push(state.path)` calls from changing the saved list. Individual path arrays are not mutated by the collector, so do not clone artifact identifiers or recursively clone paths. Keep the null state when no map existed.

In `restore()`, assign `this.artifacts = snapshot.artifacts;` after popping the same snapshot used for externals and warnings. Keep `commit()` as a stack pop so successful attempts retain their live accumulated map. Do not move collection out of `internals.finalize` or change snapshot callers in alternatives, array item matching, `$_match`, or failover handling.

Add a short description to `any.artifact()` explaining that restored speculative validation does not contribute artifacts. This request is limited to the existing transaction lifecycle; do not redefine artifact reporting for every ordinary root validation failure.

## Public tests to add

Append the tests below to `test/base.js`. They cover snapshotting both null and nonempty maps, restoring after an unsuccessful branch and a failover, successful commit, async exposure, preserving distinct preexisting IDs, and successful append to a shared ID. Do not combine a preexisting artifact ID with an append to that same ID inside an attempt that subsequently restores. In particular, do not add J3-W to the public suite.

```js
describe('artifact rollback', () => {

    it('discards artifacts from an unsuccessful alternative', () => {

        const schema = Joi.alternatives().try(
            Joi.object({ x: Joi.any().artifact('lost'), y: Joi.any().required() }),
            Joi.object({ x: Joi.any() })
        );
        const result = schema.validate({ x: 1 });
        expect(result.error).to.not.exist();
        expect(result.artifacts).to.not.exist();
    });

    it('preserves prior artifacts and commits a successful alternative', async () => {

        const schema = Joi.object({
            a: Joi.any().artifact('keep'),
            b: Joi.alternatives().try(
                Joi.object({ x: Joi.any().artifact('lost'), y: Joi.any().required() }),
                Joi.object({ x: Joi.any().artifact('winner') })
            )
        });
        const input = { a: 1, b: { x: 2 } };
        const expected = new Map([['keep', [['a']]], ['winner', [['b', 'x']]]]);
        expect(schema.validate(input).artifacts).to.equal(expected);
        expect((await schema.validateAsync(input, { artifacts: true })).artifacts).to.equal(expected);
    });

    it('discards artifacts when failover replaces an object', () => {

        const schema = Joi.object({
            a: Joi.any().artifact('keep'),
            b: Joi.object({ x: Joi.any().artifact('lost'), y: Joi.any().required() }).failover(null)
        });
        const result = schema.validate({ a: 1, b: { x: 2 } });
        expect(result.error).to.not.exist();
        expect(result.value).to.equal({ a: 1, b: null });
        expect(result.artifacts).to.equal(new Map([['keep', [['a']]]]));
    });

    it('retains committed paths for a shared artifact id', () => {

        const schema = Joi.object({
            a: Joi.any().artifact('same'),
            b: Joi.alternatives().try(Joi.any().artifact('same'))
        });
        expect(schema.validate({ a: 1, b: 2 }).artifacts).to.equal(new Map([['same', [['a'], ['b']]]]));
    });
});
```

Keep existing tests, including the pinned failover warnings/externals regressions. Both variants must pass unchanged `npm test` under Node 22 with 100% coverage, lint, and types. The new mapping callback executes with a prior distinct ID, so it is fully covered even though aliasing of a reused list is untested.

## Twin

Make exactly one change to the reference's snapshot expression: replace `[id, paths.slice()]` with `[id, paths]`. Keep the new Map, null handling, restoration assignment, stack handling, public tests, and documentation identical.

This is a shallow snapshot of mutable map values: new artifact IDs are rolled back correctly, while an appended path under an existing ID remains in both the live and saved list. It is a plausible mistake when treating a copied Map as an isolated snapshot. Use no comment or identifier that suggests a deliberate defect. Both variants change exactly the same three files.
