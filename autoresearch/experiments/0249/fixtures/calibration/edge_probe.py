import asyncio
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'OR1/gold'))
sys.path.insert(0, str(ROOT / 'OR2/gold'))
from folio import FileStore
from relay import KeyedLoader

with tempfile.TemporaryDirectory(dir=ROOT / 'calibration/scratch') as temporary:
    path = Path(temporary) / 'bad.json'
    path.write_bytes(b'\xff')
    try:
        FileStore(path).read()
    except Exception as error:
        malformed = {'type': type(error).__name__, 'bytes_preserved': path.read_bytes() == b'\xff'}

async def concurrent_close():
    started, cleanup_started, release, finished = (asyncio.Event() for _ in range(4))
    cleaned = False
    async def fetch(key):
        nonlocal cleaned
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleanup_started.set()
            try:
                await release.wait()
                cleaned = True
            finally:
                finished.set()
    loader = KeyedLoader(fetch)
    waiter = asyncio.create_task(loader.get('a'))
    await started.wait()
    first = asyncio.create_task(loader.close())
    await cleanup_started.wait()
    second_entered = asyncio.Event()
    async def close_again():
        second_entered.set()
        await loader.close()
    second = asyncio.create_task(close_again())
    await second_entered.wait()
    barrier = asyncio.Event()
    asyncio.get_running_loop().call_soon(barrier.set)
    await barrier.wait()
    prematurely_finished = finished.is_set()
    release.set()
    await asyncio.gather(first, second, waiter, return_exceptions=True)
    return {'cleanup_finished_before_release': prematurely_finished, 'cleanup_completed': cleaned}

print(json.dumps({'OR1': malformed, 'OR2': asyncio.run(concurrent_close())}))
