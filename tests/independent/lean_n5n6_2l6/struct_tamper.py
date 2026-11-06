"""Independent structure-certificate tamper hunt (single-field tampers must be REJECTED by `su2plaq_cert structure`).
usage: python struct_tamper.py <orig-structure-cert.json> <outdir> [workers]"""
import copy, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
BIN = "/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert"
orig = json.load(open(sys.argv[1])); outdir = sys.argv[2]; W = int(sys.argv[3]) if len(sys.argv) > 3 else 3
os.makedirs(outdir, exist_ok=True)
T = []  # (name, expect, mutated)
def add(name, fn, expect="REJECT"):
    d = copy.deepcopy(orig); fn(d); T.append((name, expect, d))
def S(d, f): f(d)
# ---- controls
add("ctl_unchanged", lambda d: None, "ACCEPT")
def shuf(d):
    import random; r = random.Random(5); idx = list(range(len(d["states"]))); r.shuffle(idx)
    d["states"] = [d["states"][i] for i in idx]   # k fields kept: placement by k, so same cert
add("ctl_states_list_shuffled_k_kept", shuf, "ACCEPT")
# ---- K_inner / bright / dark
def kk(d, i, j, v, sym=True):
    d["k_inner"][i][j] = v
    if sym: d["k_inner"][j][i] = v
add("K1_bright_coupling_2_to_1_everywhere", lambda d: (kk(d, 0, 31, "1"), d["bright_pairs"][0].__setitem__("coupling", "1")))
add("K2_bright_coupling_2_to_1_kinner_only", lambda d: kk(d, 0, 31, "1"))
add("K3_bright_coupling_half_to_1_everywhere", lambda d: (kk(d, 6, 16, "1"), d["bright_pairs"][5].__setitem__("coupling", "1")))
add("K4_kinner_asymmetric_one_entry", lambda d: kk(d, 0, 31, "3", sym=False))
add("K5_sign_flip_bright_entry_both", lambda d: (kk(d, 5, 17, "-1"), d["bright_pairs"][4].__setitem__("coupling", "-1")))
def dark_to_bright(d):  # make dark rows 4 and 8 a bright pair (consistent claim)
    kk(d, 4, 8, "1"); d["bright_pairs"].append({"pair": [4, 8], "coupling": "1"}); d["dark_rows"].remove(4); d["dark_rows"].remove(8)
add("K6_dark_rows_4_8_made_bright_consistently", dark_to_bright)
def dark_to_bright_u(d):  # K entry only
    kk(d, 4, 8, "1")
add("K7_dark_rows_4_8_made_bright_kinner_only", dark_to_bright_u)
add("K8_dark_row_removed_from_list", lambda d: d["dark_rows"].remove(4))
add("K9_bright_row_listed_dark", lambda d: d["dark_rows"].append(0))
add("K10_bright_pair_dropped", lambda d: d["bright_pairs"].pop())
add("K11_bright_pair_duplicated", lambda d: d["bright_pairs"].append(copy.deepcopy(d["bright_pairs"][0])))
add("K12_bright_pair_indices_changed", lambda d: d["bright_pairs"][2].__setitem__("pair", [2, 24]))
add("K13_dark_row_duplicated", lambda d: d["dark_rows"].append(d["dark_rows"][0]))
add("K14_gauge_flip_one_state", lambda d: d["gauge"].__setitem__(1, -d["gauge"][1]))
add("K15_gauge_zero", lambda d: d["gauge"].__setitem__(7, 0))
add("K16_gauge_flip_all_ctl", lambda d: d.__setitem__("gauge", [-g for g in d["gauge"]]), "ACCEPT")
# ---- spectrum
add("S1_mult_-2_16_to_17", lambda d: d["spectrum"][0].__setitem__(1, 17))
add("S2_mult_0_177_to_176_and_half_16_to_17", lambda d: (d["spectrum"][3].__setitem__(1, 176), d["spectrum"][4].__setitem__(1, 17)))
add("S3_mult_swap_-1_and_1_ctl", lambda d: None, "ACCEPT")
add("S4_two_mults_swapped_96_16", lambda d: (d["spectrum"][1].__setitem__(1, 16), d["spectrum"][2].__setitem__(1, 96)))
add("S5_eigenvalue_label_changed", lambda d: d["spectrum"][2].__setitem__(0, -0.75))
add("S6_entry_dropped", lambda d: d["spectrum"].pop())
add("S7_mult_+2_16_to_15", lambda d: d["spectrum"][6].__setitem__(1, 15))
# ---- symmetries
sidx = {s["name"]: i for i, s in enumerate(orig["symmetries"])}
add("Y1_identity_sign_flip_one", lambda d: d["symmetries"][sidx["identity"]]["signs"].__setitem__(10, -1))
add("Y2_C4_sign_flip_one", lambda d: d["symmetries"][sidx["C4"]]["signs"].__setitem__(100, -d["symmetries"][sidx["C4"]]["signs"][100]))
add("Y3_C4_perm_two_entries_swapped", lambda d: (lambda p: p.__setitem__(3, p[3]) or (p.__setitem__(3, p[9]) , p.__setitem__(9, orig["symmetries"][sidx["C4"]]["perm"][3])))(d["symmetries"][sidx["C4"]]["perm"]))
add("Y4_reflect_x_perm_duplicate_entry", lambda d: d["symmetries"][sidx["reflect_x"]]["perm"].__setitem__(5, d["symmetries"][sidx["reflect_x"]]["perm"][6]))
add("Y5_reflect_x_sign_zero", lambda d: d["symmetries"][sidx["reflect_x"]]["signs"].__setitem__(5, 0))
add("Y6_reflect_diag_perm_truncated", lambda d: d["symmetries"][sidx["reflect_diag"]]["perm"].pop())
add("Y7_cc_replaced_by_non_symmetry_swap", lambda d: (lambda p: (p.__setitem__(0, 1), p.__setitem__(1, 0)))(d["symmetries"][sidx["cc"]]["perm"]))
add("Y8_C4^2_perm_out_of_range", lambda d: d["symmetries"][sidx["C4^2"]]["perm"].__setitem__(0, 433))
add("Y9_identity_sign_flip_on_bright_state", lambda d: d["symmetries"][sidx["identity"]]["signs"].__setitem__(0, -1))
# ---- states / Gauss / labels
def first_multi(d):
    for k, st in enumerate(d["states"]):
        if len(st["terms"]) > 1: return k
