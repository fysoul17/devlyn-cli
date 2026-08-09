"use strict";

const { OnCallAcl } = require("./oncall-acl");
const { SeverityRouter } = require("./severity-router");

function routeEscalations(requests, assignments, slotLimit = requests.length) {
  const tickets = requests.map((ticket, arrival) => ({
    id: String(ticket.id),
    requester: String(ticket.requester),
    service: String(ticket.service),
    severity: String(ticket.severity),
    arrival,
  }));
  const acl = new OnCallAcl(assignments);
  const router = new SeverityRouter();

  return router
    .place(tickets, slotLimit)
    .filter((ticket) => acl.allows(ticket))
    .map(({ id, severity, slot }) => ({ id, severity, slot }));
}

module.exports = { routeEscalations };
