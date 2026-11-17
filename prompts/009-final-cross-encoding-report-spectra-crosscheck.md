# 009 — Final cross-encoding report (option (c)): spectra cross-check, tables, milestone M11

- Date: 2026-11-16. Git commit at planning time: `8f61336` (branch `merge-desktop-tracks`; the tree holds other agents' uncommitted step-B7 files).
- Trigger: coordinator request after Digonto's decisions of 2026-11-16 (STATUS "Decisions": (5) final cross-encoding report = option (c), one or two tables plus a planner-designed cross-check of energy spectra; (6) the report goes in `docs/`). Cross-track item, low number range.
- Inputs read: `notes/STATUS.md`, `prompts/001` §1 and §5, `prompts/008`, `docs/METHODS*.md`, `docs/report-{1,2,3,4,5,5-addendum,7,9,10}*.md`, `results/rishon/ks_projection.json`, `results/summary/encodings-gate-counts.md`, `reports/tests/419`.
- Research note with every number quoted here: `reports/research/006-cross-encoding-spectra-and-final-tables.md`. Methods: `docs/METHODS.md` §13 (new). Companion plan: `prompts/010-fuzzy-headline-rule-clifford-offsets.md` (the fuzzy headline; its tests H1–H3 live in the same folder and belong to this milestone).
- Plan in force after this file: the track plans stay in force for their milestones; **this file defines milestone M11** (cross-encoding comparison and final report). Locked tests: `tests/acceptance/m11/` (33 tests, new; 30 of this plan, 3 of prompts/010). No existing locked test is changed.
- Not an escalation: no earlier plan for this goal exists, so there is no "what went wrong before".

Words used (each once). *Same model* = two encodings related by a change of basis (all spectra and amplitudes agree); *different model* = no such basis change (different numbers of states). *Level* = eigenvalue of a Hamiltonian. *Isometry* = matrix $V$ with $V^\dagger V=1$; *compression* of $X$ = $V^\dagger XV$; *leak* = $(1-VV^\dagger)XV$. *Cross-verdict* (our label) = the production evaluator's verdict for the circuit of one encoding against the target built by another encoding's code. *Headline* = the archive entry a report quotes: smallest robust key $(\mathrm{CX},\sum T,\rho,\sum\mathrm{depth_{CT}},\mathrm{qubits})$ over the 20 locked angle pairs (METHODS §12.4); *$\bar T$* = $\sum T/20$ at $\varepsilon=10^{-6}$. *Closed sector* = states with no flux on the 8 outer links. *Flavour* (fuzzy) = sign of $\Psi\mapsto\Psi\Gamma_5$ on a link.

## 1. What the five encodings are (fixed facts)

| block | encoding | model | physical states | reports |
|---|---|---|---|---|
| A | twelve, spinnet, LSH | Kogut–Susskind (KS), $j_{\max}=\tfrac12$ | 433 | 1, 2 / 3, 4 / 7, (8) |
| B | rishon | SU(2) quantum link model + det term (Brower–Chandrasekharan–Wiese arXiv:hep-th/9704106; Wiese arXiv:1305.1602) | 38 432 | 5, 5-addendum, (6) |
| C | fuzzy | fuzzy gauge theory, kinetic term $\mathcal K_1+r\mathcal K_2$, $r=1$ (Alexandru et al. arXiv:2308.05253) | 101 197 218 (fixed far ends) | 9, 10 |

## 2. Decisions of this plan

| # | Question of the request | Decision | Why |
|---|---|---|---|
| i-a | same-model comparison | exact agreement at $10^{-10}$ on three levels: Hamiltonian spectra, step targets moved between sign conventions, and **cross-verdicts of the general and the compressed headline circuits** | the first two are already implied by the locked `gauge_align` checks of M0/M3/M7; the cross-verdict is new and tests the delivered circuits against a foreign construction (§4.1) |
| i-b | different models: what is honestly comparable | (1) exact identity: the KS link is a compression of the rishon link and of the fuzzy link, leak quantified; (2) a limit: the rishon model with a large det coupling and a tuned electric coupling reproduces the 433 KS levels, error $\propto1/L$ with a predicted coefficient; (3) fuzzy, $\mathcal K_1$ only: the closed sector of two flavour patterns is exactly the KS block; (4) fuzzy with $\mathcal K_2$: weak-coupling gap exponent 7 against the KS divergence, as in the paper | measured in prototypes (research 006 §3, §4); (2) and (3) are the planner's own derivations, to be labelled so |
| i-c | what is "different physics, not comparable" | state counts; spectra at equal $g^2$ outside (1)–(4); one-step unitaries and the shared observables of Reports 5 and 9; **gate counts across blocks**; any continuum-limit claim | METHODS §13.5 |
| ii-a | one table or several | **one gate table in three model blocks**, rows of blocks B and C marked "different model"; a second table for CX-first against T-first; a third for the spectra | a single table keeps the five encodings on one page; the block structure and the mark prevent reading across models |
| ii-b | headline per encoding | the robust-key minimum of each archive (CX first), quoted with $\bar T$ and with the nominal $T$; rishon: loop unit and unit + det layer; fuzzy: inner step composed from the two unit headlines (prompts/010) | METHODS §12.4; same rule for all |
| ii-c | CX-first against T | second column "T-first pick" = smallest key with $\sum T$ before CX; the CX–$\bar T$ Pareto front of every archive listed; one figure | Report 4 §3.4 did this for spinnet; now for all |
| iii | computations and tests | package `su2plaq.crosscheck` (not hashed), script `scripts/m11_results.py`, 30 locked tests (§6), steps 11.0–11.8 (§7) | — |
| iv | defaults | §12, each "default, not reviewed by Digonto" | — |

## 3. Method (equations; conventions of METHODS §1–§3, §13)

**3.1 Same model.** $H(g^2)=\tfrac{g^2}2H_E+\tfrac1{g^2}H_B$ (METHODS §2). The three encodings list the 433 states in the label order of `physical_basis(convention="cg")` and differ by signs: $H_B^{\rm twelve}=D_eH_B^{(e)}D_e$, $D_e=\mathrm{diag}(\pm1)$ = `Encoding.gauge` ($D_{\rm twelve}=1$). Transported target
$$T_{s\to d}(\text{kind},\alpha,\beta,\text{order})=D_sD_d\;V_s(\text{kind},\alpha,\beta,\text{order})\;D_dD_s .$$
Cross-verdict: `evaluate(circuit of d, encoding d, T_{s→d})`. Bauer–Fike (Numer. Math. 2 (1960) 137, doi:10.1007/BF01386217): for the normal matrix $e^{i\varphi}V$ every eigenvalue $\mu$ of the circuit block $A$ has $\min_\lambda|\mu-\lambda|\le\|A-e^{i\varphi}V\|_2\le$ `total_error`.

**3.2 Link compression.** For a normalised invariant state $s$ of the model link and the unit phase $c$ ($\arg c\in[0,\pi)$) define $V$ ($16\times5$, columns in the order of `LinkSpace(0.5).states`) by
$$V|0\rangle=s,\qquad V\,\sqrt2\,U^{\rm KS}_{ab}|0\rangle=\sqrt2\,U_{ab}\,s/c .$$
Claims: $V^\dagger V=1$; $V^\dagger U_{ab}V=cU^{\rm KS}_{ab}$; $V^\dagger L_aV=L_a^{\rm KS}$; $V^\dagger R_aV=R_a^{\rm KS}$; $V^\dagger H_E^{\rm link}V=j(j+1)$; $[VV^\dagger,L_a]=[VV^\dagger,R_a]=0$; $(V^{\otimes4})^\dagger WV^{\otimes4}=W^{\rm KS}$ with $W=\sum_{abce}U_b[a,b]\,U_r[b,c]\,U_t[e,c]^\dagger\,U_l[a,e]^\dagger$ (link $b$ least significant, as `exact.operators._build_W`). Models: `rishon_plus`/`rishon_minus` ($s=(A\pm B)/\sqrt2$, $c=1,i$; $H_E^{\rm link}=\tfrac12(L^2+R^2)$), `fuzzy_one`/`fuzzy_gamma5` ($s=\tfrac12\mathbb 1,\tfrac12\Gamma_5$ as row-major 16-vectors, $c=1$; $H_E^{\rm link}=\tfrac12\mathcal K_1$), `fuzzy_fplus`/`fuzzy_fminus` ($s=(\mathbb 1\pm\Gamma_5)/(2\sqrt2)$). Exact squared leaks: $\max_{ab}\|(1-P)U_{ab}V\|_2^2=\tfrac12,\tfrac12,1$; $\|(1-P^{\otimes4})WV^{\otimes4}\|_2^2=15,\tfrac{33}8,4$.

**3.3 KS limit of the rishon model.** $H=c_EH_E+c_BH_B+\lambda_DH_D$ on the 38 432 states ($H_D$ on all 12 links, METHODS-rishon R13) with
$$\lambda_D=-L,\qquad c_E=\frac{g^2}2-\frac{8L}3,\qquad c_B=\frac1{g^2}.$$
Statement: the 433 lowest levels of $H+24L$ tend to the 433 levels of the KS $H(g^2)$ (outer electric energy included), error $\propto1/L$; closed sector ($17\times17$, $H^{\rm closed}+8L$): $L(\lambda_k(L)-\lambda_k^{\rm KS})\to-\tfrac{13}{4g^4}w_k$, $w_k=|\langle{\rm loop}|\lambda_k^{\rm KS}\rangle|^2$, $k$ = lower, upper level of $\big[\begin{smallmatrix}0&-2/g^2\\-2/g^2&3g^2/2\end{smallmatrix}\big]$. Derivation: METHODS §13.3 (Schrieffer–Wolff, Bravyi–DiVincenzo–Loss arXiv:1105.0675).

**3.4 Fuzzy.** $H=\tfrac{g^2}4\sum_{\ell\in\rm inner}(a\mathcal K_1+b\mathcal K_2)-\tfrac2{g^2}\square$ (METHODS-fuzzy F3 at $a=1$, $b=r$). (a) Flavour blocks at $b=0$: cyclic subspace of the flavour vacuum $\bigotimes_\ell(\mathbb 1+F_\ell\Gamma_5)/(2\sqrt2)$ under $\sum\mathcal K_1$ and $\square$. (b) Isolated plaquette: the 50 Gauss-law states of the four inner links alone (`scripts/m9_results.py::isolated_plaquette_basis`); gap $=E_1-E_0$. (c) $\mathcal K_2$ on the embeddings of 3.2.

## 4. What is compared, with the measured numbers (research 006)

4.1 **Block A, exact** — spectra $\le2.8\times10^{-14}$; transported targets $\le3.0\times10^{-15}$; cross-verdicts of general circuits $1.1\times10^{-14}$ to $2.7\times10^{-13}$, of headline circuits $4.8\times10^{-15}$ (spinnet `r02-F1-002` against the LSH target) and $1.0\times10^{-13}$ (twelve `r05-F2-005` against the spinnet target, also at $(0.91,0.23)$); a foreign target at $\beta+10^{-6}$ rejected with block error $2.0000\times10^{-6}$.
4.2 **Compression identity** — all residuals $\le5\times10^{-16}$ for the six embeddings; leaks as in §3.2.
4.3 **Rishon → KS** — closed sector: prediction met to 0.17 % at $L=256$; full space at $L=128$: $L\max_k|\Delta_k|=7.095,\,2.197,\,0.746$ for $g^2=0.5,1,2$, slopes $-0.997,-1.001,-1.004$, next band $4L-7.3$ to $4L-9.6$ above.
4.4 **Fuzzy** — flavour patterns $(+,+,-,-)$, $(-,-,+,+)$: closed sector = KS block to $1.8\times10^{-15}$; twelve patterns dimension 3, two dimension 4, KS levels absent (distance $\ge0.608$). Isolated plaquette: $\mathcal K_1$ only: ground level twofold degenerate ($\le7\times10^{-15}$); $\mathcal K_2$ only: exponent 7.0004; $r=1$: 7.029; factor 16.002 for $b\to2b$; strong coupling gap$/2g^2=0.9999973$ at $g^2=16$. $\mathcal K_2$: $-4$ / $+2$ on $\tfrac12\mathbb 1$ and its flux copy, $+4$ / $-2$ on the $\Gamma_5$ copy; no matrix element of $\mathcal U$ between the copies ⇒ no KS limit inside $a\mathcal K_1+b\mathcal K_2$.
4.5 **Not comparable** — METHODS §13.5; the report states each item in one sentence with its number (433 / 38 432 / 101 197 218; closed sector 2 / 17 / 9 or 12 levels; rishon step at distance 1.990 from the KS step, `ks_projection.json`).

## 5. Interface (the builder creates stubs first; every public name raises `NotImplementedError` through `su2plaq._stub.todo`)

New package `src/su2plaq/crosscheck/` (`__init__.py`, `ks.py`, `embed.py`, `limits.py`, `report.py`). **It is in no hash list and must not be added to one** (it decides no verdict and no archive metric). It may import any production module; it must not modify a hashed file (`evaluate/*`, `encodings/*`, `rishon/{algebra,physical,operators}.py`, `fuzzy/compress_hook.py`, …).

### 5.1 `crosscheck/ks.py`
```python
KS_ENCODINGS = ("twelve", "spinnet", "lsh")
def ks_operators(encoding) -> tuple[np.ndarray, np.ndarray, np.ndarray]
    # (he_inner (433,), he_all (433,), HB (433, 433)) built by THAT encoding's own code, in its own sign convention, label order of physical_basis("cg")
    # twelve: exact.operators (route A); spinnet: exact.spinnet 6j route; lsh: lsh.operators
def ks_hamiltonian(encoding, g2, include_outer_electric=True) -> np.ndarray       # (g2/2) diag(he) + HB / g2
def gauge_signs(encoding) -> np.ndarray                                           # (433,) of +-1.0; all +1 for twelve
def transported_target(src, dst, kind, alpha, beta, order=1) -> np.ndarray        # D_s D_d V_s D_d D_s, V_s = get_encoding(src).target(kind, alpha, beta, order)
def step_circuit(encoding, which="general", alpha=0.37, beta=0.61, order=1) -> tuple[QuantumCircuit, dict]
    # "general": su2plaq.circuits.<encoding>.build_step(alpha, beta, order); info = {"which": "general", "entry": None}
    # "headline" (order 1 only): the program of robust.headline(encoding, "step", compute=False)["id"], rebuilt by the stock worker at (alpha, beta);
    #   info = {"which": "headline", "entry": id, "program_sha256": ...}; FileNotFoundError if no headline is cached; nothing is written
def cross_verdict(circuit_encoding, target_encoding, which="general", alpha=0.37, beta=0.61, order=1) -> Verdict
    # evaluator.evaluate(step_circuit(...)[0], get_encoding(circuit_encoding), transported_target(target_encoding, circuit_encoding, "step", alpha, beta, order))
```
### 5.2 `crosscheck/embed.py`
```python
LINK_MODELS = ("rishon_plus", "rishon_minus", "fuzzy_one", "fuzzy_gamma5", "fuzzy_fplus", "fuzzy_fminus")
def link_isometry(model) -> tuple[np.ndarray, complex]     # (V (16, 5), c) of §3.2; c = 1j for rishon_minus, 1 otherwise
def link_compression(model) -> dict
    # {"phase": c, "isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette": max-entry residuals, "leak_U": max_ab ||(1-P) U_ab V||_2, "leak_plaquette": ||(1-P4) W V4||_2}
```
Form the plaquette quantities from $5\times5$ factors (`kron` of four $V^\dagger XV$; the Gram matrix $(WV^{\otimes4})^\dagger(WV^{\otimes4})$ from $16^2$ products), never as a $65536\times625$ array.
### 5.3 `crosscheck/limits.py`
```python
def rishon_closed_block(c_e, c_b, lam_d) -> np.ndarray       # 17 x 17 Hermitian: c_e H_E + c_b H_B + lam_d H_D^in on the closed inner states (16 electric vacua + loop)
def rishon_levels(c_e, c_b, lam_d, k=None) -> np.ndarray     # sorted levels of c_e H_E + c_b H_B + lam_d H_D (12 links) on the 38 432 physical states; the k lowest if k is given
def rishon_ks_limit(g2, L) -> dict                           # {"g2", "L", "levels": 433 lowest of rishon_levels(g2/2 - 8L/3, 1/g2, -L) + 24 L, "ks_levels": 433 KS levels (outer electric included), "max_dev", "gap_to_next_band": level 434 - level 433}
def fuzzy_isolated_levels(g2, a=1.0, b=1.0) -> np.ndarray    # 50 sorted levels of (g2/4) sum_l (a K1 + b K2) - (2/g2) square on the Gauss-law states of the isolated plaquette
def fuzzy_flavour_block(g2, signs) -> np.ndarray             # (g2/4) sum K1 - (2/g2) square on the cyclic subspace of the flavour vacuum, signs = (F_b, F_r, F_t, F_l) in +-1; basis vector 0 = that vacuum
```
Recipes (prototype `scratch/planner/c009/shim/proto/limits.py`, which the builder may read but must not copy blindly): `rishon_levels` — project code-level operators with $P^\dagger TP$ exactly as `rishon.physical.det_sector_structure` does ($H_B$ from `operators.h_magnetic_inner`, a det term = nibble flip $A\leftrightarrow B$ with amplitude 2, $H_E=\tfrac34\times$ number of quartet links), split into the connected components of $|H_B|+|H_D|$ (305 blocks, largest 4352) and use dense `eigvalsh` per block; `rishon_closed_block` — the three operators restricted to the closed codes (`operators.closed_block_full` at two couplings gives $H_E$, $H_B$, $H_D$ by linear combination); `fuzzy_isolated_levels` — move `isolated_plaquette_basis` out of `scripts/m9_results.py` into this module (the script then imports it; a unit test compares the two projectors), project $\sum\mathcal K_1$, $\sum\mathcal K_2$, $\square$ once, and diagonalise $-\square+\tfrac{g^4}8(a\mathcal K_1+b\mathcal K_2)$ times $2/g^2$ (keeps the tiny weak-coupling gap accurate); `fuzzy_flavour_block` — the construction of `fuzzy.observables._blocks` with the flavour vacuum as start vector and generators ($\sum\mathcal K_1$, $\square$).
### 5.4 `crosscheck/report.py` and `scripts/m11_results.py`
```python
def spectra_results(out=None, root=None, headline=True) -> dict   # out=None: write <root>/results/crosscheck/spectra.json; out=False: write nothing; else the given path
def gate_table(out=None, root=None) -> dict                        # same rule, <root>/results/crosscheck/gate-table.json
def render(root=None) -> str                                       # Markdown of Tables 1-3 from the two files
def tradeoff_figure(out=None, root=None) -> pathlib.Path           # results/crosscheck/tradeoff.pdf: CX against T_avg, one panel per archive
```
`python scripts/m11_results.py [--no-headline] [--root R]` runs the four. Both files carry `provenance` (the dict of `metrics.provenance.provenance` plus `"command"`).

`spectra.json`, schema `"crosscheck-spectra-1"`: `ks` = {`max_pairwise_level_dev` {"0.5","1.0","2.0"}, `levels` {…: 433 levels of the twelve construction with outer electric}, `hb_multiplicities` {encoding: {value: count}}, `transported_target_max`, `cross_verdicts` [{`circuit`, `target`, `which`, `entry`, `alpha`, `beta`, `ok`, `total_error`, `certified`, `outer_bits_read`, `seconds`}] — general: the cyclic pairs (twelve, lsh), (spinnet, twelve), (lsh, spinnet) at the nominal pair; headline: (twelve, spinnet), (spinnet, lsh), (lsh, twelve) at $(0.37,0.61)$ and $(0.91,0.23)$, an encoding without a cached headline is skipped}; `embedding` {model: {`isometry`,`U`,`L`,`R`,`HE`,`P_commutes_generators`,`plaquette`,`phase` [re, im],`leak_U_sq`,`leak_plaquette_sq`}}; `rishon_ks_limit` = {`rule`, `closed` [{`g2`,`L`,`dev`,`L_times_dev`,`predicted`}] for $L\in\{16,…,1024\}$ (powers of 2), `full` [{`g2`,`L`,`max_dev`,`L_times_max_dev`,`gap_to_next_band`}] for $L\in\{64,128\}$}; `fuzzy` = {`flavour_blocks` [16 × {`signs`,`dim`,`ks_level_distance` {g2}}], `isolated` {`k1_only` {`g2`,`ground_splitting`,`third_level`}, `k2_only` and `r1` {`g2` starting [0.15, 0.2, …], `gap`, `slope_first_pair`, `gap_over_2g2_at_16`}}, `k2_on_embeddings` {`fuzzy_one`: [-4,2,2,2,2], `fuzzy_gamma5`: [4,-2,-2,-2,-2]}}; `closed_sector_table` = {`g2`, `ks` {g2: 2 levels}, `rishon` {"lam_d=0","lam_d=0.2","lam_d=0.5": {g2: 17 levels}} (`operators.closed_block_full`), `fuzzy` {"r=0": {g2: 9 levels}, "r=1": {g2: 12 levels}} (`fuzzy.observables.closed_sector`)}.

`gate-table.json`, schema `"crosscheck-gate-table-1"`: `unit` (text), `rows` in the order twelve, spinnet, lsh, rishon, fuzzy, each {`encoding`, `block` ("A","A","A","B","C"), `model`, `n_physical_states`, `comparable_with` (the other encodings of the block), `general` {`qubits`,`cx`,`n_rot`,`t_fixed`,`t_1e6`,`source`} read from `results/<enc>/step.json` (rishon: `step3.json`; plus `general_two_layer` from `step.json`), `headline` {`entry`,`loop_unit`,`qubits`,`cx`,`t_nominal`,`t_mean`,`depth_mean`,`angle_linear`,`offset_class`,`lean`,`source`} or null, `t_first` {`entry`,`cx`,`t_mean`} or null, `status` = "final" or "pending: …"}. Picks from `robust.headline(enc, kind, compute=False)["ranking"]`: headline = smallest (`robust_key`, `laptop_key`, `id`); T-first = smallest (`robust_key[1]`, `robust_key[0]`, `robust_key[2:]`, `laptop_key`, `id`). Rishon also `headline_with_det` {`cx`,`t_nominal`,`source`} from `results/compress/rishon/three-layer.json` (null and status pending until prompts/204 step C5). Fuzzy: `units` {`fuzzy_ub`, `fuzzy_link`: headline cells}, `headline` and `t_first` composed as $U_B$ unit + 4 link units (`cx`, `t_mean`, `t_nominal` summed that way; `source` = `results/fuzzy/compressed_step_headline.json`, status pending until it exists). A row is "final" only if every source file and headline cache it quotes exists.

## 6. Acceptance tests added (none changed) and tolerances

`tests/acceptance/m11/` — validated against the planner's reference implementation (research 006 §7): the 24 tests that need neither a result file nor a headline cache pass (K1–K3, E1–E3, F1–F3, H1; full run 24 passed and 9 `PENDING` in 121 s with 4 workers); all 33 fail with `PENDING:` without it; `pytest --collect-only -q tests/acceptance` → 407 tests. Marked slow: K4 (3), E3 at $g^2=0.5$ and 2, E3_levels, H2 (2), H3.

| File :: id | What | Tolerance | Justification |
|---|---|---|---|
| `test_cross_ks.py` :: `K1_ks_operators[3]` | $H_E$ values from the labels; $H_B$ Hermitian with multiplicities $16,96,16,177,16,96,16$; `ks_hamiltonian` composition | $10^{-12}$; counts exact | definitions; Lean-certified multiplicities (METHODS §11.3 b) |
| `K1_spectra_agree` | 433 levels pairwise equal at $g^2=0.5,1,2$, with and without outer electric; closed-sector levels present | $10^{-10}$ | project tolerance for two constructions of one operator (prompts/001 §1); measured $2.8\times10^{-14}$ |
| `K2` | signs $\pm1$; transported target = sign conjugation ($10^{-12}$) and = destination's own target | $10^{-10}$ (2-norm) | measured $3.0\times10^{-15}$ |
| `K3[3]` | general circuit against a foreign target: ok, certified, 433 inputs, `total_error`, Gauss; mutant $\beta+10^{-6}$ rejected | $10^{-10}$; block error in $[1.9,2.1]\times10^{-6}$ | exact-angle rule (prompts/004); $\|H_B\|\delta=2\times10^{-6}$, measured $2.0000\times10^{-6}$ |
| `K4[3]` (slow) | headline circuit against a foreign target at $(0.37,0.61)$ and $(0.91,0.23)$; mutant | same | measured $4.8\times10^{-15}$, $1.0\times10^{-13}$ |
| `test_cross_models.py` :: `E1[6]`, `E1_det` | §3.2 identities with operators taken from the models' own modules; exact leaks; det term $\pm2$ on the singlets | $10^{-12}$; squared plaquette leak $10^{-6}$ | algebra of $16\times16$ matrices with entries $\le2$, measured $\le5\times10^{-16}$ (the project's algebra tolerance, METHODS-fuzzy F6); the plaquette leak is a difference of Gram matrices (rounding $\sim10^{-13}$) of the exact numbers $15,\tfrac{33}8,4$ |
| `F3` | $\mathcal K_2$ eigenvalues on the two fuzzy embeddings, orthogonality, vanishing cross elements, ordering consequence | $10^{-12}$ | same |
| `E2` | `rishon_closed_block` spectrum = formula of METHODS-rishon R13 with independent couplings; limit coefficient at $L=256$; slopes $128\to256$; next level | $10^{-12}(1+\|B\|)$; 1 %; $|{\rm slope}+1|\le0.01$; $0.2$ | remainder $O(1/L)$: measured 0.17 %, 0.0024, 0.055 — margins 6, 4, 3.6; a wrong coefficient ($\tfrac{12}4$ or $\tfrac{14}4$) is off by 7.7 % |
| `E3[g2=1]`, `E3[0.5]`, `E3[2]` (slow) | 433 lowest levels against KS at $L=64,128$: slope; coefficient $\tfrac{13}{4g^4}w_{\rm upper}$; gap to level 434 in $[4L-12,4L]$ | $|{\rm slope}+1|\le0.02$; 1 %; as stated | measured slopes $-0.9973,-1.0010,-1.0043$ (margin 4.6); coefficient 0.17 %, 0.08 %, 0.30 % (margin 3.3); gaps $4L-7.3$ to $4L-9.6$ |
| `E3_levels` (slow) | `rishon_levels` at the project couplings: 38 432 levels; lowest $=\tfrac34g^2-\sqrt{\tfrac9{16}g^4+32g^{-4}}$, 256-fold | $10^{-10}$; count exact | Report 5 §3.4 closed form |
| `F1` | all 16 flavour patterns: dimensions; KS block exact for the two aligned patterns; KS levels absent elsewhere | $10^{-10}$; distance $\ge0.5$ | measured $1.8\times10^{-15}$; smallest distance 0.608 |
| `F2` | 50 levels; $\mathcal K_1$ only: splitting, third level; exponents; factor 16; strong coupling | $10^{-10}$, $\ge0.5$; $7\pm0.02$ ($\mathcal K_2$), $7\pm0.06$ ($r=1$); $16\pm0.32$; $10^{-4}$ | measured $\le7\times10^{-15}$, $\ge0.845$; 7.0004, 7.029 (corrections $\propto g^4$); 16.002; $2.7\times10^{-6}$ |
| `test_cross_results.py` :: `R1` | `spectra.json`: every stored number inside the tolerances above; two numbers recomputed; `render` names the models and files | as above; recomputation $10^{-6}$ ($L\cdot$dev), $10^{-10}$ (levels) | file = function output |
| `T1` | `gate-table.json`: blocks, state counts, general numbers = committed files, picks = robust ranking, fuzzy and det arithmetic | exact integers; $\bar T$ to $10^{-9}$ | definitions |
| `T2` | completeness gate: five rows final, headline cross-verdict for each KS encoding, clean provenance | exact | the final report must not be written from partial inputs |
| `test_headline_rule.py` :: `H1`, `H2[2]`, `H3` | prompts/010 | there | there |

