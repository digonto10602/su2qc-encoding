# Report 1 — 12-qubit encoding: general one-Trotter-step circuit

Date: 2026-11-05 · Results commit: a9702e5 (clean) · Tag: `milestone-1` · Plan: `prompts/002` + addenda `003`–`005`
Every number below is read from `results/twelve/{UE,UB,step}.json` (produced by `PYTHONPATH=src python scripts/m1_results.py`, seeds 20261104 / 12345 / 0, qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0) unless a report is cited. Verification: tester reports 015–023, audits 001–003, benchmarks 001–002.

## 1. What was asked
Build in Qiskit the circuits for one Trotter step of the Kogut–Susskind Hamiltonian, $U_E(\alpha)=e^{-i\alpha H_E}$ and $U_B(\beta)=e^{-i\beta H_B}$, for the SU(2) plaquette with 8 outer links at $j_{\max}=\tfrac12$ in Paulo's 12-qubit encoding (3 qubits $(j,m,m')$ per inner link). Verify on every Gauss-law state and count CNOT and T gates.

## 2. What was done
- **Exact reference.** The 433 physical states were built from corner singlets. Two independent constructions (electric basis; 6j spin network) give the same spectrum to $10^{-14}$. Convention: $H=\frac{g^2}{2}\sum_\ell j_\ell(j_\ell+1)-\frac1{g^2}(\mathrm{Tr}U_P+\mathrm{h.c.})$ (Paulo Eq. 16). Paulo's angle is $\alpha_P=2\beta$.
- **Circuits** (`src/su2plaq/circuits/twelve.py`):
  - $U_E$: one `p(−3α/4)` per inner link $j$-qubit.
  - $U_B$: Paulo's notebook ported. His two native multi-controlled rotations are replaced by `rccx · crx · rccx`, which is exact.
  - Trotter steps: order 1 is $U_B U_E$; order 2 is $U_E(\alpha/2)U_BU_E(\alpha/2)$.
- **Checker.** Every circuit is simulated on all 433 physical states, with the 16 outer-link qubits present. A circuit passes if (error on physical states) + (leaked amplitude) + (simulator pruning bound) $\le 10^{-10}$ for exact angles, or $\le N_{\rm rot}\varepsilon+10^{-9}$ after Clifford+T synthesis. Gauss's law of the outputs is checked separately.
- **T count:** $T=T_{\rm fixed}+\sum_{\rm rot}T_r(\varepsilon)$, with each rotation synthesised and checked by pygridsynth (Ross–Selinger).

## 3. Results at $(\alpha,\beta)=(0.37,0.61)$

### 3.1 Exactness (all 433 physical states, sparse engine, certified)
| circuit | error | leaked amplitude | Gauss residual |
|---|---|---|---|
| $U_E$ | $1.2\times10^{-13}$ | 0 | $5\times10^{-16}$ |
| $U_B$ | $2.4\times10^{-13}$ | 0 | $8\times10^{-16}$ |
| step, order 1 | $2.7\times10^{-13}$ | 0 | $3.9\times10^{-15}$ |
| step, order 2 | $2.7\times10^{-13}$ | 0 | $1\times10^{-15}$ |

Wrong targets are rejected with O(1) errors: opposite sign of $\alpha$ or $\beta$, swapped order $U_EU_B$, and order 1 checked against the order-2 target. The outer links are never written.

### 3.2 Gates (34 qubits = 12 data + 22 helper qubits; outer links read-only)
| circuit | CNOT | rotations | fixed T | depth |
|---|---|---|---|---|
| $U_E$ | 0 | 4 | 0 | 1 |
| $U_B$ | 294 | 6 | 312 | 292 |
| step, order 1 | 294 | 10 | 312 | 292 |
| step, order 2 | 294 | 14 | 312 | 293 |

### 3.3 T count after Clifford+T synthesis (pygridsynth, every synthesised circuit re-verified and certified)
| circuit | $\varepsilon=10^{-4}$ | $10^{-6}$ | $10^{-8}$ | $10^{-10}$ |
|---|---|---|---|---|
| $U_E$ | 176 | 256 | 328 | 416 |
| $U_B$ | 560 | 696 | 820 | 936 |
| step, order 1 | 736 | 952 | 1148 | 1352 |
| step, order 2 | 896 | 1224 | 1492 | 1768 |
| + outer-link electric phases (8 rotations, separate row) | +352 | +512 | +656 | +832 |

- Measured synthesis errors are 0.2–0.5 of the budget. For example, step order 1 at $10^{-6}$ has error $3.2\times10^{-6}$ against a budget of $1.0\times10^{-5}$.
- The outer-row Clifford+T circuits put H gates on the outer qubits, so this checker cannot evaluate them. The tester computed them by hand: all are within budget (reports/tests/021).

### 3.4 Comparison with Paulo's compiled circuit (like for like: $\beta=1$, $\varepsilon=10^{-6}$ per rotation, same Qiskit Clifford+T pass manager and seed)
| | qubits | CNOT | rotations | fixed T | T (Qiskit CT) | T (pygridsynth sum) |
|---|---|---|---|---|---|---|
| Paulo (notes Eq. 39) | 34 | 294 | 14 | 296 | 1162 | 1180 |
| ours | 34 | 294 | 6 | 312 | **662** | **684** |

- That is 43 % fewer T gates for the same CNOT count.
- The saving comes from 14 → 6 rotations, paid for with 16 extra fixed T.
- Error budgets differ ($6\varepsilon$ vs $14\varepsilon$), so the two counts are not at the same accuracy. Ours is the tighter one.
- Paulo's compiled file passes our checker: error $1.08\times10^{-5}$ against $2\times10^{-5}$.

## 4. Physics findings along the way
- **T-count rule.** $T\approx N_{\rm rot}(3\log_2(1/\varepsilon)+3\pm4)$, measured. The proposed form $\#T+3\ln\varepsilon$ has the wrong sign, base and multiplicity.
- **Outer links.** In this encoding the plaquette never changes the outer links, but they restrict which inner states occur. 3153 of the $3^8=6561$ outer patterns are allowed, with 1–17 inner states each, and together the inner states span all 625 codes.
- **Spin network.** The plaquette is independent of the outer links when each corner pairs its two inner links first; this is Paulo's Fig. 2 claim, test M0-X5. It depends on them in other pairings, as Digonto's note §4.2 says.
- **Paulo's notes.** Eq. 25 is missing a complex conjugate (harmless). The don't-care count is 3471, not 3470.

## 5. Problems and assumptions
- **Checker rules decided by Digonto on 2026-11-04/05:**
  - Gauss tolerance scales with rounding (prompts/003).
  - Leakage is judged as an amplitude (004).
  - The pruning cap is relative to the budget (005).
- **Aer MPS.** The MPS simulator is accurate only to about $2\times10^{-10}$, so it certifies only tolerances of $10^{-9}$ or looser. It is used only for Paulo's compiled circuit.
- **Benchmark flags** (reports/benchmarks/002). Memory for checking Paulo's circuit is up 33 % (1.1 → 1.5 GB). Warm gate counting is up 6 ms per call. No call longer than 100 ms slowed by more than 10 %.
- **For M2.** su2qc-trotter's lean22 applies the electric layer after the plaquette ($U_EU_B$). It will seed the compression loop as plaquette-only, with our $U_E$ placed in front.
