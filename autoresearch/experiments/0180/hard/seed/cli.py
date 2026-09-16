import json
import sys
from store import connect, ingest


def main():
    connection = connect(sys.argv[1])
    with open(sys.argv[2], encoding='utf-8') as stream:
        events = json.load(stream)
    inserted = ingest(connection, events)
    connection.close()
    print(json.dumps({'inserted': inserted}))


if __name__ == '__main__':
    main()
