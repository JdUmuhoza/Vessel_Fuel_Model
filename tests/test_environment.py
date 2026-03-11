import numpy as np

from vessel_fuel.environment import sw_density, sw_viscosity


def test_density_mid_range():
    rho = sw_density(15.0)
    assert 1020.0 < rho < 1035.0


def test_density_and_viscosity_decrease_with_temperature():
    assert sw_density(25.0) < sw_density(5.0)
    assert sw_viscosity(25.0) < sw_viscosity(5.0)


def test_array_matches_scalar_loop():
    temps = np.array([5.0, 15.0, 25.0])
    arr = sw_density(temps)
    loop = np.array([sw_density(float(t)) for t in temps])
    assert np.allclose(arr, loop)
