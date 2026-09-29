#!/bin/sh
# 0226 check (J3, nested attempts): when an inner attempt appends a path under an
# artifact id that the enclosing attempt's snapshot already holds, restoring the
# enclosing attempt brings back the paths it started with. Exit 0 = clause holds.
set -eu
cd "$1"
exec node - <<'JS'
const Assert = require('assert');
const Joi = require(process.cwd() + '/lib');

// Inner attempt discarded, then the enclosing attempt discarded.
const innerDiscarded = Joi.alternatives().try(Joi.object({ x: Joi.any().artifact('same'), y: Joi.any().required() }), Joi.any());
// Inner attempt committed, then the enclosing attempt discarded.
const innerCommitted = Joi.alternatives().try(Joi.object({ x: Joi.any().artifact('same') }));

for (const inner of [innerDiscarded, innerCommitted]) {
    const schema = Joi.object({
        a: Joi.any().artifact('same'),
        b: Joi.alternatives().try(Joi.object({ c: inner, z: Joi.any().required() }), Joi.any())
    });
    const result = schema.validate({ a: 1, b: { c: { x: 2 } } });
    Assert.strictEqual(result.error, undefined);
    Assert.deepStrictEqual([...result.artifacts], [['same', [['a']]]]);
}
JS
