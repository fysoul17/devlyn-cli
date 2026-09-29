#!/bin/sh
# 0226 check (J4, precision guard): for a referenced divisor, the decimal-place
# rejection uses the divisor's precision, so a value with excess decimal
# precision fails with number.multiple even when its rounded scaled remainder
# is zero (90.60000000000001 with divisor 0.3: only the precision guard rejects
# it). Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

const type = (result) => result.error && result.error.details[0].type;
const sibling = Joi.object({ step: Joi.number(), amount: Joi.number().multiple(Joi.ref('step')) });

for (const [step, value] of [[0.3, 90.60000000000001], [0.3, 92.10000000000001], [0.25, 0.251]]) {
    Assert.strictEqual(type(Joi.number().multiple(step).validate(value)), 'number.multiple', `literal ${step} ${value}`);
    Assert.strictEqual(type(Joi.number().multiple(Joi.ref('$step')).validate(value, { context: { step } })), 'number.multiple', `context ${step} ${value}`);
    Assert.strictEqual(type(sibling.validate({ step, amount: value })), 'number.multiple', `sibling ${step} ${value}`);
}
JS
