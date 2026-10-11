# 0249 final registration review v1

## Prospective verification

Recorded 2026-10-10T23:42:45.071468+00:00 before mechanical probes. Prediction: the fixed schedule has 10/10/8 unique slots with repeated B/S and descriptive A only; both engine and separate hard-domain gates, zero-success nonadvancement, all-attempt cost accounting and STOP/no-retry rules agree with reviewed v2. Current staged imports, fixture manifests, matched current 4.2.5 packages and original S bytes will match their recorded SHA-256s. Final bindings and combined evaluator calibration are pending and will be read before a verdict. No native/auth/container calls or test/evaluator reruns are permitted in this review.

## Initial reviewed input hashes

```json
{
  "autoresearch/experiments/0249/registration-v1.md": "19a5bdadf1ce305f6f53927c08254433150682c94113bc4955795a4179f37f21",
  "autoresearch/experiments/0249/schedule-v1.json": "df5bb783f7810b9d36f2dd32b1b3e7bdd3448d1b60c7defdfecdcf013f223043",
  "autoresearch/experiments/0249/registration-proposal-v2.md": "cd4652e7ff166bb8c03e81d41654733b528388558c5fd67afa812f006133fc4c",
  "autoresearch/experiments/0249/results/design-review-v1.md": "655cacce07328f65410dc512fc387d1c68d034e24f56306d5cdf9c14df6496ff",
  "autoresearch/experiments/0249/results/stage-report-v1.json": "0f4cc14ce11c610d0e3d74da47f0df168ca01daa59d819c268be673445d2f26d",
  "autoresearch/experiments/0249/results/package-integrity-v1.json": "5fb278d7ae3e7d3fbd3c6a3b8f9307d59b40481a672ce8dfd77d29ee19fe839d",
  "autoresearch/experiments/0249/fixtures/fixture-manifest-v2.json": "d246a3212afb190b4a3dc608fd3e6797ebe571c5362bf91da970088ac83f895a",
  "autoresearch/experiments/0249/results/runner-review-v1.md": "69fff839af2ff09cc5081ae29c44d574f98b8b252d9ca897e821d7fb95c236cf",
  "autoresearch/experiments/0249/results/fixture-review-v1.md": "62d8ececf98f9678fa9b71310fb86af371e2af4afe21e83fecfc4b88b050320a",
  "autoresearch/experiments/0249/results/fixture-review-v2.md": "216c0e153f468d87e9d86ff1976aba9754ac59f86a476c6a60ae832b246f2efb",
  "autoresearch/experiments/0249/results/integration-review-v1.md": "277978d3788dc5bf28e8398c240bbccd9f7df87fb6c4c61edfc2de97215ed857",
  "autoresearch/experiments/0249/results/integration-verification-v1/summary.json": "b8c47b93ec400be0a40aa6f70bdb65f52c51ae4a4bb2c4a9cfb762aeb03253b5",
  "autoresearch/experiments/0249/results/evaluator-calibration-v1.json": "7beb51630946b9fa7aecf5fe3619b1be634062cfbf6de988dd44d7bac14a39d0",
  "autoresearch/experiments/0249/results/evaluator-calibration-v2.json": "decf3735aabdbb39fc2a6ac6035ba0dd510adc0e9a5d74c08fad6f779114ee4d"
}
```

## Raw static verification before final bindings

Read-only Python/hash/JSON probe; no subprocess or evaluator call.

