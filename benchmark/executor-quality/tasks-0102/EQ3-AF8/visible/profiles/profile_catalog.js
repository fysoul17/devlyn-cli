"use strict";

function profileById(greenhouse, profileId) {
  return greenhouse.profiles.find((profile) => profile.id === profileId) || null;
}

module.exports = { profileById };
