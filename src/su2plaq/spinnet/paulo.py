"""Paulo's 15-qubit spin-network circuit file refs/paulo/spin_network_plaquette3.gates.txt (prompts/100 §2, step 3.2).

The file is exp(+i alpha_P Re Tr U_P) at alpha_P = 0.1 ("exact circuit, ancillas start/end in |0>, global phase 0").
File qubits: q0-3 = links b, r, t, l; q12-15 = corners c0..c3; q16-22 = 7 ancillas; q4-11 are never touched.
Frame (circuits/spinnet): d[0..3] links, d[4..7] corners, o[0..7] outer (optional), a[0..6] ancillas."""
from __future__ import annotations

import hashlib
import pathlib
import re

from qiskit import QuantumCircuit, QuantumRegister

GATES_FILE = pathlib.Path(__file__).resolve().parents[3] / "refs" / "paulo" / "spin_network_plaquette3.gates.txt"
SHA256 = "e4b8687f1aa5995fd975770eac0c65c8ec667e71f723fad3b3825190c693a504"   # refs/paulo/SOURCE.md
FILE_ALPHA_P = 0.1
N_FILE_QUBITS = 23
N_ANCILLA = 7

# file qubit -> frame qubit, with the outer register present (ancillas stay at 16..22) and without it (ancillas 8..14)
QUBIT_MAP = {**{q: q for q in range(4)}, **{12 + c: 4 + c for c in range(4)}, **{16 + a: 16 + a for a in range(N_ANCILLA)}}
QUBIT_MAP_OPEN = {**{q: q for q in range(4)}, **{12 + c: 4 + c for c in range(4)}, **{16 + a: 8 + a for a in range(N_ANCILLA)}}

_LINE = re.compile(r"^\s*\d+\s+(\w+)(?:\(([^)]*)\))?\s+(.*)$")
_PHASE = re.compile(r"^#\s*Global phase \(radians\):\s*(\S+)")
_GATES = {"cx": 2, "h": 1, "x": 1, "t": 1, "tdg": 1, "p": 1}


def _read() -> str:
    data = GATES_FILE.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise ValueError(f"{GATES_FILE} has sha256 {digest}, expected {SHA256}")
    return data.decode()


def parse_file() -> list:
    """[(name, qubits, angle | None)] of the gate file, in file order, file qubit numbers."""
    gates = []
    for line in _read().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _LINE.match(line)
        if m is None:
            raise ValueError(f"unparsable gate line: {line!r}")
        name, ang, rest = m.group(1), m.group(2), m.group(3)
        qs = tuple(int(i) for i in re.findall(r"q\[(\d+)\]", rest))
        if name not in _GATES or len(qs) != _GATES[name] or (name == "p") != (ang is not None):
            raise ValueError(f"unsupported gate line: {line!r}")
        gates.append((name, qs, float(ang) if ang is not None else None))
    return gates


def global_phase() -> float:
    for line in _read().splitlines():
        m = _PHASE.match(line)
        if m:
            return float(m.group(1))
    raise ValueError("global phase header not found")


def load_circuit(with_outer: bool = False) -> QuantumCircuit:
    """The file as a QuantumCircuit with registers d[8] (+ o[8]) a[7]; gates exactly as in the file."""
    regs = [QuantumRegister(8, "d")] + ([QuantumRegister(8, "o")] if with_outer else []) + [QuantumRegister(N_ANCILLA, "a")]
    qc = QuantumCircuit(*regs, name="paulo15", global_phase=global_phase())
    qmap = QUBIT_MAP if with_outer else QUBIT_MAP_OPEN
    for name, qs, ang in parse_file():
        wires = [qmap[q] for q in qs]          # KeyError if the file touched q4-11
        if name == "p":
            qc.p(ang, wires[0])
        else:
            getattr(qc, name)(*wires)
    return qc
