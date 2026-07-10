FS tasks provide `base.json` (`repo` + `sha`) and `hidden/oracle.sh`; the
evaluator runs the oracle with the cloned, patched repository as its working
directory. For a portable local source, commit a Git bundle and set `repo` to
`./source.bundle`; never commit an embedded `.git` directory under this corpus.
