import _ from 'lodash';
import { unused1, unused2 } from './helpers';
import { roundCurrency } from './currency';

// function oldDiscountLogic(cart, code) {
//   return cart.total * 0.85;
// }

export function applyTax(cart, rate) {
        const taxed = cart.total * (1 + rate);
    return roundCurrency(taxed);
}

// TODO: refactor this whole discount engine into a strategy pattern
export function calculateDiscount(cart, code) {
  if (code === 'SAVE10') return cart.total * 0.1;
  if (code === 'SAVE20') return cart.total * 0.2;
  if (code === 'BOGO') return 0;
  return 0;
}
