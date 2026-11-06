# Audit 300 — M9 fuzzy gauge theory, general one-Trotter-step circuit

Date: 2026-11-06. Auditor: Claude Opus 5.5 (high effort).
Commit range: `master` (merge-base `9b5443d`) .. `5244913` (branch `m9-fuzzy`). Scope: `src`, `lean`, `docs/METHODS-fuzzy.md`,
`prompts/300*`, `prompts/301*`, `tests/acceptance/m9`. Excluded on request: `scripts/m9_results.py`, `results/fuzzy/`, which the builder is still writing.
Plan in force: `prompts/300-fuzzy-m9-plan.md` plus the amendment `prompts/301-fuzzy-m9-test-amendment.md` (acceptance-v10).
References: P = arXiv:2308.05253v4, Eqs. 22–37. N = `refs/fuzzy/fuzzy-hamiltonian-digonto.pdf`. Check report = `scratch/fuzzy-hamiltonian-check.md`.
Tester part 1: `reports/tests/300-m9-gate-full-part1.md` (PASS).

## Verdict: PASS WITH NOTES (no blocking issue)

## Independent checks run by the auditor

The scripts are in the session scratchpad `aud/a1.py`–`a4.py`. All runs used production code with `OMP_NUM_THREADS=1`.

| # | Check | Result |
|---|---|---|
| A1 | $[\square\otimes 1_{\rm col},\,G^A_c]$ on the full 65 536-dim inner space, for every corner $c$ and every $A$, with the production orientation (`CORNER_ENDS`: $\mathcal T_L$ on outgoing links, $\mathcal T_R$ on incoming links) | **exactly 0**. The operator identity holds on the whole space, not only on the 50-dim kernel. |
| A2 | The same commutator with the orientation reversed (N Eq. 3 read literally) | 1.0, so it fails. The orientation is therefore not a free convention given the plaquette index contraction. The code's choice (P Eq. 33) is the consistent one. |
| A3 | $[\mathcal K_{1,2},\mathcal T^A_{L,R}]=0$; $\square=\square^\dagger$; `UB_row(β)` $=\exp(2i\beta\square)$ | 0 / 0 / $1.6\times10^{-15}$ |
| A4 | Gauss-kernel dimension of the isolated plaquette, from shift-invert `eigsh` of $\sum_{c,A}(G^A_c)^2$ on 65 536 dims. This is independent of the route-A/B corner rule. | **50**, with a gap to 1.5. This matches `isolated_plaquette_count` and Lean `count_isolated_plaquette`. |
| A5 | True Krylov space of $H(g^2,r)$ from $\Omega$ at nominal $g^2=1.10141$, compared with the production "invariant under the three building blocks" construction | Dimension 12 at $r=1$ and 9 at $r=0$ for both constructions; the spectra agree to $10^{-6}$. |
| A6 | `build_step` `metadata['layers']`: does it cover every instruction contiguously (orders 1 and 2, with and without outer links)? | Yes: 872/872, 1288/1288, 1080/1080 and 1496/1496 instructions, contiguous. |
| A7 | **Tamper test**: append `rz(1.0)` on qubit 0 and `cx(3,7)` after the layers of `build_step(order=1)`, then run `verify_step_samples` | **Passes**: err $1.05\times10^{-14}$, gauss $5\times10^{-15}$. See ISSUE 1. |
| A8 | Tamper test: relabel the `UK` layer as `"outer"` | Detected at $r=1$ (err 0.99). It would not be detected at $r=0$ or for gates on inner qubits inside an outer range. |
| A9 | Order-2 `build_step` ($r=1$) with the metadata removed, simulated as a whole circuit through the Aer fallback (3 random states and 1 physical state) | err $1.2\times10^{-14}$, gauss $5.5\times10^{-15}$, leak 0. This independently confirms the delivered circuit. |

The tester's spot check (b) simulated the whole 23-qubit `build_step` circuit in Qiskit `Statevector`, with no layer metadata, against `apply_step`, for all four (order, $r$) cases. It found errors of at most $7.5\times10^{-15}$. The **delivered** step circuits are therefore correct independently of ISSUE 1.

## Checklist

