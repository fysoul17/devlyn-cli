// Tiny Express server used by backend-contract fixtures. Intentionally small.
const express = require('express');

const app = express();
app.use(express.json());

const items = [
  { id: 1, name: 'alpha', qty: 3 },
  { id: 2, name: 'beta', qty: 5 },
];

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/items', (_req, res) => {
  res.json({ items });
});

app.get('/items/:id', (req, res) => {
  const id = Number(req.params.id);
  const item = items.find((it) => it.id === id);
  if (!item) {
    res.status(404).json({ error: 'not_found', id });
    return;
  }
  res.json({ item });
});

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  app.listen(port, () => {
    console.log(`bench-test-repo server listening on :${port}`);
  });
}

module.exports = { app };
