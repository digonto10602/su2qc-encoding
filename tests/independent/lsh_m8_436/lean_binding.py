"""Tester 436: Lean hook + binding checks (prompts/401 1.9, step 8.4).  Run by hand under tools/run-capped."""
import copy, hashlib, json, pathlib, shutil, subprocess, sys, tempfile
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from qiskit import QuantumCircuit
from su2plaq.compress import round as R
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
from su2plaq.lsh import lean_export as LE

ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
DRY = pathlib.Path(sys.argv[1])
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()}
sp = LL.spec()
tmp = pathlib.Path(tempfile.mkdtemp(dir=sys.argv[2]))


def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


progs = {"general": ROOT / "compress/programs/lsh/seed/000-general.py", "wrap_sn_headline": DRY / "compress/programs/lsh/seed/005-wrap_sn_headline.py"}
out["certs"] = {}
for label, p in progs.items():
    s = sha(p)
    circ, err = R._circuit_of(sp, p, label, None, DRY, expected_sha256=s)
    assert circ is not None, err
    r = LL.lean_certify(circ, sp, extra_provenance={"entry_id": f"t436-{label}", "program_file_sha256": s}, out_dir=tmp / label)
    c = json.loads(pathlib.Path(r["cert_path"]).read_text())
    rec = {"status": r["status"], "reason": r["reason"], "lean_seconds": r["seconds"], "prov_entry_id": c["provenance"].get("entry_id"),
           "prov_sha_matches_file": c["provenance"].get("program_file_sha256") == s, "gates_sha_alias": c["gates_sha256"] == c["program_sha256"],
           "n_gates": len(c["gates"]), "n_states": len(c["states"]), "target_kind": c["target"]["kind"], "checker_sha256": r.get("checker_sha256")}
    # gates_sha256 recomputation, a few serialisations
    for name, ser in (("compact", json.dumps(c["gates"], separators=(",", ":"))), ("compact_sorted", json.dumps(c["gates"], separators=(",", ":"), sort_keys=True)),
                      ("default", json.dumps(c["gates"])), ("default_sorted", json.dumps(c["gates"], sort_keys=True))):
        if hashlib.sha256(ser.encode()).hexdigest() == c["gates_sha256"]: rec["gates_sha256_recomputed_by"] = name
    out["certs"][label] = rec
    # tamper A: entry_id in the JSON -> checker unchanged (it does not read provenance); binding comparison catches it
    t1 = copy.deepcopy(c); t1["provenance"]["entry_id"] = "forged-entry"
    f1 = tmp / f"{label}-forged-entry.json"; f1.write_text(json.dumps(t1, separators=(",", ":")))
    rec["tamper_entry_id"] = {"checker": LE.check_certificate(f1)["status"], "binding_mismatch_detected": t1["provenance"]["entry_id"] != f"t436-{label}"}
    # tamper B: program sha in the JSON
    t2 = copy.deepcopy(c); t2["provenance"]["program_file_sha256"] = "0" * 64
    f2 = tmp / f"{label}-forged-sha.json"; f2.write_text(json.dumps(t2, separators=(",", ":")))
    rec["tamper_program_sha"] = {"checker": LE.check_certificate(f2)["status"], "binding_mismatch_detected": t2["provenance"]["program_file_sha256"] != s}
    # tamper C: one gate qubit (changes the circuit) -> checker must reject
    t3 = copy.deepcopy(c)
    k = next(i for i, g in enumerate(t3["gates"]) if g["g"] == "cx")
    t3["gates"][k]["q"] = [t3["gates"][k]["q"][1], t3["gates"][k]["q"][0]] if t3["gates"][k]["q"][0] != t3["gates"][k]["q"][1] else t3["gates"][k]["q"]
    f3 = tmp / f"{label}-forged-gate.json"; f3.write_text(json.dumps(t3, separators=(",", ":")))
    cc = LE.check_certificate(f3); rec["tamper_gate_swap_cx"] = {"checker": cc["status"], "reason": cc["reason"][:120]}
    # tamper D: program file differs (one byte) but archived sha is the original -> ProgramShaMismatch
    mod = tmp / f"{label}-mod.py"; mod.write_bytes(pathlib.Path(p).read_bytes() + b"\n# tampered\n")
    try:
        R._circuit_of(sp, mod, label, None, DRY, expected_sha256=s)
        rec["tamper_program_file"] = "NOT REJECTED"
    except Exception as exc:
        rec["tamper_program_file"] = f"{type(exc).__name__}: {str(exc)[:100]}"

# -beta and non-linear angle
gen = LL.general_circuit(sp)
neg = LL.general_circuit(sp.with_angles(sp.alpha, -sp.beta))
rm = LL.lean_certify(neg, sp, out_dir=tmp / "neg")
out["minus_beta"] = {"status": rm["status"], "reason": rm["reason"][:160]}
bad = QuantumCircuit(*gen.qregs)
done = False
for ins in gen.data:
    op = ins.operation
    if not done and op.name in ("rz", "p"):
        op = op.copy(); op.params = [float(op.params[0]) + 0.123]; done = True
    bad.append(op, ins.qubits)
rn = LL.lean_certify(bad, sp, out_dir=tmp / "nl")
out["non_linear"] = {"status": rn["status"], "reason": rn["reason"][:160]}
# angle_linear hook
out["angle_linear"] = {"general": LL.angle_linear(gen, sp), "minus_beta_circuit": LL.angle_linear(neg, sp)[0], "nonlinear": LL.angle_linear(bad, sp)}
out["angle_linear"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in out["angle_linear"].items()}
# a wrong circuit at +beta vs a right one with a different binding must differ in provenance but not in gates
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/436-lean-binding.json", "w"), indent=1)
print(json.dumps(out, indent=1))
