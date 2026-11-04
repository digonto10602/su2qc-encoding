# Test report 006 — M0 step 0.6: route B (spin network, 6j) and route A/B comparison

- Date: 2026-11-04
- Git commit: `038bc89` (HEAD) plus the uncommitted step-0.6 files (`src/su2plaq/exact/spinnet.py`, `src/su2plaq/exact/compare.py`, `tests/unit/test_spinnet_unit.py`)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (§2 interface, §3 row 0.6); formula in `docs/METHODS.md` §5
- Mode: step. Related reports: 003 (algebra), 004 (physical states), 005 (operators).
- Raw numbers: `results/m0_step06_tester_routeb.json`; scripts `results/m0_step06_tester_indep_routeb.py`, `results/m0_step06_tester_corner_bruteforce.py` (seed for the random gauge: 20261104).

## Commands run
```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "h_magnetic_phys_6j"
pytest -n auto tests/unit                       # 71 passed
pytest -n auto tests/acceptance/m0 -p no:cacheprovider      # 22 passed, 11 PENDING
pytest tests/acceptance/m0/test_{spinnet,algebra,geometry,physical,operators}.py -v   # 22 passed
python tools/check_lock.py ; ~/.claude/bin/acceptance-check        # LOCK OK / PASS (acceptance-v2)
pytest --collect-only -q tests/acceptance       # 84 collected, clean
python results/m0_step06_tester_indep_routeb.py ; python results/m0_step06_tester_corner_bruteforce.py
```

## 1. Official checks

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| unit tests (`tests/unit`) | all pass | 71 passed | — | PASS |
| M0-X4 spectra A vs B | max spectral difference | PASS (my own recomputation: 1.1e-14 / 4.8e-15 / 7.1e-15 at $g^2$ = 0.5 / 1 / 2) | 1e-10 | PASS |
| M0-X5 outer blocks + J | structural zeros, 128 blocks, K restriction | PASS | 1e-10 / 1e-12 | PASS |
| M0-X6 gauge_align on K | residual, D real | PASS | 1e-10 | PASS |
| earlier m0 tests (A1–A3, G1, G2, C1–C6, X1, X2, X3, X7, X8) | pass | 19 / 19 passed | — | PASS |
| `acceptance-check`, `check_lock.py` | pass | PASS, acceptance-v2, 84 tests collected | — | PASS |
| remaining m0 failures | PENDING only | 11 failures, all message `PENDING: NotImplementedError: <x> is not built yet` (`TwelveQubit` x3, `pygridsynth_word` x3, `run_batch` x2, `ct_compile`, `logical_metrics`, `save_result`) — evaluator/metrics/results are steps 0.7+ | — | PENDING (not failures) |

Counts: passed 93 (71 unit + 22 acceptance), failed 0, pending 11. New failures vs. report 005: none.

## 2. Independent physics (own script, nothing taken from `tests/`)

### (1) Independence of route B from route A
Static imports: `spinnet.py` imports only `itertools`, `numpy`, `su2plaq.geometry`, `su2plaq.su2.wigner` (`f_symbol`, `triangle`); `compare.py` imports only `numpy` and `spinnet.inner_labels`; `wigner.py` only `math`, `functools`; `geometry.py` only `dataclasses`. Run-time check: after `import su2plaq.exact.spinnet, su2plaq.exact.compare`, `sys.modules` contains only `su2plaq, .exact, .exact.compare, .exact.spinnet, .geometry, .su2, .su2.wigner`. `physical.py` and `operators.py` are never loaded. **PASS.**

