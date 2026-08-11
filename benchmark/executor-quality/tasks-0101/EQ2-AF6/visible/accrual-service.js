export function postAccrual(store, tokenRegistry, request, token) {
  const member = tokenRegistry.authenticateMember({
    value: token,
    memberId: request.memberId,
  });
  if (!member.authorized) {
    return { status: "denied", reason: member.reason };
  }

  const posted = store.appendToStatement(request);
  const scope = tokenRegistry.authorizeAccrual(member.claims, request.cycleId);
  if (!scope.authorized) {
    return { status: "denied", reason: scope.reason };
  }
  return posted;
}
