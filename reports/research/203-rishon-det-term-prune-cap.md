# Research 203 — rishon track: the determinant term as a third Trotter layer, the rishon prune cap, and how M5/M6 continue

- Date: 2026-11-10 · Author: planner · Git commit at writing: `ece4fa3` (branch `merge-desktop-tracks`)
- Prompt in force for track R: `prompts/203-rishon-m6-plan.md`; this research backs the amendment `prompts/204-rishon-det-term-amendment.md`.
- Trigger: Digonto's decisions of 2026-11-10 (`notes/STATUS.md`, Decisions): add the det coupling (audit `reports/audits/200-m5-rishon-audit.md` N1), raise the rishon prune cap to 10 % of `tol_err`, mark T1[step] slow, errata E1–E3 accepted.
- Related: `reports/tests/221-m6-round-004-step-6-4b.md` §4 (what the two changes invalidate), `reports/research/200-rishon-qlm-model-and-verification.md` (model), `reports/research/202-rishon-m6-compression-loop.md` (loop), `docs/METHODS-rishon.md` R13–R16 (written by this run).
- Machine: omnicommander, cores 6–9, every job under `tools/run-capped` / `tools/pytest-safe`. Environment: conda `coding` (python 3.12, numpy 2.5.2, scipy 1.18, qiskit 2.5.2, pygridsynth 1.2.0).

Jargon, once. *Rishon*: one of the fermions that make up a gauge link in a quantum link model (QLM). *Det term*: the operator $\det U_\ell+\det U_\ell^\dagger$ on a link, which moves both rishons of the link from one end to the other. *Trotter layer*: one factor $e^{-i\theta H_k}$ of a product formula. *Inner codes*: the 1296 valid 16-bit patterns of the four plaquette links. *Prune cap*: the largest share of the error budget that the simulator's own rounding bound (`dropped_total`) may use. *Evaluator hash*: the sha256 over the source files that decide a verdict; archive entries store it. *Replay* (my label): re-running the stored rounds with the same programs under a new evaluator hash.

## 1. Sources (read, with the equations used)

1. Brower, Chandrasekharan, Wiese, *QCD as a quantum link model*, arXiv:hep-th/9704106.
   - Eq. (2.20): $H=J\sum_{x,\mu\neq\nu}\mathrm{Tr}[U_{x,\mu}U_{x+\hat\mu,\nu}U^\dagger_{x+\hat\nu,\mu}U^\dagger_{x,\nu}]+J'\sum_{x,\mu}[\det U_{x,\mu}+\det U^\dagger_{x,\mu}]$; text before it: the extra U(1) gauge symmetry is broken "by adding the real part of the determinant of each link matrix"; the definition has no ordering ambiguity because the elements of one $U$ commute.
   - Eq. (4.5)–(4.6): with fermionic rishons $\det U_{x,\mu}=N!\,c^1_{x,+\mu}c^{1\dagger}_{x+\hat\mu,-\mu}\cdots c^N_{x,+\mu}c^{N\dagger}_{x+\hat\mu,-\mu}$; non-zero only with exactly $\mathcal N=N$ rishons per link; Eq. (4.7): $\binom{2N}{N}$ states per link (6 for SU(2)).
   - Eq. (4.8) and the text after it: "The determinant part … shifts an entire rishon-baryon — a color neutral combination of $N$ rishons — along the link."
2. Wiese, *Ultracold quantum gases and lattice systems: quantum simulation of lattice gauge theories*, arXiv:1305.1602, Sec. 4.3: Eq. (4.11) (the extra U(1) generator) and the sentence after it, "This can be done by adding the term $\gamma\sum_{\langle xy\rangle}(\det U_{xy}+\det U^\dagger_{xy})$ to the Hamiltonian"; Eq. (4.12) (rishon representation), Eq. (4.14) ($\det U$ in rishons), and "For an SU(2) gauge theory … 6 states per link".
3. Trotter orders: Hatano, Suzuki, arXiv:math-ph/0506007 (as `docs/METHODS.md` §2): first-order product formula local error $O(dt^2)$, symmetric formula $O(dt^3)$.
4. Prune cap rule: `prompts/005-relative-prune-cap.md` §1–§3 (this project): `op_norm_error = block_error + leak_amplitude + dropped_total ≤ tol_err` is rigorous for any pruning; the cap only limits the simulator's share.

