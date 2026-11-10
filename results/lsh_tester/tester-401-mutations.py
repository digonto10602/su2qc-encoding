"""Tester-401 mutation harness (steps 7.3-7.5).  Mutates a COPY of the tree (never the repo); runs the locked acceptance ids that
are green at this step (A1, K1, K2, X1, C1, C2, E1, G1, T1[UE]) and the three LSH unit-test files against each mutant.
Usage: python tester-401-mutations.py <copy_root> <out.json>"""
import json, subprocess, sys, pathlib, os, re

root = pathlib.Path(sys.argv[1]); outp = sys.argv[2]
F = {k: root / v for k, v in {
    "ops": "src/su2plaq/lsh/operators.py", "enc": "src/su2plaq/encodings/lsh.py",
    "walk": "src/su2plaq/lsh/walk.py", "circ": "src/su2plaq/circuits/lsh.py"}.items()}
orig = {k: p.read_text() for k, p in F.items()}

MUTS = [
    # ---- codec bit order / placement
    ("codec: site_code bit order reversed per site (l12 <-> l31)", "ops", "out |= r << k", "out |= r << (2 - k)"),
    ("codec: 'in' sites placed in reverse corner order (3c -> 3(3-c))", "ops", "code |= site_code(j4[p], j4[n], J[c]) << (3 * c)", "code |= site_code(j4[p], j4[n], J[c]) << (3 * (3 - c))"),
    ("codec: 'out' sites placed in reverse corner order", "ops", "code |= site_code(j[o1], j[o2], J[c]) << (12 + 3 * c)", "code |= site_code(j[o1], j[o2], J[c]) << (12 + 3 * (3 - c))"),
    ("codec: outer legs swapped (o1<->o2) in out-site code", "ops", "code |= site_code(j[o1], j[o2], J[c]) << (12 + 3 * c)", "code |= site_code(j[o2], j[o1], J[c]) << (12 + 3 * c)"),
    ("codec: p,n swapped in in-site code", "ops", "code |= site_code(j4[p], j4[n], J[c]) << (3 * c)", "code |= site_code(j4[n], j4[p], J[c]) << (3 * c)"),
    ("codec: registers l_nv <-> l_vp", "enc", '"l_nv": [1, 4, 7, 10], "l_vp": [2, 5, 8, 11]', '"l_nv": [2, 5, 8, 11], "l_vp": [1, 4, 7, 10]'),
    ("codec: out registers start at 11", "enc", 'self.registers[f"site_out_{c}"] = [12 + 3 * c, 12 + 3 * c + 1, 12 + 3 * c + 2]', 'self.registers[f"site_out_{c}"] = [11 + 3 * c, 11 + 3 * c + 1, 11 + 3 * c + 2]'),
    ("codec: label order scrambled (sorted codes)", "enc", "self._codes = np.array(codes, dtype=np.int64)", "self._codes = np.array(sorted(codes), dtype=np.int64)"),
    ("codec: decode index shifted by one", "enc", "return self._index.get(int(code))", "k = self._index.get(int(code)); return None if k is None else (k + 1) % 433"),
    ("codec: decode_state drops gauge sign", "enc", "self.basis.amps[k] * self.gauge[k])", "self.basis.amps[k])"),
    ("codec: gauge sign inverted for k=0", "enc", "self.gauge = gauge.astype(np.float64)", "self.gauge = gauge.astype(np.float64); self.gauge[0] *= -1"),
    ("codec: inner_codes returns unsorted/duplicate (drop one)", "enc", "return self._inner.copy()", "return self._inner[:-1].copy()"),
    # ---- decode fallback
    ("fallback: returns a physical state (basis 0)", "enc", "hit = self._fallback(code) if k is None else", "hit = (self.basis.keys[0], self.basis.amps[0]) if k is None else"),
    ("fallback: all codes map to one key (non-injective)", "enc", "return np.array([key], dtype=np.int64), np.array([1.0 + 0j])", "return np.array([0], dtype=np.int64), np.array([1.0 + 0j])"),
    ("fallback: inner-end sign constant (+1/2)", "enc", "g = -0.5 if fl[c][2] == 2 else 0.5", "g = 0.5"),
    ("fallback: outer-end sign constant (-1/2)", "enc", "g = 0.5 if fl[4 + c][2] == 2 else -0.5", "g = -0.5"),
    ("fallback: outer sites ignored (no half spins from out sites)", "enc", "N = fl[4 + c][0] if i == O.CORNER_OUT[c][0] else fl[4 + c][1]", "N = 0"),
    ("fallback: far ends not +1/2 (mL=mR=-1/2)", "enc", "mL = mR = 0.5", "mL = mR = -0.5"),
    ("decode: data-part validity check removed", "enc", "if code < 0 or code >> 24 or not self._valid_data[code & _DATA_MASK]:", "if code < 0 or code >> 24:"),
    ("decode: out-site flux cap check removed", "enc", "if not all(O.site_valid((code >> (12 + 3 * c)) & 7) for c in range(4)):", "if False:"),
    ("decode: fallback of 'in' sites uses N_n for both legs", "enc", "N = fl[c][0] if i == O.CORNER_PN[c][0] else fl[c][1]", "N = fl[c][1]"),
    # ---- electric weights
    ("electric: one inner weight wrong (c==2 ->  (N/2)^2 in H_E)", "ops", "e = sum((site_flux(s[c])[1] / 2) * (site_flux(s[c])[1] / 2 + 1) for c in range(4))", "e = sum((site_flux(s[c])[1] / 2) * (site_flux(s[c])[1] / 2 + (0 if c == 2 else 1)) for c in range(4))"),
    ("electric: one outer weight wrong (site out 3 counted twice)", "ops", "e += sum((f / 2) * (f / 2 + 1) for c in range(4) for f in site_flux(s[4 + c])[:2])", "e += sum((f / 2) * (f / 2 + 1) * (2 if c == 3 else 1) for c in range(4) for f in site_flux(s[4 + c])[:2])"),
    ("circuit UE: one inner phase wrong (c=2, l_nv gets 1/2)", "circ", "        qc.p(-J_HALF_PHASE * alpha, 3 * c + 1)\n    if include", "        qc.p(-(0.5 if c == 2 else J_HALF_PHASE) * alpha, 3 * c + 1)\n    if include"),
    ("circuit UE: J_HALF_PHASE 0.75 -> 0.5", "circ", "J_HALF_PHASE = 0.75", "J_HALF_PHASE = 0.5"),
    ("circuit UE: phase sign flipped on one qubit (c=1, l_pn)", "circ", "        qc.p(-J_HALF_PHASE * alpha, 3 * c)\n", "        qc.p((J_HALF_PHASE if c == 1 else -J_HALF_PHASE) * alpha, 3 * c)\n"),
    ("circuit UE: l_pn phase put on l_vp (qubit 3c+2)", "circ", "        qc.p(-J_HALF_PHASE * alpha, 3 * c)\n", "        qc.p(-J_HALF_PHASE * alpha, 3 * c + 2)\n"),
    ("circuit UE outer: l_12 weight 3/2 -> 3/4", "circ", "qc.p(-2 * J_HALF_PHASE * alpha, N_DATA + 3 * c)", "qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c)"),
    ("circuit UE outer: l_v1 phase dropped on corner 3", "circ", "            qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c + 2)", "            if c != 3:\n                qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c + 2)"),
    ("circuit UE outer: l_2v phase on l_v1 twice (c=0)", "circ", "            qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c + 1)\n", "            qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c + (2 if c == 0 else 1))\n"),
    ("circuit UE: include_outer_electric ignored", "circ", "    if include_outer_electric:\n        for c in range(4):", "    if False:\n        for c in range(4):"),
    # ---- coupling table / targets
    ("table: sign flipped for the +1 entry of code 0b100010", "walk", "table[c] = round(2 * v) / 2", "table[c] = round(2 * v) / 2 * (-1 if c == 0b100010 else 1)"),
    ("table: sign flipped for both -1/2 entries", "walk", "table[c] = round(2 * v) / 2", "table[c] = round(2 * v) / 2 * (-1 if round(2 * v) == -1 else 1)"),
    ("table: sign flipped for code 0 (-2 -> +2)", "walk", "table[c] = round(2 * v) / 2", "table[c] = round(2 * v) / 2 * (-1 if c == 0 else 1)"),
    ("table: |value| of one +1 entry halved", "walk", "table[c] = round(2 * v) / 2", "table[c] = round(2 * v) / 2 * (0.5 if c == 0b100010 else 1)"),
    ("partner: two partners swapped", "walk", "            out[c] = codes[int(nz[0])]", "            out[c] = codes[int(nz[0])] if c != 0 else 0b000000100010"),
    ("target: U_B with exp(+i beta H)", "enc", "return (v * np.exp(-1j * t * w)) @ v.conj().T", "return (v * np.exp(1j * t * w)) @ v.conj().T"),
    ("target: step order 1 composed UE @ UB", "enc", "            return U @ UE(alpha)", "            return UE(alpha) @ U"),
    ("target: step order 2 half-angle -> alpha", "enc", "return UE(alpha / 2) @ U @ UE(alpha / 2)", "return UE(alpha) @ U @ UE(alpha)"),
    ("target: UE ignores include_outer (inner HE always)", "enc", "HE = self._HE_all if include_outer_electric else self._HE_inner", "HE = self._HE_inner"),
    ("target: inner_target uses K_codes sign flipped", "enc", "self._eig_K = np.linalg.eigh(self.K_codes)", "self._eig_K = np.linalg.eigh(-self.K_codes)"),
    ("target: h_magnetic returns -H_B", "enc", "return self._HB.copy()", "return -self._HB.copy()"),
]

