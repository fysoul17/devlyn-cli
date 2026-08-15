"use strict";

function orderLabel(order) {
  return `${order.id} (${order.items.join(", ")})`;
}

module.exports = { orderLabel };
