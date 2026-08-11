import { collectLimitIssues, rankLimitIssues } from "./limit-rules.js";

export class LimitRejectionLog {
  entries = [];

  append(entry) {
    const stored = Object.freeze({ ...entry });
    this.entries.push(stored);
    return stored;
  }
}

export class LimitWriter {
  constructor(store, rejections) {
    this.store = store;
    this.rejections = rejections;
  }

  inspect(change) {
    const issue = rankLimitIssues(collectLimitIssues(change))[0] ?? null;
    if (issue !== null) {
      const stored = this.rejections.append({ changeId: change.id, ...issue });
      return {
        ok: false,
        error: "limit_rejected",
        reason: stored.reason,
        field: stored.field,
        ruleIndex: stored.ruleIndex,
      };
    }
    const plan = Object.freeze({
      changeId: change.id,
      tier: change.tier,
      rules: Object.freeze(change.rules.map((rule) => Object.freeze({ ...rule }))),
    });
    return { ok: true, plan };
  }

  commit(plan, approvedBy) {
    return this.store.write(plan, approvedBy);
  }
}
