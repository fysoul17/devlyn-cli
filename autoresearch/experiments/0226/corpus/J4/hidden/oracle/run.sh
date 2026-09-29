#!/bin/sh

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
    printf 'usage: %s <tree>\n' "$0" >&2
    exit 1
fi

ORACLE_TREE=$(cd "$1" && pwd -P) || exit 1
export ORACLE_TREE

node <<'NODE'
'use strict';

const Assert = require('node:assert/strict');
const Joi = require(process.env.ORACLE_TREE);

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

const results = {};
for (const [id, run] of Object.entries(rows)) {
    try {
        run();
        results[id] = true;
    }
    catch (error) {
        results[id] = false;
    }
}

process.stdout.write(JSON.stringify({ rows: results }) + '\n');
NODE
