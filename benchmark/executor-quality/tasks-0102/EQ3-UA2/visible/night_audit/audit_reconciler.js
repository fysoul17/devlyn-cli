export function canPublishInventory(room) {
  return room.state === "bookable" && room.inspection === "signed-off";
}

export const auditRule =
  "The night audit reconciler holds inventory publication until an inspection signoff is recorded.";
