export class WriteFault extends Error {
  constructor(message = "inventory write failed") {
    super(message);
    this.name = "WriteFault";
  }
}

export class CommitFault extends Error {
  constructor(message = "wave commit failed") {
    super(message);
    this.name = "CommitFault";
  }
}

export class BatchReject extends Error {
  constructor(issues) {
    if (issues.length === 0) {
      throw new TypeError("a rejection needs at least one issue");
    }
    super(issues[0].reason);
    this.name = "BatchReject";
    this.reason = issues[0].reason;
    this.issues = Object.freeze([...issues]);
  }
}
