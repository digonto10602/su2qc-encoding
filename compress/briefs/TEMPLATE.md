# Brief template (instantiated by `su2plaq.compress.brief.make_brief`, `compress/briefs/<encoding>/round-rrr-<family>.md`)

A brief contains paths, not pasted content:

1. **Task line** - "Rewrite the parent to improve the key; return the complete program".
2. **Pointers** - task specification, Proved structure (Lean) facts (`compress/lean/structure.json`), the `run_candidate --trial` / `--full` and `oracle` commands.
3. **Parent** - program path, entry id and sha256, feedback JSON (`results/compress/<encoding>/feedback/<id>.json`), cost, summary. Round 1 and the `seed` family have no parent.
4. **Archive alternatives** - up to 3 other elites with costs (every third round the global best is among them: migration).
5. **Last 5 attempts** of the family (id, valid / reason, key, summary).
6. **DISCOVERY notes** of all programs, last 30 lines at most.
7. **Output** - one new program `compress/programs/<encoding>/<family>/NNN-<slug>.py` (next free number), scratch only under `scratch/proposer/`.