k_multi = next(k for k, st in enumerate(orig["states"]) if len(st["terms"]) > 1)
add("G1_one_term_sign_flipped_in_multi_term_state", lambda d: d["states"][k_multi]["terms"][0].__setitem__("c", [("-" + x if x != "0" and not x.startswith("-") else x[1:] if x.startswith("-") else x) for x in d["states"][k_multi]["terms"][0]["c"]]))
add("G2_one_term_code_digit_changed", lambda d: d["states"][k_multi]["terms"][0].__setitem__("code", d["states"][k_multi]["terms"][0]["code"] + 5 ** 11))
add("G3_one_term_deleted", lambda d: d["states"][k_multi]["terms"].pop())
add("G4_state_replaced_by_copy_of_other", lambda d: d["states"][5].__setitem__("terms", copy.deepcopy(d["states"][6]["terms"])))
add("G5_state_removed", lambda d: (d["states"].pop(), d["labels"].pop(), d["gauge"].pop()))
add("G6_state_coefficient_scaled", lambda d: d["states"][k_multi]["terms"][0]["c"].__setitem__(0, "1/3"))
def gauss_violate(d):  # swap one physical state's contents with a computational basis state of a non-singlet corner pattern (unit norm)
    d["states"][1]["terms"] = [{"code": 1, "c": ["1", "0", "0", "0", "0", "0", "0", "0"]}]
add("G7_state1_replaced_by_non_gauss_basis_vector", gauss_violate)
def gauss_violate2(d):  # state 1 with a different relative sign between two terms of another state is G1; here: transposed m index on single-term state
    t = d["states"][1]["terms"][0]; t["code"] = t["code"] // 5 * 5 + (t["code"] % 5 + 1) % 5 if t["code"] % 5 != 0 else t["code"] + 1
