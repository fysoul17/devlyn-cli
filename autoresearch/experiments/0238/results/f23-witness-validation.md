# F23 precision witness supplement: prospective registration and validation

2026-10-10. Separate 0238 supplement, written before its validation runs and before any 0238 owner outputs. No model call or historical file/verdict change. This is exposed development evidence, not untouched confirmation. Only `../f23_precision.py` and this report are owned by this audit.

## Frozen scope and predictions BEFORE validation

The owner receives exactly 0234's F23 request/source. Its original `priority-rollback` and `single-warehouse-fefo` oracle rows remain required and unchanged. The new hidden supplement adds only the two inputs actually executed by d25's peer: preserve accepted submillisecond precision in submission order, and recognize equal instants across offset/fraction spellings before applying ID order. It checks their declared output schema, allocations and stock conservation, while accepting either omission or retention of exhausted zero-quantity lots as the historical oracle does. It does not prescribe a timestamp library, a parser implementation or new input/output fields.

Contract: `0234/tasks.json` F23 request says dates parse as ISO dates; order priority descending, submitted_at ascending, ID ascending; accepted allocations consume stock; rejected orders do not; exact success JSON/empty stderr and row schemas. These timestamps are ISO values accepted by historical B/H/P and reference validation; no millisecond restriction appears in the request. Interpreting submitted_at as chronological time rather than raw string order is explicit in the historical d25 finding and its equivalent-offset closure. The old reference's lexical comparator is not an authority overriding that contract.

Provenance: `/Users/aipalm/.local/share/nx01/0234-live/out/d25-F23-codex-H-r1/home/.codex/sessions/2026/10/08/rollout-2026-10-08T04-08-29-01a119b2-c761-7e50-a887-6a9cb0b87527.jsonl:61,88,91` contains the original precision probe, the exact two final input constructions and passing raw output. Owner `run/stdout:33–34,42` contains the finding, repair acknowledgement and closure. The only invocation adaptation is an ordinary temporary JSON file in place of `/dev/stdin`; expected allocations are unchanged.

| Row | Input stock and submitted orders | Expected |
| --- | --- | --- |
| submillisecond-order | One unit; `a-later` at `2027-01-01T00:00:00.0002Z`, then `z-earlier` at `.0001Z`; equal priority 1 | Accept `z-earlier`, reject `a-later`; no positive stock remains. |
| offset-equivalence | Two units; same orders plus `b-equivalent` at `2027-01-01T01:00:00.000100+01:00`; equal priority 1 | Accept `b-equivalent`, then `z-earlier`; reject `a-later`; no positive stock remains. |

Predictions fixed before executing this supplement:

- Historical B d24 and P d26 fail both rows because their comparator truncates to milliseconds and then sorts IDs. H d25 passes both rows.
- The original starter/no-op fails both rows because it does not implement fulfill-wave.
- Historical `calibration/F23/good` and `good-zero-rows` pass submillisecond-order but fail offset-equivalence because they sort raw timestamp strings. That would expose a reference gap, not invalidate a contract-grounded probe or make the old reference globally correct.
- A disposable alternative based on the old reference, replacing only raw-string time comparison with arbitrary-length exact BigInt scaled epoch comparison, passes both rows and both unchanged historical rows. This differs from H's normalized-fraction tie comparator. Test both optional-zero-row representations; neither should be required.
- Output-adjudicator controls must reject wrong/extra allocations, nonzero or duplicate remaining stock, wrong row keys, boolean quantities, incorrect rejected rows, extra stdout and nonempty stderr. It must accept valid zero-row omission/retention, object-key reordering and ordinary JSON whitespace. These are apparatus controls, not participant findings.

Historical fingerprints (SHA-256):

| Input | Hash |
| --- | --- |
| F23 request UTF-8 | `3f4c34c5909832e1f1d05fb005723cd04625a0c7dbd55a50a4f2142b2e11c6d2` |
| 0234/tasks.json | `ba7e6c7b30ba51cae0b91aae960aa03be123ca84c79e8ba87d49893474050c10` |
| 0234/oracle.js | `ae0e31c4a0755fb9ecf062bc1ac86d4c4d323e70a4c324248ab92c33a22f709a` |
| 0234/fixture_oracle.js | `4506f625d6c909ca61a1884f86497ae533af774009e77712a5b1877ac809fdb2` |
| Starter bin/cli.js | `b8f5c3c9015c8c8491430b4be3001c03d123008518cb0c25a4ecdec8fbaa640b` |
| Historical good bin/cli.js | `38a097b6e764435854b513e3982fed3d57b9b347aada024206fb91db6d03bcd5` |
| d24 B bin/cli.js | `394770f5b178a69378f34dbd59eb7b44462346217d1ff88910263330d19b556d` |
| d25 H bin/cli.js | `3ea0590fc8bf5c6eeee139285924e0347902c008733336b3c04332d676b7b739` |
| d26 P bin/cli.js | `9ebf02f5864dec547ffa67b5275c66cd450c7e80bf75e5335204bfd7367bba32` |

