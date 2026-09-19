"""Exploratory replay of the final C review's two concrete JSON counterexamples."""
from pathlib import Path
import importlib
import json
import sys


def check(work):
    sys.path.insert(0, str(work))
    before = sys.get_int_max_str_digits()
    module = importlib.import_module('stream')
    rows = []
    for kind, payload in [('valid-large-integer', b'9' * 4301), ('malformed-deep-array', b'[' * 200000)]:
        for mode in ('feed', 'finish'):
            decoder = module.Decoder()
            row = {'case': kind, 'mode': mode, 'pass': False}
            try:
                if mode == 'feed':
                    values = decoder.feed(payload + b'\n')
                else:
                    decoder.feed(payload)
                    values = decoder.finish()
                row['pass'] = (kind == 'valid-large-integer' and len(values) == 1
                               and type(values[0]) is int and values[0] == 10**4301 - 1)
                row['returned_count'] = len(values)
            except Exception as error:
                row.update(exception=type(error).__name__, message=str(error)[:200])
                if kind == 'malformed-deep-array':
                    row['pass'] = (isinstance(error, module.ParseError)
                                   and error.line == 1 and error.reason == 'json')
                    repeated = []
                    for call in (lambda: decoder.feed(b''), lambda: decoder.feed(None), decoder.finish):
                        try:
                            call()
                            repeated.append(False)
                        except Exception as again:
                            repeated.append(again is error)
                    row['same_exception'] = repeated
                    row['pass'] = row['pass'] and all(repeated)
            rows.append(row)
    return {'integer_limit_before_import': before, 'integer_limit_after_checks': sys.get_int_max_str_digits(),
            'checks': rows}


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1]).resolve())))
