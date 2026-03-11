import numpy as np

from vessel_fuel.resistance import (
    blendermann_wind_resistance,
    holtrop_mennen_resistance,
    kwon_resistance,
    stawave1_resistance,
)


def _vessel():
    return dict(
        L=120.0,
        B=20.0,
        T=7.0,
        Cb=0.72,
        S=4200.0,
        Cp=0.69,
        Cm=0.98,
        Cwp=0.83,
        lcb_frac=0.01,
        half_entrance_angle=20.0,
        transom_area=8.0,
        bulb_area=4.0,
        bulb_center=2.5,
        stern_shape_coeff=0.1,
        appendage_factor=0.1,
    )


def test_holtrop_normal_input():
    p = _vessel()
    out = holtrop_mennen_resistance(
        V_ms=7.0,
        rho=1025.0,
        nu=1.2e-6,
        g=9.81,
        **p,
    )
    assert out["R_total"] > 0.0
    assert out["Rf"] > 0.0
    assert out["Cf"] > 0.0


def test_holtrop_zero_speed():
    p = _vessel()
    out = holtrop_mennen_resistance(V_ms=0.0, rho=1025.0, nu=1.2e-6, g=9.81, **p)
    assert out["R_total"] == 0.0


def test_wave_and_wind_edge_inputs():
    rw = stawave1_resistance(Hs=0.0, wave_angle_deg=0.0, B=20.0, L=120.0, rho=1025.0, g=9.81)
    aw = blendermann_wind_resistance(7.0, wind_kn=0.0, wind_angle_deg=0.0, A_front=120.0, A_lateral=600.0, Cd_air=1.0, rho_air=1.225)
    kw = kwon_resistance(7.0, Hs=0.0, Tp=8.0, Cb=0.72, L=120.0, B=20.0, T=7.0, displacement=120 * 20 * 7 * 0.72, wave_angle_deg=0.0)
    assert rw == 0.0
    assert aw > 0.0
    assert kw == 0.0


def test_array_matches_scalar_loop():
    p = _vessel()
    speeds = np.array([4.0, 6.0, 8.0])
    arr = holtrop_mennen_resistance(V_ms=speeds, rho=1025.0, nu=1.2e-6, g=9.81, **p)["R_total"]
    loop = np.array([
        holtrop_mennen_resistance(V_ms=float(v), rho=1025.0, nu=1.2e-6, g=9.81, **p)["R_total"]
        for v in speeds
    ])
    assert np.allclose(arr, loop)
