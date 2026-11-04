"""Clifford+T compilation and synthesis (prompts/002 §2.8). Stubs (step 0.1)."""
from __future__ import annotations

from su2plaq._stub import todo


def ct_compile(qc, eps: float, level: int = 3, seed: int = 12345):
    todo("ct_compile")


def pygridsynth_word(theta: float, eps: float) -> str:
    todo("pygridsynth_word")


def pygridsynth_tcount(theta, eps) -> int:
    todo("pygridsynth_tcount")


def word_error(word, theta) -> float:
    todo("word_error")


def t_estimate(n_rot: int, t_fixed: int, eps: float) -> float:
    todo("t_estimate")


def synthesize(qc, eps: float):
    todo("synthesize")


def t_table(qc, eps_list=(1e-4, 1e-6, 1e-8, 1e-10), qiskit: bool = True) -> list[dict]:
    todo("t_table")
