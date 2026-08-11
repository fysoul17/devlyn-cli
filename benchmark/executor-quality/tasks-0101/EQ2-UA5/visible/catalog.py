from models import CatalogEntry


class SnapshotCatalog:
    """Logical retention order and completed rotation tokens."""

    def __init__(self, entries=(), completed=()):
        self._entries = list(entries)
        self._completed = set(completed)

    def __len__(self):
        return len(self._entries)

    def is_completed(self, token):
        return token in self._completed

    def contains(self, snapshot_id):
        return any(entry.snapshot_id == snapshot_id for entry in self._entries)

    def oldest(self):
        return self._entries[0]

    def remove(self, snapshot_id):
        self._entries = [
            entry for entry in self._entries if entry.snapshot_id != snapshot_id
        ]

    def append(self, snapshot_id, slot):
        parent_id = self._entries[-1].snapshot_id if self._entries else None
        self._entries.append(CatalogEntry(snapshot_id, slot, parent_id))

    def complete(self, token):
        self._completed.add(token)

    def snapshot(self):
        return list(self._entries), set(self._completed)

    def restore(self, snapshot):
        entries, completed = snapshot
        self._entries = list(entries)
        self._completed = set(completed)

    def view(self):
        return tuple(self._entries), tuple(sorted(self._completed))

    def agrees_with(self, store):
        return all(
            store.read(entry.slot) is not None
            and store.read(entry.slot)[0] == entry.snapshot_id
            for entry in self._entries
        ) and len({entry.slot for entry in self._entries}) == len(self._entries)