Nothing else is used. No method or equation below is taken from memory without one of these sources or a computation listed in §3.

## 2. Candidate designs compared

### 2.1 Where the det term enters the step

| candidate | correctness | Trotter error | cost | fit with existing code and data |
|---|---|---|---|---|
| **A. third layer in front of the existing unit**: $U_1=U_B(\beta)\,U_D(\eta)\,U_E(\alpha)=[U_BU_E]\,U_D$ | exact per layer; valid because $[H_D,H_E]=0$ (measured 0.0, §3.2) | first order, same structure as before (two non-commuting groups: $H_B$ and $H_E+H_D$); slopes 1.99 / 2.99 measured | $+32$ CX, $+8$ rotations (general gadget, §3.4) | compression unit $U_BU_E$ and its 16 archive entries stay valid; $\eta$ never enters the loop's target |
| B. full three-layer step as the compression unit | exact | same | at best $-8$ CX against A (sharing the per-link parity CX with $U_E$), and fewer rotations only at more CX (§3.5) | archive, rounds 0–4, 15 of 20 proposer sessions invalid; the laptop `TaskSpec` has no third angle and `_KINDS` is fixed (shared file) |
| C. det layer as its own loop kind `UD` | exact | same | unknown gain on a 32-CX layer | needs a third angle in the shared `TaskSpec`/worker (shared files must stay byte-identical) |

Chosen: **A**. B would buy at most about 3 % of the CX count (8 of 260) for the loss of the whole archive; C cannot be done without touching shared files and targets a layer whose rotation count is already at its per-link minimum (§3.5).

### 2.2 How the 10 % cap is applied without touching shared files

| candidate | shared files | exactness of the rule | risk |
|---|---|---|---|
| keyword `prune_fraction` in the shared `evaluate` (merge-notes M6 item 3) | `src/su2plaq/evaluate/evaluator.py` changes → the shared code hash of the twelve / spinnet / fuzzy loops goes stale | exact | forbidden by the task |
| temporarily overwrite the module constant `PRUNE_FRACTION` around the call | byte-identical | exact | global mutable state; `prompts/203` §10 forbids patching shared modules |
| **re-judge inside `su2plaq.rishon.verify.verify`**: a `pruning_bound` verdict of the shared evaluator is re-classified with the shared cascade (cap → leak → error → Gauss) and the rishon cap | byte-identical | exact for `ok` / `pruning_bound` / `error` / `gauss`; the `dirty_ancilla` vs `leak` *label* of a leaking circuit above the old cap uses a stand-in (the shared verdict does not expose the invalid-code weight) | none for validity |

Chosen: the third. It is the mechanism already written down in `prompts/203` §13 E2 (b). Because the shared cascade tests the cap first, every shared verdict other than `pruning_bound` already has `dropped_total ≤ 10^{-2}` `tol_err` and is passed through unchanged; the rule therefore only needs the fields the shared `Verdict` carries.

### 2.3 How the archive gets the new evaluator hash

| candidate | new code | record |
|---|---|---|
| edit `evaluator_sha256` and the verdicts of the 16 entries in place | new mutation logic for a strict archive | old round files describe verdicts under another rule |
| **replay**: move the old files aside, run `run_round` for rounds 0–4 with the recorded programs in order | a ~100-line driver around the existing, tested `run_round(..., proposals=…)` | every round file, feedback file, synthesis re-verification and the index are regenerated consistently; old files kept under `pre-204/` |

Chosen: replay (also what `prompts/203` §13 E2 (b) announced for a cap change).

## 3. Prototypes and measured numbers

