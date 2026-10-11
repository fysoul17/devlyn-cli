import unittest
from relay import ClosedError, KeyedLoader

class Smoke(unittest.IsolatedAsyncioTestCase):
    async def test_cache_and_completed_invalidation(self):
        calls = []
        async def fetch(key):
            calls.append(key)
            return {"name": key, "version": len(calls)}
        loader = KeyedLoader(fetch)
        self.assertEqual(await loader.get("sku"), {"name": "sku", "version": 1})
        self.assertEqual(await loader.get("sku"), {"name": "sku", "version": 1})
        self.assertEqual(calls, ["sku"])
        loader.invalidate("sku")
        self.assertEqual(await loader.get("sku"), {"name": "sku", "version": 2})
        await loader.close()
        self.assertEqual(loader.snapshot(), {})
        with self.assertRaises(ClosedError):
            await loader.get("sku")

    async def test_other_keys(self):
        async def fetch(key):
            return {"name": key}
        loader = KeyedLoader(fetch)
        self.assertEqual(await loader.get("left"), {"name": "left"})
        self.assertEqual(await loader.get("right"), {"name": "right"})
        self.assertEqual(set(loader.snapshot()), {"left", "right"})
        await loader.close()
