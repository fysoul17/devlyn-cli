import { flags } from './feature-flags';
import { formatReceipt } from './receipt';
import { formatLegacyReceipt } from './legacy-receipt';
import { calculateTax } from './tax';
import { logCheckoutEvent } from './analytics';

function legacyCheckoutPath(cart) {
  const total = cart.items.reduce((sum, item) => sum + item.price, 0);
  return formatLegacyReceipt(total);
}

function modernCheckoutPath(cart) {
  const subtotal = cart.items.reduce((sum, item) => sum + item.price, 0);
  const tax = calculateTax(subtotal);
  return formatReceipt(subtotal + tax);
}

function computeLoyaltyPoints(total) {
  return Math.floor(total / 10);
}

export function checkout(cart) {
  if (flags.ENABLE_LEGACY_CHECKOUT) {
    return legacyCheckoutPath(cart);
  }
  return modernCheckoutPath(cart);
}
