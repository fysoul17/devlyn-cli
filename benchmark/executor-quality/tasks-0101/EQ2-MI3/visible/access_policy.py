"""Badge-pass policy for room zones."""


class AccessPolicy:
    def __init__(self, passes, room_zones):
        self._passes = {
            requester: frozenset(zones)
            for requester, zones in passes.items()
        }
        self._room_zones = dict(room_zones)

    def allows(self, request):
        zone = self._room_zones.get(request.room)
        return zone is not None and zone in self._passes.get(request.requester, ())
