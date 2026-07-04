function calculateTotal(subtotal, taxRate) {
  const tax = subtotal * taxRate;
  return Math.floor((subtotal + tax) * 100) / 100;
}

module.exports = { calculateTotal };