## Validation results AFTER execution

All recorded host outcomes below match the prospective predictions. Historical verdicts remain unchanged. The historical reference is a positive only for its older coverage; it is not fully correct for the chronological offset obligation. d25 H and the two auditable alternative exact-comparator fixtures are positives for this supplement, not proofs of complete correctness. The original oracle remains required. No 0238 owner output was inspected or produced.

Pre-run witness SHA-256: `8face9ace542d944889bfff8802b352de0a3063d85ae0a8f9ccdbe4133f7f3e2`. Additional pre-run prediction: the unchanged historical oracle rejects the starter and accepts B/H/P, historical good variants and both alternative comparator variants. Host validation will use Node v25.4.0 / Python 3.14.7; container validation remains separate.

### Host execution 2026-10-10T03:49:13.812318+00:00

Historical inputs above retained identical SHA-256 after all calls. Each product was copied to disposable storage for the supplement; the historical oracle makes its own fresh copy. The two alternative positives are old `good` / `good-zero-rows` overlays with exactly one comparator replacement (`a.submitted_at.localeCompare(b.submitted_at)` -> `exactSubmittedCompare(a.submitted_at, b.submitted_at)`) and this helper inserted before the existing fs import:

```javascript
function exactSubmittedCompare(left, right) {
  const fraction = value => (value.match(/\.(\d+)/) || [])[1] || '';
  const lf = fraction(left), rf = fraction(right);
  const digits = Math.max(lf.length, rf.length), scale = 10n ** BigInt(digits);
  const exact = (value, part) => BigInt(Date.parse(value.replace(/\.\d+/, ''))) * scale
    + BigInt((part || '0').padEnd(digits, '0')) * 1000n;
  const a = exact(left, lf), b = exact(right, rf);
  return a < b ? -1 : a > b ? 1 : 0;
}
```

| Product | Supplement rows | Unchanged original rows |
| --- | --- | --- |
| starter-no-op | submillisecond-order: FAIL, offset-equivalence: FAIL | priority-rollback: 1, single-warehouse-fefo: 1 |
| B | submillisecond-order: FAIL, offset-equivalence: FAIL | priority-rollback: 0, single-warehouse-fefo: 0 |
| H | submillisecond-order: PASS, offset-equivalence: PASS | priority-rollback: 0, single-warehouse-fefo: 0 |
| P | submillisecond-order: FAIL, offset-equivalence: FAIL | priority-rollback: 0, single-warehouse-fefo: 0 |
| historical-good | submillisecond-order: PASS, offset-equivalence: FAIL | priority-rollback: 0, single-warehouse-fefo: 0 |
| alternative-exact-good | submillisecond-order: PASS, offset-equivalence: PASS | priority-rollback: 0, single-warehouse-fefo: 0 |
| historical-good-zero-rows | submillisecond-order: PASS, offset-equivalence: FAIL | priority-rollback: 0, single-warehouse-fefo: 0 |
| alternative-exact-good-zero-rows | submillisecond-order: PASS, offset-equivalence: PASS | priority-rollback: 0, single-warehouse-fefo: 0 |

Raw product results (temporary source paths are descriptive, retained cli_sha256 binds the implementation):

