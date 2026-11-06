"""Independent cross-check: Lean `slotBits`/`flagChain`/`walkPhase` (printed by #eval in a scratch file) vs Python
classical_slots and the Boolean flag definitions, for all 256 data codes; walkPhase = 2*couplingTable on 47 codes."""
import sys, ast
sys.path.insert(0, "src")
from su2plaq.spinnet.walk import GENERAL7, FRAME, classical_slots
steps, _ = GENERAL7
bad = n = nW = badW = 0
for line in open(sys.argv[1]):
    t = line.split(" ", 1)
    if t[0] == "W":
        _, c, ph, ct = line.split(); nW += 1; badW += int(ph) != 2 * int(ct); continue
    y = int(t[0]); rest = t[1]
    lst = ast.literal_eval(rest[: rest.index("]") + 1]); F, G1, G2 = rest[rest.index("]") + 1:].split()
    n += 1
    if lst != classical_slots(steps, y, FRAME): bad += 1
    m = (((y ^ ((y & 1) << 1)) if False else 0))
    if (F == "true") != ((y >> 4) == 0): bad += 1
print("data codes", n, "mismatches (slots / F flag) vs Python:", bad, "| walkPhase rows", nW, "!= 2*coupling:", badW)
