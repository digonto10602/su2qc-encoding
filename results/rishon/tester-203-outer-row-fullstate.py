"""Tester 203: outer electric row on my own full physical states: U_E^{in+out}|Psi> = exp(-i alpha H_E^{12 links})|Psi> (H_E = 3/4 per quartet link)."""
import json, subprocess, sys
src = open("results/rishon/tester-203-fullstate-soundness.py").read().split("codes = inner_codes()")[0]
exec(compile(src, "builder", "exec"))
QUART = {5, 6, 9, 10}
def nQ(keys, links):
    return sum(np.isin((keys >> (4 * l)) & 15, list(QUART)).astype(int) for l in links)
res = {}
for alpha in (0.37, 0.91):
    qe = build_UE(alpha, with_outer=True, include_outer_electric=True)
    qo = build_UE(alpha, with_outer=True)
    worst_e = worst_o = 0.0; nout = 0
    for s in samples:
        keys, amps = s["keys"], s["amps"]
        for qc, links, which in ((qe, range(12), "e"), (qo, range(4), "o")):
            b = ss.run_batch(qc, keys, cap=5_000_000)
            assert (b.keys == keys[b.cols]).all()                  # every basis state returned to itself (outer unchanged)
            ph = np.exp(-0.75j * alpha * nQ(keys, links))
            exp_amp = amps * ph
            got = np.zeros(len(keys), complex); np.add.at(got, b.cols, b.amps * amps[b.cols])
            e = np.abs(got - exp_amp).max()
            if which == "e": worst_e = max(worst_e, e); nout += int(nQ(keys, range(4, 12)).max() > 0)
            else: worst_o = max(worst_o, e)
    res[str(alpha)] = dict(max_dev_with_outer_row=worst_e, max_dev_inner_only=worst_o, n_states_with_outer_quartet=nout, n_states=len(samples))
    print(alpha, res[str(alpha)])
# does verify accept the outer-row circuit against the inner target? (outer phases are an outer operator: expected NOT equal to V_in (x) 1)
v = Vf.verify(build_UE(0.37, with_outer=True, include_outer_electric=True), enc, "UE", 0.37, None)
res["verify_outer_row_circuit_vs_inner_target"] = dict(ok=v.ok, reason=v.reason, err=v.op_norm_error, outer_read=v.outer_bits_read)
print(res["verify_outer_row_circuit_vs_inner_target"])
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), seed=SEED, res=res),
          open("results/rishon/tester-203-outer-row-fullstate.json", "w"), indent=1, default=float)
