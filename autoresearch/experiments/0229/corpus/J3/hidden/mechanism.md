# J3 mechanism record

- **Family:** failure-state preservation.
- **Mandatory clause:** "After a rejected batch, enabled states and the function sequences returned by default and alternate chains must be equivalent to their pre-call values across `core.ruler`, `block.ruler`, `inline.ruler`, and `inline.ruler2`, including when chains were already compiled."
- **Trigger:** A strict invalid batch includes both a name registered in the secondary inline ruler and an unknown name, with the requested operation changing that secondary registration's state.
- **Causal code path:** The `MarkdownIt.enable` and `MarkdownIt.disable` batch paths in `src/markdownit.ts` call `inline.ruler2.enable` or `.disable` before validating the batch, while committing the other three rulers only after validation. An unknown name throws between those stages.
- **Incorrect behavior:** The rejected batch leaves a changed secondary-inline rule state. In the witness, the primary emphasis rule remains enabled but its postprocessor is disabled, so subsequent rendering loses emphasis.
- **Executable witness:** J3-O3 in `oracle.md`.
- **Near-miss exclusions:** Valid shared-name batches, permissive batches, error text, and failed batches naming only primary-parser rules work. Cache-object identity is not promised; function sequences and enabled state are. Direct Ruler calls, preset configuration, or exceptions from user-overridden methods are outside this request. Omitting the secondary ruler entirely from successful operations would be a different defect. An objection only to the secondary inline ruler's call order relative to the primary rulers in a successful batch, with an unchanged end state, is not this defect.
