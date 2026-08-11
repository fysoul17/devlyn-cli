import { BatchReject } from "./errors.js";

const REASON_RANK = new Map([
  ["invalid", 0],
  ["conflict", 1],
  ["shortage", 2],
]);

export class ShortageReporter {
  constructor() {
    this.issues = [];
  }

  record(issue) {
    if (!REASON_RANK.has(issue.reason)) {
      throw new TypeError(`unknown pick issue: ${issue.reason}`);
    }
    this.issues.push(issue);
  }

  conclude() {
    if (this.issues.length === 0) {
      return;
    }
    const ordered = [...this.issues].sort((left, right) => {
      const byReason = REASON_RANK.get(left.reason) - REASON_RANK.get(right.reason);
      return byReason || left.arrivalIndex - right.arrivalIndex;
    });
    throw new BatchReject(ordered);
  }
}