### (2) My own derivation of the corner factor
At corner $c$ the loop passes from inner link $p$ to inner link $n$. The corner piece of the plaquette is a scalar product of two rank-$\tfrac12$ tensor operators $E_p\cdot E_n=\sum_a(-1)^{1/2-a}E^a_pE^{-a}_n$, where $E^a|j,m\rangle=\sum\langle j\,m\,\tfrac12\,a|j'\,m+a\rangle|j',m+a\rangle$. In the (inner pair | outer pair) intertwiner basis $|(j_pj_n)J,(j_1j_2)J;0\rangle$ it is diagonal in $J$ and independent of $j_1,j_2$ (Edmonds Eq. 7.1.6):
$$\langle (j_p'j_n')J|E_p\!\cdot\!E_n|(j_pj_n)J\rangle=(-1)^{j_p+j_n'+J}\begin{Bmatrix}J&j_n'&j_p'\\ \tfrac12&j_p&j_n\end{Bmatrix}\langle j_p'\|E\|j_p\rangle\langle j_n'\|E\|j_n\rangle .$$
I extracted the reduced elements numerically from Wigner–Eckart (3j with sympy): $\langle j'\|E\|j\rangle=-\sqrt{2j'+1}$ for all 5 transitions at $j\le1$. A link with spin $j\to j'$ has two ends (two corners) and the normalised link states $\sqrt{2j+1}D^j_{mm'}$ give $\sqrt{(2j+1)/(2j'+1)}$ per link. The product per link is $\sqrt{(2j+1)(2j'+1)}$ as in the builder's $F$-symbol form. The corner 6j is the same symbol as the builder's $\{J\,j_p\,j_n;\ \tfrac12\,j_n'\,j_p'\}$ (swap upper/lower in two columns).

