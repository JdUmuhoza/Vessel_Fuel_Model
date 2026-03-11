import numpy as np

from vessel_fuel.engine import auxiliary_fuel, boiler_fuel, sfoc_curve


def test_sfoc_normal_and_zones():
    sf = sfoc_curve(np.array([0.2, 0.4, 0.6, 0.8, 0.95]), sfoc_at_mcr=180.0)
    assert sf.shape == (5,)
    assert np.all(sf > 0.0)


def test_aux_and_boiler_zero_time():
    assert auxiliary_fuel(500.0, 205.0, 0.0) == 0.0
    assert boiler_fuel(300.0, 280.0, 0.0) == 0.0


def test_array_matches_scalar_loop():
    loads = np.array([0.2, 0.5, 0.8])
    arr = sfoc_curve(loads, 180.0)
    loop = np.array([sfoc_curve(float(l), 180.0) for l in loads])
    assert np.allclose(arr, loop)
