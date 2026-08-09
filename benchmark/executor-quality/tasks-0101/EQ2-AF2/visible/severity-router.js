"use strict";

class SeverityRouter {
  place(tickets, limit = tickets.length) {
    return tickets.slice(0, limit).map((ticket, index) => ({
      ...ticket,
      slot: index + 1,
    }));
  }
}

module.exports = { SeverityRouter };