All scripts are in `scratch/planner/`; they use the production operators read-only. Commands: `PYTHONPATH=src taskset -c 6-9 tools/run-capped python scratch/planner/<script>` (the last one with `PYTHONPATH=scratch/planner/shim204:src:.`). Tolerances quoted are float64 rounding levels unless stated.

### 3.1 Link operator (`proto_rishon_det_204.py`, 60 s, output `proto_rishon_det_204.json`)
- $\det U=U_{11}U_{22}-U_{12}U_{21}=2c_{L1}c^\dagger_{R1}c_{L2}c^\dagger_{R2}$: difference 0.0; the only non-zero entry is $\langle B|\det U|A\rangle=+2$ (codes $A=3$, $B=12$).
- $H_D^{\rm link}=\det U+\det U^\dagger$ on the 6-state sector: eigenvalues $(+2,-2,0,0,0,0)$.
- $[L_a,\det U]=[R_a,\det U]=0$ (0.0 for all six), $[\tfrac12\sum_a(L_a^2+R_a^2),\det U]=0$, $[n_R-n_L,\det U]=4\det U$ (0.0): SU(2) invariant, breaks the link U(1).

### 3.2 Inner Hamiltonian on the 1296 codes (same script)
- $H_D^{\rm in}=\sum_{\ell\in\{b,r,t,l\}}(\det U_\ell+{\rm h.c.})$ is real symmetric; spectrum $\{-8:1,-6:16,-4:100,-2:304,0:454,2:304,4:100,6:16,8:1\}$ = the multinomial count for per-link eigenvalues $(+2,-2,0^4)$.
- $\|[H_D,H_E]\|_2=0.0$; $\|[H_D,H_B]\|_2=22.627417=16\sqrt2$ (audit 200 N1 quoted 22.6).
- Sign of the coupling: $S=\prod_\ell e^{i\frac\pi4(n_R-n_L)_\ell}$ gives $SH_DS^\dagger=-H_D$ ($2.4\times10^{-16}$) and $SH_BS^\dagger=H_B$ (0.0); spectra of $H(\lambda_D)$ and $H(-\lambda_D)$ agree to $1.6\times10^{-14}$ at three parameter pairs.
- Closed sector (16 vacua + loop, per outer singlet choice): invariant under $H$ (0.0); zero levels 15 at $\lambda_D=0$, 5 at $\lambda_D\in\{0.2,0.5\}$ for $g^2\in\{0.5,1,2\}$; an independent $17\times17$ model (hypercube $2\lambda_D\sum_\ell X_\ell$ on the vacua, loop coupled by $-4/g^2$ to ${\rm vac}_A,{\rm vac}_B$) reproduces the production block to $3.6\times10^{-15}$.
- Trotter local error against $e^{-i\,dt\,H}$ at $g^2=1.1014$, $\lambda_D=0.4316$ (the couplings behind the nominal triple), $dt=0.4,0.2,0.1,0.05,0.025$: order 1: $7.1\times10^{-1},2.3\times10^{-1},6.0\times10^{-2},1.5\times10^{-2},3.8\times10^{-3}$ (fit slope 1.961; last pair 1.994); order 2: $4.0\times10^{-1},6.6\times10^{-2},8.8\times10^{-3},1.1\times10^{-3},1.4\times10^{-4}$ (fit 2.958; last pair 2.994).
- Identity $U_2^n=L(\tfrac12)\,U_1^n\,L(-\tfrac12)$ with $L(x)=U_D(x\eta)U_E(x\alpha)$: $2.6\times10^{-15}$ at $n=3$.
- Observables from ${\rm vac}_A$ after one / two first-order steps (E_link, P, echo):

