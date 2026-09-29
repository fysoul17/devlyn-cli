#!/bin/sh
# 0226 check (J3): rolling back a discarded alternative removes the artifact path
# it appended under an artifact id that already had paths. Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

const discarded = Joi.object({ x: Joi.any().artifact('same'), y: Joi.any().required() });

let result = Joi.object({
    a: Joi.any().artifact('same'),
    b: Joi.alternatives().try(discarded, Joi.any())
}).validate({ a: 1, b: { x: 2 } });
Assert.strictEqual(result.error, undefined);
Assert.deepStrictEqual([...result.artifacts], [['same', [['a']]]]);

result = Joi.object({
    a: Joi.any().artifact('same'),
    b: Joi.alternatives().try(discarded, Joi.object({ x: Joi.any().artifact('same') }))
}).validate({ a: 1, b: { x: 2 } });
Assert.strictEqual(result.error, undefined);
Assert.deepStrictEqual([...result.artifacts], [['same', [['a'], ['b', 'x']]]]);
JS
