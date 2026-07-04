const assert = require('assert');
const { test } = require('node:test');
const { calculateFinalPrice } = require('./discount');

test('calculateFinalPrice applies a positive discount', () => {
  assert.strictEqual(calculateFinalPrice(100, 10), 90);
});
