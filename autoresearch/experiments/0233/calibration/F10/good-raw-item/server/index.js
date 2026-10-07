const express = require('express');
const fs = require('node:fs');
const path = require('node:path');
const app = express();
app.use(express.json());
const store = path.join(__dirname, '../data/items.json');
const read = () => JSON.parse(fs.readFileSync(store, 'utf8')).items;
const write = items => fs.writeFileSync(store, JSON.stringify({ items }, null, 2) + '\n');
app.get('/health', (_req, res) => res.json({ status: 'ok' }));
app.get('/items', (_req, res) => res.json({ items: read() }));
app.get('/items/:id', (req, res) => {
  const id = Number(req.params.id);
  const item = read().find(it => it.id === id);
  if (!item) return res.status(404).json({ error: 'not_found', id });
  res.json({ item });
});
app.post('/items', (req, res) => {
  const { name, qty } = req.body || {};
  if (typeof name !== 'string' || !name.trim()) return res.status(400).json({ error: 'invalid_body', field: 'name' });
  if (typeof qty !== 'number' || !Number.isFinite(qty) || qty <= 0) return res.status(400).json({ error: 'invalid_body', field: 'qty' });
  try {
    const items = read();
    const item = { id: Math.max(0, ...items.map(it => it.id)) + 1, name, qty };
    items.push(item);
    write(items);
    res.status(200).json(item);
  } catch (error) { res.status(500).json({ error: 'store_failure', detail: error.message }); }
});
if (require.main === module) app.listen(Number(process.env.PORT) || 3000);
module.exports = { app };
