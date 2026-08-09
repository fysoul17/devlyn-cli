# Catalog response classification

The transport component classifies catalog responses. The synchronization component consumes that classification to update its cursor, retry count, quarantine count, and item snapshot.

Run the fixture tests with:

```bash
python3 -m unittest discover tests
```