| Item | Status | Where / note |
|---|---|---|
| Link operators vs P Eqs. 29–30, 22 ($\Gamma$, $T_{L,R}$, $\mathbb U_{ab}$; generators by commutator; $\mathcal U$ by left multiplication) | OK | `src/su2plaq/fuzzy/link.py:15-58`. The entries match P exactly. `lmul` $=M\otimes1$ and `rmul` $=1\otimes M^{\mathsf T}$ (row-major) are correct. |
| $\mathcal K_1$ (P Eq. 36) and $\mathcal K_2$ (P Eq. 37), with daggers and index order | OK | `link.py:66-79`. $\mathcal K_2=-\sum(\mathbb U_{ab}\Psi\mathbb U_{ab}^\dagger+\mathbb U_{ab}^\dagger\Psi\mathbb U_{ab})$ uses the gauge-invariant reading (same indices). It commutes with $\mathcal T$ (A3). |
| Plaquette (P Eq. 35): $\mathbb U_{ab}(b)\mathbb U_{bc}(r)(\mathbb U_{dc}(t))^\dagger(\mathbb U_{ad}(l))^\dagger$ | OK | `plaquette.py:22-32`. The swapped-index daggers on $t$ and $l$ match the loop $[b^+,r^+,t^-,l^-]$. Invariance is exact (A1). |
| Gauss orientation per corner vs project geometry (`geometry.py:44-57`) | OK | `gauss.py:24-29` (`CORNER_ENDS`) and `_OUTER_NEAR` (l.23) agree with `geometry._LINKS` for all 12 links (checked by hand), with `_fz.CORNERS`, and with Lean `count`. |
| Dead, wrong orientation table | ISSUE (NB-2) | `gauss.py:20-21`: the outer-link entries of `_TAIL`/`_HEAD` are wrong. |
| Couplings: $\tfrac{g^2}{4}\mathcal K_1$, $\kappa_1=\alpha/2$, $\kappa_2=r\alpha/2$ | OK | `targets.py:22-45`. $dt\cdot\tfrac{g^2}{4}=\alpha/2$ and $dt\cdot\tfrac{g^2}{4}r=\kappa_2$ both check. A flux link costs $\tfrac38g^2$, the same as KS $j=\tfrac12$ (K1 test checks the phase $e^{-3i\alpha/4}$). |
| $U_B$ sign and factor | OK | $H_B^{\rm fz}=-(\square+\square^\dagger)=-2\square$ and $U_B=e^{-i\,dt\,H_B/g^2}=e^{+2i\beta\square}$ (`targets.py:33-35`). The B1 test rejects the reversed sign. N's $\alpha_N=-2\beta$ is consistent. Note: the centre $Z_1Z_3$ on one inner link maps $\square\to-\square$ and preserves $\mathcal K_{1,2}$ and Gauss's law. The sign therefore affects only the sign of $\langle\square\rangle$, not the spectra (no action needed). |
| Time-evolution sign and Trotter ordering | OK | `circuits/fuzzy.py:381-410`. Order 1 is kinetic first in the circuit, giving the operator $U_BU_KU_E$. Order 2 is symmetric with half angles. `targets.apply_step` (l.70-84) matches, and S1 cross-checks it against an independent kron composition. |
| Outer links | OK | Each outer link gets one `link_UE(α)` and one `link_UK(κ₂)` at full angles regardless of order. This is exact because these blocks act on disjoint qubits from every inner term and commute with $\mathcal T$. `_outer_block_commutator` checks the latter from the gates. |
| Qubit endianness (F1) across `encodings/fuzzy.py`, `circuits/fuzzy.py`, `targets.py`, `verify.py`, `gauss.py`, `observables.py` | OK | All use the same map: $q_1\to4\ell+3, \dots, q_4\to4\ell$; link $\ell$ at nibble $\ell$ (b least significant); row index $2q_1+q_2$; row register $\sum_\ell(2q_1+q_2)4^\ell$ (`verify.ROW_QUBITS`, `_row_keys`, `targets._apply_ub`, `observables._square`). The tensordot axis of link $\ell$ is $3-\ell$ in every file. |
| Truncation | N/A | The fuzzy link is exactly 16-dim and nothing is truncated. |
| Normalisation and observables (F7) | OK, with note NB-3 | $g^2=\sqrt{2\alpha/\beta}$ and $dt=\beta g^2$ are correct. $\Omega=\otimes\tfrac12\mathbb 1$ is normalised. KS block and $\mathrm{Re\,Tr}W=\sigma_x$ follow the same $-2/g^2$ convention as the fuzzy $\langle1|\square|0\rangle=1$. The closed sector equals the true Krylov space (A5). |
| Precision | OK | Everything is complex128. The Aer fallback (`verify.py:131-147`) is documented as accurate to about 1e-8 and is used only for synthesised circuits, where the tolerance is $\ge n_{\rm rot}\varepsilon$. |
| Seeds | OK | `SEED=20261104` is fixed in tests and in `sample_physical_states`/`_sample_inputs`. A sub-RNG is derived deterministically. |
| Tests test the claim | ISSUE (NB-1) | The S1 step certification relies on builder-supplied `metadata['layers']` without checking that the layers cover the circuit (A7). |
| No hard-coded answers | OK | The counts in tests are literal integers, but production computes them (route A, route B), the test re-derives them (`_fz.ref_count`), and A4 confirms 50 by a direct kernel computation. |
| Tolerances not loosened; prompts/301 justified | OK | `git diff 5100314..HEAD -- tests/acceptance` touches only the two approved tests. Every tolerance is still 1e-10. O1 was tightened (dimension `== 12/9`, $H[0,0]=-4rg^2$, $E_0<-4g^2$). The order-2 $O(\alpha\beta)$ argument is right: $\langle\Omega|[\mathcal K,\square]|\Omega\rangle=0$ because $\Omega$ is a kinetic eigenstate, so the first nonzero term is $\propto\alpha\beta$. The ratio band [3, 5] rejects $O(\alpha)$ and $O(\alpha^2\beta)$ scaling. The K1 seeded-state replacement is sound. |
| Lean statements | OK, with note NB-4 | `Link.lean`: no `sorry`, no `native_decide`, `MEq_discriminates` rules out vacuity, and the scalings ($2\Gamma$, $2T$, $4\mathcal K_1$, $-4\mathcal K_2$) are stated and correct. The `K1/K2_spectrum` theorems prove a minimal polynomial plus traces; the multiplicities follow from hermiticity (`K_hermitian`) and a Vandermonde argument outside Lean, as the docstring says. `Counts.lean`: the corner roles in `count` match the geometry for all 4 corners. Both `.olean` files postdate the last source edits. |
| Provenance | N/A | The results JSON is excluded from this audit (still being written). |

