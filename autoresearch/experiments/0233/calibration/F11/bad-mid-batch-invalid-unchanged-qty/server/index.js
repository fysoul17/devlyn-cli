const express = require('express');
const app = express();
app.use(express.json());
const items = [{ id: 1, name: 'alpha', qty: 3 }, { id: 2, name: 'beta', qty: 5 }];
app.get('/health', (_req, res) => res.json({ status: 'ok' }));
app.get('/items', (_req, res) => res.json({ items }));
app.get('/items/:id', (req, res) => {
  const id = Number(req.params.id);
  const item = items.find(it => it.id === id);
  if (!item) return res.status(404).json({ error: 'not_found', id });
  res.json({ item });
});
app.post('/items/import', (req, res) => {
  const batch = req.body?.items;
  if (!Array.isArray(batch)) return res.status(400).json({ error: 'invalid_body' });
  for (const [index, item] of batch.entries()) {
    const field = typeof item?.name !== 'string' || !item.name.trim() ? 'name' : null;
    if (field) return res.status(400).json({ error: 'invalid_batch', index, field });
  }
  let id = Math.max(0, ...items.map(item => item.id));
  items.push(...batch.map(item => ({ id: ++id, name: item.name, qty: item.qty })));
  res.status(201).json({ inserted: batch.length });
});
if (require.main === module) app.listen(Number(process.env.PORT) || 3000);
module.exports = { app };
