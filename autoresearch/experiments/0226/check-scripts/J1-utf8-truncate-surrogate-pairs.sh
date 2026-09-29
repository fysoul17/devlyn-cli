#!/bin/sh
# 0226 check (J1): UTF-8 max().truncate() keeps complete surrogate pairs and the
# original code units of each kept code point. Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

const cases = [
    [4, '😀a', '😀'],
    [4, '😀', '😀'],
    [4, '😀😀', '😀'],
    [5, 'A😀B', 'A😀'],
    [6, '😀ab', '😀ab']
];

for (const [limit, input, expected] of cases) {
    const result = Joi.string().max(limit, 'utf8').truncate().validate(input);
    Assert.strictEqual(result.error, undefined, `${limit} ${JSON.stringify(input)}: ${result.error}`);
    Assert.strictEqual(result.value, expected, `${limit} ${JSON.stringify(input)}`);
}
JS
