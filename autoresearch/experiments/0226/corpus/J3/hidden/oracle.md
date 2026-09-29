# J3 hidden oracle

Run each row on a fresh schema except where reuse is explicitly part of its setup. Exactly one row is designated: **J3-W**. Every other row must pass on both variants. The reference must pass every row. These checks stay outside the repository's public test suite and outside `verification_commands`.

| ID | Designated witness | Setup | Action | Expected on reference |
| --- | --- | --- | --- | --- |
| J3-1 | No | A losing object branch records a new ID, then a clean fallback accepts | Validate an object missing the losing branch's required y | Success; no artifacts field. |
| J3-2 | No | Prior object-valued ID, losing distinct ID, winning distinct ID | Validate synchronously and asynchronously with artifacts enabled | Prior/winning paths only, in insertion order, with original ID identity. |
| J3-3 | No | Prior distinct ID and a failing child object with failover null | Validate child missing y | Child becomes null; only prior artifact remains. |
| J3-4 | No | Prior ID reused by a successful alternative | Validate both siblings | Both committed paths remain under the shared ID. |
| J3-5 | No | Array item has a losing candidate and winning candidate using distinct IDs | Validate one object item missing y | Only winning path `[0, 'x']` remains. |
| J3-6 | No | Successful when-condition probe has an artifact; selected branch has another | Validate 1 | Only selected branch artifact at root remains. |
| J3-W | **Yes** | Prior sibling records same ID as descendant of a losing alternative | Validate `{ a: 1, b: { x: 2 } }` | Success; shared ID has only path `['a']`, with no discarded `['b', 'x']`. |

## Executable rows

From the repository root under Node 22, run the following without installing dependencies:

```sh
node <<'NODE'
'use strict';

const Assert = require('node:assert/strict');
const Joi = require('.');

const losing = (id) => Joi.object({ x: Joi.any().artifact(id), y: Joi.any().required() });
const fallback = (id) => Joi.alternatives().try(losing(id), Joi.object({ x: Joi.any() }));
const rows = {
    'J3-1': () => {
        const result = fallback('lost').validate({ x: 1 });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { x: 1 });
        Assert.equal(result.artifacts, undefined);
    },
    'J3-2': async () => {
        const id = {};
        const schema = Joi.object({
            a: Joi.any().artifact(id),
            b: Joi.alternatives().try(losing('lost'), Joi.object({ x: Joi.any().artifact('winner') }))
        });
        const input = { a: 1, b: { x: 2 } };
        const result = schema.validate(input);
        Assert.ifError(result.error);
        Assert.deepEqual(result.artifacts, new Map([[id, [['a']]], ['winner', [['b', 'x']]]]));
        Assert.equal([...result.artifacts.keys()][0], id);
        const asyncResult = await schema.validateAsync(input, { artifacts: true });
        Assert.deepEqual(asyncResult.artifacts, result.artifacts);
    },
    'J3-3': () => {
        const schema = Joi.object({
            a: Joi.any().artifact('keep'),
            b: losing('lost').failover(null)
        });
        const result = schema.validate({ a: 1, b: { x: 2 } });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { a: 1, b: null });
        Assert.deepEqual(result.artifacts, new Map([['keep', [['a']]]]));
    },
    'J3-4': () => {
        const schema = Joi.object({
            a: Joi.any().artifact('same'),
            b: Joi.alternatives().try(Joi.any().artifact('same'))
        });
        const result = schema.validate({ a: 1, b: 2 });
        Assert.ifError(result.error);
        Assert.deepEqual(result.artifacts, new Map([['same', [['a'], ['b']]]]));
    },
    'J3-5': () => {
        const schema = Joi.array().items(
            losing('lost'),
            Joi.object({ x: Joi.any().artifact('winner') })
        );
        const result = schema.validate([{ x: 1 }]);
        Assert.ifError(result.error);
        Assert.deepEqual(result.artifacts, new Map([['winner', [[0, 'x']]]]));
    },
    'J3-6': () => {
        const schema = Joi.any().when(Joi.any().artifact('probe'), {
            then: Joi.any().artifact('selected')
        });
        const result = schema.validate(1);
        Assert.ifError(result.error);
        Assert.deepEqual(result.artifacts, new Map([['selected', [[]]]]));
    },
    'J3-W': () => {
        const schema = Joi.object({
            a: Joi.any().artifact('same'),
            b: fallback('same')
        });
        const result = schema.validate({ a: 1, b: { x: 2 } });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { a: 1, b: { x: 2 } });
        Assert.deepEqual(result.artifacts, new Map([['same', [['a']]]]));
    }
};


(async () => {
    for (const [id, run] of Object.entries(rows)) {
        try {
            await run();
            console.log(id + ': PASS');
        }
        catch (error) {
            console.error(id + ': FAIL', error.message);
            process.exitCode = 1;
        }
    }
})();

NODE
```

On the twin, only J3-W must print FAIL. Do not copy the designated witness into any test that runs under the public `npm test` command.
