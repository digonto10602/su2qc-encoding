"""Task specification for the compression loop (prompts/002 §2.10, §5; prompts/003-006).

`TaskSpec.render()` writes the hand-text the proposers see, in the order of Gu et al. (arXiv:2610.22367) Extended Data
Fig. 1: task, registers, circuit model, correctness, cost, proved structure (Lean), tools.  All numbers come from the spec,
the encoding and the builder tables, none are typed in.  `sha256()` hashes the spec's fields only (so a regenerated
structure.json does not change the identity of the task).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from dataclasses import dataclass

from su2plaq.encodings.base import ALT_ANGLES, NOMINAL_ANGLES

ROOT = pathlib.Path(__file__).resolve().parents[3]
STRUCTURE_JSON = ROOT / "compress" / "lean" / "structure.json"
_KINDS = ("step", "UB", "UE")
_ENCODINGS: dict = {}


def get_encoding(name: str):
    """The encoding object for `name`: the `_ENCODINGS` cache (kept, so that a hand-inserted object still works), else the
    registry's cached instance (prompts/008 §3.2); ValueError naming the known encodings otherwise."""
    if name in _ENCODINGS:
        return _ENCODINGS[name]
    from su2plaq.encodings import registry

    return registry.get(name)


def _info(name: str):
    """The registry entry of `name`, or None (hand-made test encodings, encodings still served by a track shim)."""
    from su2plaq.encodings import registry

    return registry.lookup(name)


def _hook(dotted):
    from su2plaq.encodings import registry

    return registry.resolve(dotted)


