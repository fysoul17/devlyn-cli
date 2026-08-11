export class UnknownMemberError extends Error {
  constructor(memberId) {
    super(`Unknown loyalty member ${memberId}`);
    this.name = "UnknownMemberError";
    this.memberId = memberId;
  }
}

export class CycleMismatchError extends Error {
  constructor(eventId, cycleId) {
    super(`Event ${eventId} does not belong to cycle ${cycleId}`);
    this.name = "CycleMismatchError";
    this.eventId = eventId;
    this.cycleId = cycleId;
  }
}
