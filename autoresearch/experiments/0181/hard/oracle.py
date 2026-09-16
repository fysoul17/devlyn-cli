"""Event-controlled concurrency and failure checks; timeouts are watchdogs."""
import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('submission', Path(sys.argv.pop(1)) / 'async_map.py')
submission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submission)
map_limited = submission.map_limited


async def ready(awaitable):
    return await asyncio.wait_for(awaitable, 2)


class Contract(unittest.IsolatedAsyncioTestCase):
    async def test_validation_before_input(self):
        class Untouched:
            def __iter__(self):
                raise AssertionError('input touched')
        async def worker(item):
            self.fail('worker touched')
        for limit in [True, False, 1.0, '2', None]:
            with self.subTest(limit=limit), self.assertRaises(TypeError):
                await map_limited(worker, Untouched(), limit)
        for limit in [0, -1]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                await map_limited(worker, Untouched(), limit)
        self.assertEqual(await map_limited(worker, [], 3), [])

    async def test_bound_order_refill_and_identity(self):
        started = [asyncio.Event() for _ in range(5)]
        release = [asyncio.Event() for _ in range(5)]
        values = [object(), None, False, 0, 'x']
        pulled, finished = [], set()
        def items():
            for index in range(5):
                self.assertLess(len(pulled) - len(finished), 2, 'eager intake')
                pulled.append(index)
                yield index
        async def worker(index):
            started[index].set()
            try:
                await release[index].wait()
                return values[index]
            finally:
                finished.add(index)
        task = asyncio.create_task(map_limited(worker, items(), 2))
        try:
            await ready(started[0].wait())
            await ready(started[1].wait())
            self.assertEqual(pulled, [0, 1])
            release[1].set()
            await ready(started[2].wait())
            for event in release:
                event.set()
            result = await ready(asyncio.shield(task))
            self.assertEqual(len(result), len(values))
            for actual, expected in zip(result, values):
                self.assertIs(actual, expected)
            self.assertEqual(pulled, list(range(5)))
        finally:
            for event in release:
                event.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def failure_case(self, kind):
        started = [asyncio.Event(), asyncio.Event()]
        trigger = asyncio.Event()
        cleanup_started = asyncio.Event()
        cleanup_release = asyncio.Event()
        cleanup_finished = asyncio.Event()
        unrelated_release = asyncio.Event()
        unrelated = asyncio.create_task(unrelated_release.wait())
        failure = RuntimeError('original failure')
        pulled = []
        def items():
            for index in range(5):
                if kind == 'iterator' and index == 2:
                    raise failure
                pulled.append(index)
                yield index
        async def worker(index):
            self.assertLess(index, 2, 'consumed after observed failure')
            started[index].set()
            if index == 0:
                await trigger.wait()
                if kind in ('worker', 'cancel_during_cleanup'):
                    raise failure
                if kind == 'child_cancel':
                    raise asyncio.CancelledError()
                return index
            try:
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                await cleanup_release.wait()
                cleanup_finished.set()
        task = asyncio.create_task(map_limited(worker, items(), 2))
        try:
            for event in started:
                await ready(event.wait())
            if kind == 'caller_cancel':
                task.cancel()
            else:
                trigger.set()
            await ready(cleanup_started.wait())
            self.assertFalse(task.done(), 'returned before async cleanup finished')
            self.assertEqual(pulled, [0, 1])
            self.assertFalse(unrelated.done(), 'cancelled unrelated task')
            if kind == 'cancel_during_cleanup':
                task.cancel()
                await asyncio.sleep(0)
                self.assertFalse(task.done(), 'caller cancellation skipped cleanup')
            cleanup_release.set()
            expected = asyncio.CancelledError if kind.endswith('cancel') else RuntimeError
            if kind == 'cancel_during_cleanup':
                expected = (RuntimeError, asyncio.CancelledError)
            with self.assertRaises(expected) as caught:
                await ready(asyncio.shield(task))
            if isinstance(caught.exception, RuntimeError):
                self.assertIs(caught.exception, failure)
            self.assertTrue(cleanup_finished.is_set())
        finally:
            trigger.set()
            cleanup_release.set()
            unrelated_release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, unrelated, return_exceptions=True)

    async def test_worker_failure(self):
        await self.failure_case('worker')

    async def test_iterator_failure(self):
        await self.failure_case('iterator')

    async def test_caller_cancellation(self):
        await self.failure_case('caller_cancel')

    async def test_worker_cancellation(self):
        await self.failure_case('child_cancel')

    async def test_caller_cancel_during_failure_cleanup(self):
        await self.failure_case('cancel_during_cleanup')

    async def test_iter_failure_identity(self):
        failure = LookupError('iter failed')
        class Broken:
            def __iter__(self):
                raise failure
        async def worker(item):
            self.fail('worker invoked')
        with self.assertRaises(LookupError) as caught:
            await map_limited(worker, Broken(), 2)
        self.assertIs(caught.exception, failure)


if __name__ == '__main__':
    unittest.main()
