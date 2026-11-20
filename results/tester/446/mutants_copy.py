"""Planner 402: the amended G2 helper on the real headline, on mutants, and against the old helper.
Run: PYTHONPATH=src taskset -c 0-7 tools/run-capped python scratch/planner/402/mutants.py"""
import importlib.util, json, pathlib, subprocess, sys, time, types
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
spec_ = importlib.util.spec_from_file_location("g2amended", ROOT / "tests/acceptance/m8/test_lsh_m8_gate.py")
T = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(T)
from su2plaq.compress.spec import default_spec, get_encoding
from su2plaq.compress.archive import Archive
from su2plaq.compress import robust

spec = default_spec("lsh", "step"); enc = get_encoding("lsh")
arch = Archive.load("lsh", root=ROOT, n_alt=2, strict=True)
head = {e.id: e for e in arch.entries()}[robust.headline("lsh", "step", root=ROOT)["id"]]
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
       "amended_test_sha256": __import__("hashlib").sha256((ROOT / "tests/acceptance/m8/test_lsh_m8_gate.py").read_bytes()).hexdigest(), "rows": {}}

def real(specs, e=head):
    return T._rebuild(ROOT, e, specs)

def prog(name):
    e = types.SimpleNamespace(program_path=f"scratch/tester/446/m402/mutants/{name}.py", id=name)
    return lambda specs: T._rebuild(ROOT, e, specs)

def circ_mut(fn):
    def rebuild(specs):
        res = []
        for qc in real(specs):
            qc = qc.copy(); fn(qc); res.append(qc)
        return res
    return rebuild

def drop_first_outer_cx(qc):
    for i, inst in enumerate(qc.data):
        if inst.operation.name == "cx" and qc.find_bit(inst.qubits[0]).index == 13:
            del qc.data[i]; return
    raise RuntimeError

def with_ancilla(dirty):
    def rebuild(specs):
        res = []
        for qc in real(specs):
            new = QuantumCircuit(*qc.qregs, QuantumRegister(1, "a"), global_phase=qc.global_phase)
            new.cx(13, 24)    # copy the outer bit q13 (a read) into the ancilla
            for inst in qc.data:
                new.append(inst.operation, [qc.find_bit(q).index for q in inst.qubits])
            if not dirty:
                new.cx(13, 24)    # uncompute: a valid circuit with one clean ancilla (q13 never changes)
            res.append(new)
        return res
    return rebuild

def neg_beta(specs):
    return real([s.with_angles(s.alpha, -s.beta) for s in specs])

CASES = [
    ("headline r05-F3-005 (real)", real, "pass"),
    ("W1 writes outer: cx(0->13) twice (net identity)", circ_mut(lambda qc: (qc.cx(0, 13), qc.cx(0, 13))), "fail"),
    ("W2 writes outer: x(13) twice", circ_mut(lambda qc: (qc.x(13), qc.x(13))), "fail"),
    ("W3 writes outer: h(14) twice", circ_mut(lambda qc: (qc.h(14), qc.h(14))), "fail"),
    ("W4 writes outer: swap(13,14) twice", circ_mut(lambda qc: (qc.swap(13, 14), qc.swap(13, 14))), "fail"),
    ("W5 writes outer: cx(0->13) once at the end", circ_mut(lambda qc: qc.cx(0, 13)), "fail"),
    ("C1 wrong circuit: one walk coefficient sign flipped (program)", prog("walk_sign"), "fail"),
    ("C2 wrong circuit: reads outer q16 instead of q13 (program)", prog("wrong_outer"), "fail"),
    ("C3 wrong circuit: first cx(13->0) dropped", circ_mut(drop_first_outer_cx), "fail"),
    ("C4 wrong circuit: built at -beta", neg_beta, "fail"),
    ("C5 wrong circuit: one rz shifted by 1e-8 (program)", prog("rz_1e-8"), "fail"),
    ("C6 below tolerance: one rz shifted by 1e-13 (program)", prog("rz_1e-13"), "pass"),
    ("C7 wrong circuit: extra rz(0.3) on outer q13 (diagonal read, statically allowed)", circ_mut(lambda qc: qc.rz(0.3, 13)), "fail"),
    ("C8 wrong circuit: extra cz(13,14) (diagonal read, statically allowed)", circ_mut(lambda qc: qc.cz(13, 14)), "fail"),
    ("C9 wrong circuit: x(0) at the end (leaves the physical codes)", circ_mut(lambda qc: qc.x(0)), "fail"),
    ("A1 dirty ancilla: cx(13->a) not uncomputed", with_ancilla(True), "fail"),
    ("A2 valid variant with one clean ancilla: cx(13->a) before and after the circuit (25 qubits: over the full-register limit)", with_ancilla(False), "fail"),
]
ok_all = True
for name, rebuild, expect in CASES:
    t0 = time.time()
    try:
        res = T.g2_second_engine(rebuild, spec, enc, name)
        row = {"verdict": "pass", "max_error": max(r["error"] for r in res), "n_qubits": res[0]["n_qubits"], "n_runs": res[0].get("n_runs"),
               "weights": [max(r.get(k, 0.0) for r in res) for k in ("ancilla_weight", "leak_weight", "outer_weight")],
               "full": [r.get("full") for r in res]}
    except AssertionError as exc:
        row = {"verdict": "fail", "message": str(exc)[:260]}
    row["seconds"] = round(time.time() - t0, 2); row["expected"] = expect
    good = expect == "any" or row["verdict"] == expect
    ok_all &= good
    out["rows"][name] = row
    print(("OK  " if good else "BAD ") + name, "->", json.dumps(row), flush=True)

