import asyncio
from copy import copy

class ClosedError(Exception):
    pass

class KeyedLoader:
    def __init__(self, fetch):
        self.fetch = fetch
        self._cache = {}
        self._pending = {}
        self._closed = False

    async def _load(self, key):
        result = await self.fetch(key)
        self._cache[key] = result
        self._pending.pop(key, None)
        return result

    async def get(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        if key in self._cache:
            return copy(self._cache[key])
        if key not in self._pending:
            self._pending[key] = asyncio.create_task(self._load(key))
        return copy(await self._pending[key])

    def invalidate(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        self._cache.pop(key, None)
        self._pending.pop(key, None)

    def snapshot(self):
        return copy(self._cache)

    async def close(self):
        self._closed = True
        pending = list(self._pending.values())
        self._cache.clear()
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        self._pending.clear()
