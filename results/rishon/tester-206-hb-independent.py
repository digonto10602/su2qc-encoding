"""tester-206: independent checks of the HB certificate (own 4-mode JW, own W contraction, tamper variants)."""
import itertools, json, pathlib, sys, time, copy
import numpy as np
from su2plaq.rishon import lean_export as LE

out = pathlib.Path("/home/digonto/Projects/su2qc-rishon/results/rishon")
scr = pathlib.Path("/home/digonto/Projects/su2qc-rishon/scratch/t206"); scr.mkdir(parents=True, exist_ok=True)
cert_path = LE.export_hb_certificate(scr / "cert.json")
cert = json.loads(cert_path.read_text())

# --- (a) own JW: c_k = Z^{k} sigma^-_k, mode k = bit k, occupied=1
def occ(s, k): return (s >> k) & 1
def sign(s, k): return -1 if sum(occ(s, m) for m in range(k)) % 2 else 1
def c(k):   # annihilation 16x16
    M = np.zeros((16, 16)); 
    for s in range(16):
        if occ(s, k): M[s - (1 << k), s] = sign(s, k)
    return M
cs = [c(k) for k in range(4)]; cds = [m.T for m in cs]
# CAR check
for k, l in itertools.product(range(4), repeat=2):
    assert np.allclose(cs[k] @ cds[l] + cds[l] @ cs[k], np.eye(16) * (k == l))
sector = [s for s in range(16) if bin(s).count("1") == 2]
assert sector == [3, 5, 6, 9, 10, 12]
def Uij(i, j): return cs[i] @ cds[2 + j]
def restrict(M): return M[np.ix_(sector, sector)]
mine = {}
for i, j in itertools.product(range(2), repeat=2):
    mine[f"U{i}{j}"] = restrict(Uij(i, j)); mine[f"Ud{i}{j}"] = restrict(Uij(i, j)).T   # Ud_ij = (U_ij)^dagger
# sector closure
for i, j in itertools.product(range(2), repeat=2):
    M = Uij(i, j); rest = np.setdiff1d(np.arange(16), sector)
    assert np.abs(M[np.ix_(rest, sector)]).max() == 0
dev = 0.0
for op in cert["link_ops"]:
    M = np.zeros((6, 6))
    for r, cc, v in op["entries"]: M[r, cc] = v
    dev = max(dev, np.abs(M - mine[op["name"]]).max())
print("(a) link ops vs own JW: max deviation", dev)

# --- (b) own W from the certificate link ops, and the decomposition with cert pairs
Mx = {}
for op in cert["link_ops"]:
    M = np.zeros((6, 6))
    for r, cc, v in op["entries"]: M[r, cc] = v
    Mx[op["name"]] = M
def kron4(ms):
    out_ = np.ones((1, 1))
    for m in ms: out_ = np.kron(m, out_)
    return out_
W = sum(kron4([Mx[f"U{a}{b}"], Mx[f"U{b}{cc}"], Mx[f"Ud{d}{cc}"], Mx[f"Ud{a}{d}"]]) for a, b, cc, d in itertools.product(range(2), repeat=4))
from su2plaq.rishon import operators as O
print("(b) own W vs production W:", np.abs(W - O.plaquette_W_inner().real).max())
s2 = np.sqrt(2.0)
R = np.zeros((1296, 1296))
for p in cert["pairs"]:
    k = p["kappa"][0] + p["kappa"][1] * s2
    u = np.zeros(1296); v = np.zeros(1296)
    for i, a, b in p["u"]: u[i] = a + b * s2
    for i, a, b in p["v"]: v[i] = a + b * s2
    R += k * (np.outer(u, v) + np.outer(v, u))
print("(b) 16(W+W^T) - sum kappa(...) max:", np.abs(16 * (W + W.T) - R).max())
vecs = []
for p in cert["pairs"]:
    for sd in ("u", "v"):
        x = np.zeros(1296)
        for i, a, b in p[sd]: x[i] = a + b * s2
        vecs.append(x)
