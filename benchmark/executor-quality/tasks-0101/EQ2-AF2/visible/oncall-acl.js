"use strict";

class OnCallAcl {
  constructor(assignments) {
    this.assignments = new Map(
      Object.entries(assignments).map(([service, requesters]) => [
        service,
        new Set(requesters.map(String)),
      ]),
    );
  }

  allows(ticket) {
    return this.assignments.get(ticket.service)?.has(ticket.requester) ?? false;
  }
}

module.exports = { OnCallAcl };
