# 400 — M7 plan: loop-string-hadron (LSH) encoding, general one-Trotter-step circuit → Report 7

- Date: 2026-11-10 · Author: planner (Claude Fable 5.2, high) · Git commit at writing: `8822b0b` (branch `merge-desktop-tracks`, host omnicommander)
- Trigger: coordinator kickoff of encoding 4 (LSH), numbers 400–499; `prompts/001` §3 "M7/M8 — LSH", §1 (physics fixed), §4–§6; `notes/STATUS.md` decision of 2026-11-10 ("then start LSH (M7/M8)").
- Plan in force after this file: `prompts/002` + addenda `003`–`006` for the shared machinery (evaluator, metrics, Lean generic), **this file for M7**. M8 (compression) is planned after M7 closes; §9 lists what M7 provides for it.
- Research: `reports/research/400-lsh-model.md` (every number quoted here was measured there). Methods: `docs/METHODS-lsh.md` (L1–L11). Locked tests: `tests/acceptance/m7/` (29 tests; the coordinator locks them with `python tools/lock.py m7` and `~/.claude/bin/acceptance-lock`; this run did not touch `LOCK.json`).
- Shape: same as `prompts/100` (spin network), which this encoding reuses most.

Jargon, once: *LSH (loop-string-hadron) formulation* = SU(2) gauge theory written with gauge-invariant integers at each site (for pure gauge: *loop numbers* $\ell_{ij}$ = units of flux running through a 3-valent site from leg $i$ to leg $j$); *point splitting* = each 4-valent corner becomes two 3-valent sites joined by a zero-length *virtual link*; *'in' / 'out' site* (our labels) = the site of a corner holding its two inner / two outer links; *flux* $N=2j$ of a leg; *Abelian Gauss law (AGL)* = the flux of a link read at its two ends agrees; *site code* = 3 bits of loop numbers; *inner code* = the 12 data bits; *bright / dark* = inner codes the plaquette moves / annihilates; *pair* = two bright codes exchanged by the plaquette; *transcoder* (our label) = reversible circuit rewriting the LSH data bits in place into spin-network data bits; *frame, flag, phase walk, gauge* as in `prompts/100`.