# dynamic part alone on the outer-writing circuits (static scan bypassed on purpose): does Aer see the write?
for name, fn in [("W5 dynamic only", lambda qc: qc.cx(0, 13)), ("W6 dynamic only: cx(0->13), h(13), cx(0->13)", lambda qc: (qc.cx(0, 13), qc.h(13), qc.cx(0, 13)))]:
    qc = circ_mut(fn)([spec])[0]
    res = T.aer_outer_read_check(qc, enc, *T.NOMINAL, {13: 1, 14: 1})
    out["rows"][name] = res; print(name, json.dumps(res), flush=True)
    ok_all &= not (res["error"] <= T.TOL and res["outer_weight"] <= 1e-20 and res["leak_weight"] <= 1e-20)

# the full-register block alone on wrong circuits (called directly, nominal pair): does it see them without the reduced block?
qc0 = real([spec])[0]
states = T.g2_states(qc0, enc, T.outer_reads(qc0, enc))
out["state_sector_weight_min"] = float(min((abs(states[:, [k for k, c in enumerate(enc.physical_vectors().codes) if ((int(c[0]) >> 13) & 3) == s_]]) ** 2).sum(axis=1).min() for s_ in range(4)))
for name, rebuild in [("F-C1 full register: walk sign", prog("walk_sign")), ("F-C5 full register: rz shifted by 1e-8", prog("rz_1e-8")),
                      ("F-C6 full register: rz shifted by 1e-13 (below tolerance)", prog("rz_1e-13")),
                      ("F-C7 full register: rz(0.3) on outer q13", circ_mut(lambda qc: qc.rz(0.3, 13))),
                      ("F-W5 full register: cx(0->13) at the end (static scan bypassed)", circ_mut(lambda qc: qc.cx(0, 13))),
                      ("F-W7 full register: cx(0->20) at the end, an outer qubit the circuit does not read (static scan bypassed)", circ_mut(lambda qc: qc.cx(0, 20)))]:
    t0 = time.time()
    res = T.aer_full_register_check(rebuild([spec])[0], enc, *T.NOMINAL, states)
    res["seconds"] = round(time.time() - t0, 1)
    res["would_pass"] = bool(res["error"] <= T.TOL and res["ancilla_weight"] <= 1e-20 and res["leak_weight"] <= 1e-20 and res["outer_weight_change"] <= T.TOL)
    out["rows"][name] = res; print(name, json.dumps(res), flush=True)
    ok_all &= res["would_pass"] == ("below tolerance" in name)

# old helper vs new helper on circuits that touch no outer qubit (new helper with an empty read set: 47 runs, 433 columns)
for e in arch.entries():
    if e.round == 0 and e.valid and (ROOT / e.program_path).suffix == '.py' and (ROOT / e.program_path).exists():
        qc = T._rebuild(ROOT, e, [spec])[0]
        try:
            reads = T.outer_reads(qc, enc)
        except AssertionError as exc:
            print("seed", e.id, "static:", str(exc)[:120]); continue
        if reads or enc.layout_of(qc).ancilla.__len__() > 14 or not enc.layout_of(qc).outer:
            print("seed", e.id, "skipped (reads outer / >14 ancillas / no outer register)", sorted(reads), len(enc.layout_of(qc).ancilla)); continue
        t0 = time.time(); old = T.aer_inner_check(qc, enc, *T.NOMINAL); t1 = time.time(); new = T.aer_outer_read_check(qc, enc, *T.NOMINAL, {}); t2 = time.time()
        row = {"old_47": old, "new_433": new, "t_old": round(t1 - t0, 2), "t_new": round(t2 - t1, 2)}
        out["rows"]["seed " + e.id] = row; print("seed", e.id, json.dumps(row), flush=True)
        ok_all &= old["error"] <= T.TOL and new["error"] <= T.TOL
out["all_as_expected"] = bool(ok_all)
(HERE / "mutants-rerun.json").write_text(json.dumps(out, indent=1))
print("ALL AS EXPECTED" if ok_all else "SOMETHING UNEXPECTED")
