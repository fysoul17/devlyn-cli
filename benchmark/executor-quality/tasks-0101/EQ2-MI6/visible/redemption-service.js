export function redeemCoupon(store, sessionAuth, request, sessionId) {
  const replayed = store.replay(request.idempotencyKey);
  if (replayed) {
    return replayed;
  }

  const decision = sessionAuth.authorize({ sessionId, accountId: request.accountId });
  if (!decision.authorized) {
    const denied = { status: "denied", reason: decision.reason };
    store.remember(request.idempotencyKey, denied);
    return denied;
  }

  const redeemed = store.redeem(request);
  store.remember(request.idempotencyKey, redeemed);
  return redeemed;
}
