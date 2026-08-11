import { selectLimitIssue } from "./limit-rules.js";

const DENIED = Object.freeze({ ok: false, error: "admin_denied" });

function rejection(entry) {
  return {
    ok: false,
    error: "limit_rejected",
    reason: entry.reason,
    field: entry.field,
    ruleIndex: entry.ruleIndex,
  };
}

export class LimitValidationJournal {
  entries = [];

  append(entry) {
    const stored = Object.freeze({ sequence: this.entries.length + 1, ...entry });
    this.entries.push(stored);
    return stored;
  }
}

export class LimitWriter {
  constructor(store, validations) {
    this.store = store;
    this.validations = validations;
  }

  prepare(change) {
    const issue = selectLimitIssue(change);
    if (issue !== null) {
      const stored = this.validations.append({ changeId: change.id, ...issue });
      return rejection(stored);
    }
    return {
      ok: true,
      plan: Object.freeze({
        changeId: change.id,
        rules: Object.freeze(change.rules.map((rule) => Object.freeze({ ...rule }))),
      }),
    };
  }

  apply(change, admission) {
    const prepared = this.prepare(change);
    if (!admission.ok) {
      return DENIED;
    }
    if (!prepared.ok) {
      return prepared;
    }
    return this.store.write(prepared.plan, admission);
  }
}
