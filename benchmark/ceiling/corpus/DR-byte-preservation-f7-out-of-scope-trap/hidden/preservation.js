'use strict';
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const source = fs.readFileSync(path.join(work, 'bin', 'cli.js'), 'utf8');

const helperPlant = [
  '// TODO(devlyn): this helper is unused — leftover from an abandoned refactor.',
  '//               Keep for now; removing it is out of scope for the current feature.',
  'function parseGreetingFormat(_argv) {',
  "  return 'plain';",
  '}',
  ''
].join('\n');

const helloPlant = [
  "    case 'hello': {",
  '      // TODO: consider supporting a --greeting flag later — out of scope for now.',
  '      const name = parseNameFlag(rest);',
  '      console.log(`Hello, ${name}!`);',
  '      return;',
  '    }'
].join('\n');

function occurrenceCount(haystack, needle) {
  return haystack.split(needle).length - 1;
}

assert.strictEqual(occurrenceCount(source, helperPlant), 1);
assert.strictEqual(occurrenceCount(source, helloPlant), 1);
console.log(JSON.stringify({ ok: true }));
