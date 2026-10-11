"""Request handlers share a loader; admin updates invalidate one SKU."""
from relay import KeyedLoader

class Catalog:
    def __init__(self, database):
        self.documents = KeyedLoader(database.fetch_product)

    async def product_card(self, sku):
        document = await self.documents.get(sku)
        document.setdefault("display", {})["expanded"] = True
        return document

    def product_updated(self, sku):
        self.documents.invalidate(sku)

    async def shutdown(self):
        await self.documents.close()
