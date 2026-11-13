"""Tester 408 (d): su2plaq.lsh.loop.improves / stop_key vs an independent re-statement of prompts/401 sec 1.6."""
import sys, json, itertools, random, subprocess
sys.path.insert(0, "src")
from su2plaq.lsh import loop as LP

def ref(new, old):                       # my own transcription of the plan text
    if new is None: return False
    if old is None: return True
    k = lambda r: (r["cx"], r["t_sum"], r["rho"], r["qubits"])
    if new["cx"] == old["cx"] and new["n_rot"] == old["n_rot"] and new["t_fixed"] == old["t_fixed"] \
       and abs(new["t_sum"] - old["t_sum"]) <= 20 * new["n_rot"]:
        return (new["rho"], new["qubits"]) < (old["rho"], old["qubits"])
    return k(new) < k(old)

base = dict(cx=71, t_sum=1118, rho=0, qubits=25, n_rot=17, t_fixed=48, depth=2276, id="x")
mk = lambda **kw: {**base, **kw}
cases = {}
N = 20 * 17
cases["same record -> False"] = (mk(), base, False)
cases["first headline (old None) -> True"] = (mk(), None, True)
cases["no new headline -> False"] = (None, base, False)
cases["both None -> False"] = (None, None, False)
cases["dT=-340 (=20 Nrot) same structure, equal rho,q -> tie -> False"] = (mk(t_sum=1118 - N), base, False)
cases["dT=-341 (> band) -> improves True"] = (mk(t_sum=1118 - N - 1), base, True)
cases["dT=+340 tie, equal -> False"] = (mk(t_sum=1118 + N), base, False)
cases["dT=+341 beyond band, worse -> False"] = (mk(t_sum=1118 + N + 1), base, False)
cases["dT=+100 but rho 1->0 improves (tie decided by rho)"] = (mk(t_sum=1218, rho=0), mk(rho=1), True)
cases["dT=-100 but rho 0->1 (tie, rho worse) -> False"] = (mk(t_sum=1018, rho=1), base, False)
cases["dT=-100, rho equal, qubits 25->24 -> True"] = (mk(t_sum=1018, qubits=24), base, True)
cases["dT=-100, rho equal, qubits 25->26 -> False"] = (mk(t_sum=1018, qubits=26), base, False)
cases["depth change only (ignored) -> False"] = (mk(depth=1), base, False)
cases["CX 71->70 with huge T rise -> True"] = (mk(cx=70, t_sum=5000), base, True)
cases["CX 71->72 with huge T drop -> False"] = (mk(cx=72, t_sum=10), base, False)
cases["n_rot changed (no band), dT=-5 -> lexi True"] = (mk(n_rot=16, t_sum=1113), base, True)
cases["n_rot changed (no band), dT=+5 -> lexi False"] = (mk(n_rot=16, t_sum=1123), base, False)
cases["t_fixed changed (no band), dT=-5 -> True"] = (mk(t_fixed=40, t_sum=1113), base, True)
cases["rho worse and T better beyond band -> True (lexi on T first)"] = (mk(t_sum=100, rho=1), base, True)
res = {}
for name, (n, o, want) in cases.items():
    got = LP.improves(n, o); res[name] = {"want": want, "got": got, "ref": ref(n, o), "ok": got == want == ref(n, o)}
# stop_key
res["stop_key_is_(cx,t_sum,rho,qubits)"] = {"got": LP.stop_key(base), "ok": LP.stop_key(base) == (71, 1118, 0, 25)}
res["stop_key_ignores_depth"] = {"ok": LP.stop_key(mk(depth=1)) == LP.stop_key(base)}
# constants
res["constants"] = {"got": [LP.STOP_MAX_ROUNDS, LP.STOP_NO_GAIN_ROUNDS, LP.STOP_MAX_SESSIONS, LP.T_NOISE_PER_ROTATION, LP.N_ANGLE_PAIRS],
                    "ok": [LP.STOP_MAX_ROUNDS, LP.STOP_NO_GAIN_ROUNDS, LP.STOP_MAX_SESSIONS, LP.T_NOISE_PER_ROTATION * LP.N_ANGLE_PAIRS] == [8, 3, 20, 20]}
# random fuzz vs reference
random.seed(408); bad = 0; n = 20000
for _ in range(n):
    r = lambda: dict(cx=random.choice([70, 71, 72]), t_sum=random.choice([1000, 1118, 1300, 1400, 1459, 1460, 1461, 1500]), rho=random.choice([0, 1]),
                     qubits=random.choice([24, 25, 26]), n_rot=random.choice([16, 17]), t_fixed=random.choice([48, 56]))
    a, b = r(), r()
    if LP.improves(a, b) != ref(a, b): bad += 1
res["fuzz_20000_vs_reference_mismatches"] = {"got": bad, "ok": bad == 0}
# a (documented) feature: tie rule not transitive / antisymmetric check
both = [(a, b) for a, b in itertools.product([mk(), mk(t_sum=1200), mk(t_sum=1300, qubits=24)], repeat=2)]
res["antisymmetry_both_improve_count"] = sum(LP.improves(a, b) and LP.improves(b, a) for a, b in both)
res["all_ok"] = all(v.get("ok", True) for v in res.values() if isinstance(v, dict))
res["commit"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
json.dump(res, open("results/lsh_tester/tester-408-stoprule.json", "w"), indent=1, default=str)
for k, v in res.items(): print(k, v if not isinstance(v, dict) else v.get("ok", v))
