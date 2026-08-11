export class LimitConfigStore {
  revisions = [];

  write(plan, approvedBy) {
    const revision = Object.freeze({
      revision: this.revisions.length + 1,
      changeId: plan.changeId,
      tier: plan.tier,
      rules: plan.rules,
      approvedBy: Object.freeze([...approvedBy]),
    });
    this.revisions.push(revision);
    return { ok: true, status: "applied", revision };
  }
}
