"""Paulo's 15-qubit spin-network circuit file refs/paulo/spin_network_plaquette3.gates.txt (step 3.2)."""
from __future__ import annotations

from su2plaq._stub import todo

FILE_ALPHA_P = 0.1


def parse_file() -> list:
    """[(name, qubits, angle | None)] of the gate file."""
    return todo("paulo.parse_file")


def load_circuit(with_outer: bool = False):
    """The file as a QuantumCircuit with registers d[8] (+ o[8]) a[7]."""
    return todo("paulo.load_circuit")
