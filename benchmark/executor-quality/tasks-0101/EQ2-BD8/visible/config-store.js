export class LimitConfigStore {
  revisions = [];

  write(plan, admission) {
    const revision = Object.freeze({
      revision: this.revisions.length + 1,
      changeId: plan.changeId,
      tier: admission.tier,
      rules: plan.rules,
      approvedBy: Object.freeze([...admission.approvedBy]),
    });
    this.revisions.push(revision);
    return { ok: true, status: "applied", revision: revision.revision };
  }
}
