import json, numpy as np, sys
d = json.load(open(sys.argv[1])); E = d["entries"]; pairs = d["pairs"]
def arr(e): return np.array([m["T"] for m in E[e]])
r3, r2, f2r3, f2r2 = arr("r03-F1-003"), arr("r02-F1-002"), arr("r03-F2-003"), arr("r02-F2-002")
print("CX r03/r02:", {m["cx"] for m in E["r03-F1-003"]}, {m["cx"] for m in E["r02-F1-002"]})
print("nominal (first pair): T r03, r02 =", r3[0], r2[0], " (keys 1062, 1086)")
def stat(x, name):
    print(f"{name}: n={len(x)} mean={x.mean():.2f} std={x.std(ddof=1):.2f} sem={x.std(ddof=1)/np.sqrt(len(x)):.2f} min={x.min()} max={x.max()} median={np.median(x)}  frac<0={np.mean(x<0):.2f} frac==0={np.mean(x==0):.2f} frac>0={np.mean(x>0):.2f}")
D = r3 - r2
stat(D[3:], "T(r03)-T(r02), 20 random pairs")
stat(D, "T(r03)-T(r02), all 23 pairs")
stat(D[:3], "T(r03)-T(r02), 3 official pairs")
for i, (a, b) in enumerate(pairs[:3]): print("   official", (a, b), r3[i], r2[i], D[i])
print("mean T r03 (20 random):", r3[3:].mean(), " mean T r02:", r2[3:].mean(), " F2-r02 (32CX) mean:", f2r2[3:].mean(), "F2-r03 mean", f2r3[3:].mean())
print("F1-r03 == F2-r03 T at every pair:", bool(np.all(r3 == f2r3)))
print("mean T(r03 F2, 31 CX) - T(r02 F2, 32 CX) (20 random):", (f2r3 - f2r2)[3:].mean(), " nominal:", f2r3[0] - f2r2[0])
# per-rotation, by class
k = E["r03-F1-003"][0]["kinds"]; k2 = E["r02-F1-002"][0]["kinds"]; print("n_rot", len(k), len(k2), "kinds r03", "".join("p" if x=="p" else "r" for x in k), "r02", "".join("p" if x=="p" else "r" for x in k2))
tf3 = np.array([m["T_fixed"] for m in E["r03-F1-003"]]); tf2 = np.array([m["T_fixed"] for m in E["r02-F1-002"]])
print("T_fixed r03:", set(tf3), " r02:", set(tf2))
R3 = np.array([sum(m["T_rot"]) for m in E["r03-F1-003"]]); R2 = np.array([sum(m["T_rot"]) for m in E["r02-F1-002"]])
print("synth T (rot) r03-r02, 20 random: mean %.2f; fixed T diff = %d" % ((R3-R2)[3:].mean(), (tf3-tf2)[0]))
U3 = np.array([sum(t for t,kd in zip(m["T_rot"], m["kinds"]) if kd=="p") for m in E["r03-F1-003"]]); U2 = np.array([sum(t for t,kd in zip(m["T_rot"], m["kinds"]) if kd=="p") for m in E["r02-F1-002"]])
W3 = R3-U3; W2 = R2-U2
print("U_E (4 p gates) synth T: r03 mean %.2f r02 mean %.2f (20 random); nominal r03 %d r02 %d" % (U3[3:].mean(), U2[3:].mean(), U3[0], U2[0]))
print("walk (13 rz) synth T: r03 mean %.2f r02 mean %.2f (20 random); nominal r03 %d r02 %d" % (W3[3:].mean(), W2[3:].mean(), W3[0], W2[0]))
print("U_E net (synth + 4 explicit T): r03-r02 mean %.2f; walk net: %.2f" % ((U3-U2)[3:].mean()+4, (W3-W2)[3:].mean()+ (tf3-tf2)[0]-4))
# split by the alpha-only and beta-only part
print("expected T-per-rotation scale ~", R2[3:].mean()/17)
# Probability-of-luck: how often does a random +-pi/4 shift choice save >= 24 at nominal-like?
print("number of random pairs (of 20) with D <= -24:", int(np.sum(D[3:] <= -24)), " best:", int(D[3:].min()))
