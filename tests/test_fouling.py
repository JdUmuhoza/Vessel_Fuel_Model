import numpy as np

from vessel_fuel.fouling import fouling_delta_cf


def test_fouling_zero_months():
    assert fouling_delta_cf(0.0, 0.0025) == 0.0


def test_fouling_increases_over_time():
    d1 = fouling_delta_cf(3.0, 0.0025)
    d2 = fouling_delta_cf(18.0, 0.0025)
    assert d2 > d1 > 0.0


def test_array_matches_scalar_loop():
    months = np.array([0.0, 6.0, 12.0])
    arr = fouling_delta_cf(months, 0.0025)
    loop = np.array([fouling_delta_cf(float(m), 0.0025) for m in months])
    assert np.allclose(arr, loop)
