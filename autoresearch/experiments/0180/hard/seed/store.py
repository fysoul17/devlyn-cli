import json
import sqlite3


def connect(path):
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE IF NOT EXISTS events '
                       '(seq INTEGER PRIMARY KEY AUTOINCREMENT, '
                       'event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')
    connection.commit()
    return connection


def ingest(connection, events):
    inserted = 0
    for event in events:
        connection.execute('INSERT INTO events(event_id, payload) VALUES (?, ?)',
                           (event['id'], json.dumps(event['payload'])))
        connection.commit()
        inserted += 1
    return inserted


def list_events(connection):
    return [{'id': row[0], 'payload': json.loads(row[1])}
            for row in connection.execute('SELECT event_id, payload FROM events ORDER BY seq')]
