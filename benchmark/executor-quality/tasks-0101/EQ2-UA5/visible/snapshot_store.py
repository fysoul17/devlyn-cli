class SnapshotStore:
    """Fixed-size physical slots with a rotating allocation cursor."""

    def __init__(self, capacity, images=(), next_slot=0):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._images = {
            slot: (snapshot_id, bytes(payload))
            for slot, snapshot_id, payload in images
        }
        self._next_slot = next_slot

    def reserve(self):
        slot = self._next_slot
        self._next_slot = (self._next_slot + 1) % self.capacity
        return slot

    def write(self, slot, snapshot_id, payload):
        self._images[slot] = (snapshot_id, bytes(payload))

    def read(self, slot):
        return self._images.get(slot)

    def view(self):
        return tuple(
            (slot, snapshot_id, payload)
            for slot, (snapshot_id, payload) in sorted(self._images.items())
        )

    def slots_snapshot(self):
        return dict(self._images)

    def restore_slots(self, images):
        self._images = dict(images)

    def allocation_mark(self):
        return self._next_slot

    def rewind_allocation(self, mark):
        self._next_slot = mark
