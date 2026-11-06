"""Gate-set-restricted circuit Builder for the compression loop (prompts/002 §2.10, §5; design B §1.1).

A proposer program is `def build(spec) -> Builder`.  The Builder wraps a Qiskit `QuantumCircuit` but only lets through
BASIS and MACROS gates, allocates clean ancillas (`alloc` / `free`), builds k-control Toffolis from a rccx / ccx ancilla chain
(`mcx`), imports allowed gates from a Qiskit circuit (`append_qiskit`) and carries at most three DISCOVERY lines.  Qubit
conventions: little-endian, fixed qubits first (data, then outer controls), ancillas after; `rz(t) = diag(e^{-it/2}, e^{it/2})`,
`p(l) = diag(1, e^{il})`.  Gates are recognised by class identity (`is_standard_gate`), never by name.
"""
from __future__ import annotations

import hashlib
import math
import numbers
import pathlib
import re

BASIS = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz"}
MACROS = {"ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
# (CX, T_fixed, N_rot) after level-0 lowering (measured, METHODS §7)
MACRO_COST = {"ccx": (6, 7, 0), "rccx": (3, 4, 0), "ccz": (6, 7, 0), "swap": (3, 0, 0), "ch": (1, 2, 0),
              "crz": (2, 0, 2), "crx": (2, 0, 2), "cp": (2, 0, 3), "cz": (1, 0, 0)}
MAX_DISCOVERIES = 3
_ARITY = {"x": 1, "z": 1, "h": 1, "s": 1, "sdg": 1, "t": 1, "tdg": 1, "rz": 1, "p": 1, "cx": 2, "cz": 2, "ccx": 3, "rccx": 3,
          "ccz": 3, "swap": 2, "ch": 2, "crz": 2, "crx": 2, "cp": 2}
_PARAMETRIC = {"rz", "p", "crz", "crx", "cp"}


class BuilderError(Exception):
    pass


class Builder:
    def __init__(self, spec=None, n_qubits: int | None = None):
        """With `spec`: fixed qubits = data + outer controls of the encoding (registers from the encoding).  Bare builder:
        `n_qubits` fixed qubits (tests, library routines)."""
        if spec is not None:
            from su2plaq.compress.spec import get_encoding

            enc = get_encoding(spec.encoding)
            self._registers = {k: list(v) for k, v in enc.registers.items()}
            self._fixed = [("d", enc.n_data), ("o", enc.n_outer)] if enc.n_outer else [("d", enc.n_data)]
            self.n_fixed = enc.n_data + enc.n_outer
            self.spec = spec
        elif n_qubits is not None:
            if n_qubits < 0:
                raise BuilderError("n_qubits must be non-negative")
            self._registers = {}
            self._fixed = [("q", n_qubits)] if n_qubits else []
            self.n_fixed = int(n_qubits)
            self.spec = None
        else:
            raise BuilderError("Builder needs a spec or n_qubits")
        self._ops: list[tuple[str, tuple, tuple]] = []
        self._in_use: set[int] = set()       # allocated ancilla indices currently live
        self._free: list[int] = []           # freed ancilla indices available for reuse
        self._n_anc = 0                      # ancillas ever created (highest index + 1 - n_fixed)
        self.peak_qubits = self.n_fixed
        self.discoveries: list[str] = []
        self._global_phase = 0.0

    # ------------------------------------------------------------------ registers and ancillas
    def reg(self, name) -> list[int]:
        if name not in self._registers:
            raise BuilderError(f"unknown register {name!r}; known: {sorted(self._registers)}")
        return list(self._registers[name])

    def alloc(self, n: int = 1, name=None) -> list[int]:
        """`n` clean ancilla qubits (freed indices are reused, lowest first); `name` is documentation only."""
        if not isinstance(n, int) or n < 1:
            raise BuilderError("alloc needs a positive integer")
        out = []
        for _ in range(n):
            if self._free:
                self._free.sort()
                q = self._free.pop(0)
            else:
                q = self.n_fixed + self._n_anc
                self._n_anc += 1
            self._in_use.add(q)
            out.append(q)
        self.peak_qubits = self.n_fixed + self._n_anc
        return out

    def free(self, qubits):
        """Allocator hint: the qubits are returned to the pool.  Cleanliness (|0> at the end) is checked by the evaluator."""
        for q in ([qubits] if isinstance(qubits, int) else list(qubits)):
            if q not in self._in_use:
                raise BuilderError(f"qubit {q} is not an allocated ancilla")
            self._in_use.discard(q)
            self._free.append(q)

    # ------------------------------------------------------------------ gate emission
    def _check_qubits(self, qs):
        for q in qs:
            if not isinstance(q, numbers.Integral) or isinstance(q, bool) or q < 0:
                raise BuilderError(f"qubit index must be a non-negative int, got {q!r}")
            if q >= self.n_fixed and q not in self._in_use:
                raise BuilderError(f"qubit {q} is not allocated (fixed qubits are 0..{self.n_fixed - 1}; use alloc())")
        if len(set(qs)) != len(qs):
            raise BuilderError(f"gate acts on a repeated qubit: {tuple(qs)}")

    def _emit(self, name, params, qs):
        if name not in BASIS and name not in MACROS:
            raise BuilderError(f"gate {name!r} is not allowed")
        if len(qs) != _ARITY[name] or len(params) != (1 if name in _PARAMETRIC else 0):
            raise BuilderError(f"gate {name!r} takes {_ARITY[name]} qubit(s)"
                               f"{' and one angle' if name in _PARAMETRIC else ''}")
        for th in params:
            if isinstance(th, bool) or not isinstance(th, (int, float)) or not math.isfinite(float(th)):
                raise BuilderError(f"angle must be a finite real number, got {th!r}")
        self._check_qubits(qs)
        self._ops.append((name, tuple(float(x) for x in params), tuple(int(q) for q in qs)))

    def x(self, q): self._emit("x", (), (q,))
    def z(self, q): self._emit("z", (), (q,))
    def h(self, q): self._emit("h", (), (q,))
    def s(self, q): self._emit("s", (), (q,))
    def sdg(self, q): self._emit("sdg", (), (q,))
    def t(self, q): self._emit("t", (), (q,))
    def tdg(self, q): self._emit("tdg", (), (q,))
    def rz(self, theta, q): self._emit("rz", (theta,), (q,))
    def p(self, lam, q): self._emit("p", (lam,), (q,))
    def cx(self, c, t): self._emit("cx", (), (c, t))
    def cz(self, a, b): self._emit("cz", (), (a, b))
    def ccx(self, a, b, t): self._emit("ccx", (), (a, b, t))
    def rccx(self, a, b, t): self._emit("rccx", (), (a, b, t))
    def ccz(self, a, b, t): self._emit("ccz", (), (a, b, t))
    def ch(self, c, t): self._emit("ch", (), (c, t))
    def swap(self, a, b): self._emit("swap", (), (a, b))
    def crz(self, theta, c, t): self._emit("crz", (theta,), (c, t))
    def crx(self, theta, c, t): self._emit("crx", (theta,), (c, t))
    def cp(self, theta, c, t): self._emit("cp", (theta,), (c, t))

    def mcx(self, controls: list[int], target: int):
        """Multi-controlled X.  Up to 2 controls: x / cx / ccx.  k >= 3: (k-2) rccx, ccx, (k-2) rccx on k-2 clean ancillas
        allocated here and freed again (relative phases of the rccx cancel in the mirrored uncompute): 6 + 6(k-2) CX,
        7 + 8(k-2) T.  Never a native mcx."""
        cs = list(controls)
        self._check_qubits(cs + [target])
        k = len(cs)
        if k == 0:
            self.x(target)
        elif k == 1:
            self.cx(cs[0], target)
        elif k == 2:
            self.ccx(cs[0], cs[1], target)
        else:
            a = self.alloc(k - 2, "mcx")
            chain = [(cs[0], cs[1], a[0])] + [(cs[i], a[i - 2], a[i - 1]) for i in range(2, k - 1)]
            for c1, c2, t in chain:
                self.rccx(c1, c2, t)
            self.ccx(cs[k - 1], a[k - 3], target)
            for c1, c2, t in reversed(chain):
                self.rccx(c1, c2, t)
            self.free(a)

    def append_qiskit(self, qc, qubit_map: list[int]):
        """Append a Qiskit circuit; only genuine BASIS / MACROS gate objects (class identity, not names) are accepted, no
        classical bits, no barriers other than real ones (dropped).  Anything else (native mcx >= 3, mcrx, cu, unitary,
        measure, custom gates ...) raises BuilderError and appends nothing."""
        from su2plaq.evaluate.sparse_sim import _is_barrier, is_standard_gate

        qubit_map = list(qubit_map)
        if len(qubit_map) != qc.num_qubits:
            raise BuilderError(f"qubit_map has {len(qubit_map)} entries for a {qc.num_qubits}-qubit circuit")
        pending = []
        for inst in qc.data:
            op = inst.operation
            if _is_barrier(op):
                continue
            if inst.clbits or not is_standard_gate(op) or (op.name not in BASIS and op.name not in MACROS):
                raise BuilderError(f"gate {op.name!r} is not allowed in a Builder program (allowed: {sorted(BASIS | MACROS)})")
            try:
                params = tuple(float(x) for x in op.params)
            except (TypeError, ValueError) as exc:
                raise BuilderError(f"gate {op.name!r} has a non-numeric parameter") from exc
            pending.append((op.name, params, tuple(qubit_map[qc.find_bit(q).index] for q in inst.qubits)))
        # validate everything first (all-or-nothing)
        saved = list(self._ops)
        try:
            for name, params, qs in pending:
                self._emit(name, params, qs)
        except BuilderError:
            self._ops = saved
            raise
        try:
            self._global_phase += float(qc.global_phase)
        except (TypeError, ValueError):
            pass

    def discover(self, line: str):
        """Record a DISCOVERY line (at most 3; the 4th raises)."""
        if len(self.discoveries) >= MAX_DISCOVERIES:
            raise BuilderError(f"at most {MAX_DISCOVERIES} discoveries per program")
        self.discoveries.append(str(line))

    # ------------------------------------------------------------------ result
    def circuit(self):
        """The QuantumCircuit: registers d (+ o) [or q], then one ancilla register `anc` of `peak` qubits."""
        from qiskit import QuantumCircuit, QuantumRegister

        regs = [QuantumRegister(n, nm) for nm, n in self._fixed]
        if self._n_anc:
            regs.append(QuantumRegister(self._n_anc, "anc"))
        qc = QuantumCircuit(*regs, global_phase=self._global_phase)
        for name, params, qs in self._ops:
            getattr(qc, name)(*params, *qs)
        qc.metadata = {"discoveries": list(self.discoveries)}
        return qc

    @property
    def n_gates(self) -> int:
        return len(self._ops)


# ---------------------------------------------------------------------------------------------- program files
def program_sha256(path) -> str:
    """sha256 of a program file; the file is immutable once evaluated (a changed file needs a new NNN)."""
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def parse_program_header(source: str) -> dict:
    """Contract of a program file: the module docstring starts with `SUMMARY: ...` and has at most 3 `DISCOVERY: ...` lines;
    module-level `FAMILY = "..."` and `PARENT = "..." | None`; a `def build(spec)`.  Returns {summary, discoveries, family,
    parent}; raises BuilderError on a contract violation."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise BuilderError(f"program does not parse: {exc}") from exc
    doc = ast.get_docstring(tree)
    if not doc or not doc.lstrip().startswith("SUMMARY:"):
        raise BuilderError("the module docstring must start with 'SUMMARY: ...'")
    lines = doc.strip().splitlines()
    summary = re.sub(r"^SUMMARY:\s*", "", lines[0]).strip()
    discoveries = [ln.strip() for ln in lines[1:] if ln.strip().startswith("DISCOVERY:")]
    if len(discoveries) > MAX_DISCOVERIES:
        raise BuilderError(f"at most {MAX_DISCOVERIES} DISCOVERY lines, found {len(discoveries)}")
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("FAMILY", "PARENT"):
                try:
                    consts[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError as exc:
                    raise BuilderError(f"{node.targets[0].id} must be a literal") from exc
    if not isinstance(consts.get("FAMILY"), str) or not consts["FAMILY"]:
        raise BuilderError("FAMILY = '...' is required")
    if "PARENT" not in consts or not (consts["PARENT"] is None or isinstance(consts["PARENT"], str)):
        raise BuilderError("PARENT = '...' | None is required")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "build" and len(n.args.args) == 1 for n in tree.body):
        raise BuilderError("def build(spec) is required")
    return {"summary": summary, "discoveries": discoveries, "family": consts["FAMILY"], "parent": consts["PARENT"]}
