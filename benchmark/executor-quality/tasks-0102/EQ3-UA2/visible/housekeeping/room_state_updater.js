export function applyRoomEvent(room, accounts, event) {
  if (event.type === "cleaned") {
    return {
      room: {
        ...room,
        state: "dirty",
        cleanedAt: event.at,
        inspection: "not-required",
        alreadyCharged: false,
      },
      accounts: { ...accounts },
    };
  }

  return { room: { ...room }, accounts: { ...accounts } };
}
