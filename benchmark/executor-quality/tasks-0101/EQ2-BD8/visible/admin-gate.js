export class AdminGate {
  constructor(approvals, writer, decisions) {
    this.approvals = approvals;
    this.writer = writer;
    this.decisions = decisions;
  }

  submit(request) {
    const evaluation = this.writer.inspect(request.change);
    const authorization = this.approvals.authorize(request.approvalIds, request.change.tier);
    if (!authorization.ok) {
      this.decisions.append({
        requestId: request.id,
        outcome: "denied",
        error: authorization.error,
      });
      return authorization;
    }
    if (!evaluation.ok) {
      this.decisions.append({
        requestId: request.id,
        outcome: "rejected",
        error: evaluation.error,
        reason: evaluation.reason,
      });
      return evaluation;
    }
    const result = this.writer.commit(evaluation.plan, authorization.approvedBy);
    this.decisions.append({
      requestId: request.id,
      outcome: "applied",
      revision: result.revision.revision,
    });
    return result;
  }
}
