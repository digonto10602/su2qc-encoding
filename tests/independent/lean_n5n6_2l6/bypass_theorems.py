"""Write theorem files for mutated certificates BYPASSING the Python exporter check (monkeypatched in this process only), so that
the pins inside Lean's native_decide are the only defence.  usage: bypass_theorems.py <n5dir> <outdir>"""
import sys, os
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import certify as C
C._exporter_mismatch = lambda p: None
n5, out = sys.argv[1], sys.argv[2]
names = ["ctl_UE_unchanged", "ctl_E1_legit_rescale_base_x2", "A1_fake_computational_basis_states", "B1_swap_contents_of_states_0_1",
         "C2_state50_sign_flipped", "C3_state50_times_i", "D1_UE_blocks_labelled_UB", "D4_UB_blocks_kind_UE", "D8_one_target_coefficient_changed",
         "D7_no_kind", "N6_phase", "N6_state_coeff", "N6_huge_exp_gate", "D11_beta_base_tripled_not_scaled"]
for n in names:
    C.write_theorem_file(os.path.join(n5, n + ".json"), "bypass", os.path.join(out, n + ".lean"))
print("wrote", len(names))
