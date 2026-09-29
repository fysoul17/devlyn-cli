'use strict';

const Assert = require('node:assert/strict');
const Path = require('node:path');

const Joi = require(Path.join(process.argv[2], 'lib', 'index.js'));

const rows = {
    'J2-1': () => {
        const schema = Joi.boolean().truthy('yes').falsy('no');
        for (const [input, output] of [[' yes ', true], [' NO ', false], ['yes', true], ['no', false]]) {
            const result = schema.validate(input);
            Assert.ifError(result.error);
            Assert.equal(result.value, output);
        }
    },

    'J2-2': () => {
        const schema = Joi.boolean().truthy('false').falsy('true');
        Assert.equal(schema.validate(' false ').value, false);
        Assert.equal(schema.validate(' true ').value, true);
        Assert.equal(schema.validate(true).value, true);
        Assert.equal(schema.validate(false).value, false);
    },

    'J2-3': () => {
        const schema = Joi.boolean().truthy('YES').falsy('NO').sensitive();
        Assert.equal(schema.validate(' YES ').value, true);
        Assert.equal(schema.validate(' NO ').value, false);
        Assert.equal(schema.validate(' yes ').error.details[0].type, 'boolean.base');
        const result = schema.validate(' YES ', { convert: false });
        Assert.equal(result.value, ' YES ');
        Assert.equal(result.error.details[0].type, 'boolean.base');
    },

    'J2-4': () => {
        Assert.equal(Joi.boolean().truthy('x').falsy('x').validate(' x ').value, true);
        Assert.equal(Joi.boolean().truthy(1).falsy(0).validate(1).value, true);
        Assert.equal(Joi.boolean().truthy(1).falsy(0).validate(0).value, false);
    },

    'J2-5': () => {
        const schema = Joi.boolean().truthy(' yes ');
        Assert.equal(schema.validate(' yes ').value, true);
        Assert.equal(schema.validate('yes').error.details[0].type, 'boolean.base');
        const result = schema.validate(' unknown ');
        Assert.equal(result.value, ' unknown ');
        Assert.equal(result.error.details[0].context.value, ' unknown ');
    },

    'J2-W': () => {
        const result = Joi.boolean().truthy(' yes ').falsy('yes').validate(' yes ');
        Assert.ifError(result.error);
        Assert.equal(result.value, true);
    }
};

const results = {};
for (const [id, run] of Object.entries(rows)) {
    try {
        run();
        results[id] = true;
    }
    catch {
        results[id] = false;
    }
}

process.stdout.write(`${JSON.stringify({ rows: results })}\n`);