add("G8_state1_digit0_m_shifted", gauss_violate2)
add("L1_label_J2_corner0_wrong", lambda d: d["labels"][k_multi]["J2"].__setitem__(0, 2 if d["labels"][k_multi]["J2"][0] != 2 else 0))
add("L2_label_j2_link_wrong", lambda d: d["labels"][3]["j2"].__setitem__(0, 1 - d["labels"][3]["j2"][0]))
add("L3_label_J2_corner3_wrong_other_state", lambda d: d["labels"][200]["J2"].__setitem__(3, (d["labels"][200]["J2"][3] + 2) % 4))
add("L4_inner_label_list_entry_changed", lambda d: d["inner_labels"][5]["J2"].__setitem__(1, (d["inner_labels"][5]["J2"][1] + 2) % 4))
add("L5_inner_label_removed", lambda d: (d["inner_labels"].pop(), d["k_inner"].pop(), [r.pop() for r in d["k_inner"]]))
# ---- outer support
add("O1_3153_to_3152", lambda d: d["outer_support"].__setitem__("n_keys", 3152))
add("O2_max_17_to_16", lambda d: d["outer_support"].__setitem__("max_states", 16))
add("O3_max_17_to_18", lambda d: d["outer_support"].__setitem__("max_states", 18))
add("O4_max_17_to_9_dimS_histogram_confusion", lambda d: d["outer_support"].__setitem__("max_states", 9))
# ---- inner625
add("I1_edges_128_to_127", lambda d: d["inner625"].__setitem__("n_edges", 127))
add("I2_edge_modulus_half_to_one", lambda d: d["inner625"].__setitem__("edge_moduli", ["1"]))
add("I3_edge_moduli_extra_value", lambda d: d["inner625"].__setitem__("edge_moduli", ["1/2", "1/4"]))
add("I4_component_17_to_16", lambda d: d["inner625"]["component_sizes"][-1].__setitem__(0, 16))
add("I5_component_count_464_to_465", lambda d: d["inner625"]["component_sizes"][0].__setitem__(1, 465))
add("I6_spectrum_543_to_542_plus_24_to_25", lambda d: (d["inner625"]["spectrum"][3].__setitem__(1, 542), d["inner625"]["spectrum"][2].__setitem__(1, 25)))
add("I7_spectrum_plus2_1_to_2", lambda d: d["inner625"]["spectrum"][6].__setitem__(1, 2))
add("I8_u_paulo_entry_changed", lambda d: d["u_paulo"][0][0][0][1].__setitem__(2, "1/3"))
add("I9_v_paulo_sign_flip", lambda d: d["v_paulo"][2].__setitem__(3, 1))
add("I10_v_paulo_not_perm", lambda d: d["v_paulo"][0].__setitem__(1, 1))
# ---- corner dims
add("C1_corner_dim_changed", lambda d: d["corner_kernel_dims"][0].__setitem__("dim", 2))
add("C2_corner_dim_zero_to_one", lambda d: d["corner_kernel_dims"][1].__setitem__("dim", 1))
add("C3_corner_dim_dropped", lambda d: d["corner_kernel_dims"].pop())
add("C4_corner_role_flipped", lambda d: d["corners"][0][0].__setitem__(1, 1))
add("C5_corner_link_changed", lambda d: d["corners"][1][2].__setitem__(0, 8))
# ---- algebra / link operators
add("A1_u_link_entry_changed", lambda d: d["u_link"][0][1][0][0].__setitem__(1, "1/7"))
add("A2_gens_L_entry_changed", lambda d: d["gens"]["L"][2][0][0].__setitem__(0, "1"))
add("A3_gens_R_entry_changed", lambda d: d["gens"]["R"][0][1][2].__setitem__(1, "1/2"))
add("A4_spin_half_entry_changed", lambda d: d["spin_half"][1][0][1].__setitem__(1, "1/2"))
add("A5_schema_wrong", lambda d: d.__setitem__("schema", "su2plaq-structure-2"))
add("A6_missing_field", lambda d: d.pop("inner625"))
# N6
add("N6_zero_denominator_in_state", lambda d: d["states"][k_multi]["terms"][0]["c"].__setitem__(2, "1/0"))
add("N6_zero_denominator_in_u_link", lambda d: d["u_link"][0][0][0][0].__setitem__(0, "3/0"))
add("N6_zero_denominator_in_k_inner", lambda d: d["k_inner"][0].__setitem__(31, "2/0"))
add("N6_zero_denominator_in_spectrum", lambda d: d["spectrum"][1].__setitem__(0, "1/0"))
print(len(T), "cases", flush=True)
def run(item):
    name, expect, d = item
    p = os.path.join(outdir, name + ".json"); json.dump(d, open(p, "w"), separators=(",", ":"))
    t0 = time.time()
    r = subprocess.run([BIN, "structure", p], capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or [""])[0]
    res = "ACCEPT" if line == "ACCEPT" else ("REJECT" if line.startswith("REJECT") else "OTHER")
    ok = res == expect
    os.remove(p)
    out = dict(name=name, expect=expect, got=res, ok=ok, reason=line[:170], rc=r.returncode, err=r.stderr[-150:], s=round(time.time() - t0, 1))
    print(("OK  " if ok else "BAD ") + name, "|", line[:140], f"| {out['s']}s", flush=True)
    return out
with ThreadPoolExecutor(W) as ex: res = list(ex.map(run, T))
json.dump(res, open(os.path.join(outdir, "summary.json"), "w"), indent=1)
print("TOTAL", len(res), "BAD", sum(1 for r in res if not r["ok"]), "rejected-tampers", sum(1 for r in res if r["expect"] == "REJECT" and r["got"] == "REJECT"))
