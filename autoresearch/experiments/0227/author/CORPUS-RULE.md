## Corpus

**Repository rule:**
- two real public repositories, one Python and one JavaScript/TypeScript, each pinned to a SHA, with a license that allows local modification; at that SHA the repository's own test suite passes on the host with standard tools, and no agent instruction file exists anywhere in the tree (`CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/`, `.agents/`, `.codex/`);
- never used in earlier evaluations: this excludes click, commander, django, pytest, tkem/cachetools, hapijs/joi and every other repository the evaluators have used;
- selection: the author lists eligible candidates (at least two per language) with reasons before reading any code in depth; root clones each at its default-branch head and checks the rule without any model; per language, the eligible repository with the lowest sha256 of its canonical clone URL is chosen.

**Requests:** four per repository, eight in total, one per interaction family in each repository: boundary semantics, ordering/precedence, failure-state preservation, cross-field consistency. Each is a realistic change integrated with the repository's actual behavior, outside lifecycle/installer work.

**Per request:**
- the request text (the reviewers' `spec.md`) and its public checks (`spec.expected.json`);
- a hidden oracle;
- a reference patch, believed correct;
- one defective twin: the reference with exactly one target mechanism broken, changing exactly the reference's set of files (one target, because the reviewers stop at the first blocking finding). It passes the public checks and fails its designated hidden witness. The mandatory clause it violates is stated in the request;
- a mechanism record: mandatory clause, trigger, causal code path, incorrect behavior, executable witness, near-miss exclusions. File/line supports a match; it is not the identity.

**Execution conditions:** a request states an execution condition (such as a runtime version or an environment variable) only as a declared verification command whose output evidences it — for example a version check with `stdout_contains`, or an environment assignment inside the command. A condition nothing can evidence is not stated.

**Authoring and blinding:**
- The author is a fresh, empty-context session in a workspace holding only this corpus section, the authoring instructions and the pinned clones, with web search and connectors disabled. It never sees the code or prompts under evaluation, earlier evaluation results, or any reviewer output. It selects the repositories and writes the requests, public checks, oracle specifications and mechanism records.
- A separate implementer writes the references, twins and hidden oracles from those specifications in a writable copy, under the same isolation.
- Calibration is model-free and run by root: each reference passes the public checks and every hidden oracle row; each twin passes the public checks, fails exactly its designated witness and changes exactly the reference's files. A fresh reviewer checks calibration and mechanism records before the freeze.
- A request that fails calibration is repaired or replaced under the same rule before the freeze.
