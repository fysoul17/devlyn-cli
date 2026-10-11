import asyncio
import json
from pathlib import Path
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
if root.parent.name == 'OR1':
    from examples.editor import edit_pair
    with tempfile.TemporaryDirectory() as temporary:
        result = edit_pair(Path(temporary) / 'articles.json')
    assert result.revision == 2
    assert set(result.documents) == {'headline', 'footer'}
    print(json.dumps({'passed': True, 'revision': result.revision, 'documents': result.documents}))
else:
    from examples.catalog import Catalog
    class Database:
        def __init__(self):
            self.calls = 0
        async def fetch_product(self, sku):
            self.calls += 1
            return {'sku': sku, 'version': self.calls, 'price': {'cents': 100}}
    async def exercise():
        database = Database()
        catalog = Catalog(database)
        first = await catalog.product_card('book')
        first['price']['cents'] = 999
        second = await catalog.product_card('book')
        assert second['price']['cents'] == 100 and second['version'] == 1
        assert second['display']['expanded'] is True
        catalog.product_updated('book')
        third = await catalog.product_card('book')
        assert third['version'] == 2 and database.calls == 2
        await catalog.shutdown()
        return {'passed': True, 'fetches': database.calls, 'versions': [second['version'], third['version']]}
    print(json.dumps(asyncio.run(exercise())))
