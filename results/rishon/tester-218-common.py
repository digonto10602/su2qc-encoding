"""Tester 218 common: candidates of round 1 from the archive, circuit building, own AST import scan."""
import ast, hashlib, json, importlib.util, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CANDS = [("r01-F1-001", "F1"), ("r01-F2-001", "F2"), ("r01-F4-001", "F4"), ("r01-F5-001", "F5")]
ALLOWED = {"numpy", "math", "cmath", "itertools", "functools", "collections", "fractions", "typing", "dataclasses", "operator", "heapq",
           "bisect", "qiskit", "__future__"}
ALLOWED_PROJECT = {"su2plaq.compress.oracle", "su2plaq.compress.builder", "su2plaq.compress.spec"}


def load_engine():
    sp = importlib.util.spec_from_file_location("eng217", os.path.join(HERE, "tester-217-engine.py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def entry(cid):
    return json.load(open(os.path.join(ROOT, "compress/archive/rishon/entries", cid + ".json")))


def program_path(cid):
    return os.path.join(ROOT, entry(cid)["program_path"])


def build_circuit(cid, spec):
    from su2plaq.compress import evaluate as LE
    return LE.load_program(program_path(cid)).build(spec).circuit()


def imports_of(path):
    tree = ast.parse(open(path).read())
    mods, names = [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            mods.append(("." * n.level) + (n.module or ""))
            mods += [(n.module or "") + "." + a.name for a in n.names]
        elif isinstance(n, ast.Name) and n.id in {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars"}:
            names.append(n.id)
        elif isinstance(n, ast.Attribute) and n.attr in {"system", "popen", "run", "Popen", "read_text", "write_text", "__dict__", "__class__", "__subclasses__"}:
            names.append("attr:" + n.attr)
    return mods, names
