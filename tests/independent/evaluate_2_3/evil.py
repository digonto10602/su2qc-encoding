import sys, pathlib, numpy as np
sys.path.insert(0, "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv")
from cases import prog, UE_CORE, SP
M = str(SP/"COUNT.npy")
(SP/"programs"/"evil_gate.py").write_text(prog(f'''import numpy as np
from qiskit.circuit import Gate
class Evil(Gate):
    def __init__(self):
        super().__init__("evil", 1, [])
        try:
            n = int(np.load("{M}")[0])
        except Exception:
            n = 0
        np.save("{M}", np.array([n + 1]))
    def _define(self):
        from qiskit import QuantumCircuit
        self.definition = QuantumCircuit(1)
def build(spec):
{UE_CORE}    qc = b.circuit()
    qc.append(Evil(), [0])
    b.circuit = lambda: qc
    return b
'''))
import os
if os.path.exists(M): os.remove(M)
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec
r = E.evaluate_program(SP/"programs"/"evil_gate.py", default_spec("twelve","UE"), "trial")
print(r.valid, r.reason, "constructions of Evil (expect 1 = worker only):", int(np.load(M)[0]) if os.path.exists(M) else None)
print("sys.modules proposer:", [k for k in sys.modules if k.startswith("su2plaq_program")])