```json
[
  {
    "label": "starter-no-op",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/sources/F23",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "successful valid input must exit 0",
            "successful valid input must have empty stderr",
            "stdout is not exactly one parseable JSON value"
          ],
          "raw": {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Unknown command: fulfill-wave\nUsage: bench-cli <command> [options]\n\nCommands:\n  hello [--name NAME]        Print a greeting (default name: \"world\")\n  version                    Print the CLI version from package.json\n  --help, -h                 Show this help\n\nExamples:\n  bench-cli hello\n  bench-cli hello --name alice\n  bench-cli version\n"
          }
        },
        {
          "id": "offset-equivalence",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "successful valid input must exit 0",
            "successful valid input must have empty stderr",
            "stdout is not exactly one parseable JSON value"
          ],
          "raw": {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Unknown command: fulfill-wave\nUsage: bench-cli <command> [options]\n\nCommands:\n  hello [--name NAME]        Print a greeting (default name: \"world\")\n  version                    Print the CLI version from package.json\n  --help, -h                 Show this help\n\nExamples:\n  bench-cli hello\n  bench-cli hello --name alice\n  bench-cli version\n"
          }
        }
      ],
      "cli_sha256": "b8f5c3c9015c8c8491430b4be3001c03d123008518cb0c25a4ecdec8fbaa640b",
      "status": "FAIL"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 1,
        "stdout": "",
        "stderr": "Error: non-JSON fulfill-wave:  Unknown command: fulfill-wave\nUsage: bench-cli <command> [options]\n\nCommands:\n  hello [--name NAME]        Print a greeting (default name: \"world\")\n  version                    Print the CLI version from package.json\n  --help, -h                 Show this help\n\nExamples:\n  bench-cli hello\n  bench-cli hello --name alice\n  bench-cli version\n\n    at run (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/fixture_oracle.js:14:17)\n    at f23 (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/fixture_oracle.js:137:18)\n    at module.exports (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/fixture_oracle.js:148:30)\n    at main (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/oracle.js:114:41)\n    at Object.<anonymous> (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/oracle.js:158:1)\n    at Module._compile (node:internal/modules/cjs/loader:1803:14)\n    at Module._extensions..js (node:internal/modules/cjs/loader:1934:10)\n    at Module.load (node:internal/modules/cjs/loader:1524:32)\n    at Module._load (node:internal/modules/cjs/loader:1326:12)\n    at TracingChannel.traceSync (node:diagnostics_channel:328:14)\n"
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 1,
        "stdout": "",
        "stderr": "Error: non-JSON fulfill-wave:  Unknown command: fulfill-wave\nUsage: bench-cli <command> [options]\n\nCommands:\n  hello [--name NAME]        Print a greeting (default name: \"world\")\n  version                    Print the CLI version from package.json\n  --help, -h                 Show this help\n\nExamples:\n  bench-cli hello\n  bench-cli hello --name alice\n  bench-cli version\n\n    at run (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/fixture_oracle.js:14:17)\n    at f23 (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/fixture_oracle.js:137:18)\n    at module.exports (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/fixture_oracle.js:148:30)\n    at main (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/oracle.js:114:41)\n    at Object.<anonymous> (/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/oracle.js:158:1)\n    at Module._compile (node:internal/modules/cjs/loader:1803:14)\n    at Module._extensions..js (node:internal/modules/cjs/loader:1934:10)\n    at Module.load (node:internal/modules/cjs/loader:1524:32)\n    at Module._load (node:internal/modules/cjs/loader:1326:12)\n    at TracingChannel.traceSync (node:diagnostics_channel:328:14)\n"
      }
    ]
  },
  {
    "label": "B",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/Users/aipalm/.local/share/nx01/0234-live/out/d24-F23-codex-B-r1/snapshot",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "accepted order/allocation schema or stock allocation differs",
            "rejected order/reason/schema differs"
          ],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"a-later\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"z-earlier\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "accepted order/allocation schema or stock allocation differs",
            "rejected order/reason/schema differs"
          ],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"a-later\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"b-equivalent\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"z-earlier\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "394770f5b178a69378f34dbd59eb7b44462346217d1ff88910263330d19b556d",
      "status": "FAIL"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  },
  {
    "label": "H",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/Users/aipalm/.local/share/nx01/0234-live/out/d25-F23-codex-H-r1/snapshot",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"b-equivalent\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "3ea0590fc8bf5c6eeee139285924e0347902c008733336b3c04332d676b7b739",
      "status": "PASS"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  },
  {
    "label": "P",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/Users/aipalm/.local/share/nx01/0234-live/out/d26-F23-codex-P-r1/snapshot",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "accepted order/allocation schema or stock allocation differs",
            "rejected order/reason/schema differs"
          ],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"a-later\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"z-earlier\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "accepted order/allocation schema or stock allocation differs",
            "rejected order/reason/schema differs"
          ],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"a-later\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"b-equivalent\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"z-earlier\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "9ebf02f5864dec547ffa67b5275c66cd450c7e80bf75e5335204bfd7367bba32",
      "status": "FAIL"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  },
  {
    "label": "historical-good",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/private/var/folders/l8/3dwz4xpx761bj1z0r_pyhh100000gn/T/0238-f23-validation-jsfe5lk7/historical-good",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "accepted order/allocation schema or stock allocation differs",
            "rejected order/reason/schema differs"
          ],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"a-later\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"b-equivalent\",\"reason\":\"insufficient_stock\"}],\"remaining\":[]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "38a097b6e764435854b513e3982fed3d57b9b347aada024206fb91db6d03bcd5",
      "status": "FAIL"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  },
  {
    "label": "alternative-exact-good",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/private/var/folders/l8/3dwz4xpx761bj1z0r_pyhh100000gn/T/0238-f23-validation-jsfe5lk7/alternative-exact-good",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"b-equivalent\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "6eeb61f0d6b68ceed60eed83a03c1844609a8ea4feee67e5af677a41444e8115",
      "status": "PASS"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  },
  {
    "label": "historical-good-zero-rows",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/private/var/folders/l8/3dwz4xpx761bj1z0r_pyhh100000gn/T/0238-f23-validation-jsfe5lk7/historical-good-zero-rows",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "FAIL",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [
            "accepted order/allocation schema or stock allocation differs",
            "rejected order/reason/schema differs"
          ],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"a-later\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"b-equivalent\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "35384d618fe498226e17dd8b49751b6c320075b5b462bee9470c4865318abbfe",
      "status": "FAIL"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  },
  {
    "label": "alternative-exact-good-zero-rows",
    "supplement": {
      "schema": "0238-f23-precision-v1",
      "source": "/private/var/folders/l8/3dwz4xpx761bj1z0r_pyhh100000gn/T/0238-f23-validation-jsfe5lk7/alternative-exact-good-zero-rows",
      "rows": [
        {
          "id": "submillisecond-order",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 1,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        },
        {
          "id": "offset-equivalence",
          "status": "PASS",
          "input": {
            "warehouses": [
              {
                "id": "w",
                "distance": 0,
                "lots": [
                  {
                    "sku": "s",
                    "lot": "l",
                    "qty": 2,
                    "expires": "2028-01-01"
                  }
                ]
              }
            ],
            "orders": [
              {
                "id": "a-later",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0002Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "z-earlier",
                "priority": 1,
                "submitted_at": "2027-01-01T00:00:00.0001Z",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              },
              {
                "id": "b-equivalent",
                "priority": 1,
                "submitted_at": "2027-01-01T01:00:00.000100+01:00",
                "lines": [
                  {
                    "sku": "s",
                    "qty": 1,
                    "single_warehouse": false
                  }
                ]
              }
            ]
          },
          "expected": {
            "accepted": [
              {
                "id": "b-equivalent",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              },
              {
                "id": "z-earlier",
                "allocations": [
                  {
                    "sku": "s",
                    "warehouse": "w",
                    "lot": "l",
                    "qty": 1
                  }
                ]
              }
            ],
            "rejected": [
              {
                "id": "a-later",
                "reason": "insufficient_stock"
              }
            ]
          },
          "errors": [],
          "raw": {
            "exit_code": 0,
            "stdout": "{\"accepted\":[{\"id\":\"b-equivalent\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]},{\"id\":\"z-earlier\",\"allocations\":[{\"sku\":\"s\",\"warehouse\":\"w\",\"lot\":\"l\",\"qty\":1}]}],\"rejected\":[{\"id\":\"a-later\",\"reason\":\"insufficient_stock\"}],\"remaining\":[{\"warehouse\":\"w\",\"sku\":\"s\",\"lot\":\"l\",\"qty\":0,\"expires\":\"2028-01-01\"}]}\n",
            "stderr": ""
          }
        }
      ],
      "cli_sha256": "3a335feb5326adfebfcdecf9775d7d4694f600440b3033333d585705e6f4c015",
      "status": "PASS"
    },
    "original_oracle": [
      {
        "row": "priority-rollback",
        "exit_code": 0,
        "stdout": "{\"row\":\"priority-rollback\",\"pass\":true}\n",
        "stderr": ""
      },
      {
        "row": "single-warehouse-fefo",
        "exit_code": 0,
        "stdout": "{\"row\":\"single-warehouse-fefo\",\"pass\":true}\n",
        "stderr": ""
      }
    ]
  }
]
```

