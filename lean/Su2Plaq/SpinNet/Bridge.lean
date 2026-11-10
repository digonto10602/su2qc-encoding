import Su2Plaq.SpinNet.Circuit
import Su2Plaq.SpinNet.Semantics
import Su2Plaq.SpinNet.Spectrum

/-!
# Su2Plaq.SpinNet.Bridge -- the exact tables equal the M3 tables (M3x step W4, prompts/102 section 2)

The only file of the M3x extension that loads Mathlib (through `Circuit` -> `Counts`).  `Recoupling.lean` proves that the
exported tables `exportedCodes` / `exportedTwoK` are the valid inner codes and `2K` computed from Racah 6j symbols;
`Circuit.lean` proves `walk_table_exact` for `validInnerCodes` / `couplingTable` (copied from Python).  `tables_agree`
says the two pairs of lists are the same, so the 6j-derived `K` is the `K` whose Walsh angle table the circuit realises,
and `Semantics.lean` / `Spectrum.lean` (which use `exportedCodes` / `exportedTwoK`) are statements about the same data.
Heavy computation stays in the Mathlib-free files; this proof is a comparison of two short lists.
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.SpinNet

theorem tables_agree : exportedCodes = validInnerCodes ∧ exportedTwoK = couplingTable := by
  decide

end Su2Plaq.SpinNet
