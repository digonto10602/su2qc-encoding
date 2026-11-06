import Mathlib

/-!
# Su2Plaq.Synthesis — error accumulation for synthesised rotations (docs/METHODS.md §11.1 f)

`‖U_1⋯U_N − V_1⋯V_N‖ ≤ ∑ ‖U_i − V_i‖` for factors of norm `≤ 1` in any normed ring, and the form used by
`prompts/003`: words `W_r = c_r R_r + Δ_r` with `|c_r| = 1`, `‖R_r‖ ≤ 1`, `‖W_r‖ ≤ 1` satisfy
`‖∏ W − (∏ c) ∏ R‖ ≤ ∑ ‖Δ_r‖`.
Adapted from `scratch/planner/lean/P1_telescoping.lean` (the prototype's `synth_bound` was unfinished;
this version is stated over `Fin n` and proved by induction).  Kernel-checked, standard axioms only.
-/
namespace Su2Plaq
section Ring
variable {R : Type*} [NormedRing R] [NormOneClass R]

theorem norm_list_prod_le_one (L : List R) (h : ∀ u ∈ L, ‖u‖ ≤ 1) : ‖L.prod‖ ≤ 1 := by
  induction L with
  | nil => simp
  | cons u us ih =>
    rw [List.prod_cons]
    have hu : ‖u‖ ≤ 1 := h u (List.mem_cons_self ..)
    have hus : ‖us.prod‖ ≤ 1 := ih (fun v hv => h v (List.mem_cons_of_mem _ hv))
    calc ‖u * us.prod‖ ≤ ‖u‖ * ‖us.prod‖ := norm_mul_le _ _
      _ ≤ 1 * 1 := mul_le_mul hu hus (norm_nonneg _) zero_le_one
      _ = 1 := one_mul 1

/-- `‖U_1⋯U_N − V_1⋯V_N‖ ≤ ∑ ‖U_i − V_i‖` when every factor has norm `≤ 1` (e.g. unitaries). -/
theorem prod_sub_prod_le (U V : List R) (hlen : U.length = V.length)
    (hU : ∀ u ∈ U, ‖u‖ ≤ 1) (hV : ∀ v ∈ V, ‖v‖ ≤ 1) :
    ‖U.prod - V.prod‖ ≤ (List.zipWith (fun u v => ‖u - v‖) U V).sum := by
  induction U generalizing V with
  | nil =>
    cases V with
    | nil => simp
    | cons v vs => simp at hlen
  | cons u us ih =>
    cases V with
    | nil => simp at hlen
    | cons v vs =>
      simp only [List.prod_cons, List.zipWith_cons_cons, List.sum_cons]
      have hlen' : us.length = vs.length := by simpa using hlen
      have hus : ‖us.prod‖ ≤ 1 := norm_list_prod_le_one us (fun w hw => hU w (List.mem_cons_of_mem _ hw))
      have hv : ‖v‖ ≤ 1 := hV v (List.mem_cons_self ..)
      have ih' := ih vs hlen' (fun w hw => hU w (List.mem_cons_of_mem _ hw)) (fun w hw => hV w (List.mem_cons_of_mem _ hw))
      have hsplit : u * us.prod - v * vs.prod = (u - v) * us.prod + v * (us.prod - vs.prod) := by noncomm_ring
      calc ‖u * us.prod - v * vs.prod‖ = ‖(u - v) * us.prod + v * (us.prod - vs.prod)‖ := by rw [hsplit]
        _ ≤ ‖(u - v) * us.prod‖ + ‖v * (us.prod - vs.prod)‖ := norm_add_le _ _
        _ ≤ ‖u - v‖ * ‖us.prod‖ + ‖v‖ * ‖us.prod - vs.prod‖ := add_le_add (norm_mul_le _ _) (norm_mul_le _ _)
        _ ≤ ‖u - v‖ * 1 + 1 * ‖us.prod - vs.prod‖ := by gcongr
        _ ≤ ‖u - v‖ + (List.zipWith (fun u v => ‖u - v‖) us vs).sum := by linarith