Raw adjudicator controls:

```json
[
  {
    "name": "valid-omitted-zero-key-order-whitespace",
    "expected_valid": true,
    "actual_valid": true,
    "errors": [],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": []\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "valid-retained-zero",
    "expected_valid": true,
    "actual_valid": true,
    "errors": [],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "valid-json-number-equivalence",
    "expected_valid": true,
    "actual_valid": true,
    "errors": [],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1.0,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0.0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "wrong-allocation-stock",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "accepted order/allocation schema or stock allocation differs"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 2,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "wrong-allocation-row",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "accepted order/allocation schema or stock allocation differs"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"other\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "boolean-allocation",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "allocation quantity must be numeric, not boolean"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": true,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "extra-accepted-row-key",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "accepted order/allocation schema or stock allocation differs"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"extra\": 1,\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "nonzero-remaining",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "remaining stock/schema differs (zero row optional)"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 1,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "duplicate-remaining",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "remaining stock/schema differs (zero row optional)"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    },\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "boolean-remaining",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "remaining quantity must be numeric, not boolean"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": false,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "wrong-remaining-schema",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "remaining stock/schema differs (zero row optional)"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"extra\": 1,\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "wrong-rejected",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "rejected order/reason/schema differs"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"z-earlier\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": [\n    {\n      \"expires\": \"2028-01-01\",\n      \"lot\": \"l\",\n      \"qty\": 0,\n      \"sku\": \"s\",\n      \"warehouse\": \"w\"\n    }\n  ]\n}\n",
      "stderr": ""
    }
  },
  {
    "name": "extra-stdout",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "stdout is not exactly one parseable JSON value"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": []\n}\ndone",
      "stderr": ""
    }
  },
  {
    "name": "nonempty-stderr",
    "expected_valid": false,
    "actual_valid": false,
    "errors": [
      "successful valid input must have empty stderr"
    ],
    "raw": {
      "exit_code": 0,
      "stdout": "{\n  \"accepted\": [\n    {\n      \"allocations\": [\n        {\n          \"lot\": \"l\",\n          \"qty\": 1,\n          \"sku\": \"s\",\n          \"warehouse\": \"w\"\n        }\n      ],\n      \"id\": \"z-earlier\"\n    }\n  ],\n  \"rejected\": [\n    {\n      \"id\": \"a-later\",\n      \"reason\": \"insufficient_stock\"\n    }\n  ],\n  \"remaining\": []\n}\n",
      "stderr": "notice\n"
    }
  }
]
```