Numbers behind a tolerance come from `scratch/planner/c009/*.json` (research 006). No tolerance was chosen to make a failing prototype pass; every limit test was measured at 3 to 6 times below its bound.

## 7. Milestone M11 — steps

Rules for every step: orient with `graphify query/explain` before reading files; `graphify update .` after code changes; fast check `tools/pytest-safe -n 4 tests/unit`; acceptance runs with `PYTEST_MEM_MAX=11G tools/pytest-safe -n 4 …`; never bare `pytest -n auto` on acceptance; unit tests for every new function.

| Step | Builds | Done-check (tester runs it) | Acceptance ids that must turn green |
|---|---|---|---|
| 11.0 | stubs for §5 (and for prompts/010 §4) | `tools/pytest-safe -n 4 tests/acceptance/m11 -q` → 33 failed, every message `PENDING:`; `pytest --collect-only -q tests/acceptance` clean (407) | — |
| 11.1 | `ks.py`: `ks_operators`, `ks_hamiltonian`, `gauge_signs`, `transported_target` | signs of twelve all $+1$; six ordered pairs | `test_cross_ks.py::test_M11_K1_ks_operators_of_each_encoding` (3), `::test_M11_K1_spectra_agree_between_the_three_constructions`, `::test_M11_K2_gauge_signs_and_transported_targets` |
| 11.2 | `ks.py`: `step_circuit`, `cross_verdict` | tester repeats one cross-verdict with its own evaluator call and one extra mutant (wrong order) | `::test_M11_K3_general_circuit_against_another_encodings_target` (3); slow, once the headline caches exist (prompts/008 Phase C): `::test_M11_K4_…[twelve-spinnet]`, `[spinnet-lsh]` |
| 11.3 | `embed.py` | tester recomputes one $V$ by an independent route (e.g. Casimir eigenvectors) | `test_cross_models.py::test_M11_E1_ks_link_is_a_compression_of_the_model_link` (6), `::test_M11_E1_rishon_det_term_separates_the_two_singlets`, `::test_M11_F3_fuzzy_k2_orders_the_flux_copies_against_the_plaquette` |
| 11.4 | `limits.py`: rishon functions | tester: 305 blocks, largest 4352; level count 38 432; peak memory $<1$ GB | `::test_M11_E2_rishon_closed_sector_reaches_the_ks_block`, `::test_M11_E3_rishon_433_lowest_levels_reach_the_ks_spectrum[1.0]`; slow: `[0.5]`, `[2.0]`, `::test_M11_E3_rishon_levels_at_the_project_couplings` |
| 11.5 | `limits.py`: fuzzy functions (+ `isolated_plaquette_basis` moved, `scripts/m9_results.py` importing it; `results/fuzzy/*.json` must not change) | tester: 50 states, Gauss residual $\le10^{-12}$; `python scripts/m9_results.py` splitting row unchanged | `::test_M11_F1_fuzzy_flavour_sectors_at_r0`, `::test_M11_F2_fuzzy_isolated_plaquette_gap` |
| 11.6 | `report.spectra_results`, `scripts/m11_results.py`; first `spectra.json` (headline cross-verdicts for the archives that have a cache) | file reproducible bit for bit except `seconds` and provenance time | `test_cross_results.py::test_M11_R1_spectra_results_file` (needs 11.7 for `render`) |
| 11.7 | `report.gate_table`, `render`, `tradeoff_figure`; first `gate-table.json` | tester recomputes every cell of Table 1 from the source files | `::test_M11_T1_gate_table_file`, `::test_M11_R1_spectra_results_file` |
| H.1–H.3 | prompts/010 | there | `test_headline_rule.py` H1, H2 (2), H3 |
| 11.8 | after `milestone-6` (rishon replay C2, `three-layer.json`, Report 6), the M8 gate (LSH loop, Report 8), the M2c gate (prompts/008 Phase C) and H.3: re-run `scripts/m11_results.py` on a clean commit (worktree, as the other tracks do) | `git_dirty` false in both files | `::test_M11_K4_…[lsh-twelve]`, `::test_M11_T2_final_report_inputs_complete` |
| gate | tester full (m0…m11 + unit + `acceptance-check`) → auditor (physics of §3, wording of §8) → benchmark (new quantity: wall time of `scripts/m11_results.py`) → tag `milestone-11` → **Report 11** | — | all 33 |

