# 000 — Starter plan: SU(2) plaquette with outer links, truncations and encodings

Date: 2026-11-04 · Author: coordinator (from chat with Digonto)
Supersedes: the 2×2-periodic-lattice plan (archived at git tag `archive-2x2-lattice`; do not use it).

## 1. Source material (read these first)
- `refs/su2_plaquette_truncations_encodings.md` — Digonto's note (4 Nov 2026): geometry, truncation
  schemes, encodings, state counts, register sizes, open questions (§7). **This defines the project.**
- `refs/su2_plaquette_encodings.py` — Digonto's script that produces every number in the note
  (numpy only, under 1 s). Reference output was checked against the note on 2026-11-04: all numbers match.
- `refs/2610.22367v1*` — Gu, Kemeny, Yelin, Lukin (background only).

## 2. System
- One square plaquette, 4 inner links + 8 outer links ($L=12$), 4 four-valent corners ($V=4$).
- Link and corner conventions as in the note §1 and the script docstring
  (inner links b, r, t, l; corners (0,0):b,l (1,0):b,r (1,1):r,t (0,1):t,l).
- Boundary choices: **closed** (outer links $j=0$), **open** (outer far ends free; "labels" and "full" counts),
  and **static boundary charges** (outer links fixed to chosen spins; note §7, not yet implemented).
- Hamiltonian: Kogut–Susskind, $H = \frac{g^2}{2}\sum_{\ell} j_\ell(j_\ell+1) - \frac{1}{2g^2}\sum_P (\operatorname{tr} U_P + \text{h.c.})$
  (planner to fix normalisation and cite it).

## 3. Goals, in order (planner turns these into milestones with locked acceptance tests)
1. **Verify the note.** Reproduce every number in note §5 with an *independent* code path
   (not by importing the reference script), e.g. explicit construction of the gauge-invariant subspace
   in the full electric basis for the smallest cases, and recoupling/fusion counting for the rest.
   Resolve the register-size issue in §5 below. Check the unverified claims in note §7 against the papers.
2. **Plaquette operator in the spin-network basis** ($6j$/$9j$ recoupling), closed and open boundaries,
   $j_{\max}=1/2$ first, then $j_{\max}=1$. Cross-check against the full electric basis $|j,m_L,m_R\rangle$
   with Gauss's law projected out (exact diagonalisation: same spectrum in the physical sector).
3. **Per-encoding qubit Hamiltonians and circuits** (one Trotter step of $e^{-iHt}$), with gate counts
   per encoding, and equivalence checks between encodings on shared observables.

## 4. Decisions carried over from the previous plan (confirm with Digonto)
- Circuits in Qiskit 2.5.2 / Aer 0.17.2, CPU only. Tests run in parallel (`pytest -n auto`, pytest-xdist 3.8.0).
- Cost metric: CNOT count first, then depth, then qubits.

## 5. Known issue found on reading (2026-11-04, coordinator)
Note §5 register table vs its own bullets:
- "q-deformed spin network" row gives 16 qubits at $j_{\max}=1/2$, but the bullet under it and §5 counts say
  SU(2)$_1$ needs **no** intertwiner register ($n=12$, the open count is exactly 256).
- "Spin network" row gives 20 at $j_{\max}=1/2$; the bullet says 16 suffices.
Cause: the script's register sizes (`report()`, `reg` dict) give every corner a register for all
$J = 0,\tfrac12,\dots,2j_{\max}$. That is a simple upper bound, not the minimum. Link spins already fix
whether $J$ is integer or half-integer, and in SU(2)$_1$ they fix $J$ completely.
Planner: define "register size" precisely (simple layout vs minimum) and report both.

## 6. Open questions for the planner
- Which boundary choice the circuit milestones use (open, closed, or static charges).
- Which encodings get full circuits vs only a register count (note §5 lists 10 rows).
- Intertwiner pairing convention at a 4-valent corner (which two links pair first) and its effect on the
  plaquette matrix elements.
