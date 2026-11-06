# Task-specification template (instantiated by `TaskSpec.render()`, written by `TaskSpec.write()`)

Sections, in the order of Gu, Kemeny, Yelin, Lukin (arXiv:2610.22367) Extended Data Fig. 1. Every number is filled from the
`TaskSpec` fields, the encoding (`Encoding.describe()`), the builder cost tables (`MACRO_COST`) and, if present,
`compress/lean/structure.json`; nothing is typed here.

1. **Task** - the operator (U_B U_E, U_B or U_E) on the physical states of the encoding, nominal and alternate angle pairs, ancillas clean.
2. **Registers** - `Encoding.describe()`: data and outer registers, codec table, controls the target never changes.
3. **Circuit model** - `BASIS` and `MACROS` with their (CX, T, rotations) costs, `Builder.alloc/free/mcx`, qubit cap.
4. **Correctness** - combined error bound (block error + leak amplitude + pruning bound) <= `tol_err`, Gauss residual <= `tol_gauss`, identical skeleton at the alternate angles, evaluation budget; the evaluator is ground truth.
5. **Cost** - lexicographic key (CX, T_eps, depth_CT, qubits), pygridsynth at `eps`, MAP-Elites cell definition.
6. **Proved structure (Lean)** - machine-checked facts (prompts/006), "pending" until `compress/lean/structure.json` exists.
7. **Tools** - `run_candidate` and `oracle` commands, the program contract (`SUMMARY:`, `DISCOVERY:` lines, `FAMILY`, `PARENT`, `build(spec)`).

Instances: `compress/specs/<encoding>-<kind>.md`.
