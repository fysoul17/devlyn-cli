# J1 hidden oracle

Run each row on a fresh schema except where reuse is explicitly part of its setup. Exactly one row is designated: **J1-W**. Every other row must pass on both variants. The reference must pass every row. These checks stay outside the repository's public test suite and outside `verification_commands`.

| ID | Designated witness | Setup | Action | Expected on reference |
| --- | --- | --- | --- | --- |
| J1-1 | No | UTF-8 max 4 with truncate | Validate `ééx` | Success, `éé`; the exact byte boundary is retained. |
| J1-2 | No | UTF-8 budgets 2, 0, and 8; allow empty | Validate `漢x`, `abc`, and `abc` respectively | Empty, empty, and unchanged `abc`. |
| J1-3 | No | Each accepted UTF-8 spelling with max 3 | Validate `éé` | Success, one `é`. |
| J1-4 | No | Sibling-ref budget plus trim and replacement | Validate converted budget 3 and ` xx `; then omit budget | First returns budget 3 and text `é`; second reports `any.ref`. |
| J1-5 | No | Disabled conversion/truncation, disallowed empty, no encoding, latin1 | Validate the cases in the executable row | Existing max/empty errors and existing non-UTF-8 truncation are preserved. |
| J1-W | **Yes** | UTF-8 max 5 with truncate | Validate `A😀B` | Success, exactly `A😀`, whose UTF-8 length is 5. |

## Executable rows

From the repository root under Node 22, run the following without installing dependencies:

```sh
node <<'NODE'
'use strict';

const Assert = require('node:assert/strict');
const Joi = require('.');

const truncated = (limit, encoding = 'utf8') => Joi.string().allow('').max(limit, encoding).truncate();
const rows = {
    'J1-1': () => {
        const result = truncated(4).validate('ééx');
        Assert.ifError(result.error);
        Assert.equal(result.value, 'éé');
    },
    'J1-2': () => {
        Assert.equal(truncated(2).validate('漢x').value, '');
        Assert.equal(truncated(0).validate('abc').value, '');
        Assert.equal(truncated(8).validate('abc').value, 'abc');
    },
    'J1-3': () => {
        for (const encoding of ['utf-8', 'UTF8', 'UTF-8']) {
            Assert.equal(truncated(3, encoding).validate('éé').value, 'é');
        }
    },
    'J1-4': () => {
        const schema = Joi.object({
            limit: Joi.number(),
            text: Joi.string().max(Joi.ref('limit'), 'utf8').truncate().trim().replace(/x/g, 'é')
        });
        const result = schema.validate({ limit: '3', text: ' xx ' });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { limit: 3, text: 'é' });
        Assert.equal(schema.validate({ text: 'xx' }).error.details[0].type, 'any.ref');
    },
    'J1-5': () => {
        const schema = Joi.string().max(3, 'utf8').truncate();
        const result = schema.validate('éé', { convert: false });
        Assert.equal(result.value, 'éé');
        Assert.equal(result.error.details[0].type, 'string.max');
        Assert.equal(schema.truncate(false).validate('éé').error.details[0].type, 'string.max');
        Assert.equal(Joi.string().max(0, 'utf8').truncate().validate('x').error.details[0].type, 'string.empty');
        Assert.equal(Joi.string().max(2).truncate().validate('abcd').value, 'ab');
        Assert.equal(truncated(2, 'latin1').validate('ééx').value, 'éé');
    },
    'J1-W': () => {
        const result = Joi.string().max(5, 'utf8').truncate().validate('A\u{1F600}B');
        Assert.ifError(result.error);
        Assert.equal(result.value, 'A\u{1F600}');
        Assert.equal(Buffer.byteLength(result.value, 'utf8'), 5);
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

On the twin, only J1-W must print FAIL. Do not copy the designated witness into any test that runs under the public `npm test` command.
