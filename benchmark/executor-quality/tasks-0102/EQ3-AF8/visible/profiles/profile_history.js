"use strict";

function profileNames(greenhouse) {
  return greenhouse.profiles.map((profile) => profile.id);
}

module.exports = { profileNames };