TESTS = ["tests/acceptance/m7/test_lsh_model.py", "tests/acceptance/m7/test_lsh_codec.py",
         "tests/acceptance/m7/test_lsh_circuits.py::test_M7_E1_electric_step", "tests/acceptance/m7/test_lsh_circuits.py::test_M7_G1_evaluator_sees_abelian_gauss_law_violations",
         "tests/acceptance/m7/test_lsh_metrics.py::test_M7_T1_t_table_and_synth_verify[UE]"]
UNIT = ["tests/unit/test_lsh_codec_unit.py", "tests/unit/test_lsh_circuits_unit.py", "tests/unit/test_lsh_operators_unit.py"]
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")


def run(tests):
    cmd = ["taskset", "-c", "14-17", "python", "-m", "pytest", "-n", "4", "-q", "-p", "no:cacheprovider", "--tb=no", "-rfE", *tests]
    r = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    txt = r.stdout + r.stderr
    failed = re.findall(r"^(?:FAILED|ERROR) (\S+)", txt, flags=re.M)
    return failed, (txt.strip().splitlines() or [""])[-1]


res = []
fa, la = run(TESTS); fu, lu = run(UNIT)
print("BASELINE:", fa, la, "|", fu, lu, flush=True)
res.append({"mutation": "baseline", "acc_failed": fa, "unit_failed": fu, "acc": la, "unit": lu})
for name, key, old, new in MUTS:
    if orig[key].count(old) != 1:
        print("SKIP (pattern count %d): %s" % (orig[key].count(old), name), flush=True)
        res.append({"mutation": name, "error": "pattern count %d" % orig[key].count(old)}); continue
    F[key].write_text(orig[key].replace(old, new))
    try:
        fa, la = run(TESTS); fu, lu = run(UNIT)
    finally:
        F[key].write_text(orig[key])
    short = lambda L: sorted({x.split("::")[-1].split("[")[0] + ("[" + x.split("[")[1] if "[" in x else "") for x in L})
    caught = bool(fa or fu)
    print(("CAUGHT " if caught else "MISSED ") + name, "| acc:", short(fa), "| unit:", len(fu), flush=True)
    res.append({"mutation": name, "file": key, "caught": caught, "acc_failed": short(fa), "n_unit_failed": len(fu), "unit_first": short(fu)[:5], "acc": la, "unit": lu})
json.dump(res, open(outp, "w"), indent=1)
print("caught", sum(1 for r in res if r.get("caught")), "of", sum(1 for r in res if "caught" in r))
