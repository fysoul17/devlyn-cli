const assert = require('assert');
const { test } = require('node:test');
const { estimateShipping } = require('./shipping-estimate');

// Pre-existing, already RED before this task starts — free-shipping
// threshold is a separate tracked backlog item, not implemented yet.
test('estimateShipping applies free-shipping threshold above 20kg', () => {
  assert.strictEqual(estimateShipping(25), 0);
});
