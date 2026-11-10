"""Tester 215: (i) evaluate_program full mode on the general STEP program (E4's first half, independent rerun) and
(ii) verify_synthesised on the general UE circuit (spot check of the 21-min E4 second half on a small circuit)."""
import json, subprocess, time
import su2plaq.rishon.compress as RC
from su2plaq.rishon.compress import spec as S, baselines as BL, evaluate as EV
spec = S.rishon_spec("step"); path = BL.general_program_path(spec); t = time.time()
r = EV.evaluate_program(str(path), spec, mode="full")
print("STEP full:", r.valid, r.reason, "err", r.verdict.op_norm_error, "dropped", r.verdict.dropped_total, "gauss", r.verdict.gauss_residual,
      "alts", [(v.ok, v.op_norm_error, v.dropped_total) for v in r.verdicts_alt], "skel", r.skeleton_equal, "key", r.metrics["cx"], r.metrics["t_eps"], r.metrics["depth_ct"], r.metrics["qubits"],
      "wall", time.time() - t, "n_inputs", r.verdict.n_inputs, "gauss_states", r.verdict.extra.get("gauss_states"), flush=True)
specu = S.rishon_spec("UE"); t = time.time()
sv = EV.verify_synthesised(BL.general_circuit(specu), specu)
print("UE synth:", sv["ok"], "err", sv["verdict"].op_norm_error, "tol", sv["tolerances"], "n_rot", sv["n_rot"], "t_total", sv["t_total"], "wall", time.time() - t)
json.dump(dict(commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(),
  step=dict(valid=r.valid, reason=r.reason, err=r.verdict.op_norm_error, dropped=r.verdict.dropped_total, gauss=r.verdict.gauss_residual, alts=[[v.ok, v.op_norm_error] for v in r.verdicts_alt], key=[r.metrics["cx"], r.metrics["t_eps"], r.metrics["depth_ct"], r.metrics["qubits"]]),
  ue_synth=dict(ok=sv["ok"], err=sv["verdict"].op_norm_error, tol=sv["tolerances"], n_rot=sv["n_rot"], t_total=sv["t_total"])), open("results/rishon/tester-215-fullprogram.json", "w"), indent=1)