Steps 11.1–11.7 and H.1 do not depend on any other track and can start now (they touch no hashed file, so they do not disturb the consolidation window). K4, H2, H3, T1's final rows and T2 wait for the items named.

## 8. The final report (written by the coordinator from the two JSON files and the earlier reports)

File: `docs/report-11-cross-encoding-comparison.md` ("Report 11"). Order: (1) what was asked, (2) what was done, (3) results and what they mean, (4) problems and assumptions; plain English, every jargon word defined once, math in LaTeX, every number with source file and commit.

- **§3.1 The five encodings and three models** — the table of §1 with one sentence per model; statement that blocks B and C are other theories on the same lattice, with the citations of §9.
- **Table 1 (gate counts, one table, three blocks).** Columns: block | encoding | model (blocks B, C marked "different model — compare within the row only") | register (qubits of the step circuit) | general step: CX, rotations, fixed T, $T(10^{-6})$ | compressed headline: entry id, qubits, CX, rotations, $T$ nominal, $\bar T$, angle-linear, Lean | factor general/headline in CX and in $\bar T$ | outer rows (separate, uncompressed: KS 8 phases; LSH 12; rishon outer electric and det rows; fuzzy 80 rotations) | source. Rows: twelve, spinnet, LSH; rishon (two lines: loop unit $U_BU_E$, and three-layer step with det); fuzzy (inner step composed from the unit headlines; the two unit lines beneath it). Below the table: one sentence that ratios between blocks are not efficiency statements.
- **Table 2 (CX first against T first).** Per archive: headline (CX, $\bar T$) | T-first pick (entry, CX, $\bar T$) | general (CX, $\bar T$ or $T$) | Pareto front points. Sentence per archive on which cost model would pick which entry (the project ranks CX first, prompts/001 §1). Figure `results/crosscheck/tradeoff.pdf`.
- **Table 3 (spectra cross-check).** 3a same model: largest level difference per $g^2$, cross-verdict errors (general, headline), the rejected mutant. 3b compression identity: residuals and the leak table. 3c limits: rishon $L\cdot$dev table and slope, predicted coefficient; fuzzy flavour sectors. 3d side-by-side closed-sector levels at $g^2=0.5,1,2$ (KS 2; rishon 17 at $\lambda_D=0,0.2,0.5$; fuzzy 9 at $r=0$, 12 at $r=1$) and the gap exponents at weak and strong coupling — headed "different models: these numbers are not expected to agree". 3e the list of §4.5.
- **§4 Problems and assumptions** — every default of §12 and of prompts/010 §8 as "default, not reviewed by Digonto"; the planner's own derivations named as such; provenance flags (fuzzy general results from a dirty tree `8e71c38`, reproduced by tester 301).

