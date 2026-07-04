const { recordUsage } = require('../lib/telemetry');

function calculateFinalPrice(price, discountPercent) {
  recordUsage('calculateFinalPrice');
  const discount = price * discountPercent / 100;
  return price - discount;
}

module.exports = { calculateFinalPrice };
