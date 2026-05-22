export function logCheckoutEvent(orderId, amount) {
  console.log(`[checkout] order=${orderId} amount=${amount}`);
}

export function logPageView(path) {
  console.log(`[pageview] ${path}`);
}
