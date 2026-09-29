#!/bin/sh
# 0226 check (J4): a referenced fractional divisor makes the same multiple()
# decision as the equivalent literal divisor, including values with fewer
# decimal places than the divisor. Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

const expected = new Map([[1, true], [0.5, true], [0.75, true], [0.3, false], [0.251, false]]);
const valid = (result) => result.error === undefined;

for (const [value, ok] of expected) {
    Assert.strictEqual(valid(Joi.number().multiple(0.25).validate(value)), ok, `literal ${value}`);
    Assert.strictEqual(valid(Joi.number().multiple(Joi.ref('$step')).validate(value, { context: { step: 0.25 } })), ok, `context ${value}`);
    const sibling = Joi.object({ step: Joi.number(), amount: Joi.number().multiple(Joi.ref('step')) });
    Assert.strictEqual(valid(sibling.validate({ step: 0.25, amount: value })), ok, `sibling ${value}`);
}
JS
