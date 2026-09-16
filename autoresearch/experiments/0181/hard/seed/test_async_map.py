import unittest
from async_map import map_limited


class Legacy(unittest.IsolatedAsyncioTestCase):
    async def test_values(self):
        async def worker(value):
            return value * 2
        self.assertEqual(await map_limited(worker, range(3), 2), [0, 2, 4])

    async def test_empty(self):
        async def worker(value):
            self.fail('empty input called worker')
        self.assertEqual(await map_limited(worker, [], 1), [])

    async def test_generator(self):
        async def worker(value):
            return str(value)
        self.assertEqual(await map_limited(worker, (i for i in range(3)), 1), ['0', '1', '2'])