## Issues

### NB-1 (NON-BLOCKING; fix before M10 compression): the step verifier trusts the layer metadata and does not check coverage
**Where.** `src/su2plaq/fuzzy/verify.py:171-213`. `InnerAction._build_layers` iterates over `metadata['layers']`, and l.183 skips `"outer"` ranges entirely. Neither `verify_step_samples` (l.274) nor `gauss_residual_outputs` (l.350) asserts that the ranges partition `range(len(qc.data))`, nor that `"outer"` ranges touch only register `o`.

**Why this is wrong.** METHODS-fuzzy F6 (l.93) lists a "gate-list partition into the three layers" as part of what is certified. That partition is never checked: any instruction outside the listed ranges is silently ignored.

**Failure scenario (demonstrated, A7).** Append `rz(1.0, 0)` and `cx(3, 7)` to `build_step(0.37, 0.61, order=1)` without updating the metadata. `verify_step_samples` then returns err $1.05\times10^{-14}$ and gauss $5\times10^{-15}$, so a wrong circuit passes S1. The same happens for inner gates placed inside an `"outer"` range at $r=0$.

**M10 risk.** Qiskit `transpile` and `QuantumCircuit.copy` keep `metadata`, so an optimised step would carry stale index ranges. Most misalignments raise, but instructions past the last inner range, or inside outer ranges, are dropped silently. `cliffordt.synthesize` (`metrics/cliffordt.py:95`) builds a fresh circuit without metadata and therefore falls back to the whole-circuit Aer path, so T1 is not affected.

