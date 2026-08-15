export const standardCart = Object.freeze({ towels: 12, soap: 18, water: 6 });

export function refillNeeded(cart) {
  return Object.entries(standardCart).filter(([item, amount]) => cart[item] < amount);
}