Results (sympy `wigner_6j`, my own phase $e^{i\pi(j_p+j_n'+J)}$, my own link norms), 47 inner labels:

| comparison | got |
|---|---|
| $\max\|\,|P_{\rm mine}|-|P_{\rm builder}|\,\|$ | 8.9e-16 |
| $P_{\rm mine}/P_{\rm builder}$ over the 16 non-zero entries | exactly $1+0i$ for all (no sign flips, no gauge needed) |
| $K_{\rm mine}$ vs $K_{\rm builder}$ directly / after own gauge fit | 1.8e-15 / 1.8e-15 |
| 433 labels: route A vs **my** route B, own gauge fit | 8.9e-16 |
| 433 labels: route A vs builder route B, own gauge fit | 2.7e-15 (modulus 2.7e-15) |
| unsymmetrised $\Psi^\dagger W\Psi$ (route A, built by me) vs builder $P$ | moduli 1.6e-15, gauge residual 1.6e-15; $P$ symmetric exactly, $P_{\rm vac,all}=P_{\rm all,vac}=1$ |

**Verdict: my formula agrees with the builder's mapping in magnitude and sign.** The corner phase $(-1)^{1/2}$ per corner, which is ill-defined for one corner, gives $(i)^4=1$ for the 4 corners. This agrees with the plan's pairs $(p,n)$: c0 $(l,b)$, c1 $(b,r)$, c2 $(r,t)$, c3 $(t,l)$, which I also checked against `geometry.py` (loop $b\,r\,t^\dagger l^\dagger$: c0 has links b,l out; c1 b in, r out; c2 r,t in; c3 t out, l in).

Corner-level brute force (explicit CG singlets for four legs $(l,b,o_1,o_2)$, $o_i\in\{0,\tfrac12,1\}$, operator $E\cdot E$ built from CG matrices; scalar property checked: $[C,J^{z,+}]\le2.2\times10^{-16}$):
pairing $(l\,b|o_1o_2)$: amplitude is $J$-diagonal (J off-diagonal max 0), spread over all admissible outer spin pairs 4.4e-16, and equals $\sqrt{(2j_l'+1)(2j_b'+1)}\,|\{6j\}|$ to 4.4e-16 (all 8 inner transitions tested).

Negative controls on the 47×47 comparison (they show what the comparison does and does not discriminate):
- dropping the link-normalisation factors: modulus mismatch 2.25 (detected);
- swapping the primed arguments of `f_symbol`: modulus mismatch 1.0 (detected);
- dropping the Edmonds phase or swapping $p\leftrightarrow n$ at c0: **not detected** (diff 1.8e-15), because the 6j is symmetric under that swap and phases are pure gauge here (see the caveat in §4).

### (3) Spectra, route A vs route B (433×433)

| quantity | $\max|\Delta E|$ A vs builder B | A vs my B | min / max eigenvalue of A |
|---|---|---|---|
| $g^2=0.5$ | 1.1e-14 | 1.1e-14 | −3.643 / 4.393 |
| $g^2=1$ | 4.8e-15 | 5.2e-15 | −1.386 / 2.886 |
| $g^2=2$ | 7.1e-15 | 7.1e-15 | −0.303 / 3.303 |
| $H_B$ alone | 2.7e-15 | — | $-2$ (x16), $-1$ (x96), $-\tfrac12$ (x16), $0$ (x177), $\tfrac12$ (x16), $1$ (x96), $2$ (x16) |

Hermiticity: $\|H_B^{\rm B}-H_B^{{\rm B}\,T}\|=0$, $\|H_B^{\rm A}-H_B^{{\rm A}\dagger}\|$ = 0 in the symmetric form used. All $\le10^{-10}$ plan tolerance.

### (4) Claim (ii): block structure of $H_B^{\rm phys}$ (433×433, route-B label order)

| quantity | route A | route B |
|---|---|---|
| max off-block element between different outer-spin strings | 0.0 (exact) | 0.0 (exact) |
| max element between different $J$ tuples ($J$ violation) | 2.95e-16 | 0.0 |
| number of blocks (distinct outer strings) | 128 (of $2^8=256$; parity: $\sum_{\rm outer}j$ integer at each corner forces an even number of half-integer outer spins) | 128 |
| block dims histogram (dim: count) | {2: 41, 3: 52, 4: 8, 5: 22, 9: 4, 17: 1}, sum = 433, min 2, max 17 | same |
| per-block $\max\|\,|{\rm block}|-|K_{\rm sub}|\,\|$ | 2.7e-15 | block $-K_{\rm sub}$: 0.0 (identical by construction) |
| per-block gauge residual (own routine) | 2.7e-15 | — |
| inner labels covered by the union of blocks | 47 of 47 | |

Caveats on what this proves. (a) Block-diagonality in the outer spins is structural in route A ($W$ acts on the 4 inner links only, hence max off-block = 0.0 exactly); the non-trivial content is that each block equals the *same* $K$ restricted (agreement 2.7e-15) and that $J$ is conserved (3e-16). (b) Route B has no dependence on the outer spins in its formula, so the route-B row is a tautology; it matters only because route A (independent, electric basis) reproduces it. (c) The signs of A relative to K *do* depend on the outer pattern (12 of 16 element classes change sign between blocks) — this is route A's per-state phase gauge, harmless since each block is gauge-equivalent to $K_{\rm sub}$.

**Converse: another pairing depends on the outer spins** (corner brute force, `results/m0_step06_tester_corner_bruteforce.py`). Keep the corner operator $E_l\cdot E_b$ but couple the legs as $(l\,o_1|b\,o_2)$ with intermediate spin $K$ instead of $(l\,b|o_1o_2)$ with $J$:
- inner transition $(j_l,j_b)=(\tfrac12,\tfrac12)\to(1,1)$, $K=\tfrac12\to K'=1$: amplitude is $1.2247$ for $(o_1,o_2)=(0,0)$, $1.0$ for $(0,1)$, $1.0$ for $(1,0)$, $0.8165$ for $(1,1)$. In the $(l\,b|o_1o_2)$ pairing the same transition ($J=0\to0$) is $1.2247$ for every $(o_1,o_2)$ (spread 4.4e-16). The same dependence holds for $(\tfrac12,\tfrac12)\to(1,0)$ ($0.7071$ at $o=(0,1)$ vs $0.5774$ at $o=(1,1)$) and $(\tfrac12,\tfrac12)\to(0,1)$.
- Inside the physical $j_{\max}=\tfrac12$ truncation (all spins $\le\tfrac12$) no label triple is shared by two outer patterns, because the allowed $K$ values themselves depend on $o$: $(0,0)\to(\tfrac12,\tfrac12)$ is a $1\times1$ block $[1.4142]$ at $o=(0,0)$ ($K=0\to K'=\tfrac12$) but at $o=(\tfrac12,\tfrac12)$ it is $K=\tfrac12\to K'\in\{0,1\}$ with amplitudes $(0.7071,\,1.2247)$. The Frobenius weight is conserved ($0.7071^2+1.2247^2=2=1.4142^2$), so it is the same operator redistributed over an outer-dependent label set. In the $(l\,b|o_1o_2)$ pairing it is $[1.4142]$ at both.
This explains the two statements: Paulo's Fig. 2 (plaquette needs no outer information) holds in the (inner|outer) pairing; the note's §4.2 ("depends on the outer links") holds in pairings that mix an inner with an outer leg. (The $o=1$ rows are an illustration of the local algebra only; they lie outside $j_{\max}=\tfrac12$.)

### (5) $K$ (47×47)
- Shape 47×47, $\|K-K^T\|=0$, real, max $|K_{ij}|=2.000$ (vacuum $\leftrightarrow$ all-half, modulus $2$ as required by Paulo Eq. 37).
- Dark rows (all-zero): **31**; bright rows: **16**; every dark label has a corner with $J=1$; no bright label has $J=1$.
- Only 16 non-zero entries: $K$ is a perfect matching of the 16 bright labels into 8 disjoint pairs (2×2 blocks) with couplings $\{2,1^{\times6},\tfrac12\}$ in modulus.
- Spectrum (multiplicity): $-2\,(1)$, $-1\,(6)$, $-\tfrac12\,(1)$, $0\,(31)$, $+\tfrac12\,(1)$, $+1\,(6)$, $+2\,(1)$ — consistent with 16-fold, 96-fold, 16-fold multiplicities in the 433 spectrum after weighting by outer completions.
- $K_{\rm inner}$ built on 47 inner labels = restriction of the 433-label construction (unit test `test_inner_P_matches_full_P_restricted` passes).

### (6) `gauge_align` on a random complex gauge (seed 20261104, $D_{\rm true}=e^{i\theta}$, $\theta\sim U[0,2\pi)$)

| matrix | residual $\max|A-DBD^\dagger|$ | $\max\|D\|-1|$ | $D$ vs $D_{\rm true}$ (per connected component, up to one phase) | modulus-mismatch test ($A\to2A$) |
|---|---|---|---|---|
| $H_B$ route B (433) | 5.0e-16 | 2.2e-16 | 2.5e-16 (305 components) | returns `(None, 2.0)` |
| $K$ (47) | 2.8e-16 | 1.1e-16 | 2.2e-16 (39 components) | returns `(None, 2.0)` |
| $H_B$ route A (433) | 5.5e-16 | 2.2e-16 | 2.3e-16 (305 components) | returns `(None, 2.0)` |

PASS. Caveat: because every component has at most 2 nodes (matching), $D$ is determined only up to a phase per component and, equivalently, **every sign pattern is gauge-equivalent**. My negative control (flipping the sign of one symmetric element pair) therefore returns residual 5e-16, i.e. `gauge_align` correctly says "equivalent", and a flip cannot be distinguished by it on these matrices. It does not detect a wrong *relative* sign of $P_{01}$ and $P_{10}$ either; that is caught instead by the modulus test, since $|K_{01}|=|P_{01}+P_{10}|=2|P_{01}|$ requires equal signs. I verified $P_{01}=P_{10}$ directly ($P$ symmetric, 0.0).

## 3. Observations (not failures)
1. Gauge-invariant content of route A/B agreement is only: moduli of 128 pair couplings plus $P_{01}=P_{10}$; the "diagonal $\pm1$ gauge" statement is therefore weaker than it sounds (no loops in the connection graph). Fine for $H_B$ and its spectrum, but the *sign of $P$ as an operator* (e.g. $\mathrm{Tr}\,U_P$ vs $-\mathrm{Tr}\,U_P$) is fixed only through the vacuum amplitude $+1$ (confirmed: $A_{\rm all,vac}=A_{\rm vac,all}=+1.0$, $P_B=+1.0$).
2. API inconsistency (not a bug): `spinnet.labels(diagram=None, jmax=0.5)` takes the diagram first (matches METHODS and the test, which use keywords), whereas `inner_labels(jmax)` takes `jmax` first; `labels(0.5)` raises `AttributeError`.
3. The builder's `gauge_align` in my random-gauge test recovered the gauge on matchings only; the inverted-phase bug from the prototype is fixed (recovery to 2.5e-16 on three matrices).
4. In my own gauge routine a `RuntimeWarning` (divide by zero) occurred only in the deliberately wrong "swapped primes" negative control (zero pattern); irrelevant to production code.

## 4. Verdict
**PASS.** X4, X5, X6 green; all earlier m0 tests green; 71 unit tests green; lock and acceptance-check pass; 11 remaining acceptance failures are PENDING (evaluator, metrics, results, `TwelveQubit`: steps 0.7+). Independent derivation and brute-force agree with the builder's mapping $f\_symbol(J_c,j_p,j_n,\tfrac12,j_n',j_p')$ in magnitude and sign (ratio exactly 1 on all 16 entries), and claim (ii) is numerically confirmed in the (inner|outer) pairing with the converse demonstrated in the mixed pairing.