V = np.array(vecs); G = V @ V.T
print("(b) Gram dev from 16 I:", np.abs(G - 16 * np.eye(162)).max(), " support:", int((np.abs(V).sum(0) > 0).sum()), "dark:", 1296 - int((np.abs(V).sum(0) > 0).sum()))
w = np.linalg.eigvalsh(-(W + W.T)); 
vals = np.round(w, 9); u_, cnt = np.unique(vals, return_counts=True); print("(b) spectrum of -(W+W^T):", dict(zip(u_.tolist(), cnt.tolist())))
# det sign check on sector: 2*U00*U11 on A
D = 2 * mine["U00"] @ mine["U11"]; print("(a) det U on sector = 2|B><A| ?", np.abs(D - 2 * np.outer(np.eye(6)[5], np.eye(6)[0])).max())

# --- (c) tamper variants
def swapk(c_):
    i = next(i for i, p in enumerate(c_["pairs"]) if p["kappa"] == [1, 0]); j = next(i for i, p in enumerate(c_["pairs"]) if p["kappa"] == [2, 0])
    c_["pairs"][i]["kappa"], c_["pairs"][j]["kappa"] = [2, 0], [1, 0]
def k2to1(c_):
    i = next(i for i, p in enumerate(c_["pairs"]) if p["kappa"] == [2, 0]); c_["pairs"][i]["kappa"] = [1, 0]
def k4s2(c_):
    i = next(i for i, p in enumerate(c_["pairs"]) if p["kappa"] == [0, 4]); c_["pairs"][i]["kappa"] = [5, 0]
def vecentry(c_): c_["pairs"][3]["u"][0][1] += 1
def vecidx(c_): c_["pairs"][3]["u"][0][0] = (c_["pairs"][3]["u"][0][0] + 1) % 1296
def droppair(c_): c_["pairs"].pop(10)
def droplast(c_): c_["pairs"].pop()
def addpair_dup(c_): c_["pairs"].append(copy.deepcopy(c_["pairs"][0]))
def outofrange(c_): c_["pairs"][0]["u"][0][0] = 1296
def ncodes(c_): c_["n_codes"] = 1295
def linksign(c_): c_["link_ops"][0]["entries"][0][2] *= -1
def udflip(c_): c_["link_ops"][5]["entries"][0][2] *= -1
def dropentry(c_): c_["link_ops"][2]["entries"].pop()
def swapuv(c_): c_["pairs"][5]["u"], c_["pairs"][5]["v"] = c_["pairs"][5]["v"], c_["pairs"][5]["u"]   # should still be VALID (H symmetric)
def negboth(c_): c_["pairs"][5]["u"] = [[i, -a, -b] for i, a, b in c_["pairs"][5]["u"]]               # sign of u only: should be rejected (kappa sign)
def negkappa(c_): c_["pairs"][5]["kappa"] = [-a for a in c_["pairs"][5]["kappa"]]
def zeroentry_dark(c_): c_["pairs"][0]["u"].append([1295, 0, 0])   # zero-valued extra entry: should still be accepted (semantically identical)
variants = dict(swap_kappa_1_2=swapk, kappa_2_to_1=k2to1, kappa_4sqrt2_to_5=k4s2, vector_entry=vecentry, vector_index_shift=vecidx,
                drop_pair_mid=droppair, drop_pair_last=droplast, duplicate_pair=addpair_dup, index_out_of_range=outofrange, n_codes_1295=ncodes,
                link_sign_flip=linksign, Ud_sign_flip=udflip, link_entry_dropped=dropentry,
                swap_u_v_valid=swapuv, negate_u_only=negboth, negate_kappa=negkappa, zero_entry_valid=zeroentry_dark)
res = {}
for name, f in variants.items():
    c_ = copy.deepcopy(cert)
    f(c_)
    cp = scr / f"{name}.json"; cp.write_text(json.dumps(c_))
    if name == "n_codes_1295":
        pass
    lf = LE.write_hb_lean(cp, scr / f"{name}.lean")
    t0 = time.time()
    try:
        r = LE.check_hb(lf, timeout=600)
        res[name] = {"status": r["status"], "seconds": round(time.time() - t0, 2), "py_mirror": None}
    except Exception as e:
        res[name] = {"status": "EXC " + repr(e)[:200]}
    try:
        res[name]["py_mirror"] = LE.check_hb_python(c_)
    except Exception as e:
        res[name]["py_mirror"] = "EXC " + type(e).__name__
    print(name, res[name]["status"], res[name]["seconds"], flush=True)
json.dump({"commit": "b4c1917+uncommitted", "variants": res}, open(out / "tester-206-hb-tamper.json", "w"), indent=1, default=str)
