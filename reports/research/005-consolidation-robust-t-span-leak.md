# Research 005 — consolidation of the merged repo: robust-T key decision, exact span leak, hash inventory

- Date: 2026-11-10. Git commit: `6d9bae8` (working tree dirty: other agents' track files). Prompt in force: `prompts/002` (+ addenda); this note supports `prompts/008-merged-repo-consolidation.md`.
- Related: `notes/merge-notes-{spinnet,rishon,fuzzy}.md`, `reports/audits/{002,100,300,301}`, `reports/tests/115`, `reports/research/003` (leak as amplitude), `prompts/104` §11 E3, `prompts/203` §13 E3, `prompts/204` §6.2.
- No new external method is introduced. External sources already in `docs/METHODS.md`: Ross and Selinger, arXiv:1403.2975 (T-count of one $z$-rotation $\approx3\log_2(1/\varepsilon)+O(\log\log(1/\varepsilon))$, used for the T-noise argument of §1); Gu, Kemeny, Yelin, Lukin, arXiv:2610.22367 (the loop). Everything else is linear algebra proved below or measured here.
- Scripts and raw numbers (planner scratch, gitignored): `scratch/planner/c008/` — `proto_robust_t_all.{py,json,log}`, `evaluator_n3.py` (copy of `src/su2plaq/evaluate/evaluator.py` at `6d9bae8` plus the span-leak accumulation), `proto_n3_span_leak.{py,json,log}`, `proto_n3_twelve_best.{py,json,log}`, `proto_n3_aer.{py,json}`, `proto_n3_paulo.{py,json,log}`, `check_m2c_reference.py`. All runs: `taskset -c 2-3 tools/run-capped python <script>`, conda env `coding`, BLAS threads 1, machine omnicommander under load from other agents (wall times are upper bounds).

Words used: *T-count* = number of T gates after replacing every rotation by its pygridsynth Clifford+T word at $\varepsilon=10^{-6}$; *archive key* = the lexicographic cost $(\mathrm{CX},T_{10^{-6}},\mathrm{depth_{CT}},\mathrm{qubits})$ at the nominal angles; *robust key* = the same with T and depth summed over 20 fixed seeded angle pairs (tracks S and R); *headline* = the entry a report quotes; *span leak* = output amplitude that stays inside the code space (valid link codes, ancillas 0) but leaves the span of the physical (Gauss-law) states; *replay* = re-evaluating all recorded rounds of an archive in order under changed evaluator code.

## 1. Robust T: archive key or headline rule?

**Measured** (`proto_robust_t_all.py`; T only, $T=T_{\rm fixed}+\sum_r$ pygridsynth T, $\varepsilon=10^{-6}$; the 20 pairs of `default_rng(20261107)`, $\alpha\sim U(0.05,2.0)$ then $\beta\sim U(0.05,1.2)$; every entry with a program file):

| archive | entries | best by (CX, $T_{\rm nominal}$) = best by (CX, $\sum T$)? | pairs of entries at equal CX whose order flips | best entry: $T_{\rm nominal}$ vs mean $\pm$ std over the 20 pairs | T-only wall |
|---|---|---|---|---|---|
| twelve | 21 of 22 | yes, full ranking identical | 0 | 912 vs $927.4\pm11.9$ (13 rotations) | 82 s |
| fuzzy_ub | 11 | yes, full ranking identical | 0 | 1902 vs $1860.4\pm53.2$ (28 rotations) | 63 s |
| fuzzy_link | 4 | yes, full ranking identical | 0 | 644 vs $628.8\pm17.0$ (10 rotations) | 8 s |
| spinnet (reports/tests/115) | — | **no**: r03 beats r02 by 24 T at the nominal pair, loses by $13.2\pm2.3$ T on average | 1 | — | — |
| rishon (merge note) | — | nominal margin 30 T between two 252-CX programs, 20-pair margin 7.8 T | 0 (margin shrinks 4x) | — | — |

The nominal T of one program fluctuates by 12–53 T (std over angle pairs) for 10–28 rotations; the 20-pair mean has a standard error $\sqrt{20}\approx4.5$ times smaller (2.7 T for the twelve best). The skeleton of every entry is constant over the 20 pairs.

**Decision: keep the archive key; make the robust key the headline rule of every encoding** (one shared module, `su2plaq.compress.robust`). Reasons, in order of weight:
1. The key is the definition of the archive in four locked milestones (`tuple(M.key(r.metrics)) == tuple(best.key)` in m2, m4, m6, m10; cells; 76 stored entries; round files; three published reports). A new key is a new archive for every encoding, not a refresh.
2. The key steers the search; the headline is what leaves the project. The search is led by CX (first component); T only breaks ties, and MAP-Elites cells are 9 % wide in T. The failure the proposal names (rewarding $\pm\pi/4$ luck) harms only the quoted number and the proposers' effort; both are handled by the headline rule plus the "Headline rule" paragraph in every brief (as tracks S and R do since round 3).
3. On the three archives that never had the rule the two rankings agree completely (table), so adopting it as headline changes no published number there; on spinnet and rishon the headline rule is already locked (M4-S8/S9, M6-H1/H2).
4. Cost: the full robust metric needs 20 more syntheses per entry in every evaluation; as a headline it is computed once per archive entry and cached.

## 2. Exact span leak (audit 100 N3, audit 002 R1)

Write the action of the circuit on the physical inputs as $U\Psi=\Psi A+S+X$ (METHODS §6): $\Psi$ the isometry of the $d$ physical states into the code space, $A=\Psi^\dagger U\Psi$, $X$ outside the code space, $S=(P_{\mathcal C}-\Psi\Psi^\dagger)U\Psi$. The three ranges are orthogonal, so with $D=A-e^{i\varphi}V$
$$\|U\Psi-e^{i\varphi}\Psi V\|_2=\sqrt{\lambda_{\max}(D^\dagger D+S^\dagger S+X^\dagger X)}\le\|D\|_2+\|S\|_2+\|X\|_2 .$$
The evaluator reports $\|D\|_2+\texttt{dropped\_total}+\|X\|_2$ and controls $S$ only per state through the Gauss residual ($\|s_k\|\le4\,g$).

**Formula (no difference of Gram matrices).** For outer pattern $o$: $P_o$ ($n_{\rm in}\times m_o$) the inner components of the $m_o$ states with support on $o$, thin QR $P_o=B_oR_o$ (cached per encoding), $\Omega_o=M_{r(o)}P_o$ the in-code output, $Y_o=B_o^\dagger\Omega_o$, $C_o=\Omega_o-B_oY_o$, $D_o=Y_o\Pi_o-R_oA_{[o,:]}$ ($\Pi_o$ places the $m_o$ columns among all columns, $A_{[o,:]}$ the rows of $A$ of those states). The $o$-component of column $k$ of $S$ is $\Omega_oe_k-P_oA_{[o,k]}=C_oe_k+B_o(Y_oe_k-R_oA_{[o,k]})$, two orthogonal pieces, hence
$$S^\dagger S=\sum_o\Pi_o^{\top}C_o^\dagger C_o\Pi_o+\sum_oD_o^\dagger D_o,\qquad\texttt{span\_leak}=\sqrt{\lambda_{\max}(S^\dagger S)} .$$
Every term is a residual formed directly, so the absolute accuracy is $\sim10^{-15}$. The existing diagnostic $w_{\rm code}-\sum|A|^2$ is a difference of $O(1)$ numbers and bottoms out at $\sqrt{10^{-15}}$.

**Measured** (`proto_n3_*.py`; sparse engine unless noted):

| circuit | `op_norm_error` | exact $\|S\|_2$ | old diagnostic $\sqrt{\max_k(w-|A|^2)}$ | $4g$ | total | tol | extra time |
|---|---|---|---|---|---|---|---|
| spinnet $U_E$ synth $10^{-6}$ | $2.183\cdot10^{-6}$ | $3.153\cdot10^{-7}$ | $3.15\cdot10^{-7}$ | $2.23\cdot10^{-6}$ | $2.498\cdot10^{-6}$ | $4.001\cdot10^{-6}$ | 0.05 s |
| spinnet step synth $10^{-6}$ | $2.381\cdot10^{-6}$ | $3.153\cdot10^{-7}$ | $3.15\cdot10^{-7}$ | $2.05\cdot10^{-6}$ | $2.696\cdot10^{-6}$ | $8.001\cdot10^{-6}$ | 0.03 s |
| spinnet $U_E$ synth $10^{-4}$ | $1.255\cdot10^{-4}$ | $1.922\cdot10^{-5}$ | $1.92\cdot10^{-5}$ | $1.36\cdot10^{-4}$ | $1.447\cdot10^{-4}$ | $4.0\cdot10^{-4}$ | 0.04 s |
| spinnet $U_B$ synth $10^{-6}$, all exact spinnet circuits | — | 0 | 0 | $2\cdot10^{-15}$ | — | — | 0.03 s |
| twelve $U_E$ exact | $1.2\cdot10^{-13}$ | $3.3\cdot10^{-15}$ | $6.4\cdot10^{-8}$ | $2.1\cdot10^{-15}$ | $1.2\cdot10^{-13}$ | $10^{-10}$ | 0.5 s |
| twelve step exact (general) | $2.7\cdot10^{-13}$ | $3.3\cdot10^{-15}$ | $6.7\cdot10^{-8}$ | $1.6\cdot10^{-14}$ | $2.7\cdot10^{-13}$ | $10^{-10}$ | 0.4 s |
| twelve $U_E$ synth $10^{-6}$ | $2.141\cdot10^{-6}$ | $3.153\cdot10^{-7}$ | $3.17\cdot10^{-7}$ | $4.5\cdot10^{-7}$ | $2.456\cdot10^{-6}$ | $4.001\cdot10^{-6}$ | 0.4 s |
| twelve archive best r05-F2-005 (reads 4 outer bits, 16 groups) | $1.0\cdot10^{-13}$ | $3.2\cdot10^{-15}$ | $7.0\cdot10^{-8}$ | $2.9\cdot10^{-15}$ | $1.0\cdot10^{-13}$ | $10^{-10}$ | 0.75 s of 16.8 s |
| twelve r02-F4-002 (no outer bit read) | $1.9\cdot10^{-13}$ | $3.3\cdot10^{-15}$ | $6.3\cdot10^{-8}$ | $3.5\cdot10^{-15}$ | $1.9\cdot10^{-13}$ | $10^{-10}$ | 1.5 s |
| M0-E5 circuit, `aer_mps`, tol $10^{-9}$ | $1.2\cdot10^{-13}$ | $3.3\cdot10^{-15}$ | — | — | $1.2\cdot10^{-13}$ | $10^{-9}$ | — |
| Paulo's compiled circuit (M1-P1), `aer_mps` | $1.0756\cdot10^{-5}$ | $1.31\cdot10^{-10}$ | — | $4.8\cdot10^{-10}$ | $1.0756\cdot10^{-5}$ | $2\cdot10^{-5}$ | 0.84 s of 76 s |

Readings. (i) The three spin-network numbers equal the auditor's independent values ($3.15\cdot10^{-7}$, $1.92\cdot10^{-5}$; totals $2.50$, $2.70\cdot10^{-6}$, $1.45\cdot10^{-4}$). (ii) A second independent reference, a dense $256\times256$ unitary of the data register built with `qiskit.quantum_info.Operator` (the one used by the locked test M2C-E1), agrees to $6\cdot10^{-16}$ (span) and $1.2\cdot10^{-15}$ (leak) (`check_m2c_reference.py`). (iii) On the twelve-qubit encoding the old diagnostic sits at $6$–$7\cdot10^{-8}$ for circuits whose true span leak is $3\cdot10^{-15}$: it cannot certify anything at $10^{-10}$; the direct formula can. (iv) No locked verdict flips: all totals stay inside their tolerances, including M0-E5 and M1-P1 under `aer_mps`. (v) Cost $\le1.5$ s per verdict on the twelve-qubit encoding (3153 outer patterns, 8050 stacked rows), $\le0.05$ s on the spin network.

**Alternative considered:** the operator-norm Gauss bound of audit 002 R1, $\|S\|_2\le\sqrt{\tfrac43\lambda_{\max}\sum_{c,a}(G^a_cY)^\dagger(G^a_cY)}$. Rigorous and also cancellation-free, but an upper bound that is loose by $\sqrt{\tfrac43\sum_cJ_c(J_c+1)}\ge1.6$ (measured ratio $g/\|S\|=1.77$ on the spin network implies $\ge2.0$), and it exists only for encodings with a Kogut–Susskind Gauss decoder. The exact formula needs nothing but the data the evaluator already holds, works for every encoding, and costs the same.

## 3. What goes stale when shared files change (inventory)

`provenance.code_hash()` now: `0bd7e7d9…`. Archives: twelve 22 entries (17 at the current hash incl. the best, 5 round-0 seeds at `810e86f2…`), spinnet 20 at the start of this run (all current; rounds 5 added 3 more since), fuzzy_ub 11 and fuzzy_link 4 (all current), rishon 16 at two old rishon hashes (replay "204" pending, prompts/204 step C2). So **today the m2, m4 and m10 hash checks pass**; the first edit of a file in `EVALUATOR_FILES` breaks all of them at once, and breaks rishon's (its list contains the shared one). `compress/lean/structure.json` carries exporter `a3fefb12…`, the code is at `0a74819e…` (stale; no test checks it; the m2 test rewrites the file on every run).

Replay cost from the round files (`results/compress/<enc>/round-*.json`, `wall_s` and `lean_seconds`): twelve $164+529+135+137+137+527=1629$ s of which Lean 691 s, i.e. 938 s of evaluation (largest single entry 242 s of a 300 s budget: needs quiet cores); spinnet 44 s; rishon $1317+99+176+123+87=1802$ s (prompts/204 budgets 45–110 min for its replay); fuzzy_ub 30 s; fuzzy_link 5 s. Lean certificate of the twelve best: 351 s.
