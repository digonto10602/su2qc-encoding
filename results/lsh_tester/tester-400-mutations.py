"""Tester-400 mutation harness: mutates a COPY of src/su2plaq/lsh/operators.py (never the repo) and runs the locked
acceptance ids A1, K1, K2, X1 and the LSH unit tests against the copy.  Usage:
  python results/lsh_tester/tester-400-mutations.py <copy_root> <out.json>
<copy_root> must contain src/, tests/acceptance/m7, tests/unit/test_lsh_*.py, pytest.ini (made by the tester)."""
import json, subprocess, sys, pathlib, os, re

root = pathlib.Path(sys.argv[1]); outp = sys.argv[2]
op = root / "src/su2plaq/lsh/operators.py"
orig = op.read_text()

MUTS = [
    # (name, kind, old, new)
    ("site rule: drop 110 from VALID_SITE", "site", "VALID_SITE = (0b000, 0b001, 0b010, 0b100, 0b110)", "VALID_SITE = (0b000, 0b001, 0b010, 0b100)"),
    ("site rule: add 111 to VALID_SITE", "site", "VALID_SITE = (0b000, 0b001, 0b010, 0b100, 0b110)", "VALID_SITE = (0b000, 0b001, 0b010, 0b100, 0b110, 0b111)"),
    ("site rule: add 011 (replace 010)", "site", "VALID_SITE = (0b000, 0b001, 0b010, 0b100, 0b110)", "VALID_SITE = (0b000, 0b001, 0b011, 0b100, 0b110)"),
    ("site rule: flux N_2 uses l23+l31 (wrong leg sum)", "site", "return l31 + l12, l12 + l23, l23 + l31", "return l31 + l12, l23 + l31, l12 + l23"),
    ("site rule: cap only N_1<=1 (drop N_2 cap)", "site", "return n1 <= 1 and n2 <= 1", "return n1 <= 1"),
    ("site rule: cap N_1<=1, N_2<=2", "site", "return n1 <= 1 and n2 <= 1", "return n1 <= 1 and n2 <= 2"),
    ("AGL: skip virtual-link condition", "site", "if fl[c][2] != fl[4 + c][2]:", "if False:"),
    ("AGL: inner link compares N_1 of next with N_1 of this", "site", "if fl[c][1] != fl[c2][0]:", "if fl[c][0] != fl[c2][0]:"),
    ("ladder: L++ factor (S+2) -> (S+1)", "ladder", "math.sqrt((l12 + 1) * (S + 2))", "math.sqrt((l12 + 1) * (S + 1))"),
    ("ladder: L-- factor (S+1) -> S", "ladder", "math.sqrt(l12 * (S + 1))", "math.sqrt(l12 * S)"),
    ("ladder: L+- sign flipped", "ladder", "-math.sqrt((l31 + 1) * l23)", "math.sqrt((l31 + 1) * l23)"),
    ("ladder: L-+ (l31) -> (l31+1)", "ladder", "-math.sqrt(l31 * (l23 + 1))", "-math.sqrt((l31 + 1) * (l23 + 1))"),
    ("ladder: dressing (N_p+1) dropped", "ladder", "return new, amp / math.sqrt((n_n_new + 1) * (n_p_old + 1))", "return new, amp / math.sqrt((n_n_new + 1))"),
    ("ladder: dressing uses N_n of old state", "ladder", "n_n_new = new[0] + new[1]", "n_n_new = l12 + l23"),
    ("ladder: overall factor 2 on L++", "ladder", "new, amp = (l12 + 1, l23, l31), math.sqrt((l12 + 1) * (S + 2))", "new, amp = (l12 + 1, l23, l31), 2 * math.sqrt((l12 + 1) * (S + 2))"),
    ("vertex: c0 (0,0) sign +1 -> -1", "vertex", "(((+1, -1, +1), (-1, -1, -1)), ((+1, +1, +1), (+1, +1, -1))),      # c0", "(((-1, -1, +1), (-1, -1, -1)), ((+1, +1, +1), (+1, +1, -1))),      # c0"),
    ("vertex: c1 (0,0) sign +1 -> -1", "vertex", "(((+1, +1, +1), (+1, +1, -1)), ((-1, -1, +1), (+1, -1, -1))),      # c1", "(((-1, +1, +1), (+1, +1, -1)), ((-1, -1, +1), (+1, -1, -1))),      # c1"),
    ("vertex: c1 (1,0) sign -1 -> +1", "vertex", "(((+1, +1, +1), (+1, +1, -1)), ((-1, -1, +1), (+1, -1, -1))),      # c1", "(((+1, +1, +1), (+1, +1, -1)), ((+1, -1, +1), (+1, -1, -1))),      # c1"),
    ("vertex: c2 (0,1) sign -1 -> +1", "vertex", "(((+1, +1, -1), (-1, +1, +1)), ((+1, -1, -1), (+1, -1, +1))),      # c2", "(((+1, +1, -1), (+1, +1, +1)), ((+1, -1, -1), (+1, -1, +1))),      # c2"),
    ("vertex: c3 (1,1) sign -1 -> +1", "vertex", "(((-1, -1, -1), (-1, -1, +1)), ((+1, +1, -1), (-1, +1, +1))),      # c3", "(((-1, -1, -1), (-1, -1, +1)), ((+1, +1, -1), (+1, +1, +1))),      # c3"),
    ("vertex: c3 (0,0) sign -1 -> +1", "vertex", "(((-1, -1, -1), (-1, -1, +1)), ((+1, +1, -1), (-1, +1, +1))),      # c3", "(((+1, -1, -1), (-1, -1, +1)), ((+1, +1, -1), (-1, +1, +1))),      # c3"),
    ("vertex: c0 (0,1) sigma (-,-)->(+,+)", "vertex", "(((+1, -1, +1), (-1, -1, -1)), ((+1, +1, +1), (+1, +1, -1))),      # c0", "(((+1, -1, +1), (-1, +1, +1)), ((+1, +1, +1), (+1, +1, -1))),      # c0"),
    ("electric: N_n -> N_p read at in-site", "elec", "e = sum((site_flux(s[c])[1] / 2) * (site_flux(s[c])[1] / 2 + 1) for c in range(4))", "e = sum((site_flux(s[c])[0] / 2) * (site_flux(s[c])[0] / 2 + 1) for c in range(4))"),
    ("electric: j(j+1) -> j^2", "elec", "e = sum((site_flux(s[c])[1] / 2) * (site_flux(s[c])[1] / 2 + 1) for c in range(4))", "e = sum((site_flux(s[c])[1] / 2) ** 2 for c in range(4))"),
    ("electric: outer legs flux N_3 included", "elec", "for f in site_flux(s[4 + c])[:2])", "for f in site_flux(s[4 + c]))"),
    ("K: drop h.c. (K = -P)", "K", "return -(P + P.T)", "return -P"),
    ("h_magnetic: couple all codes regardless of outer part", "K", "by_outer.setdefault(c >> 12, []).append(k)", "by_outer.setdefault(0, []).append(k)"),
]