### CLI exit and freeze check

```json
[
  {
    "label": "pass",
    "exit_code": 0,
    "stdout": "{\"schema\": \"0238-f23-precision-v1\", \"source\": \"/Users/aipalm/.local/share/nx01/0234-live/out/d25-F23-codex-H-r1/snapshot\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"b-equivalent\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"3ea0590fc8bf5c6eeee139285924e0347902c008733336b3c04332d676b7b739\", \"status\": \"PASS\"}\n",
    "stderr": ""
  },
  {
    "label": "fail",
    "exit_code": 1,
    "stdout": "{\"schema\": \"0238-f23-precision-v1\", \"source\": \"/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234/sources/F23\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"successful valid input must exit 0\", \"successful valid input must have empty stderr\", \"stdout is not exactly one parseable JSON value\"], \"raw\": {\"exit_code\": 1, \"stdout\": \"\", \"stderr\": \"Unknown command: fulfill-wave\\nUsage: bench-cli <command> [options]\\n\\nCommands:\\n  hello [--name NAME]        Print a greeting (default name: \\\"world\\\")\\n  version                    Print the CLI version from package.json\\n  --help, -h                 Show this help\\n\\nExamples:\\n  bench-cli hello\\n  bench-cli hello --name alice\\n  bench-cli version\\n\"}}, {\"id\": \"offset-equivalence\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"successful valid input must exit 0\", \"successful valid input must have empty stderr\", \"stdout is not exactly one parseable JSON value\"], \"raw\": {\"exit_code\": 1, \"stdout\": \"\", \"stderr\": \"Unknown command: fulfill-wave\\nUsage: bench-cli <command> [options]\\n\\nCommands:\\n  hello [--name NAME]        Print a greeting (default name: \\\"world\\\")\\n  version                    Print the CLI version from package.json\\n  --help, -h                 Show this help\\n\\nExamples:\\n  bench-cli hello\\n  bench-cli hello --name alice\\n  bench-cli version\\n\"}}], \"cli_sha256\": \"b8f5c3c9015c8c8491430b4be3001c03d123008518cb0c25a4ecdec8fbaa640b\", \"status\": \"FAIL\"}\n",
    "stderr": ""
  },
  {
    "label": "stop",
    "exit_code": 2,
    "stdout": "{\"schema\": \"0238-f23-precision-v1\", \"source\": \"/nonexistent/0238-witness-control\", \"rows\": [], \"status\": \"STOP\", \"error\": \"snapshot has no bin/cli.js\"}\n",
    "stderr": ""
  }
]
```

Frozen witness SHA-256: `8face9ace542d944889bfff8802b352de0a3063d85ae0a8f9ccdbe4133f7f3e2`. This matches the pre-run witness hash above. Host Node v25.4.0 / Python 3.14.7; Docker/pinned-image validation was not performed in this audit. Future runtime/admission must preserve the two historical oracle rows and add these supplement rows explicitly, seal this witness, and retain its raw results. Exit 2 denotes apparatus STOP, not a product FAIL.

## Pinned image validation: prediction BEFORE execution

