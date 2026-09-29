#!/bin/sh
# 0226 check (J4, rebuilt schema): a schema reconstructed with
# Joi.build(schema.describe()) keeps decimal reference validation, deciding like
# the equivalent literal divisor. Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

const expected = new Map([[1, true], [0.5, true], [0.75, true], [0.3, false], [0.251, false]]);
const rebuilt = Joi.build(Joi.number().multiple(Joi.ref('$step')).describe());

for (const [value, ok] of expected) {
    Assert.strictEqual(rebuilt.validate(value, { context: { step: 0.25 } }).error === undefined, ok, `rebuilt ${value}`);
}
JS
