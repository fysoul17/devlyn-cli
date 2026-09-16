import unittest
from store import connect, ingest, list_events


class LegacyTests(unittest.TestCase):
    def test_roundtrip(self):
        connection = connect(':memory:')
        try:
            events = [{'id': 'a', 'payload': {'message': 'hello'}}]
            self.assertEqual(ingest(connection, events), 1)
            self.assertEqual(list_events(connection), events)
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
