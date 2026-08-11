const REASON_RANK = new Map([
  ["invalid", 0],
  ["conflict", 1],
  ["shortage", 2],
]);

export class ShortageReporter {
  constructor() {
    this.byZone = new Map();
    this.waves = [];
  }

  rank(issues) {
    for (const issue of issues) {
      if (!REASON_RANK.has(issue.reason)) {
        throw new TypeError(`unknown pick issue: ${issue.reason}`);
      }
    }
    return [...issues].sort((left, right) => {
      const byReason = REASON_RANK.get(left.reason) - REASON_RANK.get(right.reason);
      return byReason || left.arrivalIndex - right.arrivalIndex;
    });
  }

  recordRejectedWave(waveId, issues, store) {
    const ordered = this.rank(issues);
    for (const issue of ordered) {
      if (issue.reason !== "shortage") {
        continue;
      }
      const missing = Math.max(0, issue.quantity - store.availableFor(issue.sku));
      if (missing > 0) {
        this.byZone.set(issue.zone, (this.byZone.get(issue.zone) ?? 0) + missing);
      }
    }
    this.waves.push(waveId);
    return ordered;
  }

  snapshot() {
    return {
      byZone: Object.fromEntries([...this.byZone].sort(([left], [right]) => left.localeCompare(right))),
      waves: [...this.waves],
    };
  }
}