**Still missing before Report 11 can be complete** (T2 stays red until then): Report 6 (rishon compression; waits for replay C2 and `three-layer.json`, prompts/204–205); Report 8 (LSH compression; M8 phases 1–2 after prompts/008 Phase B, prompts/401); the Report 10 update (fuzzy headline `r10-F1-010`, composed headline step, "angle-linear: no (Clifford offsets)" for the archive best; prompts/010); the M2c gate (headline caches and `summary.json` headline for twelve, fuzzy_ub, fuzzy_link). Also open and to be listed: no Lean certificate for rishon and fuzzy circuits (`n_a`).

## 9. References (each opened in this run; details in research 006 §1)
arXiv:2308.05253 (fuzzy; Eq. 34, Sec. IV B, Fig. 3, Sec. VI); arXiv:hep-th/9704106 and arXiv:hep-lat/0309182 (quantum link models, dimensional reduction; abstracts); arXiv:1305.1602 Sec. 4.3 (det term); arXiv:2104.00025 (large-$S$ route for U(1) links; abstract); arXiv:1105.0675 (Schrieffer–Wolff; abstract); doi:10.1007/BF01386217 (Bauer–Fike); arXiv:1912.06133 (LSH). The compression identity, the rishon KS limit and the flavour-sector statement were not found in these sources: they are derivations of this plan.

