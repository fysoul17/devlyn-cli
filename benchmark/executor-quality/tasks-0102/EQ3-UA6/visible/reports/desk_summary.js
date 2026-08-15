"use strict";

function deskSummary(state) {
  return { requests: state.requests.length, notices: state.notifications.length };
}

module.exports = { deskSummary };
