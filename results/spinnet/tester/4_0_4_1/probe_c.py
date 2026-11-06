import re, json, itertools, pathlib, numpy as np
from su2plaq.spinnet import loop as L
from su2plaq.compress.spec import get_encoding
L.install()
enc = get_encoding("spinnet")
facts = {f["name"]: f for f in L.structure_facts()["facts"]}
root = pathlib.Path(".")
# independent recount: do not use loop's helpers / walk.coupling_table; use enc.labels and raw H_B
labels = enc.labels
print("n labels", len(labels))
codes = [int(c) for c in enc._codes]
data = sorted({c & 0xFF for c in codes})
bright = [c for c in data if c >> 4 == 0]
dark = [c for c in data if c >> 4 != 0]
print("inner", len(data), "bright", len(bright), "dark", len(dark), "pairs", len({min(c, c ^ 15) for c in bright}), "states", len(set(codes)))
# multiplicities: eigenvalues of H_B (dense, independent) on 433 states
HB = np.asarray(enc.h_magnetic()); HB = HB.toarray() if hasattr(HB, "toarray") else HB
assert np.allclose(HB, HB.conj().T)
ev = np.linalg.eigvalsh(HB)
vals, counts = np.unique(np.round(ev * 2) / 2, return_counts=True)
print("spectrum", list(zip(vals.tolist(), counts.tolist())), "max |ev*2-round|", np.abs(ev*2-np.round(ev*2)).max())
# bright-pair classes by independent count of states per pair class
by_data = {}
for c in codes: by_data.setdefault(c & 0xFF, 0); by_data[c & 0xFF] += 1
print("states per data code (bright), and pair sums:")
pairsum = {}
for c in bright:
    k = min(c, c ^ 15); pairsum[k] = pairsum.get(k, 0) + by_data[c]
print(pairsum)
# magnitude of K per pair: from H_B matrix elements between the two codes in outer block (one state each)
inv = {}
for i, c in enumerate(codes): inv[c] = i
kk = {}
for y in bright:
    if y < y ^ 15:
        # H_B element between full state codes y+256*o and (y^15)+256*o for each o present
        els = set()
        for c in codes:
            if c & 0xFF == y and (c ^ 15) in inv:
                els.add(round(abs(HB[inv[c], inv[c ^ 15]]) , 9))
        kk[y] = els
print("pair K magnitudes (elements |H_B| of paired states):", kk)
# Lean source recount of values by regexp
def num(f, t):
    s = (root / "lean/Su2Plaq/SpinNet" / f).read_text()
    m = re.search(rf"theorem {t}\b.*?=\s*(\d+)\s*:=", s, re.S); return int(m.group(1))
for n in ["card_inner_labels","card_bright_labels","card_dark_labels","card_bright_pairs","card_states_spinnet","mult_two","mult_one","mult_half"]:
    print(n, "loop", facts[n]["value"], "lean", num("Counts.lean", n))
print(json.dumps(facts["couplings_2k"]["value"]), json.dumps(facts["spectrum_multiplicities"]["value"]))
print("eig_mult in Lean:", re.search(r"theorem eig_mult.*?(\[[0-9, ]+\])", (root/"lean/Su2Plaq/SpinNet/Spectrum.lean").read_text(), re.S).group(1))