```json
{
  "stage_status": "PASS",
  "execution_inputs_count": 119,
  "execution_input_mismatches": [],
  "fixture_file_count": 38,
  "fixture_mismatches": [],
  "existing_task_contract_equal": {
    "E1": true,
    "B5": true
  },
  "runtime_hash_matches_stage": true,
  "tasks_hash_matches_stage": true,
  "control_manifest_matches_stage": true,
  "unique_slots": 28,
  "total_slots": 28,
  "block_counts": {
    "OR1": 10,
    "OR2": 10,
    "CONTROLS": 8
  },
  "arm_engine_task_counts": {
    "('OR1', 'codex', 'B')": 2,
    "('OR1', 'claude', 'S')": 2,
    "('OR1', 'codex', 'A')": 1,
    "('OR1', 'claude', 'B')": 2,
    "('OR1', 'codex', 'S')": 2,
    "('OR1', 'claude', 'A')": 1,
    "('OR2', 'codex', 'S')": 2,
    "('OR2', 'claude', 'B')": 2,
    "('OR2', 'codex', 'A')": 1,
    "('OR2', 'claude', 'S')": 2,
    "('OR2', 'codex', 'B')": 2,
    "('OR2', 'claude', 'A')": 1,
    "('E1', 'claude', 'B')": 1,
    "('E1', 'claude', 'S')": 1,
    "('E1', 'codex', 'S')": 1,
    "('E1', 'codex', 'B')": 1,
    "('B5', 'codex', 'B')": 1,
    "('B5', 'codex', 'S')": 1,
    "('B5', 'claude', 'S')": 1,
    "('B5', 'claude', 'B')": 1
  },
  "schedule_only_ABS": true,
  "package_claims": {
    "status": "PASS",
    "base": "d1f170ed3bd57441b95ea525156e80644543acb1",
    "version": "4.2.5",
    "S_treatment_bytes": "IDENTICAL_TO_0247",
    "B_vs_S_exact_differences": [
      "package/AGENTS.md",
      "package/CLAUDE.md",
      "package/bin/instruction-templates.json",
      "package/config/skills/_shared/pair.md",
      "package/config/skills/_shared/runtime-principles.md"
    ],
    "mode_changes": {
      "B": [],
      "H": [],
      "P": [],
      "S": []
    },
    "selected_native_arms": [
      "A",
      "B",
      "S"
    ],
    "unused_archive_arms": [
      "H",
      "P"
    ]
  },
  "package_recorded_input_mismatches": [],
  "runtime_noncredential_configuration": {
    "boot_catalogs": {
      "claude": {
        "A": {
          "mcp_servers": [],
          "plugins": [
            {
              "name": "cc-plugin-agents-md",
              "path": "builtin",
              "source": "cc-plugin-agents-md@builtin"
            },
            {
              "name": "cc-plugin-plugin-authoring",
              "path": "builtin",
              "source": "cc-plugin-plugin-authoring@builtin"
            },
            {
              "name": "cc-plugin-telemetry",
              "path": "builtin",
              "source": "cc-plugin-telemetry@builtin"
            }
          ],
          "skills": [
            "batch",
            "claude-api",
            "code-review",
            "dataviz",
            "debug",
            "deep-research",
            "design",
            "design-sync",
            "doctor",
            "fewer-permission-prompts",
            "loop",
            "plugin-authoring",
            "run",
            "run-skill-generator",
            "schedule",
            "simplify",
            "update-config",
            "verify",
            "workflow-authoring"
          ]
        },
        "B": {
          "mcp_servers": [],
          "plugins": [
            {
              "name": "cc-plugin-agents-md",
              "path": "builtin",
              "source": "cc-plugin-agents-md@builtin"
            },
            {
              "name": "cc-plugin-plugin-authoring",
              "path": "builtin",
              "source": "cc-plugin-plugin-authoring@builtin"
            },
            {
              "name": "cc-plugin-telemetry",
              "path": "builtin",
              "source": "cc-plugin-telemetry@builtin"
            }
          ],
          "skills": [
            "batch",
            "claude-api",
            "code-review",
            "dataviz",
            "debug",
            "deep-research",
            "design",
            "design-sync",
            "devlyn-engines",
            "devlyn-ideate",
            "doctor",
            "fewer-permission-prompts",
            "loop",
            "plugin-authoring",
            "run",
            "run-skill-generator",
            "schedule",
            "simplify",
            "update-config",
            "verify",
            "workflow-authoring"
          ]
        },
        "S": {
          "mcp_servers": [],
          "plugins": [
            {
              "name": "cc-plugin-agents-md",
              "path": "builtin",
              "source": "cc-plugin-agents-md@builtin"
            },
            {
              "name": "cc-plugin-plugin-authoring",
              "path": "builtin",
              "source": "cc-plugin-plugin-authoring@builtin"
            },
            {
              "name": "cc-plugin-telemetry",
              "path": "builtin",
              "source": "cc-plugin-telemetry@builtin"
            }
          ],
          "skills": [
            "batch",
            "claude-api",
            "code-review",
            "dataviz",
            "debug",
            "deep-research",
            "design",
            "design-sync",
            "devlyn-engines",
            "devlyn-ideate",
            "doctor",
            "fewer-permission-prompts",
            "loop",
            "plugin-authoring",
            "run",
            "run-skill-generator",
            "schedule",
            "simplify",
            "update-config",
            "verify",
            "workflow-authoring"
          ]
        }
      }
    },
    "image": "sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998",
    "phase": "measured"
  },
  "routes": {
    "claude": {
      "owner": {
        "effort": "max",
        "engine": "claude",
        "model": "claude-opus-5-5"
      },
      "peer_routes": {
        "H": {
          "effort": "max",
          "engine": "claude",
          "model": "claude-opus-5-5"
        },
        "P": {
          "child_effort": "high",
          "child_model": "gpt-6-sol",
          "effort": "max",
          "engine": "codex",
          "model": "gpt-6-astra"
        }
      },
      "product_roles": {
        "pair_judge": {
          "effort": "max",
          "engine": "codex",
          "model": "gpt-6-astra"
        },
        "primary_judge": {
          "effort": "max",
          "engine": "claude",
          "model": "claude-opus-5-5"
        },
        "worker": {
          "engine": "claude"
        }
      },
      "reviewer": {
        "effort": "high",
        "engine": "codex",
        "model": "gpt-6-astra"
      }
    },
    "codex": {
      "owner": {
        "child_effort": "high",
        "child_model": "gpt-6-sol",
        "effort": "max",
        "engine": "codex",
        "model": "gpt-6-astra"
      },
      "peer_routes": {
        "H": {
          "child_effort": "high",
          "child_model": "gpt-6-sol",
          "effort": "max",
          "engine": "codex",
          "model": "gpt-6-astra"
        },
        "P": {
          "effort": "max",
          "engine": "claude",
          "model": "claude-opus-5-5"
        }
      },
      "product_roles": {
        "pair_judge": {
          "effort": "max",
          "engine": "claude",
          "model": "claude-opus-5-5"
        },
        "primary_judge": {
          "effort": "max",
          "engine": "codex",
          "model": "gpt-6-astra"
        },
        "worker": {
          "effort": "high",
          "engine": "codex",
          "model": "gpt-6-sol"
        }
      },
      "reviewer": {
        "effort": "high",
        "engine": "claude",
        "model": "claude-opus-5-5"
      }
    }
  },
  "watchdogs": {
    "assessor": 600,
    "evaluator": 600,
    "owner": 5400,
    "review": 600
  }
}
```

