# Ideation: `fuzzy_ub` / `UB` (exp(+2i beta square), 8 row qubits)

Facts checked numerically (`scratch/proposer/ub_an*.py`, from `plaquette_row` and `block_structure`):

- W = square is real, Hermitian and has entries in {0, +-1}; columns hold 0/1/2/4 nonzeros (120/32/96/8). Its spectrum is
  {+-4, +-2^24, +-1^16, 0^174}. The Pauli form is 64 strings with coefficient +-1/8. Per link the strings are XI/YX/YY/YZ
  (four anticommuting gammas), and their symplectic rank is 11. Only 62.5 % of the pairs commute.
- After the parity frame (f = q1^b, p = (p_r, p_t, p_l)), sector p is a 32x32 operator on (f, q2^b, q2^r, q2^t, q2^l).
  The rank-4 sectors (sv 2) are a singlet projector on one vertex pair on each side. The f=1 side uses bl, tl or rt
  and the f=0 side uses rt, br or tl:
  p0 bl|rt, p1 bl|br, p2 bl|tl, p4 tl|rt, p5 tl|br, p7 rt|br. In p3 (sv 4, rank 1) both sides hold two singlets, and p6
  (sv 1) is a signed cyclic permutation.
- **No sector is a commuting Pauli sum on its own** (so no sector is plain-Clifford-conjugate to X_f (x) diag). Each one
  becomes commuting after **one f-controlled permutation pi of the four q2 qubits**. The good pi per sector
  (pi[i] = target of q2^i, order b r t l) are:
  p0 {(1,0,3,2),(1,3,0,2),(2,0,3,1),(2,3,0,1)}, p1 {(0,3,1,2),(0,3,2,1),(3,0,1,2),(3,0,2,1)},
  p2/p3/p6/p7 incl. (2,1,0,3) = swap(b,t), p4 {(0,2,3,1),(0,3,2,1),(1,2,3,0),(1,3,2,0)},
  p5 {(2,3,0,1),(2,3,1,0),(3,2,0,1),(3,2,1,0)}.
- **Under the single f-controlled swap(q2^b, q2^t), sectors {2,3,6,7} (the p_t = 1 half) are jointly commuting: there are
  16 distinct Pauli strings on (f, q2) in the union.** No f-controlled pi makes any pair of sectors in {0,1,4,5} mutually
  commuting.
- Key freedom: exp(i 2 beta |p><p| (x) W_p) = F^dag exp(i 2 beta |p><p| (x) F W_p F^dag) F holds for any F acting on
  (f, q2) only. **Frames never need p-control**, because the middle rotation is the identity outside sector p.
  Adjacent frames merge.

## 1. `routed-halfplaq-phasepoly`: one Fredkin plus one phase polynomial for the p_t=1 half, per-sector sandwiches for the rest (expected 230-300 CX)
Datapath:
1. Parity frame (3 CX).
2. One Fredkin (f; q2^b <-> q2^t), about 8 CX.
3. One Clifford C_A on (f, q2) (<= ~12 CX) that diagonalises the 16 commuting strings.
4. A phase polynomial on (f, q2', p_r, p_l) with p_t as a literal control. Sectors 2/3/6/7 contribute rank-1/rank-4/full
   indicator terms; Gray-code it at about 1 CX per parity term, roughly 40-64 CX.
5. Undo C_A and the Fredkin.
6. Sectors 0, 1, 4, 5 each get a sandwich: f-controlled pi_p from the table, chosen to share Fredkins between
   neighbours (p1 and p4 share swap(r,l), so order 1 then 4), a 5-qubit Clifford, and a multi-controlled R_x(-8 beta) on
   f. Its controls are the 3 p-literals plus the 2 singlet-flag bits, computed with an rccx ladder into one clean ancilla
   and then crx: about 26 CX per sector.
7. Undo the parity frame.

Most of the weight is in the phase polynomial and the four MC-R_x ladders; this replaces the baseline's 8 controlled
frames with one shared frame for half the sectors.

## 2. `sector-sandwich-uncontrolled`: eight F_p^dag MC-R_x F_p rounds with unconditioned frames (expected 300-420 CX)
This is the generic, easy-to-verify version.
1. Parity frame (3 CX).
2. For each p in a Gray order: F_p = (f-controlled pi_p from the table) followed by a Clifford on (f, q2) that maps W_p to
   sigma_p X_f (x) |1_S><1_S|, with |S| = 2 singlet flags (sv 2), 4 (p3) or 0 (p6).
3. Middle: R_x(-4 beta sigma_p) on f, controlled on p (3 literals) and on S. Use an rccx compute/uncompute ladder into
   one ancilla plus crx: 14 / 26 / 38 CX for |S| = 0/2/4.
4. Merge F_p F_{p'}^dag between rounds; Fredkins cancel when consecutive sectors use the same pi.

Per round this is about 10-16 CX of frame plus the ladder, so about 8 x 40. Angles are 4 beta sigma (sigma in {1,2,4}), so
they are rational multiples of beta and the circuit is Lean-certifiable. Can be a stepping stone to family 1.

## 3. `vertex-slot-routing`: route q2 spins into vertex slots, then one global multiplexed R_x (expected 180-320 CX, speculative)
Use gauge structure: the spin of each link sits at its start or end vertex depending on q1, and W moves every spin to the
other endpoint, with a singlet contraction on doubly-occupied vertices.
1. Use 4 q1-controlled moves (Toffoli + CNOT into clean ancilla slots, about 7 CX each) to place the spins in
   per-vertex 2-slot registers.
2. Bell-decode every vertex register (CX+H): the singlet becomes |11>, a computational flag.
3. Rename slots so that the f=0 and f=1 partners differ only in f and in a fixed slot permutation (Clifford).
4. Apply one multiplexed R_x on f whose angle function sigma(p, flags) has a sparse Walsh spectrum:
   sigma = 1 on p6, 2 x flag on the rank-4 sectors, 4 x flag_v x flag_v' on p3.
5. Undo the routing.

All 8 sectors share a single frame, so there is no per-sector ladder. The risk is that the routing and the sector-dependent
slot permutation cost more than family 1's per-sector sandwiches. Try it only if family 1 stalls above ~250 CX.
