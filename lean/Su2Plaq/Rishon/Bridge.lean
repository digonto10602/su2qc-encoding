import Su2Plaq.Rishon.Counts
import Su2Plaq.Rishon.HBLink
import Su2Plaq.Rishon.CornerKernel
import Su2Plaq.Rishon.UESemantics

/-!
# Su2Plaq.Rishon.Bridge — ties the Mathlib-free M5x files to the laptop's counts (prompts/202 step W4, METHODS-rishon R9)

`CornerKernel.lean` is Mathlib-free and therefore carries its own copies `fuseR` / `cornerCountR` of the laptop's `fuse` /
`cornerCount` (`Su2Plaq.Structure.Counts`, read-only).  This file is the only M5x file that imports Mathlib (through
`Su2Plaq.Rishon.Counts`): it states that the two corner counts agree on all 16 Boolean end-spin patterns, so that
`corner_kernel_dims` (joint Gauss kernel dimension = `cornerCountR`) is a statement about the laptop's `cornerCount`
used by `patternCount` / `rishonTotal`.  The proof is `decide +kernel` (kernel reduction; standard axioms only).
Importing `HBLink`, `CornerKernel` and `UESemantics` here makes `lake build Su2Plaq` build all four files.
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.Rishon

theorem corner_count_agree : ∀ a b c d : Bool, cornerCountR a b c d = cornerCount a b c d := by
  decide +kernel

end Su2Plaq.Rishon