Recorded 2026-10-10T03:52:19.646907+00:00. The same frozen witness will run in image `sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`, with Docker `--init --network none --read-only`, read-only input mounts and disposable writable tmpfs. No model process or model network call is involved. Predictions: starter fails both supplement and original rows; historical B/P fail both supplement rows but pass both original rows; H passes all four; historical good/good-zero-rows pass submillisecond-order and fail offset-equivalence while passing both original rows; both exact-time alternatives pass all four. All prediction outcomes must be retained, including a mismatch or infrastructure failure.

The two alternatives are now retained research-only overlays, reconstructed by the exact helper/replacement above. Apply each over the unchanged 0234 F23 source when building a control. They must never enter participant mounts or prompts. The zero-row overlay preserves the historical zero-row variant's test-file coverage; these are oracle controls, not newly asserted complete end-to-end products.

| Retained alternative CLI | SHA-256 |
| --- | --- |
| autoresearch/experiments/0238/calibration/F23/exact-time/bin/cli.js | `6eeb61f0d6b68ceed60eed83a03c1844609a8ea4feee67e5af677a41444e8115` |
| autoresearch/experiments/0238/calibration/F23/exact-time-zero-rows/bin/cli.js | `3a335feb5326adfebfcdecf9775d7d4694f600440b3033333d585705e6f4c015` |

### Pinned image raw execution AFTER run