TESTS_ACC = ["tests/acceptance/m7/test_lsh_model.py::test_M7_A1_register_agl_counts",
             "tests/acceptance/m7/test_lsh_model.py::test_M7_K1_ladder_factors_from_prepotentials",
             "tests/acceptance/m7/test_lsh_model.py::test_M7_K2_plaquette_operator_vs_route_b_and_a",
             "tests/acceptance/m7/test_lsh_model.py::test_M7_X1_spectra_three_routes"]
env = dict(os.environ, PER_JOB_MEM="6G", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")

def run(tests, extra=()):
    cmd = ["taskset", "-c", "14-17", "/home/digimonk/Projects/su2qc-encoding/tools/run-capped", "python", "-m", "pytest", "-n", "4", "-q", "-p", "no:cacheprovider",
           "--tb=no", "-rf", *extra, *tests]
    r = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    txt = r.stdout + r.stderr
    failed = re.findall(r"^FAILED (\S+)", txt, flags=re.M)
    last = txt.strip().splitlines()[-1] if txt.strip() else ""
    return failed, last

res = []
# baseline
f, last = run(TESTS_ACC + ["tests/unit"])
print("BASELINE (unmutated copy):", f, last, flush=True)
res.append({"mutation": "baseline", "failed": f, "summary": last})
for name, kind, old, new in MUTS:
    if orig.count(old) != 1:
        print("SKIP (pattern count %d): %s" % (orig.count(old), name)); res.append({"mutation": name, "error": "pattern count %d" % orig.count(old)}); continue
    op.write_text(orig.replace(old, new))
    try:
        f_acc, l1 = run(TESTS_ACC)
        f_unit, l2 = run(["tests/unit"])
    finally:
        op.write_text(orig)
    short = lambda L: [x.split("::")[-1] for x in L]
    caught = bool(f_acc or f_unit)
    print(("CAUGHT " if caught else "MISSED ") + name, "| acceptance:", short(f_acc), "| unit:", len(f_unit), "failed", flush=True)
    res.append({"mutation": name, "kind": kind, "caught": caught, "acceptance_failed": short(f_acc), "n_unit_failed": len(f_unit),
                "unit_failed_first": short(f_unit)[:6], "acc_summary": l1, "unit_summary": l2})
json.dump(res, open(outp, "w"), indent=1)
print("caught", sum(1 for r in res if r.get("caught")), "of", sum(1 for r in res if "caught" in r))
