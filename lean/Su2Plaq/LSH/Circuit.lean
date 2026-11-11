import Su2Plaq.SpinNet.Circuit

/-!
# Su2Plaq.LSH.Circuit — kernel-checked structure of the LSH general circuit (M7, prompts/400 §1.5, §4)

Transcoder + spin-network walk on bit patterns (`Nat`, Toffoli semantics for `rccx`).  Wires: data `0..11`
(`'in'` site `c` at `3c..3c+2 = l_pn, l_nv, l_vp`), ancillas `12..18 = (A, B, F, P, Q, G1, G2)`.

* `transcode_into_spinnet`, `transcode_injective`, `transcode_w`: the transcoder maps the 47 LSH inner codes one-to-one
  onto the 47 spin-network inner codes and leaves `w_c = j_p xor j_n` on the third wire of every site.
* `coupling_matches_spinnet`: the LSH coupling table equals the spin-network one under that map.
* `pre_maps_partner_to_x`: transcoder + CX frame turn the plaquette move into `X` on the walk target wire 0.
* `walk_table_exact`: the integer Walsh table reproduces `2 · (2 K)` on all 47 codes; `ancillas_clean`: flags are uncomputed.

The tables and circuit segments between the generated markers are written by
`su2plaq.lsh.lean_export.write_lean_tables` from the Python objects; never edit them by hand.
`tests/unit/test_lsh_lean_export_unit.py` fails if the block drifts from `walk.skeleton(0)`.
Definitions are those of the planner prototype `scratch/planner/lean/LSHCircuit.lean`.
-/
set_option maxRecDepth 100000
set_option maxHeartbeats 0

namespace Su2Plaq.LSH
open Su2Plaq.SpinNet (Op bt run step)

