"""Tester-402 mutation harness (steps 7.6-7.7).  Mutates a COPY of the tree (never the repo).  Per mutant: the locked m7 ids
for the circuits (B1[0.61], B2, B3, S1[1], S1[2], T1[UB], T1[step], E1[0.37]), the four LSH unit-test files, and my independent
checker (`tester-402-independent.py --quick`: own simulator, 433 states).
Usage: python tester-402-mutations.py <copy_root> <out.json>"""
import json, subprocess, sys, pathlib, os, re

root = pathlib.Path(sys.argv[1]); outp = sys.argv[2]
WALK = root / "src/su2plaq/lsh/walk.py"
orig = WALK.read_text()
TR = "TRANSCODE: tuple = tuple(transcode_steps())"
SOLVE = "    theta, *_ = np.linalg.lstsq(A, b, rcond=None)\n"
RET = "    return pre + (el if electric else []) + core + (el if electric == 2 else []) + mirror(pre), 7"
assert orig.count(TR) == 1 and orig.count(SOLVE) == 1 and orig.count(RET) == 1

MUTS = []
for k in range(12):
    MUTS.append((f"transcoder: drop gate {k} (forward AND inverse use the same TRANSCODE)", TR,
                 f"TRANSCODE: tuple = tuple(s for i, s in enumerate(transcode_steps()) if i != {k})"))
for k in (0, 1, 2, 3, 5, 6, 8, 11):
    MUTS.append((f"transcoder: drop gate {k} of the INVERSE only", RET,
                 f"    _inv = mirror(pre); _inv = _inv[:{k}] + _inv[{k + 1}:]\n"
                 "    return pre + (el if electric else []) + core + (el if electric == 2 else []) + _inv, 7"))
for k in range(4):
    MUTS.append((f"walk: sign of angle {k} flipped", SOLVE, SOLVE + f"    theta = np.array(theta); theta[{k}] = -theta[{k}]\n"))
MUTS.append(("walk: angle 2 off by 1e-3 relative", SOLVE, SOLVE + "    theta = np.array(theta); theta[2] *= 1.001\n"))
MUTS.append(("walk: all angles x(-1) (beta -> -beta)", SOLVE, SOLVE + "    theta = -np.array(theta)\n"))
MUTS.append(("step: order-1 layers swapped (U_E applied after U_B)", RET,
             "    return pre + (el if electric == 2 else []) + core + (el if electric else []) + mirror(pre), 7"))
MUTS.append(("step: order-2 second electric layer dropped", RET,
             "    return pre + (el if electric else []) + core + mirror(pre), 7"))
MUTS.append(("step: electric layer on the CBIT wires instead of LINK wires", "    el = [(\"p_alpha\", q) for q in LINK]", "    el = [(\"p_alpha\", q) for q in CBIT]"))
MUTS.append(("frame: first cx of FRAME dropped", 'FRAME: tuple = (("cx", LINK[1], LINK[3]), ("cx", LINK[0], LINK[1]), ("cx", LINK[0], LINK[2]))',
             'FRAME: tuple = (("cx", LINK[0], LINK[1]), ("cx", LINK[0], LINK[2]))'))
MUTS.append(("flags: one X on a CBIT dropped (first)", '[("x", q) for q in CBIT]', '[("x", q) for q in CBIT[1:]]'))

TESTS = ["tests/acceptance/m7/test_lsh_circuits.py::test_M7_B1_magnetic_inner_block[0.61]", "tests/acceptance/m7/test_lsh_circuits.py::test_M7_B2_physical_states",
         "tests/acceptance/m7/test_lsh_circuits.py::test_M7_B3_gauss_and_clean_ancillas", "tests/acceptance/m7/test_lsh_circuits.py::test_M7_S1_step_orders",
         "tests/acceptance/m7/test_lsh_circuits.py::test_M7_E1_electric_step[0.37]",
         "tests/acceptance/m7/test_lsh_metrics.py::test_M7_T1_t_table_and_synth_verify[UB]", "tests/acceptance/m7/test_lsh_metrics.py::test_M7_T1_t_table_and_synth_verify[step]"]
UNIT = ["tests/unit/test_lsh_walk_unit.py", "tests/unit/test_lsh_circuits_unit.py", "tests/unit/test_lsh_codec_unit.py", "tests/unit/test_lsh_operators_unit.py"]
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def run(tests):
    cmd = ["taskset", "-c", "14-17", "python", "-m", "pytest", "-n", "4", "-q", "-p", "no:cacheprovider", "--tb=no", "-rfE", *tests]
    r = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    txt = r.stdout + r.stderr
    return re.findall(r"^(?:FAILED|ERROR) (\S+)", txt, flags=re.M), (txt.strip().splitlines() or [""])[-1]


def indep():
    e2 = dict(env, PYTHONPATH=str(root / "src"))
    r = subprocess.run(["taskset", "-c", "14-17", "python", "results/lsh_tester/tester-402-independent.py", "--quick"], cwd=root, env=e2,
                       capture_output=True, text=True)
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
    crashed = r.returncode not in (0, 1) or ("Traceback" in r.stderr)
    return fails, crashed, (r.stderr.strip().splitlines() or [""])[-1][:200]


res = []
fa, la = run(TESTS); fu, lu = run(UNIT); fi, cr, er = indep()
print("BASELINE:", fa, la, "|", fu, lu, "| indep fails", len(fi), cr, flush=True)
res.append({"mutation": "baseline", "acc_failed": fa, "unit_failed": fu, "acc": la, "unit": lu, "indep_fails": len(fi)})
short = lambda L: sorted({x.split("::")[-1] for x in L})
for name, old, new in MUTS:
    WALK.write_text(orig.replace(old, new))
    try:
        fa, la = run(TESTS); fu, lu = run(UNIT); fi, cr, er = indep()
    finally:
        WALK.write_text(orig)
    caught_acc, caught_unit, caught_indep = bool(fa), bool(fu), bool(fi) or cr
    print(("CAUGHT " if (caught_acc or caught_unit or caught_indep) else "MISSED ") + name, "| acc:", short(fa), "| unit:", len(fu), "| indep fails:", len(fi), "crash" if cr else "", flush=True)
    res.append({"mutation": name, "caught": caught_acc or caught_unit or caught_indep, "caught_by_acceptance": caught_acc, "acc_failed": short(fa),
                "caught_by_unit": caught_unit, "n_unit_failed": len(fu), "unit_first": short(fu)[:4], "caught_by_independent": caught_indep,
                "indep_first": fi[:2], "indep_crash": er if cr else ""})
json.dump(res, open(outp, "w"), indent=1)
print("caught", sum(1 for r in res if r.get("caught")), "of", len(MUTS))
print("caught by acceptance", sum(1 for r in res if r.get("caught_by_acceptance")), "| by unit", sum(1 for r in res if r.get("caught_by_unit")), "| by independent", sum(1 for r in res if r.get("caught_by_independent")))
