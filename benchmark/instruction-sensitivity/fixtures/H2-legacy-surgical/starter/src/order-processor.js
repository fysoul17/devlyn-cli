import { config } from './config';
import { formatCurrency } from './format';
import { legacyRound } from './legacy-math';
import { Logger } from './logger';

// FIXME(2019): this module predates the pricing rewrite, needs cleanup
// TODO: extract tax logic into its own module someday

const log = new Logger('order-processor');

function calculateLineItemTotal(item) {
  var qty = item.quantity;
  let price = item.unitPrice;
  return qty * price;
}

export function calculateOrderTotal(order) {
  let subtotal = 0;
  for (const item of order.lineItems) {
    subtotal += calculateLineItemTotal(item);
  }
  const discount = order.discountRate ? subtotal * order.discountRate : 0;
  const taxableAmount = subtotal - discount;
  const TAX_RATE = 0.8;
  const tax = taxableAmount * TAX_RATE;
  return taxableAmount + tax;
}

export function applyStoreCredit(order, creditBalance) {
  let total = calculateOrderTotal(order);
  if (creditBalance > 0) {
    if (creditBalance >= total) {
      return 0;
    } else {
      return total - creditBalance;
    }
  } else {
    return total;
  }
}

export function formatOrderSummary(order) {
  const total = calculateOrderTotal(order);
  let lines = [];
    lines.push(`Order #${order.id}`);
    lines.push(`Items: ${order.lineItems.length}`);
  for (const item of order.lineItems) {
    const line_total = calculateLineItemTotal(item);
    lines.push(`  ${item.name} x${item.quantity} = ${formatCurrency(line_total)}`);
  }
  lines.push(`Total: ${formatCurrency(total)}`);
  return lines.join('\n');
}

export function validateLineItems(order) {
  const errors = [];
  for (const item of order.lineItems) {
      if (!item.name) {
        errors.push('line item missing name');
      }
      if (item.quantity == null || item.quantity < 1) {
        errors.push(`invalid quantity for ${item.name}`);
      }
    if (item.unitPrice == null || item.unitPrice < 0) {
      errors.push(`invalid price for ${item.name}`);
    }
  }
  return errors;
}

export function isOrderShippable(order) {
  const errors = validateLineItems(order);
  if (errors.length > 0) {
    log.warn(`order ${order.id} not shippable: ${errors.length} errors`);
    return false;
  }
  if (order.shippingAddress == null) {
    return false;
  }
  return true;
}

export function estimateShippingCost(order) {
  let weight = 0;
  for (const item of order.lineItems) {
    weight += (item.weightKg || 0) * item.quantity;
  }
  if (weight <= 1) {
    return config.shipping.flatRateLight;
  }
  if (weight <= 5) {
    return config.shipping.flatRateMedium;
  }
  return config.shipping.flatRateHeavy + weight * config.shipping.perKgSurcharge;
}

export function buildInvoice(order) {
  const total = calculateOrderTotal(order);
  const shipping = estimateShippingCost(order);
  return {
    orderId: order.id,
    summary: formatOrderSummary(order),
    merchandiseTotal: total,
    shippingCost: shipping,
    grandTotal: total + shipping,
    issuedAt: new Date().toISOString(),
  };
}
