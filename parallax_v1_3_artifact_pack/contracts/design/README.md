# Design Contract Notes

`design_tokens.json` is the canonical token source for Figma and code.

Token consumers should preserve semantic roles. Do not rename `active`, `wall`, `detour`, `interruption`, `waiting`, `start_latency`, or `privacy` roles into generic chart colors. These roles map directly to temporal semantics and accessibility requirements.
