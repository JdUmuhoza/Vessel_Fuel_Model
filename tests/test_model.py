import numpy as np

from vessel_fuel.model import calibrate_model, calibration_report, fuel_components, fuel_model


def _params():
    return {
        "L": 120.0,
        "B": 20.0,
        "T": 7.0,
        "design_draft": 6.5,
        "S": 4200.0,
        "CB": 0.72,
        "MCR": 10000.0,
        "sfoc_at_mcr": 180.0,
        "eta_0": 0.72,
        "eta_wave_loss": 0.03,
        "A_front": 120.0,
        "A_lateral": 700.0,
        "months_since_cleaning": 10.0,
        "trim_m": 0.3,
    }


def _env(wind=12.0, hs=1.5):
    return {
        "wind_kn": wind,
        "wind_angle_deg": 20.0,
        "Hs": hs,
        "Tp": 8.0,
        "wave_angle_deg": 0.0,
        "sst_c": 15.0,
        "depth_m": 50.0,
    }


def test_model_normal_case():
    fuel = fuel_model(120.0, 12.0, _env(), _params())
    assert fuel > 0.0


def test_model_zero_speed_edge():
    fuel = fuel_model(120.0, 0.0, _env(), _params())
    assert fuel == 0.0


def test_model_monotonicity_speed():
    p = _params()
    e = _env()
    f1 = fuel_model(100.0, 8.0, e, p)
    f2 = fuel_model(100.0, 12.0, e, p)
    f3 = fuel_model(100.0, 15.0, e, p)
    assert f1 < f2 < f3


def test_array_matches_scalar_loop():
    p = _params()
    e = _env()
    speeds = np.array([8.0, 10.0, 12.0])
    arr = fuel_model(100.0, speeds, e, p)
    loop = np.array([fuel_model(100.0, float(s), e, p) for s in speeds])
    assert np.allclose(arr, loop)


def test_component_breakdown_sums_to_total():
    components = fuel_components(120.0, 12.0, _env(), _params())
    subtotal = components["main_fuel_mt"] + components["aux_fuel_mt"] + components["boiler_fuel_mt"]
    assert np.isclose(subtotal, components["total_fuel_mt"])
    assert components["calm_water_resistance_n"] > 0.0


def test_adverse_conditions_increase_fuel_use():
    p = _params()
    calm = fuel_model(100.0, 12.0, _env(wind=0.0, hs=0.0), p)
    adverse = fuel_model(100.0, 12.0, _env(wind=22.0, hs=3.0), p)
    assert adverse > calm


def test_slow_steaming_reduces_trip_fuel():
    p = _params()
    env = _env(wind=8.0, hs=0.8)
    slow = fuel_model(100.0, 8.0, env, p)
    service = fuel_model(100.0, 12.0, env, p)
    assert slow < service


def test_fouling_case_increases_fuel_use():
    clean = _params()
    foul = _params()
    clean["months_since_cleaning"] = 0.0
    foul["months_since_cleaning"] = 24.0
    assert fuel_model(100.0, 12.0, _env(), foul) > fuel_model(100.0, 12.0, _env(), clean)


def test_current_and_depth_affect_transit_time_and_fuel():
    p = _params()
    aided = fuel_components(100.0, 12.0, {**_env(), "current_kn": 2.0, "current_angle_deg": 180.0}, p)
    opposed = fuel_components(100.0, 12.0, {**_env(), "current_kn": 2.0, "current_angle_deg": 0.0}, p)
    shallow = fuel_components(100.0, 12.0, {**_env(), "depth_m": 10.0}, p)
    deep = fuel_components(100.0, 12.0, {**_env(), "depth_m": 100.0}, p)
    assert aided["transit_time_h"] < opposed["transit_time_h"]
    assert shallow["calm_water_resistance_n"] > deep["calm_water_resistance_n"]


def test_calibration_converges_with_synthetic_data():
    p = _params()
    true_calib = {"calm_water": 1.15, "wind": 0.90, "waves": 1.20, "sfoc_factor": 1.05, "fouling": 1.10}

    obs = []
    for speed, wind, hs in [(9.0, 8.0, 0.5), (10.5, 12.0, 1.0), (12.0, 15.0, 1.5), (13.0, 18.0, 2.0), (14.0, 10.0, 0.8), (11.0, 14.0, 1.2)]:
        env = _env(wind=wind, hs=hs)
        obs.append(
            {
                "distance_km": 120.0,
                "speed_tw_kn": speed,
                "env": env,
                "fuel_mt": fuel_model(120.0, speed, env, p, true_calib),
            }
        )

    fitted = calibrate_model(obs, p)
    assert abs(fitted["calm_water"] - true_calib["calm_water"]) < 0.3
    assert abs(fitted["wind"] - true_calib["wind"]) < 0.4
    assert abs(fitted["waves"] - true_calib["waves"]) < 0.4
    assert abs(fitted["sfoc_factor"] - true_calib["sfoc_factor"]) < 0.2
    assert abs(fitted["fouling"] - true_calib["fouling"]) < 0.4


def test_calibration_report_metrics_are_small_for_synthetic_truth():
    p = _params()
    calib = {"calm_water": 1.1, "wind": 0.95, "waves": 1.15, "sfoc_factor": 1.02, "fouling": 1.05}
    obs = []
    for speed in [9.0, 10.0, 11.5, 13.0, 14.0]:
        env = _env(wind=10.0 + speed / 2.0, hs=0.5 + speed / 20.0)
        obs.append(
            {
                "distance_km": 120.0,
                "speed_tw_kn": speed,
                "env": env,
                "fuel_mt": fuel_model(120.0, speed, env, p, calib),
            }
        )

    report = calibration_report(obs, p, calib)
    assert report["count"] == 5
    assert report["rmse"] < 1e-8
    assert report["mape_pct"] < 1e-6
