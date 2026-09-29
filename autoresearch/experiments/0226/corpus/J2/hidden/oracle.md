# J2 hidden oracle

Run each row on a fresh schema except where reuse is explicitly part of its setup. Exactly one row is designated: **J2-W**. Every other row must pass on both variants. The reference must pass every row. These checks stay outside the repository's public test suite and outside `verification_commands`.

| ID | Designated witness | Setup | Action | Expected on reference |
| --- | --- | --- | --- | --- |
| J2-1 | No | truthy yes, falsy no | Validate padded/case-varied and unpadded spellings | Correct true/false values. |
| J2-2 | No | Custom registrations conflict with canonical boolean strings | Validate canonical strings and actual booleans | Canonical meanings and actual booleans win. |
| J2-3 | No | Sensitive custom uppercase strings | Validate matching/mismatched case and disable conversion | Matching padded strings convert; lowercase and strict inputs report `boolean.base`. |
| J2-4 | No | Same candidate in both sets; numeric custom values | Validate padded x, 1, and 0 | true, true, and false. |
| J2-5 | No | Only padded truthy registration | Validate exact registration, its unpadded spelling, and an unknown padded input | Exact match succeeds; registration is not trimmed; failed input/context retain whitespace. |
| J2-W | **Yes** | truthy `' yes '`, falsy `'yes'` | Validate `' yes '` | Success, true from the original-input match. |

## Executable rows

From the repository root under Node 22, run the following without installing dependencies:

```sh
node <<'NODE'
'use strict';

const Assert = require('node:assert/strict');
const Joi = require('.');

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


(async () => {
    for (const [id, run] of Object.entries(rows)) {
        try {
            await run();
            console.log(id + ': PASS');
        }
        catch (error) {
            console.error(id + ': FAIL', error.message);
            process.exitCode = 1;
        }
    }
})();

NODE
```

On the twin, only J2-W must print FAIL. Do not copy the designated witness into any test that runs under the public `npm test` command.