```json
{
  "argv": [
    "docker",
    "run",
    "--name",
    "devlyn-0238-f23-calibration-68eae547b1e0",
    "--rm",
    "--init",
    "--network",
    "none",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--pids-limit",
    "256",
    "--memory",
    "4g",
    "--cpus",
    "2",
    "--tmpfs",
    "/tmp:rw,nosuid,exec,size=536870912",
    "--env",
    "HOME=/tmp",
    "--env",
    "TMPDIR=/tmp",
    "--env",
    "PYTHONDONTWRITEBYTECODE=1",
    "--mount",
    "type=bind,src=/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0234,dst=/research/0234,readonly",
    "--mount",
    "type=bind,src=/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0238/f23_precision.py,dst=/witness/f23_precision.py,readonly",
    "--mount",
    "type=bind,src=/Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0238/calibration,dst=/controls,readonly",
    "--mount",
    "type=bind,src=/Users/aipalm/.local/share/nx01/0234-live/out/d24-F23-codex-B-r1/snapshot,dst=/history/B,readonly",
    "--mount",
    "type=bind,src=/Users/aipalm/.local/share/nx01/0234-live/out/d25-F23-codex-H-r1/snapshot,dst=/history/H,readonly",
    "--mount",
    "type=bind,src=/Users/aipalm/.local/share/nx01/0234-live/out/d26-F23-codex-P-r1/snapshot,dst=/history/P,readonly",
    "-i",
    "-w",
    "/tmp",
    "sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998",
    "python3",
    "-"
  ],
  "started_at": "2026-10-10T03:53:25.394049+00:00",
  "ended_at": "2026-10-10T03:53:26.602967+00:00",
  "exit_code": 0,
  "stdout": "{\"witness_sha256\": \"8face9ace542d944889bfff8802b352de0a3063d85ae0a8f9ccdbe4133f7f3e2\", \"python\": \"3.12.14\", \"node\": \"v22.23.2\", \"products\": [{\"label\": \"starter-no-op\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/research/0234/sources/F23\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"successful valid input must exit 0\", \"successful valid input must have empty stderr\", \"stdout is not exactly one parseable JSON value\"], \"raw\": {\"exit_code\": 1, \"stdout\": \"\", \"stderr\": \"Unknown command: fulfill-wave\\nUsage: bench-cli <command> [options]\\n\\nCommands:\\n  hello [--name NAME]        Print a greeting (default name: \\\"world\\\")\\n  version                    Print the CLI version from package.json\\n  --help, -h                 Show this help\\n\\nExamples:\\n  bench-cli hello\\n  bench-cli hello --name alice\\n  bench-cli version\\n\"}}, {\"id\": \"offset-equivalence\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"successful valid input must exit 0\", \"successful valid input must have empty stderr\", \"stdout is not exactly one parseable JSON value\"], \"raw\": {\"exit_code\": 1, \"stdout\": \"\", \"stderr\": \"Unknown command: fulfill-wave\\nUsage: bench-cli <command> [options]\\n\\nCommands:\\n  hello [--name NAME]        Print a greeting (default name: \\\"world\\\")\\n  version                    Print the CLI version from package.json\\n  --help, -h                 Show this help\\n\\nExamples:\\n  bench-cli hello\\n  bench-cli hello --name alice\\n  bench-cli version\\n\"}}], \"cli_sha256\": \"b8f5c3c9015c8c8491430b4be3001c03d123008518cb0c25a4ecdec8fbaa640b\", \"status\": \"FAIL\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 1, \"stdout\": \"\", \"stderr\": \"Error: non-JSON fulfill-wave:  Unknown command: fulfill-wave\\nUsage: bench-cli <command> [options]\\n\\nCommands:\\n  hello [--name NAME]        Print a greeting (default name: \\\"world\\\")\\n  version                    Print the CLI version from package.json\\n  --help, -h                 Show this help\\n\\nExamples:\\n  bench-cli hello\\n  bench-cli hello --name alice\\n  bench-cli version\\n\\n    at run (/research/0234/fixture_oracle.js:14:17)\\n    at f23 (/research/0234/fixture_oracle.js:137:18)\\n    at module.exports (/research/0234/fixture_oracle.js:148:30)\\n    at main (/research/0234/oracle.js:114:41)\\n    at Object.<anonymous> (/research/0234/oracle.js:158:1)\\n    at Module._compile (node:internal/modules/cjs/loader:1781:14)\\n    at Object..js (node:internal/modules/cjs/loader:1913:10)\\n    at Module.load (node:internal/modules/cjs/loader:1505:32)\\n    at Function._load (node:internal/modules/cjs/loader:1309:12)\\n    at wrapModuleLoad (node:internal/modules/cjs/loader:254:19)\\n\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 1, \"stdout\": \"\", \"stderr\": \"Error: non-JSON fulfill-wave:  Unknown command: fulfill-wave\\nUsage: bench-cli <command> [options]\\n\\nCommands:\\n  hello [--name NAME]        Print a greeting (default name: \\\"world\\\")\\n  version                    Print the CLI version from package.json\\n  --help, -h                 Show this help\\n\\nExamples:\\n  bench-cli hello\\n  bench-cli hello --name alice\\n  bench-cli version\\n\\n    at run (/research/0234/fixture_oracle.js:14:17)\\n    at f23 (/research/0234/fixture_oracle.js:137:18)\\n    at module.exports (/research/0234/fixture_oracle.js:148:30)\\n    at main (/research/0234/oracle.js:114:41)\\n    at Object.<anonymous> (/research/0234/oracle.js:158:1)\\n    at Module._compile (node:internal/modules/cjs/loader:1781:14)\\n    at Object..js (node:internal/modules/cjs/loader:1913:10)\\n    at Module.load (node:internal/modules/cjs/loader:1505:32)\\n    at Function._load (node:internal/modules/cjs/loader:1309:12)\\n    at wrapModuleLoad (node:internal/modules/cjs/loader:254:19)\\n\"}]}, {\"label\": \"B\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/history/B\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"accepted order/allocation schema or stock allocation differs\", \"rejected order/reason/schema differs\"], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"accepted order/allocation schema or stock allocation differs\", \"rejected order/reason/schema differs\"], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"b-equivalent\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"394770f5b178a69378f34dbd59eb7b44462346217d1ff88910263330d19b556d\", \"status\": \"FAIL\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}, {\"label\": \"H\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/history/H\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"b-equivalent\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"3ea0590fc8bf5c6eeee139285924e0347902c008733336b3c04332d676b7b739\", \"status\": \"PASS\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}, {\"label\": \"P\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/history/P\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"accepted order/allocation schema or stock allocation differs\", \"rejected order/reason/schema differs\"], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"accepted order/allocation schema or stock allocation differs\", \"rejected order/reason/schema differs\"], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"b-equivalent\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"9ebf02f5864dec547ffa67b5275c66cd450c7e80bf75e5335204bfd7367bba32\", \"status\": \"FAIL\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}, {\"label\": \"historical-good\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/tmp/0238-image-controls-roaafvez/historical-good\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"accepted order/allocation schema or stock allocation differs\", \"rejected order/reason/schema differs\"], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"a-later\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"b-equivalent\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"38a097b6e764435854b513e3982fed3d57b9b347aada024206fb91db6d03bcd5\", \"status\": \"FAIL\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}, {\"label\": \"historical-good-zero-rows\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/tmp/0238-image-controls-roaafvez/historical-good-zero-rows\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"FAIL\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [\"accepted order/allocation schema or stock allocation differs\", \"rejected order/reason/schema differs\"], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"a-later\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"b-equivalent\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"35384d618fe498226e17dd8b49751b6c320075b5b462bee9470c4865318abbfe\", \"status\": \"FAIL\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}, {\"label\": \"alternative-exact-good\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/tmp/0238-image-controls-roaafvez/alternative-exact-good\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"b-equivalent\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"6eeb61f0d6b68ceed60eed83a03c1844609a8ea4feee67e5af677a41444e8115\", \"status\": \"PASS\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}, {\"label\": \"alternative-exact-good-zero-rows\", \"supplement\": {\"schema\": \"0238-f23-precision-v1\", \"source\": \"/tmp/0238-image-controls-roaafvez/alternative-exact-good-zero-rows\", \"rows\": [{\"id\": \"submillisecond-order\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 1, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}, {\"id\": \"offset-equivalence\", \"status\": \"PASS\", \"input\": {\"warehouses\": [{\"id\": \"w\", \"distance\": 0, \"lots\": [{\"sku\": \"s\", \"lot\": \"l\", \"qty\": 2, \"expires\": \"2028-01-01\"}]}], \"orders\": [{\"id\": \"a-later\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0002Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"z-earlier\", \"priority\": 1, \"submitted_at\": \"2027-01-01T00:00:00.0001Z\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}, {\"id\": \"b-equivalent\", \"priority\": 1, \"submitted_at\": \"2027-01-01T01:00:00.000100+01:00\", \"lines\": [{\"sku\": \"s\", \"qty\": 1, \"single_warehouse\": false}]}]}, \"expected\": {\"accepted\": [{\"id\": \"b-equivalent\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}, {\"id\": \"z-earlier\", \"allocations\": [{\"sku\": \"s\", \"warehouse\": \"w\", \"lot\": \"l\", \"qty\": 1}]}], \"rejected\": [{\"id\": \"a-later\", \"reason\": \"insufficient_stock\"}]}, \"errors\": [], \"raw\": {\"exit_code\": 0, \"stdout\": \"{\\\"accepted\\\":[{\\\"id\\\":\\\"b-equivalent\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]},{\\\"id\\\":\\\"z-earlier\\\",\\\"allocations\\\":[{\\\"sku\\\":\\\"s\\\",\\\"warehouse\\\":\\\"w\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":1}]}],\\\"rejected\\\":[{\\\"id\\\":\\\"a-later\\\",\\\"reason\\\":\\\"insufficient_stock\\\"}],\\\"remaining\\\":[{\\\"warehouse\\\":\\\"w\\\",\\\"sku\\\":\\\"s\\\",\\\"lot\\\":\\\"l\\\",\\\"qty\\\":0,\\\"expires\\\":\\\"2028-01-01\\\"}]}\\n\", \"stderr\": \"\"}}], \"cli_sha256\": \"3a335feb5326adfebfcdecf9775d7d4694f600440b3033333d585705e6f4c015\", \"status\": \"PASS\"}, \"original_oracle\": [{\"row\": \"priority-rollback\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"priority-rollback\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}, {\"row\": \"single-warehouse-fefo\", \"exit_code\": 0, \"stdout\": \"{\\\"row\\\":\\\"single-warehouse-fefo\\\",\\\"pass\\\":true}\\n\", \"stderr\": \"\"}]}]}\n",
  "stderr": "",
  "teardown": {
    "inspect_exit": 1,
    "inspect_stderr": "Error: No such object: devlyn-0238-f23-calibration-68eae547b1e0\n",
    "removed": false
  }
}
```