## 10. Expected cost

| Item | Wall time | Memory | Source |
|---|---|---|---|
| K1, K2 | $<20$ s | $<1$ GB | prototype |
| K3 | 16 s (twelve), $\le10$ s others, shared machine | 0.8 GB | shim run |
| K4 | 15–30 s per case with a warm headline cache | 0.8 GB | prototype (13.5 s per evaluation of the twelve headline) |
| E1 (each), F3 | 2–5 s; $<1$ s | $<0.5$ GB | shim run |
| E2 | 5 s | — | shim run |
| E3 per coupling | 20 s alone (6 s setup + 5.5 s per diagonalisation pass), 51 s on the shared machine | 0.55 GB | prototype |
| F1, F2 | 2 s; 15–68 s (shared machine) | $<1$ GB | shim runs |
| `scripts/m11_results.py` | about 4–5 min (prototype 247 s for `spectra_results` with two headline circuits) | $<1$ GB | `validate_results.log` |
| not-slow m11 suite | about 2 min with 4 workers | $<1$ GB per worker | shim runs: 21 tests in 107 s; all 33 (slow included) in 121 s on the shared machine |
| builder calls | 11.0–11.5: one each; 11.6–11.7: 1–2 | — | estimate |

## 11. Do-not-retry list
- Extracting the circuit's physical block from `evaluate` by editing `evaluate/evaluator.py` (hashed; every archive would go stale inside the consolidation window) — use cross-verdicts and Bauer–Fike.
- Forming $WV^{\otimes4}$ as a dense $65536\times625$ array (0.66 GB per copy) or any dense operator on the 38 432 states.
- Comparing rishon or fuzzy with KS "at equal $\beta$" as if agreement were expected (Reports 5 and 9 already show order-one differences; that is the physics).
- Looking for a KS limit of the fuzzy model by scanning $(a,b)$ in $a\mathcal K_1+b\mathcal K_2$: excluded by the lemma of §4.4 (scan in research 006 §4.3).
- Computing the weak-coupling gap from unscaled levels at $g^2<0.1$ (the gap falls below the rounding of the level scale).
- Quoting the archive best instead of the headline in the final table, or a nominal-angle $T$ without $\bar T$.

