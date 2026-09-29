#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo 'usage: oracle/run.sh <tree>' >&2
    exit 2
fi

tree_root=$(cd "$1" && pwd -P)

node - "$tree_root" <<'NODE'
'use strict';

const Assert = require('node:assert/strict');
const Path = require('node:path');
const Joi = require(Path.resolve(process.argv[2]));

const truncated = (limit, encoding = 'utf8') => Joi.string().allow('').max(limit, encoding).truncate();

const checks = {
    'J1-1': () => {
        const result = truncated(4).validate('ééx');
        Assert.ifError(result.error);
        Assert.equal(result.value, 'éé');
    },
    'J1-2': () => {
        Assert.equal(truncated(2).validate('漢x').value, '');
        Assert.equal(truncated(0).validate('abc').value, '');
        Assert.equal(truncated(8).validate('abc').value, 'abc');
    },
    'J1-3': () => {
        for (const encoding of ['utf-8', 'UTF8', 'UTF-8']) {
            Assert.equal(truncated(3, encoding).validate('éé').value, 'é');
        }
    },
    'J1-4': () => {
        const schema = Joi.object({
            limit: Joi.number(),
            text: Joi.string().max(Joi.ref('limit'), 'utf8').truncate().trim().replace(/x/g, 'é')
        });
        const result = schema.validate({ limit: '3', text: ' xx ' });
        Assert.ifError(result.error);
        Assert.deepEqual(result.value, { limit: 3, text: 'é' });
        Assert.equal(schema.validate({ text: 'xx' }).error.details[0].type, 'any.ref');
    },
    'J1-5': () => {
        const schema = Joi.string().max(3, 'utf8').truncate();
        const result = schema.validate('éé', { convert: false });
        Assert.equal(result.value, 'éé');
        Assert.equal(result.error.details[0].type, 'string.max');
        Assert.equal(schema.truncate(false).validate('éé').error.details[0].type, 'string.max');
        Assert.equal(Joi.string().max(0, 'utf8').truncate().validate('x').error.details[0].type, 'string.empty');
        Assert.equal(Joi.string().max(2).truncate().validate('abcd').value, 'ab');
        Assert.equal(truncated(2, 'latin1').validate('ééx').value, 'éé');
    },
    'J1-W': () => {
        const result = Joi.string().max(5, 'utf8').truncate().validate('A\u{1F600}B');
        Assert.ifError(result.error);
        Assert.equal(result.value, 'A\u{1F600}');
        Assert.equal(Buffer.byteLength(result.value, 'utf8'), 5);
    }
};

const rows = {};
for (const [id, check] of Object.entries(checks)) {
    try {
        check();
        rows[id] = true;
    }
    catch {
        rows[id] = false;
    }
}

process.stdout.write(JSON.stringify({ rows }) + '\n');
NODE