Pinned environment: Node v22.23.2 / Python 3.12.14. Container returned 0; its own named-container inspection confirmed absence after `--rm` teardown. No forced removal was needed: True.

| Product | Supplement rows | Original oracle exits |
| --- | --- | --- |
| starter-no-op | submillisecond-order: FAIL, offset-equivalence: FAIL | 1, 1 |
| B | submillisecond-order: FAIL, offset-equivalence: FAIL | 0, 0 |
| H | submillisecond-order: PASS, offset-equivalence: PASS | 0, 0 |
| P | submillisecond-order: FAIL, offset-equivalence: FAIL | 0, 0 |
| historical-good | submillisecond-order: PASS, offset-equivalence: FAIL | 0, 0 |
| historical-good-zero-rows | submillisecond-order: PASS, offset-equivalence: FAIL | 0, 0 |
| alternative-exact-good | submillisecond-order: PASS, offset-equivalence: PASS | 0, 0 |
| alternative-exact-good-zero-rows | submillisecond-order: PASS, offset-equivalence: PASS | 0, 0 |

All pinned-image results match the prospectively recorded expectations and host results. This completes the previously outstanding pinned-image calibration; the earlier host-only limitation describes the first validation stage. The witness stayed byte-identical. Both retained alternative CLI hashes match the disposable alternatives recorded in the original host raw results. Historical B/H/P and reference verdicts were not relabeled; only the new supplement results are reported. No model invocation occurred.