## Final binding inputs before verification

```json
{
  "autoresearch/experiments/0249/bindings-v1.json": "5a1cf15b25b16df8fb9e2305efe9e478ec18a75a29d6e862331208407d47ffdb",
  "autoresearch/experiments/0249/results/evaluator-report-v2.json": "f8a830fc485e918a852e289ba9b1152ab581843456bca2a9d4214df352ee2a3c"
}
```

## Raw final static verification

Read-only file/hash/JSON comparison, with no test, evaluator, native or auth invocation.

```json
{
  "binding_sha256": "5a1cf15b25b16df8fb9e2305efe9e478ec18a75a29d6e862331208407d47ffdb",
  "calibration_sha256": "f8a830fc485e918a852e289ba9b1152ab581843456bca2a9d4214df352ee2a3c",
  "input_count": 119,
  "selected_count": 495,
  "input_mismatches": [],
  "selected_mismatches": [],
  "calibration_and_binding_inputs_equal": true,
  "controls": {
    "oracle": {
      "files": 28,
      "exact_match": true
    },
    "packages": {
      "files": 969,
      "exact_match": true
    },
    "public": {
      "files": 64,
      "exact_match": true
    }
  },
  "task_sources": {
    "OR1": {
      "files": 8,
      "exact_match": true
    },
    "OR2": {
      "files": 7,
      "exact_match": true
    },
    "E1": {
      "files": 629,
      "exact_match": true
    },
    "B5": {
      "files": 2,
      "exact_match": true
    }
  },
  "calibration_cases": [
    {
      "task": "OR1",
      "variant": "baseline",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "OR1",
      "variant": "gold",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "OR1",
      "variant": "fault",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "OR2",
      "variant": "baseline",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "OR2",
      "variant": "gold",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "OR2",
      "variant": "fault",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "E1",
      "variant": "baseline",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "STOP_CALIBRATION"
    },
    {
      "task": "E1",
      "variant": "gold",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "B5",
      "variant": "baseline",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    },
    {
      "task": "B5",
      "variant": "gold",
      "hash_matches": true,
      "rows_match": true,
      "public_pass": true,
      "source_unchanged": true,
      "original_driver_status": "PASS"
    }
  ],
  "raw_cases_unique": 10,
  "raw_container_calls": 32,
  "review_report_not_circularly_bound": true,
  "initial_review_hashes_unchanged": true
}
```

