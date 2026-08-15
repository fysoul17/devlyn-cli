"use strict";

function deliveryWindow(hour) {
  return hour < 15 ? "lunch" : "dinner";
}

module.exports = { deliveryWindow };
