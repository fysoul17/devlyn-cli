export class AdminDecisionLedger {
  entries = [];

  append(entry) {
    const stored = Object.freeze({ sequence: this.entries.length + 1, ...entry });
    this.entries.push(stored);
    return stored;
  }
}
