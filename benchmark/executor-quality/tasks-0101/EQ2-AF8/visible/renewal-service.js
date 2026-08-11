export function renewCertificate(state, request) {
  const authorization = state.authority.authorize(
    request.certificateId,
    request.accountId,
    request.requestDay,
  );
  const assessment = state.csrReviewer.review(
    request.csr,
    state.authority.subjectFor(request.certificateId),
  );
  return state.issuanceGate.continue(
    authorization,
    assessment,
    () => state.issuer.issue(authorization, request.csr, request.requestDay),
  );
}
