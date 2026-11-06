"""Cost metrics of a candidate circuit (prompts/002 §2.10; docs/METHODS.md §7)."""
from __future__ import annotations

import math

from su2plaq.compress.synth import cell, gridsynth_T, gridsynth_word, key  # noqa: F401  (key / cell are re-exported: the metrics module is where callers look)
from su2plaq.metrics.cliffordt import synthesize, t_estimate
from su2plaq.metrics.logical import logical_metrics

ESTIMATE_EPS = (1e-6, 1e-10)


def metrics(qc, spec, measured: bool = True) -> dict:
    """{"cx","t_fixed","n_rot","t_eps","t_estimate":{eps: t_fixed + 3 n_rot log2(1/eps)},"synth_error_bound","depth","depth_ct",
    "qubits","gates"} of the level-0 lowering of `qc`.  qubits = qc.num_qubits (data + outer + ancillas), never a Builder
    attribute.  measured=True: t_eps = t_fixed + sum of pygridsynth T over the rotations at spec.eps and depth_ct = depth of
    the synthesised Clifford+T circuit; measured=False: t_eps and depth_ct are the estimate / the lowered depth (trial mode)."""
    lm = logical_metrics(qc)
    n_rot, t_fixed = lm["n_rot"], lm["t_fixed"]
    est = {eps: t_estimate(n_rot, t_fixed, eps) for eps in ESTIMATE_EPS}
    t_meas = None
    if measured:
        t_meas = {eps: t_fixed + sum(gridsynth_T(th, eps) for th in lm["rz_angles"]) for eps in ESTIMATE_EPS}
        t_eps = t_fixed + sum(gridsynth_T(th, spec.eps) for th in lm["rz_angles"])
        synth, _info = synthesize(qc, spec.eps, word_fn=gridsynth_word)
        depth_ct = synth.depth()
    else:
        t_eps = t_estimate(n_rot, t_fixed, spec.eps)
        depth_ct = lm["depth"]
    return {"cx": lm["cx"], "t_fixed": t_fixed, "n_rot": n_rot, "t_eps": t_eps, "t_estimate": est,
            "t_measured": t_meas, "synth_error_bound": n_rot * spec.eps, "depth": lm["depth"], "depth_ct": depth_ct, "qubits": qc.num_qubits,
            "gates": lm["gates"], "measured": bool(measured)}
