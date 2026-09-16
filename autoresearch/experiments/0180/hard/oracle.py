"""Black-box API/CLI oracle. No required implementation shape."""
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(ROOT))
from store import connect, ingest, list_events


def event(identifier, **payload):
    return {'id': identifier, 'payload': payload}


class Contract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'events.db'
        self.db = connect(self.path)
        self.addCleanup(self.db.close)
        self.prior = [event('existing', z='last', a='first')]
        self.assertEqual(ingest(self.db, self.prior), 1)

    def test_retry_order_and_durability(self):
        batch = [event('b', text='한글'), event('existing', a='first', z='last'),
                 event('b', text='한글'), event(' a '), event('a')]
        self.assertEqual(ingest(self.db, iter(batch)), 3)
        self.assertEqual(ingest(self.db, batch), 0)
        expected = self.prior + [batch[0], batch[3], batch[4]]
        self.assertEqual(list_events(self.db), expected)
        self.db.close()
        with closing(connect(self.path)) as reopened:
            self.assertEqual(list_events(reopened), expected)
            self.assertEqual(ingest(reopened, batch), 0)

    def assert_atomic(self, batch, error):
        with self.assertRaises(error):
            ingest(self.db, batch)
        self.assertEqual(list_events(self.db), self.prior)
        with closing(connect(self.path)) as observer:
            self.assertEqual(list_events(observer), self.prior)
        self.assertEqual(ingest(self.db, [event('retry')]), 1)

    def test_empty_batch(self):
        self.assertEqual(ingest(self.db, iter(())), 0)
        self.assertEqual(list_events(self.db), self.prior)
        result = self.run_cli('[]')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '{"inserted": 0}\n', ''))

    def test_conflicts(self):
        self.assert_atomic([event('new'), event('existing', a='different')], ValueError)

    def test_intra_batch_conflict(self):
        self.assert_atomic([event('new'), event('new', x='different')], ValueError)

    def test_invalid_events(self):
        invalid = [None, [], {}, {'id': 'x'}, event(''), event(3), event(True),
                   {'id': 'x', 'payload': []}, {'id': 'x', 'payload': {'x': 1}},
                   {'id': 'x', 'payload': {1: 'x'}}, {**event('x'), 'extra': 'x'}]
        for bad in invalid:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ingest(self.db, [event('new'), bad])
            self.assertEqual(list_events(self.db), self.prior)

    def test_iterator_failure(self):
        def broken():
            yield event('new')
            raise RuntimeError('source interrupted')
        self.assert_atomic(broken(), RuntimeError)

    def test_insert_failure(self):
        self.db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON events "
                        "WHEN NEW.event_id = 'blocked' BEGIN SELECT RAISE(FAIL, 'blocked'); END")
        self.db.commit()
        self.assert_atomic([event('new'), event('blocked')], sqlite3.DatabaseError)

    def test_legacy_schema(self):
        legacy = Path(self.directory.name) / 'legacy.db'
        with closing(sqlite3.connect(legacy)) as raw, raw:
            raw.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, '
                        'event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')
            raw.execute('INSERT INTO events VALUES (?, ?, ?)', (7, 'old', '{"b":"2", "a":"1"}'))
            schema = raw.execute("SELECT sql FROM sqlite_master WHERE name='events'").fetchone()
        with closing(connect(legacy)) as opened:
            self.assertEqual(ingest(opened, [event('old', a='1', b='2'), event('new')]), 1)
            self.assertEqual(list_events(opened), [event('old', b='2', a='1'), event('new')])
            self.assertEqual(opened.execute('SELECT seq,payload FROM events WHERE event_id=?', ('old',)).fetchone(),
                             (7, '{"b":"2", "a":"1"}'))
            self.assertEqual(opened.execute("SELECT sql FROM sqlite_master WHERE name='events'").fetchone(), schema)

    def run_cli(self, content, path=None):
        file = Path(self.directory.name) / 'input.json'
        file.write_text(content, encoding='utf-8')
        return subprocess.run([sys.executable, str(ROOT / 'cli.py'), str(path or self.path), str(file)],
                              cwd=ROOT, capture_output=True, text=True, timeout=10)

    def assert_cli_error(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertTrue(result.stderr.startswith('error: '), result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1, result.stderr)
        self.assertGreater(len(result.stderr.strip()), len('error:'))
        self.assertNotIn('Traceback', result.stderr)

    def test_cli_success(self):
        batch = json.dumps([event('x'), event('x')])
        for expected in (1, 0):
            result = self.run_cli(batch)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (0, json.dumps({'inserted': expected}) + '\n', ''))

    def test_cli_failures(self):
        for content in ('{', '{}', 'null', '1', '""',
                        json.dumps([event('new'), event('existing', different='value')]),
                        json.dumps([event('new'), {'id': 'invalid'}])):
            with self.subTest(content=content):
                self.assert_cli_error(self.run_cli(content))
                self.assertEqual(list_events(self.db), self.prior)
        self.assert_cli_error(self.run_cli('[]', Path(self.directory.name)))
        missing = Path(self.directory.name) / 'missing\nfile'
        result = subprocess.run([sys.executable, str(ROOT / 'cli.py'), str(self.path), str(missing)],
                                capture_output=True, text=True, timeout=10)
        self.assert_cli_error(result)
        self.db.execute("CREATE TRIGGER reject_cli BEFORE INSERT ON events "
                        "WHEN NEW.event_id = 'blocked' BEGIN SELECT RAISE(FAIL, 'bad\nmessage'); END")
        self.db.commit()
        self.assert_cli_error(self.run_cli(json.dumps([event('new'), event('blocked')])))
        self.assertEqual(list_events(self.db), self.prior)


if __name__ == '__main__':
    unittest.main()