## Verdict — REVISE before freeze

**One HIGH binding-completeness finding; no native dispatch is approved by this review.** The design, selected fixtures/packages, accounting and conditional schedule are otherwise acceptable. Preserve this v1 result and close the finding in a narrow v2 binding review; do not rerun adapter tests or evaluator calibration.

### H1: import-time B5/E1 row inventories are outside the frozen binding set

`0233/check.py:49–52` constructs `ROWS` from `0233/tasks.json`, and `0234/check.py:49–52` does the same with `0234/tasks.json`. Later assignment of the current `TASKS` does not rebuild either dictionary. Thus these original JSON files determine B5's five rows and E1's three rows. Neither appears in `bindings-v1.json`'s 119 inputs or 495 selected artifacts. A changed original row inventory could change the scored obligations while every currently bound SHA still passes.

Smallest correction: preserve v1 and bind those two exact original JSON files in a new binding version. The registered root check before/between slots must verify the full selected-artifact set as well as the runner's 119 execution inputs. No change to frozen earlier files, runner, evaluator, task contracts or calibration is needed. This enforces **No workaround**, **No guesswork** and **Production ready**.

Raw observation: reading the union of binding `inputs` and `selected_artifacts` and filtering task inventories found only `/Users/aipalm/.local/share/nx01/0249-live/staged-v1/tasks.json` and the repository's `0249/tasks-v1.json`. Source inspection confirmed the two original import-time ROWS comprehensions. No mutation probe was needed or performed.

### Accepted decision and execution rules

The 10/10/8 fixed schedule has 28 unique slots, two B and two S draws for each engine/hard task, one descriptive A each, and eight E1/B5 controls. Per-engine/per-hard-task success counts and all-attempt whole owner resources are explicit; no task or engine pooling rescues a regression. Positive-success admission requires correctness and all three resources nonregressing plus at least one strict gain. B=0/S>0 remains QUALITY_GAIN / RESOURCE_NOT_COMPARABLE and cannot advance; other zero-denominator cases do not invent ratios or extra draws. Controls preserve correctness per engine/task and use only the two control tasks' aggregate resources separately for each engine.

This closes the earlier design HIGH and aligns prediction/decision. Descriptive A adds neither an admission veto nor a repeated native superiority claim. The bounded shared candidate closes on nonadvancement, with no automatic engine-specific switch, successor or favorable retry (**No overengineering**).

Independent block audit before its gate is appropriate for unchanged apparatus. Native built-in identity/accounting/teardown/usage STOP and root's mechanical/binding check remain mandatory for every cell; a detected STOP ends the active block immediately and receives an audit before closure. Block audit does not authorize ten further runs after a known fault. No overlap with independent owners/reviewers/heavy tests is allowed. Every native child, failed/recovered call and owner recheck remains charged; cached input/thinking counted once. Unknown usage remains unknown with preserved incurred wall/lower bounds, no grading after accounting/identity STOP, and unrun slots stay NOT_RUN. These satisfy **Optimized** without weakening **Production ready**.

### Accepted preparation evidence and its limits

The current 4.2.5 B/S baseline is matched at the reviewed upstream commit plus nine product-file deltas; the integration PASS binds twelve relevant inputs. Bound package verification records four offline B/S-engine installations, 969 payloads/modes, exact prior S trigger/guide, and no extra helper. H/P remain unscheduled format artifacts. Existing E1/B5 contracts exactly match 0237; all 646 registered source-file hashes and 1061 staged control files match. Fixture v2's 38 manifest entries match, M1 is closed, all 22 hard-task obligations retain public contract provenance and finite-scope limitations.

