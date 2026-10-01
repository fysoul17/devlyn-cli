# P2 mechanism record

- **Family:** ordering/precedence.
- **Mandatory clause:** “When both an exact tuple key and a name-only key match, select the tuple entry by key presence, including when its value is `None` or zero.”
- **Trigger:** a mapping contains the parsed `(tzname, tzoffset)` pair with value `None` and the parsed name with a non-`None` timezone value.
- **Causal code path:** `_build_tzaware` correctly selects mapping resolution, but `_build_tzinfo` uses `.get(pair)` followed by `if tzdata is None` to decide whether to try the name. It therefore conflates a present `None` entry with an absent key.
- **Incorrect behavior:** the less specific name entry wins and an aware datetime is returned, despite the exact pair's explicit naive result.
- **Executable witness:** `P2-W` in `hidden/oracle.md`, using `('BRST', -10800): None` and `'BRST': NAME_ZONE` for the same parsed input.
- **Near-miss exclusions:** zero-valued pair handling; tokenization or offset sign errors; callback invocation order; missing-key fallback; fold/name assignment; failure to honor `ignoretz`. The twin retains these behaviors. This defect requires a present `None` pair and a conflicting non-`None` name entry.
