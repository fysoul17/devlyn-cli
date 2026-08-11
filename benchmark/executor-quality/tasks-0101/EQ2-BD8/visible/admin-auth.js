const DENIED = Object.freeze({ ok: false, error: "admin_denied" });
const REQUIRED_ROLES = new Set(["operator", "security"]);

export class ApprovalDirectory {
  #approvals;

  constructor(approvals = []) {
    this.#approvals = new Map(approvals.map((approval) => [approval.id, { ...approval }]));
  }

  authorize(approvalIds, tier) {
    const uniqueIds = [...new Set(Array.isArray(approvalIds) ? approvalIds : [])];
    const grants = uniqueIds.map((id) => this.#approvals.get(id));
    const roles = new Set(grants.map((grant) => grant?.role));
    const admitted = uniqueIds.length === 2
      && grants.every((grant) => grant?.active === true && grant.tiers.includes(tier))
      && roles.size === REQUIRED_ROLES.size
      && [...REQUIRED_ROLES].every((role) => roles.has(role));
    if (!admitted) {
      return DENIED;
    }
    return { ok: true, tier, approvedBy: uniqueIds };
  }
}
