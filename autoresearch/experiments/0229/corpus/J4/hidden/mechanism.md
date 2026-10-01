# J4 mechanism record

- **Family:** cross-field consistency.
- **Mandatory clause:** "The metadata and `map` of a definition token must describe the same source occurrence, including when another definition with the same normalized label, or a pre-populated `env.references` entry, determines link resolution." The same defect also violates R2 ("parsed from that definition"); a finding citing R2 for the shadowed definition's payload source identifies this same mechanism.
- **Trigger:** A successfully parsed reference definition has a normalized label already present in the lookup environment with different destination/title values.
- **Causal code path:** The reference block rule parses local values, preserves the first lookup entry, then emits the occurrence token. The twin fills the new metadata payload from the lookup entry instead of the locally parsed occurrence.
- **Incorrect behavior:** The second definition token has the source map of the second definition but the destination and title of the first. Lookup and rendered links remain correct, hiding the inconsistency from rendering fixtures.
- **Executable witness:** J4-O3 in `oracle.md`.
- **Near-miss exclusions:** First-definition-wins link resolution is required. Unique definitions, title decoding and fallback, map calculation, stripping, and null-prototype snapshot allocation all work in this twin. Aliasing metadata to the lookup entry, modifying inline link/image metadata, or changing source maps would be separate defects. Raw destination spelling is not required; metadata uses normalized values.