@dataclass
class TaskSpec:
    encoding: str
    kind: str
    alpha: float
    beta: float
    order: int = 1
    alt_angles: tuple = ALT_ANGLES
    tol_err: float = 1e-10      # combined bound: block error + dropped_total + leak amplitude (prompts/004)
    tol_gauss: float = 1e-10    # Gauss residual of the outputs (prompts/003)
    eps: float = 1e-6
    eval_budget_s: float = 300.0
    support_cap: int = 5_000_000
    max_qubits: int | None = None
    cell_k: int = 8
    trial_inputs: int = 64
    trial_seed: int = 0

    def __post_init__(self):
        if self.kind not in _KINDS:
            raise ValueError(f"kind must be one of {_KINDS}, got {self.kind!r}")
        if self.order not in (1, 2):
            raise ValueError(f"order must be 1 or 2, got {self.order}")
        self.alt_angles = tuple(tuple(float(x) for x in pair) for pair in self.alt_angles)

    # ------------------------------------------------------------------ identity
    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, default=repr).encode()).hexdigest()

    def with_angles(self, alpha: float, beta: float) -> "TaskSpec":
        """Copy with other nominal angles (skeleton checks at the alternate pairs)."""
        return dataclasses.replace(self, alpha=float(alpha), beta=float(beta))

    def peak_qubit_cap(self) -> int:
        enc = get_encoding(self.encoding)
        if self.max_qubits is not None:
            return self.max_qubits
        if hasattr(enc, "peak_qubit_cap"):
            return enc.peak_qubit_cap(self)
        return enc.n_data + enc.n_outer + 32

    # ------------------------------------------------------------------ rendering
    def _operator_text(self) -> str:
        if self.kind == "UE":
            return r"$U=U_E(\alpha)$"
        if self.kind == "UB":
            return r"$U=U_B(\beta)$"
        if self.order == 1:
            return r"$U=U_B(\beta)\,U_E(\alpha)$ (electric layer first in the circuit)"
        return r"$U=U_E(\alpha/2)\,U_B(\beta)\,U_E(\alpha/2)$"

    def _synth_rule_text(self) -> str:
        from su2plaq.evaluate.evaluator import PRUNE_FRACTION, synth_tolerances

        slack = synth_tolerances(0, self.eps)["tol_err"]
        return (f"The circuit you submit is exact-angle; its Clifford+T synthesis (pygridsynth at $\\varepsilon={self.eps:g}$) is "
                f"re-verified separately with both tolerances $N_{{\\rm rot}}\\varepsilon+{slack:g}$ (the triangle inequality over "
                f"the $N_{{\\rm rot}}$ synthesised rotations). The simulator's certified pruning bound (`dropped_total`) must be at "
                f"most {PRUNE_FRACTION:g} times the error tolerance (programs that keep hundreds of tiny amplitudes alive are "
                "rejected as `pruning_bound`).")

    def _structure_file(self) -> pathlib.Path:
        """The facts file of this encoding: `info.structure_json` (relative to the repository root) when registered, else the
        twelve-qubit `STRUCTURE_JSON`."""
        info = _info(self.encoding)
        return ROOT / info.structure_json if info is not None and info.structure_json else STRUCTURE_JSON

    def _structure_section(self) -> str:
        head = "## Proved structure (Lean)\n\n"
        sj = self._structure_file()
        if not sj.exists():
            info = _info(self.encoding)
            shown = info.structure_json if info is not None and info.structure_json else "compress/lean/structure.json"
            return head + f"pending: `{shown}` has not been generated yet.\n"
        facts = json.loads(sj.read_text()).get("facts", [])
        lines = []
        for f in facts:
            if f.get("proved_by") == "numerical":
                continue
            ref = f.get("theorem") or f.get("certificate")
            note = f.get("note")
            lines.append(f"- `{f['name']}` = {f['value']} (proved by {f['proved_by']}{', ' + str(ref) if ref else ''})"
                         + (f" -- {note}" if note else ""))
        body = "\n".join(lines) if lines else "(no machine-proved facts recorded)"
        return head + ("Machine-checked facts about the problem (Lean 4); the numerical evaluator remains ground truth.\n\n"
                       + body + "\n")

    def render(self) -> str:
        """The proposer text: `info.render_spec(self)` when the encoding is registered with one, else the default text."""
        info = _info(self.encoding)
        if info is not None and info.render_spec:
            return _hook(info.render_spec)(self)
        return self._render_default()

    def _tool_commands(self) -> tuple:
        """(candidate command, oracle command) of the tool section: `info.tools` or the stock CLIs."""
        info = _info(self.encoding)
        if info is not None and info.tools:
            return tuple(info.tools)
        return ("python -m su2plaq.compress.run_candidate", "python -m su2plaq.compress.oracle")

    def _render_default(self) -> str:
        from su2plaq.compress.builder import BASIS, MACRO_COST, MACROS

        enc = get_encoding(self.encoding)
        n_phys = len(enc.basis.labels)
        a0, b0 = self.alpha, self.beta
        alts = ", ".join(f"({a:g}, {b:g})" for a, b in self.alt_angles)
        costs = ", ".join(f"{m} ({c[0]}, {c[1]}, {c[2]})" for m, c in MACRO_COST.items() if m in MACROS or m == "cz")
        gates = " ".join(sorted(BASIS))
        macros = " ".join(sorted(MACROS))
        tool = f"--encoding {self.encoding} --kind {self.kind}"
        cand_cmd, oracle_cmd = self._tool_commands()
        return (
            f"# Task specification: `{self.encoding}` / `{self.kind}`\n\n"
            f"## Task\n\nImplement {self._operator_text()} for the SU(2) plaquette at $j_{{\\max}}=\\tfrac12$ in the "
            f"{enc.n_data}-qubit encoding, exactly (up to one global phase) on every one of the {n_phys} physical states, at "
            f"$(\\alpha,\\beta)=({a0:g},{b0:g})$ and, with the same gate skeleton (gate names and qubits; angles may differ), at "
            f"{alts}. Unphysical inputs are don't-care. Every ancilla you allocate must be returned to $|0\\rangle$ on physical "
            "inputs. Angles must be computed from the spec's `alpha`/`beta` (and the oracle), never typed in.\n\n"
            f"## Registers\n\n{enc.describe()}\n"
            f"## Circuit model\n\nGates `{gates}` and macros `{macros}` with costs (CX, T, rotations): {costs}. "
            "`Builder.alloc/free` for clean ancillas; `Builder.mcx` for 3 or more controls (native mcx, mcrx, cu, unitary and "
            f"measurement are rejected); at most {self.peak_qubit_cap()} qubits in total; emission-time classical computation "
            "(including oracle queries) is allowed.\n\n"
            f"## Correctness\n\nThe combined error bound `op_norm_error` = block error + leak amplitude (+ certified simulator "
            f"pruning bound) must be at most {self.tol_err:g} on the physical block after one global phase, and the Gauss residual "
            f"of the outputs at most {self.tol_gauss:g}; the skeleton must be identical at the three angle pairs; evaluation wall "
            f"at most {self.eval_budget_s:g} s and at most {self.support_cap} stored amplitudes. {self._synth_rule_text()} "
            "The evaluator is ground truth.\n\n"
            f"## Cost\n\nKey $(\\mathrm{{CX}},\\,T_{{\\varepsilon}},\\,\\mathrm{{depth}}_{{\\rm CT}},\\,\\mathrm{{qubits}})$, "
            f"lexicographic. $T_\\varepsilon=T_{{\\rm fixed}}+\\sum_r T_r$ with each rotation $T_r$ measured with pygridsynth at "
            f"$\\varepsilon={self.eps:g}$; estimate $3\\log_2(1/\\varepsilon)$ per rotation. MAP-Elites cells "
            f"$(\\lfloor{self.cell_k}\\log_2(\\mathrm{{CX}}+1)\\rfloor,\\lfloor{self.cell_k}\\log_2(T_\\varepsilon+1)\\rfloor)$.\n\n"
            f"{self._structure_section()}\n"
            "## Tools\n\n"
            f"`{cand_cmd} <program.py> {tool} --trial` (seconds; {self.trial_inputs} physical "
            "inputs, nominal angles, T estimate) or `--full`.\n"
            f"`{oracle_cmd} {tool} [--column j] [--element i j] [--codec] [--block o]` prints the exact "
            "target (matrix column, element, codec, outer block); programs may call `su2plaq.compress.oracle` and `numpy`, nothing "
            "else from the project.\n\n"
            "Program contract: write ONE file `compress/programs/<encoding>/<family>/NNN-slug.py` whose docstring starts with "
            "`SUMMARY: ...` followed by at most 3 `DISCOVERY: ...` lines, with `FAMILY = \"...\"`, `PARENT = \"...\" | None` and "
            "`def build(spec) -> Builder`.\n")

    def write(self, path=None) -> pathlib.Path:
        p = pathlib.Path(path) if path is not None else ROOT / "compress" / "specs" / f"{self.encoding}-{self.kind}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.render())
        return p


def default_spec(encoding: str = "twelve", kind: str = "step") -> TaskSpec:
    """Spec at the nominal angles of the encoding (NOMINAL_ANGLES), order 1."""
    if encoding not in NOMINAL_ANGLES:
        raise ValueError(f"unknown encoding {encoding!r}")
    a, b = NOMINAL_ANGLES[encoding]
    return TaskSpec(encoding=encoding, kind=kind, alpha=a, beta=b)