| $(\alpha,\beta,\eta)$ | $n=1$ | $n=2$ |
|---|---|---|
| $(0.37,0.61,0)$ | 0.03469942, 0, 0.00056142 | 0.09098081, 0.73412183, 0.87250756 |
| $(0.37,0.61,0.29)$ | 0.01166226, 0, 0.00584640 | 0.00949237, −0.03380158, 0.15150238 |
| $(0.91,0.23,0.53)$ | 0.14102519, 0, 0.03105932 | 0.00956695, 0.21274107, 0.02106778 |
| $(1.70,1.00,1.07)$ | 0.04451880, 0, 0.00081747 | 0.11272422, 0.58185315, 0.01900932 |

  (audit 200 N1's probe, echo $7.8\times10^{-3}$ at $\eta=0.3$: reproduced, 0.00778703.)

### 3.3 The 38 432-state physical space (`proto_rishon_det_sectors_204.py`, 3.6 s, 0.3 GB)
Operators lifted to the 352 016 distinct 48-bit codes of the physical states and projected, $M=P^\dagger TP$; weight leaving the physical space $\|TP\|_F^2-\|P^\dagger TP\|_F^2\le5.8\times10^{-11}$ for $H_B$ and for each of the 12 link det terms (no code without a partner).

| quantity | $\lambda_D=0$ | inner det (4 links) | all 12 links |
|---|---|---|---|
| distinct corner-charge tuples $(Q_0..Q_3)$ | 431 (conserved) | not conserved | not conserved |
| charge changes | none ($H_B$) | $\pm2$ on the two corners of the link, total 0 (8 vectors, rank 3) | also $\pm2$ on one corner (16 vectors, rank 4) |
| dynamical blocks (connected components of $H$) | 31 870 (25 933 single, 5 312 pairs, 625 triples) | 4 976 (largest 17) | 305 (largest 4 352) |
| block of ${\rm vac}_A$ | 3 states, 1 charge sector | 17 states, 15 charge sectors | 4 352 states (the whole closed sector), 431 charge sectors |

Also: $[H_D^{\rm outer},H_B]=5\times10^{-15}$, $[H_D^{\rm outer},H_D^{\rm inner}]=0$ on the physical space; there are 128 outer spin patterns, each with 1–16 blocks under the full det term.

### 3.4 Circuit of the det layer (`proto_rishon_det_circuit_204.py`, 76 s, 1.3 GB; `proto_rishon_det_numbers_204.py`, 42 s)
Per link, qubits $(L_1,L_2,R_1,R_2)$: `cx(L1,L2)`, `cx(R1,R2)`, `h(L1)`, `h(R1)`, `cx(L1,R1)`, `rz(2η)` on $R_1$, `cx(L2,R1)`, `rz(2η)` on $R_1$, `cx(L2,R1)`, `cx(L1,R1)`, `h(L1)`, `h(R1)`, `cx(R1,R2)`, `cx(L1,L2)`: 8 CX, 2 rotations, 4 Hadamards, no ancilla.
- Link gadget against $e^{-i\eta(\det U+\det U^\dagger)}$ on the sector (16×6 block, no phase fitted): $3.3$–$3.7\times10^{-16}$ at $\eta\in\{0.29,0.53,1.07,-0.4\}$.
- $U_D$ on the 1296 codes with the production verifier: `ok`, certified, `op_norm_error` $2.4$–$4.7\times10^{-14}$, `dropped_total` $1.3$–$3.0\times10^{-15}$, Gauss $2\times10^{-16}$, phase 1, 5–7 s each. Wrong sign: error 1.97.
- Counts (laptop `metrics`, pygridsynth at $10^{-6}$): 32 CX, 8 rotations, $T_{\rm fixed}=0$, $T=496$ ($\eta=0.29$), 496 (0.53), 512 (1.07); depth 10, depth$_{\rm CT}$ 326; 48 qubits. Over the 20 angles of the eta set (`default_rng(20261110).uniform(0.05,1.2,20)`): $\sum T=10\,016$, mean 500.8, range 480–512.
- All 12 links (inner + outer row): 96 CX, 24 rotations; per-link certificate bound $4.0\times10^{-15}$ (max link $3.3\times10^{-16}$) at $\eta\in\{0.29,-0.53,1.07,\pi/4\}$; a $10^{-7}$ angle mutant gives $5.0\times10^{-8}$, the wrong sign 13.2.
- General three-layer step $(0.37,0.61,0.29)$: `ok`, `op_norm_error` $5.0\times10^{-13}$, `dropped_total` $4.5\times10^{-13}$; det layer placed after $U_B$: error 1.615 (= the exact $\|U_DU_BU_E-U_BU_DU_E\|_2$).
- **Headline program `r04-F1-004` with the det layer in front**, three triples: `ok`, certified, `op_norm_error` $1.8$–$2.0\times10^{-13}$, `dropped_total` $1.5\times10^{-13}$, Gauss $\le1.2\times10^{-15}$, 53 qubits, 9 s each. Keys: unit $(228,846,1417,53)$, three-layer $(260,1342,1743,53)$; angle-averaged $T$: $843.8+500.8=1344.6$.

### 3.5 Why two rotations per link is the minimum for the det layer taken alone
On a link's six valid codes $U_D$ has three distinct eigenphases, $e^{-2i\eta}$ on $(A+B)/\sqrt2$, $e^{+2i\eta}$ on $(A-B)/\sqrt2$ and 1 on the quartet. One rotation $e^{-i\theta P/2}$ has two; so each link needs at least two $\eta$-dependent rotations whatever frame is used. For the two-Pauli form $e^{-i\eta XXXX}e^{+i\eta YYXX}$ the weight count gives 8 CX (3 to reduce one weight-4 string, 1 for the second, 4 back); I found no 6- or 7-CX form but did not prove 8 minimal (my own estimate, not a literature bound). Joint tricks across links (counting $n_+-n_-$ into a register: 4 rotations instead of 8) cost Toffolis and CX, and CX is the first key component.

### 3.6 Prune cap numbers on this machine (`proto_rishon_det_numbers_204.py`)
| circuit | `dropped_total` | block error | shared verdict (1 %) | rishon verdict (10 %) |
|---|---|---|---|---|
| $U_B$, ccx ladders | $3.02\times10^{-13}$ | $4.1\times10^{-14}$ | ok | ok |
| $U_B$, rccx ladders | $2.281\times10^{-12}$ | $3.4\times10^{-13}$ | pruning_bound | ok |
| $U_B$, mcx ladders | $2.131\times10^{-12}$ | $3.1\times10^{-13}$ | pruning_bound | ok |
| step, rccx ladders | $2.915\times10^{-12}$ | $3.7\times10^{-13}$ | pruning_bound | ok |
| step, mcx ladders | $2.695\times10^{-12}$ | $3.4\times10^{-13}$ | pruning_bound | ok |
| step, windowed Qiskit L3 (round-000.json) | $3.788\times10^{-12}$ | $3.5\times10^{-13}$ | pruning_bound | expected ok |

Budget at the new cap with the worst measured rate ($1.1\times10^{-15}$ per branching gate, `prompts/203` §13 E2): $\lfloor10^{-11}/1.1\times10^{-15}\rfloor=9090$ branching gates (was 909).

### 3.7 The new locked tests were run against a prototype of the interface
`scratch/planner/shim204/shim204.py` patches prototype implementations of every new name into the production modules in-process (no file under `src/` is written). With it (`PYTHONPATH=scratch/planner/shim204:. tools/pytest-safe -p shim204 -n 4 …`) the new tests pass where they can (results of the last run are quoted in `prompts/204` §10); without it all of them fail with `PENDING:`.

## 4. What is not settled by this research
- Whether 8 CX per link is minimal for the det gadget (§3.5).
- The physical value of $\lambda_D$: BCW and Wiese leave $J'$ / $\gamma$ free. The nominal $\eta=0.29$ is a generic test angle (it corresponds to $\lambda_D=0.43$ at the nominal $g^2=1.10$, $dt=0.67$), not a physics recommendation.
- No Kogut–Susskind counterpart of the det term exists; the KS comparison of Report 5 stays a $\lambda_D=0$ comparison.
