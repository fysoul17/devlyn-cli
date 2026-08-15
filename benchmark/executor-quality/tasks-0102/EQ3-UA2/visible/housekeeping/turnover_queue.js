export function nextTurnover(rooms) {
  return rooms.find((room) => room.state === "dirty") ?? null;
}

export function assignAttendant(room, attendant) {
  return { ...room, attendant };
}
