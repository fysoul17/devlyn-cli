# Release artifact vault

The catalog is a JSON object keyed by artifact name. The grants file maps caller tokens to arrays of scopes.

List artifact keys with:

```sh
python3 cli.py list catalog.json
```

Run the tests with:

```sh
python3 -m unittest discover tests
```
