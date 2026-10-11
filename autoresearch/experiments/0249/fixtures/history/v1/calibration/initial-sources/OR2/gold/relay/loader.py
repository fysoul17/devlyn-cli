import asyncio
from copy import deepcopy

class ClosedError(Exception):
    pass

class KeyedLoader:
    def __init__(self, fetch):
        self.fetch = fetch
        self._cache = {}
        self._pending = {}
        self._owned = set()
        self._closed = False

    def _settled(self, task):
        self._owned.discard(task)
        if not task.cancelled():
            task.exception()

    async def _load(self, key):
        task = asyncio.current_task()
        try:
            result = deepcopy(await self.fetch(key))
            if not self._closed and self._pending.get(key) is task:
                self._cache[key] = deepcopy(result)
            return result
        finally:
            if self._pending.get(key) is task:
                self._pending.pop(key)

    async def get(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        if key in self._cache:
            return deepcopy(self._cache[key])
        if key not in self._pending:
            task = asyncio.create_task(self._load(key))
            self._pending[key] = task
            self._owned.add(task)
            task.add_done_callback(self._settled)
        return deepcopy(await asyncio.shield(self._pending[key]))

    def invalidate(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        self._cache.pop(key, None)
        self._pending.pop(key, None)

    def snapshot(self):
        return deepcopy(self._cache)

    async def close(self):
        self._closed = True
        self._cache.clear()
        pending = list(self._owned)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        self._pending.clear()
