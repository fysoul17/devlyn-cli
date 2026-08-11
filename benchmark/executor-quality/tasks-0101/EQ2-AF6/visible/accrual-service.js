export function postAccrual(store, tokenRegistry, request, token) {
  const accrued = store.aggregate(request);
  const decision = tokenRegistry.authorize({
    value: token,
    memberId: request.memberId,
    cycleId: request.cycleId,
  });
  if (!decision.authorized) {
    return { status: "denied", reason: decision.reason };
  }
  return accrued;
}
