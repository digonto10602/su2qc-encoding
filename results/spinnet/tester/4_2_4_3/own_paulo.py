"""Own check of Paulo's 15-qubit file against the loop's gauge: Aer on all 433 states, own route-B target (scipy expm of exact.spinnet H_B)
and an independently derived sign gauge (sign pattern of M/V), compared with loop.import_seed('paulo15').gauge."""
import sys, json, numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import own_verify as OV
from su2plaq.circuits import spinnet as C
from su2plaq.spinnet import loop as L
from su2plaq.compress.spec import default_spec

sp = L.spec()
seed = L.import_seed(sp, "paulo15")
qc = seed.qc
beta = seed.beta
outs, anc, outer = OV.aer_block(qc)
V = OV.targetB("UB", None, beta)
raw = OV.err(outs, V)
# independent gauge: on entries with |V_ij| > 0.05 the ratio M_ij/V_ij = ph * d_i d_j
big = np.abs(V) > 0.05
R = np.zeros_like(V); R[big] = outs[big] / V[big]
ph = np.exp(1j * np.angle(R[big]).mean()) if False else None
# phase: the diagonal entries with |V_ii| > 0.05 have d_i d_i = +1
diag = np.diag(R)[np.abs(np.diag(V)) > 0.05]
ph = diag.mean() / abs(diag.mean())
S = np.real(R / ph)          # d_i d_j on the big entries
d = np.zeros(433)
# propagate signs per connected component of the big-entry graph
seen = np.zeros(433, bool)
ncomp = 0
for s0 in range(433):
    if seen[s0]: continue
    ncomp += 1; d[s0] = 1; seen[s0] = True; stack = [s0]
    while stack:
        i = stack.pop()
        for j in np.nonzero(big[i])[0]:
            if not seen[j]:
                d[j] = d[i] * np.sign(S[i, j]); seen[j] = True; stack.append(j)
            elif abs(S[i, j] - d[i] * d[j]) > 1e-6:
                raise RuntimeError(f"inconsistent sign {i},{j}")
# components are fixed only up to a sign each; compare with the loop's gauge as D V D (invariant under per-block sign)
g = seed.gauge
Vg = g[:, None] * V * g[None, :]
Vd = d[:, None] * V * d[None, :]
res = {"n_qubits": qc.num_qubits, "beta": beta, "err_raw_vs_ungauged_target": raw, "err_vs_loop_gauge": OV.err(outs, Vg), "err_vs_own_gauge": OV.err(outs, Vd),
       "ancilla_leak_weight": anc, "outer_changed": outer, "n_components_of_big_entry_graph": ncomp,
       "loop_gauge_n_minus_states": int((g < 0).sum()), "loop_gauge_minus_data_codes": L.gauge_minus_codes(g),
       "loop_gauge_pm1": bool(np.all(np.abs(np.abs(g) - 1) == 0)), "len_gauge": int(len(g)),
       "ratio_matrix_consistency": "no inconsistency raised",
       "max_offdiag_diff_gauges": float(np.abs(Vg - Vd).max())}
# expected number of -1 states: states whose data code in {8..15} (bright, bit 3 set)
dc = OV.codes & 0xFF
res["states_with_data_code_in_8_15"] = int(np.isin(dc, np.arange(8, 16)).sum())
res["loop_minus_states_equal_that_set"] = bool(np.array_equal(g < 0, np.isin(dc, np.arange(8, 16))))
# ungauged by flipping beta -> -beta? (METHODS: sign gauge == beta -> -beta on those pairs)  also random 8-negative vector fails
rng = np.random.default_rng(20261104)
g8 = np.ones(433); g8[rng.choice(433, 8, replace=False)] = -1
res["err_with_random_8_negative_vector"] = OV.err(outs, g8[:, None] * V * g8[None, :])
print(json.dumps(res, indent=1))