## 12. Risks and stop conditions
- **A cross-verdict fails for a headline circuit** (K4 red with `total_error` $>10^{-10}$ while the entry is valid in its own archive): that would mean the encoding's own target differs from the others — contradicts M0/M3/M7. Stop, send to the fixer with the verdict; if no bug is found, stop and ask Digonto (a result contradicting established checks).
- **E3 coefficient outside 1 %** with a correct-looking implementation: check the level matching (sorted levels) and the shift $24L$ first; if the numbers of research 006 §3.2 cannot be reproduced, return to the planner.
- **Phase C replay changes an archive best or a headline** (ids in §8 and research 006 §6 are from the pre-replay state): the tests take ids from `robust.headline`, so they follow; the report text must be re-read against `gate-table.json`.
- **LSH loop not finished**: K4[lsh], T2 stay PENDING; do not weaken T2 — Report 11 is then issued as "draft, LSH compression pending" only if Digonto asks for it.
- Stop and ask Digonto when: an agent believes a tolerance of §6 is wrong; the auditor disputes one of the three derivations (compression identity, rishon limit, flavour sectors) and no error is found in the numerics.

## 13. Defaults taken in this run — each one "default, not reviewed by Digonto"
D1. Milestone number 11, test folder `tests/acceptance/m11`, plan numbers 009/010 and research numbers 006/007 in the low cross-track range (`next-num` proposed 402 for both folders), report name "Report 11", file `docs/report-11-cross-encoding-comparison.md`.
D2. One gate table in three model blocks with "different model" marks, not separate tables.
D3. Headline per encoding = robust-key minimum (CX first), shown with $\bar T$ and nominal $T$; T-first pick as a second column; Pareto fronts and one figure.
D4. Unit of the table = first-order step on the inner links, outer rows separate; rishon shown as loop unit and as three-layer step with det; fuzzy as the inner step composed from the two unit headlines at $r=1$.
D5. Couplings of the spectra tables: $g^2\in\{0.5,1,2\}$; $\lambda_D\in\{0,0.2,0.5\}$; $r\in\{0,1\}$; limit parameter $L\in\{64,128\}$ (full space) and up to 1024 (closed sector).
D6. The rishon KS limit is formulated with three independent couplings ($c_E$ may be negative); it is presented as a property of the model family, not of the project's nominal point.
D7. Fuzzy comparisons = compression identity, flavour-sector statement at $r=0$, weak- and strong-coupling gap; and the statement that no KS limit exists inside $a\mathcal K_1+b\mathcal K_2$. $\mathcal K_3=\Gamma_5$ of the paper (its Eq. 38) is not in the project's model and was not examined.
D8. Cross-verdict pairs are cyclic (three general, three headline), not all six.
D9. `su2plaq.crosscheck` is not hashed; results under `results/crosscheck/`.
D10. Only `E3[g2=1]` runs in the not-slow set; the other two couplings and the 38 432-level test are slow.
D11. T2 ties the M11 gate to Reports 6 and 8 and the Report 10 update (no partial final report).
D12. The three derivations are reported as "our derivation, verified numerically", without a literature claim.