-- BEGIN generated (su2plaq.lsh.lean_export.write_lean_tables; do not edit by hand)
def lshInnerCodes : List Nat := [0, 34, 266, 272, 306, 585, 590, 596, 625, 630, 644, 673, 678, 905, 910, 916, 945, 950, 1028, 1057, 1062, 1289, 1294, 1300, 1329, 1334, 2122, 2128, 2162, 2176, 2210, 2442, 2448, 2482, 3145, 3150, 3156, 3185, 3190, 3204, 3233, 3238, 3465, 3470, 3476, 3505, 3510]
def lshCoupling : List Int := [-4, 2, 2, 2, 0, -4, 0, 2, 0, 0, 2, 2, 0, 0, 0, 0, 0, 0, 2, 2, 0, 2, 0, -1, 0, 0, 2, 2, 0, 2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
def lshPartner : List Nat := [585, 596, 644, 673, 306, 0, 590, 34, 625, 630, 266, 272, 678, 905, 910, 916, 945, 950, 2122, 2128, 1062, 2176, 1294, 2210, 1329, 1334, 1028, 1057, 2162, 1289, 1300, 2442, 2448, 2482, 3145, 3150, 3156, 3185, 3190, 3204, 3233, 3238, 3465, 3470, 3476, 3505, 3510]
def lshAngles : List Int := [-7, -2, 6, 3]
def transOps : List Op := [.cx 1 2, .cx 1 0, .ccx 2 0 1, .cx 4 5, .cx 4 3, .ccx 5 3 4, .cx 7 8, .cx 7 6, .ccx 8 6 7, .cx 10 11, .cx 10 9, .ccx 11 9 10]
def frameOps : List Op := [.cx 3 9, .cx 0 3, .cx 0 6]
def flagOps : List Op := [.x 1, .x 4, .x 7, .x 10, .ccx 1 4 12, .ccx 7 10 13, .ccx 12 13 14, .x 6, .x 9, .ccx 6 9 15, .ccx 14 15 16, .x 3, .ccx 16 3 17, .x 3, .ccx 16 3 18]
def walkOps : List Op := [.rz 0, .cx 14 0, .rz 0, .cx 14 0, .cx 17 0, .rz 0, .cx 17 0, .cx 18 0, .rz 0, .cx 18 0]
-- END generated

/-- the transcoder on a 12-bit inner code (Toffoli semantics for rccx) -/
def transcode (x : Nat) : Nat := (run x transOps).1
/-- spin-network data code read off the transcoded register: links at wires 0,3,6,9, corner bits at 1,4,7,10 -/
def toSpinNet (y : Nat) : Nat :=
  bt y 0 + 2 * bt y 3 + 4 * bt y 6 + 8 * bt y 9 + 16 * bt y 1 + 32 * bt y 4 + 64 * bt y 7 + 128 * bt y 10
/-- w wires 2,5,8,11 after transcoding -/
def wBits (y : Nat) : List Nat := [bt y 2, bt y 5, bt y 8, bt y 11]
def parities (y : Nat) : List Nat :=
  [(bt y 9 + bt y 0) % 2, (bt y 0 + bt y 3) % 2, (bt y 3 + bt y 6) % 2, (bt y 6 + bt y 9) % 2]

theorem table_lengths : lshInnerCodes.length = 47 ∧ lshCoupling.length = 47 ∧ lshPartner.length = 47 := by decide

/-- the transcoder maps the 47 LSH inner codes one-to-one onto the 47 spin-network inner codes -/
theorem transcode_into_spinnet : ∀ i, i < 47 →
    Su2Plaq.SpinNet.validInnerCodes.contains (toSpinNet (transcode (lshInnerCodes.getD i 0))) = true := by decide
theorem transcode_injective : (lshInnerCodes.map (fun x => toSpinNet (transcode x))).Nodup := by decide
/-- the third wire of every site holds w_c = j_p xor j_n (no information beyond the spin-network code) -/
theorem transcode_w : ∀ i, i < 47 → wBits (transcode (lshInnerCodes.getD i 0)) = parities (transcode (lshInnerCodes.getD i 0)) := by decide
/-- the LSH coupling table equals the spin-network one under the transcoder -/
theorem coupling_matches_spinnet : ∀ i, i < 47 →
    lshCoupling.getD i 0 =
      Su2Plaq.SpinNet.couplingTable.getD
        (Su2Plaq.SpinNet.validInnerCodes.idxOf (toSpinNet (transcode (lshInnerCodes.getD i 0)))) 0 := by decide

/-- transcoder followed by the CX frame -/
def pre (x : Nat) : Nat := (run x (transOps ++ frameOps)).1
/-- bright pairs: transcoder + frame turn the plaquette move (code -> partner) into X on the target wire 0 -/
theorem pre_maps_partner_to_x : ∀ i, i < 47 → lshCoupling.getD i 0 ≠ 0 →
    pre (lshPartner.getD i 0) = pre (lshInnerCodes.getD i 0) ^^^ 1 := by decide

def start (x : Nat) : Nat := (pre x >>> 1) <<< 1
def slotBits (x : Nat) : List Nat := (run (start x) (flagOps ++ walkOps)).2
def walkPhase (x : Nat) : Int := (List.zipWith (fun b a => if b = 0 then a else -a) (slotBits x) lshAngles).sum
theorem walk_slots_match : ∀ i, i < 47 → (slotBits (lshInnerCodes.getD i 0)).length = lshAngles.length := by decide
theorem walk_table_exact : ∀ i, i < 47 → walkPhase (lshInnerCodes.getD i 0) = 2 * lshCoupling.getD i 0 := by decide
/-- flags are uncomputed and the data wires other than the target are unchanged by flags + walk -/
theorem ancillas_clean : ∀ i, i < 47 →
    (run (run (start (lshInnerCodes.getD i 0)) (flagOps ++ walkOps)).1 flagOps.reverse).1 = start (lshInnerCodes.getD i 0) := by decide

end Su2Plaq.LSH
