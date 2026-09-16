"""Map an asynchronous worker over inputs."""


async def map_limited(worker, items, limit):
    return [await worker(item) for item in items]
