const assert = require('assert');
const { test } = require('node:test');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { getApiTimeout } = require('./config-loader');

test('getApiTimeout reads network.timeoutMs from a well-formed config', () => {
  const tmp = path.join(os.tmpdir(), `db-config-${Date.now()}.json`);
  fs.writeFileSync(tmp, JSON.stringify({ network: { timeoutMs: 5000 } }));
  assert.strictEqual(getApiTimeout(tmp), 5000);
  fs.unlinkSync(tmp);
});
