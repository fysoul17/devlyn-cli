const assert = require('assert');
const { test } = require('node:test');
const { calculateTotal } = require('./order-total');

test('calculateTotal applies tax with no rounding needed', () => {
  assert.strictEqual(calculateTotal(100, 0.1), 110);
});
