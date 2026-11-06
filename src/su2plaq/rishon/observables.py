"""Shared observables rishon vs Kogut-Susskind (prompts/200 §2.7; METHODS-rishon R5). Stubs (step 5.0); built in 5.3/5.5."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def ks_closed_block(g2: float) -> np.ndarray:
    todo("rishon.observables.ks_closed_block")


def closed_spectra(g2_list=(0.5, 1.0, 2.0)) -> dict:
    todo("rishon.observables.closed_spectra")


def observables(alpha: float, beta: float, n_steps: int = 2, order: int = 1) -> dict:
    todo("rishon.observables.observables")


def closed_forms(alpha, beta) -> dict:
    todo("rishon.observables.closed_forms")


def observables_table(angles=((0.37, 0.61), (0.91, 0.23), (1.70, 1.00))) -> dict:
    todo("rishon.observables.observables_table")