## 0. Environment and commands (read `scratch/agent-common.md` first; memory rule is hard)
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 16-19 tools/pytest-safe -n 4 -q tests/unit -k lsh                 # fast check after every edit (builder)
taskset -c 16-19 tools/pytest-safe -n 4 -q -m "not slow" tests/acceptance/m7 # step acceptance (tester); -k <id> for one id
taskset -c 16-19 tools/pytest-safe -n 4 -q tests/acceptance                  # milestone gate (m0..m10 as locked)
python -m pytest --collect-only -q tests/acceptance/m7                       # 29 tests, must stay clean
python tools/check_lock.py && ~/.claude/bin/acceptance-check
cd lean && PER_JOB_MEM=12G ../tools/run-capped taskset -c 16-19 lake build Su2Plaq   # never touch Structure/Counts.lean
graphify update .                                                           # after code changes
```
New files only (builder): `src/su2plaq/lsh/{__init__,operators,walk,lean_export}.py`, `src/su2plaq/encodings/lsh.py`, `src/su2plaq/circuits/lsh.py`, `tests/unit/test_lsh_*.py`, `scripts/m7_results.py`, `results/lsh/`, `lean/Su2Plaq/LSH/{Counts,Circuit}.lean`, `lean/Su2PlaqCert/LSH/{Check,Main,Pins}.lean`. Appends to shared files, nothing else: two import lines in `lean/Su2Plaq.lean`, one `[[lean_exe]]` block in `lean/lakefile.toml` (step 7.L3). **Do not edit** `src/su2plaq/{evaluate,metrics,compress,exact,su2,spinnet,rishon,fuzzy,lean}/*`, `encodings/{base,twelve,spinnet,rishon,fuzzy}.py`, `circuits/{twelve,spinnet,rishon,fuzzy}.py`: the spin-network and rishon compression loops run concurrently and record the hash of those files in every round.

## 1. Method (equations and sources: `docs/METHODS-lsh.md`)

**1.1 Model (L1–L2).** Pure-gauge Kogut–Susskind theory of METHODS §2 in LSH variables (Raychowdhury–Stryker, arXiv:1912.06133, Sec. V) on the point-split diagram with the **(inner | outer) pairing** at every corner (`geometry.point_split`): 'in' site $c$ has legs $(1,2,3)=(p(c),n(c),v)$ with $(p,n)=(l,b),(b,r),(r,t),(t,l)$ for $c_0..c_3$; 'out' site $c$ has legs (outer 1, outer 2, $v$) with outer links $(o_0,o_1),(o_2,o_3),(o_4,o_5),(o_6,o_7)$. Site basis $|\ell_{12},\ell_{23},\ell_{31}\rangle$, fluxes $N_1=\ell_{31}+\ell_{12}$, $N_2=\ell_{12}+\ell_{23}$, $N_3=\ell_{23}+\ell_{31}$, $j_i=N_i/2$, $\ell_{12}=j_1+j_2-j_3$ (cyclic). Truncation $j\le\tfrac12$ on physical links, $J\le1$ on virtual links ⇒ loop numbers in $\{0,1\}$, 1 qubit each (arXiv:1812.07554: $N=\lceil\log_2(\bar j+1)\rceil$).

**1.2 Register and validity (L2–L3).** Site code $s=\ell_{12}+2\ell_{23}+4\ell_{31}$; valid site codes (flux cap $N_1,N_2\le1$) $=\{0,1,2,4,6\}$. Data `d[0..11]`: 'in' site $c$ at qubits $3c,3c{+}1,3c{+}2=(\ell_{pn},\ell_{nv},\ell_{vp})$. Outer `o[0..11]` (read-only): 'out' site $c$ at $12{+}3c,..=(\ell_{12},\ell_{2v},\ell_{v1})$. Physical codes = all sites valid + AGL on the 4 inner links ($N_n(\text{in},c)=N_p(\text{in},c{+}1)$) + AGL on the 4 virtual links ($N_v(\text{in},c)=N_v(\text{out},c)$). Measured: **433** physical codes = the codes of the 433 route-B labels; **47** inner codes (16 bright, 31 dark = a site in `110`); 305 outer-site patterns; raw register without the cap: 82 inner / 5920 states.

**1.3 Operators (L4).** Dressed ladder factor $\langle\ell'|(N_n+1)^{-1/2}\mathcal L^{\sigma_p\sigma_n}_{pn}(N_p+1)^{-1/2}|\ell\rangle$ from the factorisation table ($S=\sum\ell$): $\mathcal L^{++}$: $\ell_{pn}{+}1$, $\sqrt{(\ell_{pn}+1)(S+2)}$; $\mathcal L^{--}$: $\ell_{pn}{-}1$, $\sqrt{\ell_{pn}(S+1)}$; $\mathcal L^{+-}$: $\ell_{vp}{+}1,\ell_{nv}{-}1$, $-\sqrt{(\ell_{vp}+1)\ell_{nv}}$; $\mathcal L^{-+}$: $\ell_{vp}{-}1,\ell_{nv}{+}1$, $-\sqrt{\ell_{vp}(\ell_{nv}+1)}$. $\mathrm{Tr}\,U_P=\mathrm{tr}(\mathcal V_{c_0}\mathcal V_{c_1}\mathcal V_{c_2}\mathcal V_{c_3})$ with the vertex-factor matrices LL, RL, RR, LR of METHODS-lsh L4 (table `VERTEX` in §2); $H_B=-(\mathrm{Tr}\,U_P+{\rm h.c.})$; $H_E=\sum_\ell\tfrac{N_\ell}2(\tfrac{N_\ell}2+1)$, inner links read at the $n$-leg of their 'in' site. Terms leaving the valid codes are dropped. Measured: $K_{\rm LSH}=-(P+P^{\mathsf T})$ on the 47 inner codes equals the 6j $K_{\rm inner}$ entry by entry ($1.8\cdot10^{-15}$): matching of 8 pairs (partner = per-site flip `000`↔`001`, `010`↔`100`), couplings $-2$ / $-\tfrac12$ / $+1$ by $w_c=N_v\bmod2$ pattern (all 0 / all 1 / two 1), 31 dark rows; spectra vs routes A and B $\le1.0\cdot10^{-14}$.

**1.4 Target, gauge, decoding (L5–L6).** Target = LSH operator in label order (same matrix as the spin-network target). Route A by the real diagonal gauge of `gauge_align(H_A, H_B^{LSH})` (64 minus signs, $8.9\cdot10^{-16}$). `decode_state`: physical code $k$ ↦ `gauge[k]` × route-A state; data-valid, outer-site-valid, AGL-violating code (28 942 of them) ↦ single electric basis state with every spin-$\tfrac12$ end at corner $c$ a $G^z$ eigenstate: inner ends $+\tfrac12$ ($J_{\rm in}\ne1$) or $-\tfrac12$ ($J_{\rm in}=1$), outer ends $-\tfrac12$ ($J_{\rm out}\ne1$) or $+\tfrac12$ ($J_{\rm out}=1$), far ends $m=+\tfrac12$; cg convention $G^z=-m_L$ ('out' end), $+m_R$ ('in' end). Gauss residual $\ge\tfrac12$, keys distinct, orthogonal to all physical states (measured on all 28 942). Other codes → `ValueError`.

**1.5 General circuit for $U_B$ (L7).** Transcoder $T$ per 'in' site $(x,y,z)=$ qubits $(3c,3c{+}1,3c{+}2)$: `cx(y,z); cx(y,x); rccx(z,x,y)` → wires 0,3,6,9 = $j_b,j_r,j_t,j_l$ (`LINK`), wires 1,4,7,10 = corner bits $[J_c=1]$ (`CBIT`), wires 2,5,8,11 = $w_c$ (`WBIT`). Then the spin-network construction (prompts/100 §1.5) on those wires: frame `cx(3,9); cx(0,3); cx(0,6)`; `h(0)`; flags on ancillas `a[0..6]` $=(A,B,F,P,Q,G_1,G_2)$: `x` on 1,4,7,10; `rccx(1,4,A)`; `rccx(7,10,B)`; `rccx(A,B,F)`; `x(6); x(9); rccx(6,9,P)`; `rccx(F,P,Q)`; `x(3); rccx(Q,3,G1); x(3); rccx(Q,3,G2)`; walk on wire 0: `rz; cx(F,0) rz cx(F,0); cx(G1,0) rz cx(G1,0); cx(G2,0) rz cx(G2,0)`; flags reversed; `h(0)`; frame reversed; $T$ reversed. Angles solved at build time from the LSH coupling table ($\sum_r\theta_r(-1)^{p_r(y)}=2\beta k(y)$ on all 47 codes; expected $(-\tfrac72,-1,3,\tfrac32)\beta$). Measured: 94 CX, 4 rotations, 88 fixed T, 7 ancillas, depth 87, error $1.4$–$2.6\cdot10^{-14}$.

**1.6 $U_E$ and the step (L7).** Stand-alone `build_UE`: `p(-3α/4)` on qubits $3c$ and $3c{+}1$ of every 'in' site (8 phases, 0 CX). `include_outer_electric`: `p(-3α/2)` on $12{+}3c$, `p(-3α/4)` on $12{+}3c{+}1$ and $12{+}3c{+}2$ (12 phases). `build_step`: electric layer **inside the transcoded frame**, `p(-3α/4)` (order 1, before the frame) or `p(-3α/8)` before the frame and after its inverse (order 2) on wires 0,3,6,9: 94 CX, 8 / 12 rotations.

**1.7 Spin-network circuits in the LSH register (L8).** `wrap_spinnet(C)` $=T^\dagger CT$ with $C$'s data wires 0–3 → `LINK`, 4–7 → `CBIT`, ancillas kept: +40 CX, +32 T. Comparison rows `general7`, `pairs9`, `flags4` (measured 94/4/88, 74/9/56, 84/4/80).

**1.8 Lean (L10).** Kernel-checked counts and circuit structure; native per-circuit certificate through a checker pinned to the LSH states (§4).

## 2. Interface (the builder creates stubs raising `NotImplementedError` first; the locked tests call exactly these). Prototypes to copy, not to re-derive: `scratch/planner/m7shim/proto/{lsh_operators,encodings_lsh,lsh_walk,circuits_lsh}.py` (they pass the 23 non-Lean, non-results locked tests), `scratch/planner/lean/{LSHCounts,LSHCircuit}.lean`.

```python
# src/su2plaq/lsh/operators.py        (loop-number arithmetic only: no import of su2plaq.exact.*, su2plaq.su2.wigner)
VALID_SITE = (0, 1, 2, 4, 6); SITE_J1 = 6
CORNER_PN = ((3, 0), (0, 1), (1, 2), (2, 3)); CORNER_OUT = ((4, 5), (6, 7), (8, 9), (10, 11)); LINK_NAMES = ("b", "r", "t", "l")
VERTEX_TYPES = ("LL", "RL", "RR", "LR")
VERTEX: tuple   # VERTEX[c][i][k] = (sign, sigma_p, sigma_n); c0: ((+,-,+),(-,-,-)),((+,+,+),(+,+,-)); c1: ((+,+,+),(+,+,-)),((-,-,+),(+,-,-));
                #                                              c2: ((+,+,-),(-,+,+)),((+,-,-),(+,-,+)); c3: ((-,-,-),(-,-,+)),((+,+,-),(-,+,+))
def site_flux(s: int) -> tuple[int, int, int]                     # (N_1, N_2, N_3)
def site_valid(s: int) -> bool
def site_code(j1, j2, j3) -> int                                   # ValueError unless the three loop numbers are integers in {0, 1}
def ladder_amplitude(l: tuple[int, int, int], sigma_p: int, sigma_n: int) -> tuple[tuple[int, int, int], float] | None   # §1.3, any l >= 0
def loop_ladder(s: int, sigma_p: int, sigma_n: int) -> tuple[int, float] | None     # 3-bit version; None also if a loop number leaves {0, 1}
def inner_code_of(j4, J) -> int                                    # 12-bit code of inner spins (j_b, j_r, j_t, j_l) and (J_0..J_3)
def code_of_label(label) -> int                                    # 24-bit; label = ((j_0..j_11), (J_0..J_3))
def agl_violations(code: int) -> tuple[str, ...]                   # subset of ("b","r","t","l","v0","v1","v2","v3"); no cap check
def is_physical_code(code: int) -> bool                            # 0 <= code < 2^24, 8 valid sites, no AGL violation
def inner_codes() -> np.ndarray                                    # 47 sorted int64, enumerated in LSH variables
def physical_codes() -> np.ndarray                                 # 433 sorted int64, enumerated in LSH variables
def plaquette_inner() -> np.ndarray                                # 47x47 P[new, old] = <new|Tr U_P|old>, inner_codes order
def K_lsh() -> np.ndarray                                          # -(P + P^T)
def h_magnetic_lsh(codes) -> np.ndarray                            # (n, n): K_lsh between codes with equal outer part
def h_electric_lsh(codes, include_outer: bool = False) -> np.ndarray   # (n,) diagonal; accepts 12-bit inner codes too

# src/su2plaq/encodings/lsh.py
N_DATA, N_OUTER = 12, 12
code_of_label                                                      # re-export
def label_of_code(code: int) -> tuple | None
class LSH(Encoding):
    name = "lsh"; n_data = 12; n_outer = 12; is_basis_encoding = True
    registers = {"d": [0..11], "o": [12..23], "l_pn": [0,3,6,9], "l_nv": [1,4,7,10], "l_vp": [2,5,8,11],
                 "site_in_c": [3c,3c+1,3c+2], "site_out_c": [12+3c,12+3c+1,12+3c+2]  (c = 0..3)}
    basis: PhysicalBasis                 # route A (cg); basis.labels == exact.spinnet.labels(jmax=0.5) (asserted)
    labels; K_codes: np.ndarray          # 47x47 = operators.K_lsh()
    gauge: np.ndarray; gauge_residual: float      # gauge_align(H_A, H_B^LSH); RuntimeError if residual > 1e-10 or not real +-1
    def inner_codes(self) -> np.ndarray; def physical_vectors(self) -> EncodedBasis      # 433 unit codes in label order, n_data 12, n_outer 12
    def decode(self, code: int) -> int | None
    def decode_state(self, codes, amps) -> tuple[np.ndarray, np.ndarray]                 # §1.4
    def target(self, kind, alpha, beta, order=1, include_outer_electric=False) -> np.ndarray     # 433x433; ValueError on unknown kind/order
    def inner_target(self, kind, alpha, beta, order=1) -> np.ndarray                              # 47x47
    def h_magnetic(self) -> np.ndarray; def h_electric(self, include_outer=False) -> np.ndarray
    def layout_of(self, qc) -> Layout    # as SpinNet.layout_of with 12 / 12
    def describe(self) -> str            # markdown; must contain "47", "433", "Abelian"
    def import_map(self, source: str) -> dict | str   # "spinnet": {"wrap": "su2plaq.circuits.lsh:wrap_spinnet", "kind": "UB", "fixed_angle": False,
                                                      #   "skeletons": ["general7","pairs9","flags4","flags5","flags6"], "extra_cx": 40, "extra_t": 32, "note"};
                                                      # "paulo15": dict (fixed_angle True, note on the gauge); "paulo34"/"lean22"/"lean22_v2": reason str; else ValueError

# src/su2plaq/lsh/walk.py              Step = ("cx",c,t) | ("x",q) | ("h",q) | ("rccx",a,b,t) | ("rz",q) | ("p_alpha",q); data 0..11, ancillas 12..
LINK = (0, 3, 6, 9); CBIT = (1, 4, 7, 10); WBIT = (2, 5, 8, 11); TARGET = 0; J_HALF_PHASE = 0.75
TRANSCODE: tuple; FRAME: tuple
def transcode_steps() -> list; def mirror(steps) -> list
def skeleton(electric: int = 0) -> tuple[list, int]               # 0: U_B, 1: step order 1, 2: step order 2; (steps, 7)
def classical_run(steps, code: int) -> int; def classical_slots(steps, code: int) -> list[int]
def coupling_table(enc) -> dict[int, float]; def partner_table(enc) -> dict[int, int]
def solve_angles(steps, table, beta) -> tuple[np.ndarray, float]; def angle_fractions(steps, table, max_den=64) -> list[Fraction]
def build(steps, n_anc, table, alpha, beta, order=1, with_outer=False, name="UB") -> QuantumCircuit    # registers d[12], [o[12]], a[n_anc]

# src/su2plaq/circuits/lsh.py          (register order d, [o], a)
def build_UE(alpha, with_outer=False, include_outer_electric=False)     # ValueError if include_outer_electric and not with_outer
def build_UB(beta, with_outer=False)                                     # metadata {"kind","beta","skeleton","angles","angle_fractions"}
def build_step(alpha, beta, order=1, with_outer=False)                   # ValueError for order not in (1, 2)
def wrap_spinnet(sn_qc, with_outer=False)                                # ValueError unless sn_qc has register d[8] first and no "o"

# src/su2plaq/lsh/lean_export.py
def coupling_ints(enc) -> list[int]; def partner_ints(enc) -> list[int]; def angle_ints(enc) -> list[int]     # sorted inner-code order; angles in units of beta/2
def lean_literals(enc) -> dict[str, str]       # keys "codes","coupling","partner","angles": "[" + ", ".join(str(x)) + "]", verbatim in Circuit.lean
def write_lean_tables(path=None) -> pathlib.Path    # block between `-- BEGIN generated` / `-- END generated` of lean/Su2Plaq/LSH/Circuit.lean
def export_certificate(qc, enc, kind, alpha, beta, order, out_path) -> pathlib.Path | str
def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout=900.0) -> dict   # {"status","reason","cert_path","seconds","axioms"}; `lake exe su2plaq_cert_lsh check`
def write_pins(path=None) -> pathlib.Path      # lean/Su2PlaqCert/LSH/Pins.lean

# scripts/m7_results.py                PYTHONPATH=src python scripts/m7_results.py [--out results/lsh]   (pattern of scripts/m3_results.py; §5)
```
Lean names (LOCKED by `tests/acceptance/m7/test_lsh_lean.py`), namespace `Su2Plaq.LSH`: `Counts.lean`: `card_site_codes : siteCodes = 5`, `site_valid_list : (List.range 8).filter siteValid = [0, 1, 2, 4, 6]`, `flux_injective`, `flux_even`, `card_inner_codes : innerCodes = 47`, `card_bright_codes : brightCodes = 16`, `card_dark_codes : darkCodes = 31`, `card_states_lsh : totalStates = 433`, `card_bright_states : brightStates = 256`, `card_raw_inner : rawInner = 82`, `card_raw_states : rawStates = 5920` — each statement on the `theorem` line, definitions as the prototype. `Circuit.lean` (imports `Su2Plaq.SpinNet.Circuit`): `transcode_into_spinnet`, `transcode_injective`, `transcode_w`, `coupling_matches_spinnet`, `pre_maps_partner_to_x`, `walk_table_exact`, `ancillas_clean` (+ `walk_slots_match`, `table_lengths`), tables `lshInnerCodes`, `lshCoupling`, `lshPartner`, `lshAngles`, `transOps`, `frameOps`, `flagOps`, `walkOps` generated. `lean/Su2Plaq.lean` gains `import Su2Plaq.LSH.Counts` and `import Su2Plaq.LSH.Circuit`. No `native_decide`, `sorry`, `admit` in `lean/Su2Plaq/LSH/`.

## 3. Steps (one builder call each; tester verifies the listed ids; commit after PASS)

| Step | Builds | Done-check (tester) | Acceptance ids (`tests/acceptance/m7/`) |
|---|---|---|---|
| 7.0 | stubs for every name of §2 (`NotImplementedError`), `src/su2plaq/lsh/__init__.py`, `tests/unit/test_lsh_operators_unit.py` skeleton | `pytest --collect-only -q tests/acceptance/m7` → 29 tests; `tools/pytest-safe -n 4 tests/acceptance/m7` → 29 failures, every one `PENDING:`; unit suite green | — |
| 7.1 | `lsh/operators.py`: site rules, `site_code`, `code_of_label`, `inner_code_of`, `agl_violations`, `is_physical_code`, `inner_codes`, `physical_codes`; `encodings/lsh.label_of_code` | A1 green; unit: counts 5 / 47 / 16 / 31 / 433 / 305 / 82 / 5920 recomputed in the unit test by a second loop | `test_lsh_model.py::test_M7_A1_register_agl_counts` |
| 7.2 | `lsh/operators.py`: `VERTEX`, `VERTEX_TYPES`, `ladder_amplitude`, `loop_ladder`, `plaquette_inner`, `K_lsh`, `h_magnetic_lsh`, `h_electric_lsh` | K1, K2, X1 green; tester reports $\max|K_{\rm LSH}-K_{6j}|$ and the three spectra differences | `::test_M7_K1_ladder_factors_from_prepotentials`, `::test_M7_K2_plaquette_operator_vs_route_b_and_a`, `::test_M7_X1_spectra_three_routes` |
| 7.3 | `encodings/lsh.py`: codec, 433 unit vectors, gauge, `decode`, `decode_state` with the fallback (§1.4), `layout_of`, `describe`, `import_map` | C1 green; `evaluate(identity on d[12], enc, eye(433))` ok; unit: fallback keys of **all** 28 942 codes distinct and disjoint from the physical supports | `test_lsh_codec.py::test_M7_C1_codec_and_vectors` |
| 7.4 | `LSH.target`, `inner_target`, `h_magnetic`, `h_electric`; `lsh/walk.coupling_table`, `partner_table` | C2 green (target equals `SpinNet.target` to 1e-12) | `::test_M7_C2_target_lsh_equals_route_b_and_spinnet` |
| 7.5 | `circuits/lsh.build_UE` (+ outer row) | E1 green; outer row reads 12 bits, 305 blocks | `test_lsh_circuits.py::test_M7_E1_electric_step[0.37/0.91]` |
| 7.6 | `lsh/walk.py` complete (`TRANSCODE`, `FRAME`, `skeleton`, `classical_*`, `solve_angles`, `angle_fractions`, `mirror`, `build`); `circuits/lsh.build_UB` | B1 at β ∈ {0.4, 0.61, 1, 2}, B2, B3, G1 green; expected 94 CX / 4 rot / 88 T / 7 anc and angles $(-\tfrac72,-1,3,\tfrac32)\beta$ (reported, not asserted beyond the sanity bounds) | `::test_M7_B1_magnetic_inner_block[*]`, `::test_M7_B2_physical_states`, `::test_M7_B3_gauss_and_clean_ancillas`, `::test_M7_G1_evaluator_sees_abelian_gauss_law_violations` |
| 7.7 | `circuits/lsh.build_step` (electric layer inside the transcoded frame) | S1 green for both orders; wrong order and $-\beta$ rejected | `::test_M7_S1_step_orders[1/2]` |
| 7.8 | `circuits/lsh.wrap_spinnet` | V1 green: +40 CX, +32 T exactly | `test_lsh_external.py::test_M7_V1_wrapped_spinnet[general7/pairs9/flags4]` |
| 7.9 | nothing new in `src/` expected (metrics are shared); fix only what T1 exposes in the LSH files | T1 green for UE, UB, step; pygridsynth vs Qiskit within 10 % | `test_lsh_metrics.py::test_M7_T1_t_table_and_synth_verify[UE/UB/step]` |
| 7.10 | `scripts/m7_results.py` → `results/lsh/{UE,UB,step}.json` (+ `*.qpy`/`*.qasm3`), §5 | R1 green on a **clean** commit; tester recomputes ≥ 20 numbers independently (Aer statevector on the 19-qubit d + a circuits is allowed: 8 MB per state) | `test_lsh_results.py::test_M7_R1_results_files[UE/UB/step]` |
| 7.L1 | `lean/Su2Plaq/LSH/Counts.lean` (copy `scratch/planner/lean/LSHCounts.lean`, header), import line | `lake build Su2Plaq` green under `tools/run-capped`; L1 green | `test_lsh_lean.py::test_M7_L1_lsh_counts_kernel_checked` |
| 7.L2 | `lsh/lean_export.py` (`coupling_ints`, `partner_ints`, `angle_ints`, `lean_literals`, `write_lean_tables`), `lean/Su2Plaq/LSH/Circuit.lean` (copy the prototype; tables between the generated markers), import line; unit test that the generated block equals `walk.skeleton(0)` | L2 green | `::test_M7_L2_general_circuit_structure_kernel_checked` |
| 7.L3 | `lean/Su2PlaqCert/LSH/{Check,Main,Pins}.lean` (copies of `Su2PlaqCert/SpinNet/*` with register sizes 12 + 12 and the LSH pins), `[[lean_exe]] su2plaq_cert_lsh` in `lakefile.toml`; `lsh/lean_export.{export_certificate,certify,write_pins}` (adapt `spinnet/lean_export.py`: `N_DATA = N_OUTER = 12`, states = 433 unit codes, exact blocks from $K$'s spectral projectors, electric weight $\tfrac34\sum_cN_n(c)$, base $(d_\alpha,d_\beta)=(4,4)$, order 2: $(8,4)$) | L3 green: `certified` ≤ 900 s, tampered angle → `rejected`/`n_a`; unit: exported Laurent target vs `enc.target` ≤ 1e-12 at the three angle pairs | `::test_M7_L3_native_certificate_general_step` (slow) |
| 7.11 | METHODS-lsh L11 filled from `results/lsh/*.json` (planner or builder under planner review), `graphify update .`; gate: tester full → auditor → tester benchmark (`reports/benchmarks/4NN`: encoding build, `evaluate` of `build_UB(with_outer=True)` physical, `m7_results.py` wall) → `git tag milestone-7` → Report 7 (§5) | — | all m7 |

Builder briefs must include: graphify-first rule; copy the prototypes; the allowed-gate set (`ALLOWED` in the tests); angles are solved, never typed in; no native `mcx`, `mcrx`, `cu`, `unitary`; the do-not-edit list of §0; `tools/pytest-safe` / `tools/run-capped` only, cores 16–19.

## 4. Lean (trust levels of METHODS §11)
- **Kernel-checked** (7.L1, 7.L2): the counts of §1.2 from the LSH rules alone (site cap, AGL), independently of `Su2Plaq.card_physical` (the corner-fusion count): two kernel proofs of 433 by different rules. Circuit structure: transcoder is a bijection of the 47 codes onto the spin-network codes, the coupling tables agree under it, transcoder + frame map the plaquette move to $X$ on wire 0, the integer Walsh table is exact, ancillas return to 0.
- **Native-certified** (7.L3): per-circuit certificate of `build_step(0.37, 0.61, 1, with_outer=True)` (31 qubits ≤ 62), valid for all $(\alpha,\beta)$ of the angle-linear family (METHODS §11.2, §11.5).
- **Numerical**: the oscillator derivation of the ladder factors and vertex factors (M7-K1), couplings, route-A gauge.

## 5. Results and Report 7 (`docs/report-7-lsh-general-circuit.md`, rendered from `results/lsh/*.json` only; structure of Report 3)
`scripts/m7_results.py` writes, for $U_E$, $U_B$, step (order 1) at $(0.37,0.61)$ on the d-only circuits: exact-angle verdict, logical metrics, 4-row $T(\varepsilon)$ table with a synthesised verdict per row (`row["synth"]["verdict"]`), provenance. `extra.physics` (all files) = `{n_physical_states: 433, n_inner_codes: 47, n_bright_codes: 16, n_outer_site_patterns: 305, n_raw_agl_states: 5920, n_agl_violating_data_valid_codes: 28942, qubits_data: 12, qubits_outer: 12, couplings, gauge_minus_count, spectra_vs_route_A, spectra_vs_route_B, K_minus_K6j}` — every entry computed in the script. `UE.extra.outer_electric_row` = `{verification, metrics}` of `build_UE(α, True, True)`. `step.extra.order2` = `{verification, metrics}`. `UB.extra.comparison` = `{"wrapped_spinnet": {name: {verification, logical, spinnet_logical, t_table_pygridsynth (ε = 1e-6 first)} for name in general7, pairs9, flags4 (+ flags5, flags6)}, "transcoder": {"cx": 20, "t_fixed": 16, "n_rot": 0, "ancilla": 0} (from `logical_metrics` of the transcoder alone), "spinnet": the spin-network general circuit's logical counts and T(1e-6)}`.
Report 7: 1. what was asked; 2. what was done (model, register, validity rule, operators, circuit, checker rules); 3. results: exactness table, gates, $T(\varepsilon)$ table incl. the **outer-link electric row** (12 phases), like-for-like table LSH vs spin network vs twelve-qubit (the LSH overhead is the transcoder: +40 CX, +32 T, +4 data qubits); 4. physics findings: LSH ladder factors derived from the oscillators and equal to the 6j operator without any sign gauge; AGL + flux cap ⇔ 433 states (two kernel proofs); the AGL creates gates that are identities on the physical space (M7-G1 e); the pairing comparison of METHODS-lsh L1; 5. problems / assumptions (§10).

## 6. Acceptance tests and tolerances (why each number)

| Id | Tolerance | Justification |
|---|---|---|
| M7-A1 | exact integers | counts and bit rules |
| M7-K1 | 1e-12 | oscillator Fock space cut at 4 quanta per mode is exact on the tested states (≤ 3 quanta per mode after one raising operator); entries are products of ≤ 6 square roots; measured $1.2\cdot10^{-15}$ |
| M7-K2 | 1e-12 (LSH vs 6j, structure); 1e-10 (route A gauge) | same-arithmetic identities (measured $1.8\cdot10^{-15}$); route A carries the corner-singlet `eigh` rounding (M0-X4/X6 level, measured $8.9\cdot10^{-16}$) |
| M7-X1 | 1e-10 (spectra), 1e-12 (closed block) | as M0-X4: `eigvalsh` of a 433×433 matrix with $\|H\|\le6$; measured $1.0\cdot10^{-14}$ |
| M7-C1 | norms/overlaps 1e-12; Gauss of physical decodes 1e-10; fallback Gauss ≥ 0.5 − 1e-10; gauge residual 1e-10 | unit codes exact; analytic fallback bound $|G^z|\ge\tfrac12$ (measured min exactly 0.5); as M3-C1 |
| M7-C2 | 1e-12 (same-route identities, LSH vs spin-network target, block structure); 1e-10 (route A, ±β gauge) | `expm`/`eigh` of a Hermitian matrix with $\|H\|\le2$ (measured $1.1\cdot10^{-15}$) |
| M7-E1, B1, B2, B3, S1, V1 | error 1e-10, weights 1e-20, Gauss 1e-10, span leak 1e-12; angle-linearity 1e-9 with denominators ≤ 4 | exact-angle rule of prompts/003–004; float64 over ≤ 300 gates (measured $2.6\cdot10^{-14}$, Gauss $5\cdot10^{-16}$) |
| M7-B1, S1 cost sanity | `cx ≤ 188`, `1 ≤ n_rot ≤ 16`, `ancilla ≤ 16`; step: between 4 and 8 electric rotations per layer; skeleton angle-independent | twice the specified construction (94 / 4 / 7) excludes degenerate implementations without fixing the design; skeleton independence is the M8 validity rule |
| M7-E1 rotation bounds | `4 ≤ n_rot ≤ 8`, outer row +8..+12, `cx == 0` | one phase per link (4) is the minimum for a diagonal layer without CX; the LSH register spreads a link's flux over 2 bits (8); outer: 8 links, 12 bits |
| M7-V1 | counts exact: CX + 40, T + 32 | the transcoder is 4 × (2 `cx` + 1 `rccx`) each way; `rccx` = 3 CX, 4 T (METHODS §7) |
| M7-G1 | leak 1 ± 1e-12; Gauss ≥ 0.5 − 1e-10; error 2 ± 1e-10 | analytic values of the constructed wrong circuits (permutations and a $\pm1$ diagonal) |
| M7-T1 | synthesised: `tol_err = tol_gauss = n_rot ε + 1e-9`; band and 10 % as M1-T1 / M3-T1 | prompts/003–004 rule unchanged; measured 0.1–0.33 of the budget |
| M7-R1 | as the verification fields; structural keys | definition of the files (§5) |
| M7-L1, L2 | 900 s per `print_axioms`; exact | as M3; prototypes 10.8 s and 21 s |
| M7-L3 | 900 s; exact | prompts/006 §7 budget; ~290 gates on 433 unit states (spin network: ~160 gates) |

Checked in this run: `python -m pytest --collect-only -q tests/acceptance/m7` → 29 tests; `tools/pytest-safe -n 4 tests/acceptance/m7` → 29 failures, all `PENDING:`; with the prototypes served under the production names (`PYTHONPATH=scratch/planner/m7shim tools/pytest-safe -p shim_plugin -n 4 tests/acceptance/m7`) → 23 passed in 14.6 s, 6 `PENDING:` (3 Lean, 3 results); six mutated prototypes are rejected (`scratch/planner/m7shim/mutation_check.py`). No test builds an object larger than a 15 625-dimensional sparse operator; peak memory per worker < 1 GB.

## 7. Do-not-retry
- A CNOT-only frame for the LSH register: impossible (the plaquette move is affine with a non-trivial linear part; 8 different difference vectors). One `rccx` per site is the minimum of this construction.
- Exact `ccx` in the transcoder "to be safe": `rccx` is exact here (its phase is constant on every pair); `ccx` costs +24 CX, +24 T.
- Building the LSH operator from the 6j symbols or from route A and calling it LSH: `lsh/operators.py` uses loop-number arithmetic only; 6j and route A appear only in the tests and in `gauge_align`.
- Decoding AGL-violating codes to zero vectors, to a $J$-blind product state, or raising inside `decode_state` for them: use the rule of §1.4 (a $J$-blind fallback is rejected by M7-C1).
- Reading the outer register to decide bright/dark: not needed in this pairing ($J_c$ is on the 'in' site).
- Typing rotation angles; native `mcx` ≥ 3 controls / `mcrx` / `cu` / `unitary`; editing the files of the do-not-edit list (§0); `native_decide` in `lean/Su2Plaq/LSH/`.
- Raychowdhury–Stryker's uniform pairing for this plaquette (18 qubits touched, non-matching $H_B$; research 400 §6) unless Digonto asks for it (§10 D1).

## 8. Risks and stop conditions
- **Stop and ask Digonto** when: a locked tolerance or test is believed wrong; K1 or K2 fails with the prototype copied unchanged (would mean the installed `exact.spinnet` / `physical` differ from what the planner ran: commit `8822b0b`); a `pruning_bound` verdict on a circuit whose `op_norm_error` ≤ `tol_err`; a synthesised sum in $(\text{tol},\sqrt2\,\text{tol}]$ (prompts/004 §7); the LSH checker rejects the exact certificate while the numerical verdict is ok.
- Concurrency: other agents run `lake build` and compression rounds; `lake` takes a build lock — Lean steps may wait; never kill another agent's `lake`. All heavy commands under `tools/run-capped` (shared 24 GB slice).
- `print_axioms` on `Circuit.lean` loads Mathlib (≈ 8 GB): run `test_lsh_lean.py` with `-n 1` if the slice is busy.
- The evaluator's `inner_span` fast path builds an SVD of the 47 × 433 inner components: fine (0.5 s). The `physical` method on 31 qubits keeps one basis state per input (no growth: the only branching qubit is wire 0).
- L3 depends on adapting `spinnet/lean_export.py`; if its internals (`C._gate_records`, `E.omega_power`) changed since `8822b0b`, the planner amends the step, not the builder the shared modules.

## 9. What M7 provides for M8 (compression), by design
- `LSH` implements the same protocol as `SpinNet` (`inner_codes`, `physical_vectors`, `decode_state`, `target`, `inner_target`, `K_codes`, `layout_of`, `describe`, `import_map`), so the M8 hook `su2plaq/lsh/loop.py` can be a copy of `su2plaq/spinnet/loop.py` (`install()`: `_ENCODINGS["lsh"]`, `NOMINAL_ANGLES["lsh"] = (0.37, 0.61)`, worker command, `_certify` dispatch to `lsh.lean_export.certify`) without editing `compress/*`.
- Seeds: general (94 CX / $T_{10^{-6}}$ 598 for the step), and through `wrap_spinnet` the skeletons `pairs9`, `flags4`, `flags5`, `flags6` and (after M4) the spin-network archive best.
- Structure facts for the proposer spec (kernel-checked in 7.L1/7.L2): 5 site codes, 47 / 16 / 31, 433, transcoder bijection, $w_c$ available for free on wires 2, 5, 8, 11 after two CX per site, 305 outer patterns, AGL-trivial gates (M7-G1 e).
- Budgets: evaluation ≈ 0.5 s per circuit and angle pair; peak qubits 12 + 12 + 32 = 56 ≤ 62 (Lean certificate limit).

## 10. Decisions taken by default — for Digonto to confirm or change
- **D1 (pairing).** (inner | outer) point splitting at all four corners, as plan 001 §3 — not Raychowdhury–Stryker's uniform $(+e_1,+e_2\,|\,-e_1,-e_2)$ split, which on this plaquette touches 6 sites (18 qubits) and makes $H_B$ a non-matching operator with $\sqrt3$ entries (research 400 §6). On a periodic lattice the uniform split is the natural one.
- **D2 (register).** Raw LSH loop numbers, 1 qubit each: 24 qubits (12 data + 12 outer), site bit order $(\ell_{12},\ell_{23},\ell_{31})$, 'in' sites first. The reduced variant with the Abelian constraints solved (about half the registers, arXiv:1812.07554 Sec. IV) is not used: it would stop being the "LSH with Abelian link checks" row of the note.
- **D3 (cutoff).** Flux cap 1 on physical links, virtual flux up to 2 ($J\le1$): the 433 states of the other encodings. (Capping $J\le\tfrac12$ would give the 256-state space of note §7.)
- **D4 (general circuit).** Transcoder + the spin-network `general7` walk (94 CX, 4 rotations, 88 T, 7 ancillas). Cheaper wrapped skeletons exist already (`pairs9` 74 CX, `flags4` 84 CX / $T$ 330) and are reported as comparison rows and used as M8 seeds, as in M3/M4.
- **D5 (electric layer).** Stand-alone $U_E$ = 8 phases, no CX (alternative: 4 phases + 8 CX). In the step the layer sits inside the transcoded frame (4 phases per layer), so the step has 8 / 12 rotations.
- **D6 (outer electric row).** 12 phases on the 12 outer-site qubits (8 links spread over 12 bits), reported separately as for the other encodings.
- **D7 (signs).** Target in the LSH sign convention of arXiv:1912.06133, which coincides with route B; route A through `gauge_align`. External circuits are compared up to the pair-sign gauge as in M3.
- **D8 (Lean scope).** Kernel-checked counts and circuit structure + one native certificate with a new executable `su2plaq_cert_lsh`. The oscillator derivation of the ladder factors stays numerical (locked test), not formalised.

## 11. Expected cost
Builder: 7.0 ≈ 0.5 h; 7.1–7.2 ≈ 2 h (prototype exists); 7.3–7.4 ≈ 2 h; 7.5–7.8 ≈ 2 h; 7.9 ≈ 0.5 h; 7.10 ≈ 2 h; 7.L1 ≈ 0.5 h; 7.L2 ≈ 2 h; 7.L3 ≈ 4 h. Runtime: encoding build 0.35 s; `evaluate` ≤ 0.5 s per circuit (0.5 s for the 305-block outer row); `t_table` ≤ 1.2 s; m7 fast suite ≈ 15 s on 4 cores; `m7_results.py` ≈ 1–2 min; Lean `Counts.lean` 11 s, `Circuit.lean` 21 s, certificate expected < 5 min. Memory: Python ≤ 1 GB per worker (measured 0.29 GB for the whole prototype run); Lean ≤ 8 GB (`Circuit.lean`, Mathlib import), always under `tools/run-capped`.
