"use strict";

function electionTime(hour, minute) {
  return `${hour}:${String(minute).padStart(2, "0")}`;
}

module.exports = { electionTime };
