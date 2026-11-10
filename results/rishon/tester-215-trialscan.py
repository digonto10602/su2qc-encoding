"""Tester 215 probe (b): trial-mode detection rate of a 1e-6 relative angle perturbation, one crx at a time (all 81 crx of the general
step circuit), vs the full mode on a sample; and trial-vs-full on the general UE program (phase, verdict)."""
import json, subprocess, time
import numpy as np
from qiskit.circuit import CircuitInstruction
import su2plaq.rishon.compress as RC
from su2plaq.rishon.compress import spec as S, baselines as BL, evaluate as EV
spec = S.rishon_spec("step"); qc0 = BL.general_circuit(spec)
ix = [i for i, x in enumerate(qc0.data) if x.operation.name == "crx"]
det = []
for i in ix:
    q = qc0.copy(); op = q.data[i].operation.copy(); op.params = [float(op.params[0]) * (1 + 1e-6)]
    q.data[i] = CircuitInstruction(op, q.data[i].qubits, q.data[i].clbits)
    r = EV.evaluate_circuit(q, spec, mode="trial")
    det.append(not r.valid)
print("trial detects", sum(det), "of", len(det), "crx perturbations (1e-6 relative)")
# expected: block size of each pair
pairs = S.RishonCompressView().bright_pairs() if False else None
# UE program: trial vs full
specu = S.rishon_spec("UE"); path = BL.general_program_path(specu)
rt = EV.evaluate_program(str(path), specu, mode="trial"); rf = EV.evaluate_program(str(path), specu, mode="full")
print("UE program trial:", rt.valid, rt.reason, rt.verdict.op_norm_error, rt.verdict.phase, rt.metrics["t_eps"], rt.metrics.get("measured"))
print("UE program full :", rf.valid, rf.reason, rf.verdict.op_norm_error, rf.verdict.phase, rf.metrics["t_eps"], rf.metrics.get("measured"))
same = {k: rt.metrics[k] == rf.metrics[k] for k in ("cx", "t_fixed", "n_rot", "depth", "qubits")}
print("metrics equal (cx,t_fixed,n_rot,depth,qubits):", same, "| trial t_eps is estimate", rt.metrics["t_estimate"][1e-6], "full t_eps measured", rf.metrics["t_eps"])
print("phase difference", abs(np.angle(np.exp(1j * (rt.verdict.phase - rf.verdict.phase)))), "n_inputs trial/full", rt.verdict.n_inputs, rf.verdict.n_inputs)
print("trial states", EV.trial_states(specu)[:8], "...", "deterministic:", (EV.trial_states(specu) == EV.trial_states(specu)).all())
json.dump(dict(commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), seed=0, trial_detects=int(sum(det)), n_crx=len(det),
               ue=dict(trial=[rt.valid, rt.verdict.op_norm_error, rt.verdict.phase], full=[rf.valid, rf.verdict.op_norm_error, rf.verdict.phase], metrics_equal=same)),
          open("results/rishon/tester-215-trialscan.json", "w"), indent=1, default=lambda z: [z.real, z.imag] if isinstance(z, complex) else float(z))