**Why not blocking.** `build_step`'s metadata covers every instruction contiguously (A6), and the tester's whole-circuit Statevector check (report 300, (b)) confirms all four variants to $\le7.5\times10^{-15}$.

**Minimal fix.** In `_build_layers`:
- assert `sorted ranges` are contiguous and cover `[0, len(qc.data))`;
- assert that every instruction in an `"outer"` range acts only on `o` qubits;
- optionally store a hash of the instruction list in the metadata and refuse a mismatch.

Add a unit test that the tamper in A7 is rejected.

### NB-2 (NON-BLOCKING): wrong outer-link entries in `_TAIL`/`_HEAD`
**Where.** `src/su2plaq/fuzzy/gauss.py:20-21`. The comment says "(tail corner, head corner); far end = -1". The entries for links 6–10 are wrong: o2 should be (1, −1) but is listed (2, −1); o3 should be (−1, 1) but is (2, −1); o4 and o5 should be (2, −1) but are (−1, 1); o6 should be (−1, 3) but is (−1, −1).

**Why not blocking.** The only use, l.128, reads these tables for `INNER` links only. Outer links go through `_OUTER_NEAR`, which is correct. The counts are therefore unaffected.

**Risk.** Anyone reusing `_TAIL`/`_HEAD` for outer links, for example in M10 or in a route-B variant, gets the wrong orientation.

**Fix.** Correct the six entries or truncate both lists to the 4 inner links.

### NB-3 (NON-BLOCKING, documentation): the closed-sector spectrum omits the outer-link constant
**Where.** `src/su2plaq/fuzzy/observables.py:89-95` builds $H$ on the four inner links only.

**Why it matters.** F3's $H^{\rm fz}$ sums over all 12 links. In $\Omega$ the 8 outer links contribute the constant $8\cdot\tfrac{g^2}{4}\,r\,(-4)=-8rg^2$ (`outer_vacuum_energy`). As a result:
- `closed_sector_spectrum`, $H[0,0]=-4rg^2$ and $E_0=-5.839$ are spectra of $H^{\rm inner}$, shifted by $+8rg^2$ relative to F3's $H$;
- the Loschmidt echo and the plaquette are unaffected.

METHODS-fuzzy F7 item 2 says "eigenvalues of $H$" without this qualifier. The module docstring does mention it, but the shared-table JSON will not.

**Fix.** Add `"energy_offset_outer": outer_vacuum_energy(g2, r)` (or a "spectrum of $H^{\rm inner}$" label) to each fuzzy row, and add one sentence to F7.

### NB-4 (NON-BLOCKING, statement scope): the Lean count theorems certify the formula, not $\dim\ker G$
**Where.** `lean/Su2Plaq/Fuzzy/Counts.lean:62-82` proves that the route-A combinatorial expression evaluates to 50 / 12 800 / 101 197 218 / 6 767 266 914. That the expression equals the Gauss-kernel dimension is the Clebsch–Gordan argument of METHODS F4, which lives outside Lean.

**Status.** The statements are not vacuous. Python (two routes), the test reference and A4 (a direct kernel dimension of 50) agree.

**Fix.** Report 9 should phrase the Lean result as "the corner-rule counts are verified by kernel evaluation", not "the physical dimension is proved".

### NB-5 (NON-BLOCKING, wording)
**Where.** `docs/METHODS-fuzzy.md:111` and `prompts/301:14` say "the *outer* kinetic half-layers act on $U_B|\Omega\rangle$".

**Why it matters.** This means the outermost (last-applied) inner half-layers, not the outer-link blocks. Those are applied once at full angle, commute with everything and do not change $\langle\square\rangle$. `one_step_plaquette` acts on the 4 inner links only, so the code is right.

**Fix.** Reword to "the final inner kinetic half-layer".

## Return summary
VERDICT: PASS WITH NOTES. No blocking issues. NB-1 (the step verifier does not check that the layer metadata covers the whole circuit, so a wrong circuit can pass, as A7 demonstrated) should be fixed before M10 reuses `verify_step_samples` on transformed circuits.