Combined actual-evaluator calibration binds ten unique raw cases and 32 invocations; recorded rows total 82 (57 PASS/25 FAIL), all ten public checks pass and sources remain unchanged. No evaluator was rerun by this reviewer. V1's E1 STOP is retained verbatim: actual frozen JS `assert` throws `Error(row)`, while the driver expected `AssertionError`. Raw E1 baseline has the exact expected `shout`/`name-with-shout` errors at the original oracle assertion stack and the default row PASS. Narrow reconciliation is justified and is not a post-accounting native regrade or favorable reroll. Seven raw cases were reused; only three previously unrun cases were subsequently executed. Recorded teardown is clean; no new container inspection was performed here.

0248 remains closed with Codex S STOP/PARTIAL and unknown whole cost, ungraded downstream source, no F23 retake, and historical failed/stopped costs retained in the bound interpretation. No prior efficacy is reattributed to 4.2.5.

### Follow-up scope acknowledged

After H1 was reported, root independently identified that binding mutable integration-publisher paths would conflict with authorized later product delivery. Root will preserve exact verified product/template bytes and the accepted patch in an immutable baseline snapshot, retain original 4.2.5 path/HEAD provenance, and bind the copies. This is a proposed v2 provenance-lifecycle resolution, not a defect in candidate efficacy or a request to rebuild unchanged archives.

The final immutable freeze and independent freeze/binding audit remain required after review closure. This review performed only source/document reads and hash/JSON comparisons, with no native/auth/container calls, no tests/evaluator reruns, no product edits and no earlier frozen-file mutations. Only this report was written during the registration review.

## Initial inputs after review

2026-10-10T23:45:28.223101+00:00

Changed: []

```json
{
  "autoresearch/experiments/0249/registration-v1.md": "19a5bdadf1ce305f6f53927c08254433150682c94113bc4955795a4179f37f21",
  "autoresearch/experiments/0249/schedule-v1.json": "df5bb783f7810b9d36f2dd32b1b3e7bdd3448d1b60c7defdfecdcf013f223043",
  "autoresearch/experiments/0249/registration-proposal-v2.md": "cd4652e7ff166bb8c03e81d41654733b528388558c5fd67afa812f006133fc4c",
  "autoresearch/experiments/0249/results/design-review-v1.md": "655cacce07328f65410dc512fc387d1c68d034e24f56306d5cdf9c14df6496ff",
  "autoresearch/experiments/0249/results/stage-report-v1.json": "0f4cc14ce11c610d0e3d74da47f0df168ca01daa59d819c268be673445d2f26d",
  "autoresearch/experiments/0249/results/package-integrity-v1.json": "5fb278d7ae3e7d3fbd3c6a3b8f9307d59b40481a672ce8dfd77d29ee19fe839d",
  "autoresearch/experiments/0249/fixtures/fixture-manifest-v2.json": "d246a3212afb190b4a3dc608fd3e6797ebe571c5362bf91da970088ac83f895a",
  "autoresearch/experiments/0249/results/runner-review-v1.md": "69fff839af2ff09cc5081ae29c44d574f98b8b252d9ca897e821d7fb95c236cf",
  "autoresearch/experiments/0249/results/fixture-review-v1.md": "62d8ececf98f9678fa9b71310fb86af371e2af4afe21e83fecfc4b88b050320a",
  "autoresearch/experiments/0249/results/fixture-review-v2.md": "216c0e153f468d87e9d86ff1976aba9754ac59f86a476c6a60ae832b246f2efb",
  "autoresearch/experiments/0249/results/integration-review-v1.md": "277978d3788dc5bf28e8398c240bbccd9f7df87fb6c4c61edfc2de97215ed857",
  "autoresearch/experiments/0249/results/integration-verification-v1/summary.json": "b8c47b93ec400be0a40aa6f70bdb65f52c51ae4a4bb2c4a9cfb762aeb03253b5",
  "autoresearch/experiments/0249/results/evaluator-calibration-v1.json": "7beb51630946b9fa7aecf5fe3619b1be634062cfbf6de988dd44d7bac14a39d0",
  "autoresearch/experiments/0249/results/evaluator-calibration-v2.json": "decf3735aabdbb39fc2a6ac6035ba0dd510adc0e9a5d74c08fad6f779114ee4d"
}
```
