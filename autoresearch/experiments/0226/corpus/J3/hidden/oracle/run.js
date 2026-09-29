'use strict';

const Assert = require('node:assert/strict');
const Path = require('node:path');
const Joi = require(Path.resolve(process.argv[2]));

const losing = (id) => Joi.object({ x: Joi.any().artifact(id), y: Joi.any().required() });
const fallback = (id) => Joi.alternatives().try(losing(id), Joi.object({ x: Joi.any() }));

const checks = {
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
    const rows = {};
    for (const [id, run] of Object.entries(checks)) {
        try {
            await run();
            rows[id] = true;
        }
        catch {
            rows[id] = false;
        }
    }

    process.stdout.write(JSON.stringify({ rows }) + '\n');
})().catch((error) => {
    process.stderr.write(error.stack + '\n');
    process.exitCode = 1;
});
