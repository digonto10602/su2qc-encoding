"""Unit tests of su2plaq.rishon.compress.three_layer (prompts/204 step C1): constants, det-layer metrics, error paths."""
import numpy as np
import pytest

from su2plaq.rishon.compress import three_layer as TL


def test_constants_and_eta_set():
    assert TL.DET_TRIPLES == ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))
    assert len(TL.ETA_SET) == 20 and all(0.05 <= e <= 1.2 for e in TL.ETA_SET)
    assert np.array_equal(np.array(TL.ETA_SET), np.random.default_rng(20261110).uniform(0.05, 1.2, 20))
    from su2plaq.rishon.compress import robust

    assert robust.ANGLE_SET_SEED == 20261107 and len(robust.ANGLE_SET) == 20     # the (alpha, beta) set is a separate generator


def test_det_layer_metrics_shape():
    m = TL.det_layer_metrics(0.29)
    assert m["cx"] == 32 and m["n_rot"] == 8 and m["t_fixed"] == 0 and m["qubits"] == 48 and m["eta"] == 0.29
    assert tuple(m["key"])[0] == 32 and tuple(m["key"])[3] == 48 and len(m["t_eps_set"]) == 20
    assert m["t_sum"] == sum(m["t_eps_set"]) and abs(m["t_mean"] - m["t_sum"] / 20) <= 1e-12 and m["t_eps"] > 0


def test_verify_three_layer_needs_an_entry(tmp_path):
    with pytest.raises(ValueError):
        TL.verify_three_layer(root=tmp_path)
    with pytest.raises(ValueError):
        TL.verify_three_layer("r99-nope-000", root=tmp_path)