/-- `Fin n`-indexed form of `prod_sub_prod_le`. -/
theorem prod_ofFn_sub_le {n : ℕ} (u v : Fin n → R) (hu : ∀ i, ‖u i‖ ≤ 1) (hv : ∀ i, ‖v i‖ ≤ 1) :
    ‖(List.ofFn u).prod - (List.ofFn v).prod‖ ≤ ∑ i, ‖u i - v i‖ := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [List.ofFn_succ, List.ofFn_succ, List.prod_cons, List.prod_cons, Fin.sum_univ_succ]
    have hus : ‖(List.ofFn fun i : Fin n => u i.succ).prod‖ ≤ 1 :=
      norm_list_prod_le_one _ (fun w hw => by
        obtain ⟨i, rfl⟩ := List.mem_ofFn.mp hw
        exact hu _)
    have ih' := ih (fun i => u i.succ) (fun i => v i.succ) (fun i => hu _) (fun i => hv _)
    have hsplit : u 0 * (List.ofFn fun i : Fin n => u i.succ).prod - v 0 * (List.ofFn fun i : Fin n => v i.succ).prod
        = (u 0 - v 0) * (List.ofFn fun i : Fin n => u i.succ).prod
          + v 0 * ((List.ofFn fun i : Fin n => u i.succ).prod - (List.ofFn fun i : Fin n => v i.succ).prod) := by
      noncomm_ring
    rw [hsplit]
    have hv0 := hv 0
    calc _ ≤ ‖(u 0 - v 0) * (List.ofFn fun i : Fin n => u i.succ).prod‖
          + ‖v 0 * ((List.ofFn fun i : Fin n => u i.succ).prod - (List.ofFn fun i : Fin n => v i.succ).prod)‖ :=
          norm_add_le _ _
      _ ≤ ‖u 0 - v 0‖ * ‖(List.ofFn fun i : Fin n => u i.succ).prod‖
          + ‖v 0‖ * ‖(List.ofFn fun i : Fin n => u i.succ).prod - (List.ofFn fun i : Fin n => v i.succ).prod‖ :=
          add_le_add (norm_mul_le _ _) (norm_mul_le _ _)
      _ ≤ ‖u 0 - v 0‖ * 1 + 1 * ∑ i : Fin n, ‖u i.succ - v i.succ‖ := by
          gcongr
      _ = _ := by ring
end Ring

section Algebra
variable {A : Type*} [NormedRing A] [NormOneClass A] [NormedAlgebra ℂ A]

omit [NormOneClass A] in
/-- The product of scaled factors is the scaled product. -/
theorem prod_ofFn_smul {n : ℕ} (c : Fin n → ℂ) (R : Fin n → A) :
    (List.ofFn fun i => c i • R i).prod = (∏ i, c i) • (List.ofFn R).prod := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [List.ofFn_succ, List.ofFn_succ, List.prod_cons, List.prod_cons, Fin.prod_univ_succ, ih (fun i => c i.succ) (fun i => R i.succ),
      smul_mul_smul_comm]

/-- Synthesis error accumulation: words `W_i = c_i • R_i + Δ_i` with `‖c_i‖ = 1`, `‖R_i‖ ≤ 1`, `‖W_i‖ ≤ 1` give
`‖∏ W_i − (∏ c_i) • ∏ R_i‖ ≤ ∑ ‖Δ_i‖`. -/
theorem synth_bound {n : ℕ} (c : Fin n → ℂ) (R Δ : Fin n → A) (hc : ∀ i, ‖c i‖ = 1) (hR : ∀ i, ‖R i‖ ≤ 1)
    (hW : ∀ i, ‖c i • R i + Δ i‖ ≤ 1) :
    ‖(List.ofFn fun i => c i • R i + Δ i).prod - (∏ i, c i) • (List.ofFn R).prod‖ ≤ ∑ i, ‖Δ i‖ := by
  rw [← prod_ofFn_smul]
  have hV : ∀ i, ‖c i • R i‖ ≤ 1 := fun i => by
    rw [norm_smul, hc i, one_mul]; exact hR i
  refine (prod_ofFn_sub_le _ _ hW hV).trans (le_of_eq ?_)
  refine Finset.sum_congr rfl fun i _ => ?_
  rw [add_sub_cancel_left]
end Algebra
end Su2Plaq
