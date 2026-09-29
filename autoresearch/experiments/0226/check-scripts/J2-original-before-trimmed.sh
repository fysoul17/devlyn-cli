#!/bin/sh
# 0226 check (J2): a custom truthy/falsy match on the original input takes
# precedence over a match found only after trimming. Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

let result = Joi.boolean().truthy(' yes ').falsy('yes').validate(' yes ');
Assert.strictEqual(result.error, undefined);
Assert.strictEqual(result.value, true);

result = Joi.boolean().truthy('yes').falsy(' yes ').validate(' yes ');
Assert.strictEqual(result.error, undefined);
Assert.strictEqual(result.value, false);
JS
