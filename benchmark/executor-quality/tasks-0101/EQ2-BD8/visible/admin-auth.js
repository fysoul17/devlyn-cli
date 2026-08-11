const DENIED = Object.freeze({ ok: false, error: "admin_denied" });

export class ApprovalDirectory {
  #approvals;

  constructor(approvals = []) {
    this.#approvals = new Map(approvals.map((approval) => [approval.id, { ...approval }]));
  }

  authorize(approvalIds, tier) {
    const uniqueIds = [...new Set(Array.isArray(approvalIds) ? approvalIds : [])];
    if (uniqueIds.length !== 2) {
      return DENIED;
    }
    const quorum = uniqueIds.map((id) => this.#approvals.get(id));
    const admitted = quorum.every(
      (approval) => approval?.active === true && approval.tiers.includes(tier),
    );
    if (!admitted) {
      return DENIED;
    }
    return { ok: true, approvedBy: uniqueIds };
  }
}
