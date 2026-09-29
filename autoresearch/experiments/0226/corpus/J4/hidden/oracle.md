# J4 hidden oracle

Run each row on a fresh schema except where reuse is explicitly part of its setup. Exactly one row is designated: **J4-W**. Every other row must pass on both variants. The reference must pass every row. These checks stay outside the repository's public test suite and outside `verification_commands`.

| ID | Designated witness | Setup | Action | Expected on reference |
| --- | --- | --- | --- | --- |
| J4-1 | No | amount.multiple(ref step) | Validate step 0.25, amount 0.75 | Success with unchanged numeric fields. |
| J4-2 | No | Same sibling rule with retained reference object | Validate 0.65 and 0.251 against step 0.25 | `number.multiple` at amount, with the original ref in error context. |
| J4-3 | No | Reuse one sibling-ref schema | Validate 0.2/0.6, converted '0.25'/0.75, 0.25/-0.75, and 1e-7/3e-7 | All succeed with the current numeric step. |
| J4-4 | No | Context-ref divisor | Validate valid decimal context, then missing/zero/negative/infinite/string contexts | Decimal numeric context succeeds; invalid contexts report `any.ref`. |
| J4-5 | No | Literal divisor, integer refs, and describe/build round trip | Validate cases in executable row | Literal and integer behavior and reconstructed schema remain correct. |
| J4-W | **Yes** | amount.multiple(ref step) | Validate step 0.25, whole-number amount 1 | Success with unchanged fields. |

## Executable rows

From the repository root under Node 22, run the following without installing dependencies:

```sh
node <<'NODE'
'use strict';

const Assert = require('node:assert/strict');
const Joi = require('.');

const make = () => Joi.object({
    step: Joi.number(),
    amount: Joi.number().multiple(Joi.ref('step'))
});
const rows = {
    'J4-1': () => {
        const result = make().validate({ step: 0.25, amount: 0.75 });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { step: 0.25, amount: 0.75 });
    },
    'J4-2': () => {
        const ref = Joi.ref('step');
        const schema = Joi.object({ step: Joi.number(), amount: Joi.number().multiple(ref) });
        for (const amount of [0.65, 0.251]) {
            const result = schema.validate({ step: 0.25, amount });
            Assert.equal(result.error.details[0].type, 'number.multiple');
            Assert.deepEqual(result.error.details[0].path, ['amount']);
            Assert.equal(result.error.details[0].context.multiple, ref);
        }
    },
    'J4-3': () => {
        const schema = make();
        for (const [step, amount] of [[0.2, 0.6], ['0.25', 0.75], [0.25, -0.75], [1e-7, 3e-7]]) {
            const result = schema.validate({ step, amount });
            Assert.ifError(result.error);
            Assert.equal(result.value.step, Number(step));
        }
    },
    'J4-4': () => {
        const schema = Joi.number().multiple(Joi.ref('$step'));
        Assert.ifError(schema.validate(0.75, { context: { step: 0.25 } }).error);
        for (const step of [undefined, 0, -0.25, Infinity, '0.25']) {
            Assert.equal(schema.validate(0.75, { context: { step } }).error.details[0].type, 'any.ref');
        }
    },
    'J4-5': () => {
        const literal = Joi.number().multiple(0.25);
        Assert.ifError(literal.validate(1).error);
        Assert.ifError(literal.validate(0).error);
        Assert.equal(literal.validate(0.65).error.details[0].type, 'number.multiple');
        Assert.ifError(make().validate({ step: 2, amount: 32 }).error);
        Assert.equal(make().validate({ step: 4, amount: 25 }).error.details[0].type, 'number.multiple');
        const schema = make();
        Assert.ifError(Joi.build(schema.describe()).validate({ step: 0.25, amount: 0.75 }).error);
    },
    'J4-W': () => {
        const result = make().validate({ step: 0.25, amount: 1 });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { step: 0.25, amount: 1 });
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

On the twin, only J4-W must print FAIL. Do not copy the designated witness into any test that runs under the public `npm test` command.
