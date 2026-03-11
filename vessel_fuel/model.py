"""Main vessel fuel model pipeline."""

from __future__ import annotations

from typing import Any, Iterable, Union

import numpy as np
from scipy.optimize import minimize

from .engine import auxiliary_fuel, boiler_fuel, sfoc_curve
from .environment import sw_density, sw_viscosity
from .fouling import fouling_delta_cf
from .resistance import (
    blendermann_wind_resistance,
    holtrop_mennen_resistance,
    kwon_resistance,
    stawave1_resistance,
)

ArrayLikeFloat = Union[float, np.ndarray]

rho_sw_default = 1025.0
rho_air = 1.225
nu_sw_default = 1.19e-6
g = 9.81
kts2ms = 0.51444
nm2km = 1.852


def _arr(x: Any, default: float = 0.0) -> np.ndarray:
    if x is None:
        return np.asarray(default, dtype=float)
    return np.asarray(x, dtype=float)


def _get(params: dict[str, Any], key: str, default: Any) -> Any:
    return params.get(key, default)


def _safe_time_h(distance_km: ArrayLikeFloat, speed_tw_kn: ArrayLikeFloat) -> np.ndarray:
    d = np.asarray(distance_km, dtype=float)
    v = np.asarray(speed_tw_kn, dtype=float)
    return np.where(v > 0.0, d / (v * nm2km), 0.0)


def _maybe_scalar(x: Any, is_scalar: bool) -> Any:
    arr = np.asarray(x, dtype=float)
    return float(arr) if is_scalar and arr.ndim == 0 else arr


def _projected_current_kn(env: dict[str, Any]) -> np.ndarray:
    current_kn = _arr(env.get("current_kn", 0.0))
    current_angle_deg = _arr(env.get("current_angle_deg", 180.0))
    theta = np.deg2rad(current_angle_deg)
    return -current_kn * np.cos(theta)


def _draft_trim_factor(vessel_params: dict[str, Any]) -> float:
    draft = float(_get(vessel_params, "T", 0.0))
    design_draft = float(_get(vessel_params, "design_draft", draft if draft > 0.0 else 1.0))
    trim_m = abs(float(_get(vessel_params, "trim_m", 0.0)))

    draft_term = abs(draft - design_draft) / max(design_draft, 1e-6)
    trim_term = trim_m / max(draft, 1e-6)
    return 1.0 + 0.12 * draft_term + 0.04 * trim_term


def _shallow_water_factor(depth_m: np.ndarray, draft_m: float, speed_ms: np.ndarray) -> np.ndarray:
    depth = np.asarray(depth_m, dtype=float)
    if np.all(depth <= 0.0):
        return np.ones_like(speed_ms, dtype=float)

    valid_depth = np.maximum(depth, draft_m + 1e-6)
    depth_ratio = valid_depth / max(draft_m, 1e-6)
    froude_depth = np.where(valid_depth > 0.0, speed_ms / np.sqrt(g * valid_depth), 0.0)
    penalty = np.where(depth_ratio < 4.0, (4.0 - depth_ratio) / 4.0, 0.0)
    return 1.0 + 0.20 * penalty**2 + 0.35 * np.maximum(froude_depth - 0.5, 0.0) ** 2


def fuel_components(
    distance_km: ArrayLikeFloat,
    speed_tw_kn: ArrayLikeFloat,
    env: dict[str, Any],
    vessel_params: dict[str, Any],
    calib: dict[str, float] | None = None,
) -> dict[str, ArrayLikeFloat]:
    """Compute component-wise resistance, power, and fuel diagnostics.

    Parameters
    ----------
    distance_km : float or numpy.ndarray
        Segment distance (km).
    speed_tw_kn : float or numpy.ndarray
        Speed through water (knots).
    env : dict
        Environmental inputs: ``wind_kn``, ``wind_angle_deg``, ``Hs``, ``Tp``,
        ``current_kn``, ``current_angle_deg``, ``sst_c``, ``depth_m``.
    vessel_params : dict
        Vessel geometry, engine, and operating parameters.
    calib : dict, optional
        Calibration multipliers ``{calm_water, wind, waves, sfoc_factor, fouling}``.

    Returns
    -------
    dict
        Component-level diagnostics including resistance, efficiency, load,
        operating time, and fuel contributions.

    References
    ----------
    Holtrop-Mennen, Blendermann, ISO 15016 STAWAVE-1, Kwon (2008),
    Schultz (2007), UNESCO (1983), Sharqawy (2010).
    """
    calib = calib or {}
    calm_fac = float(calib.get("calm_water", 1.0))
    wind_fac = float(calib.get("wind", 1.0))
    wave_fac = float(calib.get("waves", 1.0))
    sfoc_fac = float(calib.get("sfoc_factor", 1.0))
    foul_fac = float(calib.get("fouling", 1.0))

    speed_kn = np.maximum(np.asarray(speed_tw_kn, dtype=float), 0.0)
    distance = np.maximum(np.asarray(distance_km, dtype=float), 0.0)
    is_scalar = speed_kn.ndim == 0 and distance.ndim == 0
    v_ms = speed_kn * kts2ms

    current_component_kn = _projected_current_kn(env)
    speed_over_ground_kn = np.maximum(speed_kn + current_component_kn, 0.0)
    time_h = _safe_time_h(distance, speed_over_ground_kn)

    sst = env.get("sst_c", None)
    rho = _arr(sw_density(sst), rho_sw_default) if sst is not None else np.asarray(rho_sw_default)
    nu = _arr(sw_viscosity(sst), nu_sw_default) if sst is not None else np.asarray(nu_sw_default)

    L = float(_get(vessel_params, "L", 100.0))
    B = float(_get(vessel_params, "B", 18.0))
    T = float(_get(vessel_params, "T", 6.0))
    S = float(_get(vessel_params, "S", 2.2 * (L * B + L * T)))
    Cb = float(_get(vessel_params, "CB", 0.70))

    Cp = float(_get(vessel_params, "Cp", 0.68))
    Cm = float(_get(vessel_params, "Cm", 0.98))
    Cwp = float(_get(vessel_params, "Cwp", 0.82))
    lcb_frac = float(_get(vessel_params, "lcb_frac", 0.0))
    half_entrance_angle = float(_get(vessel_params, "half_entrance_angle", 20.0))
    transom_area = float(_get(vessel_params, "transom_area", 0.0))
    bulb_area = float(_get(vessel_params, "bulb_area", 0.0))
    bulb_center = float(_get(vessel_params, "bulb_center", T * 0.45))
    stern_shape_coeff = float(_get(vessel_params, "stern_shape_coeff", 0.0))
    appendage_factor = float(_get(vessel_params, "appendage_factor", 0.10))

    A_front = float(_get(vessel_params, "A_front", B * T))
    A_lateral = float(_get(vessel_params, "A_lateral", L * T))
    Cd_air = float(_get(vessel_params, "Cd_air", 1.0))

    res = holtrop_mennen_resistance(
        V_ms=v_ms,
        L=L,
        B=B,
        T=T,
        Cb=Cb,
        S=S,
        Cp=Cp,
        Cm=Cm,
        Cwp=Cwp,
        lcb_frac=lcb_frac,
        half_entrance_angle=half_entrance_angle,
        transom_area=transom_area,
        bulb_area=bulb_area,
        bulb_center=bulb_center,
        stern_shape_coeff=stern_shape_coeff,
        appendage_factor=appendage_factor,
        rho=rho,
        nu=nu,
        g=g,
    )

    wind_kn = _arr(env.get("wind_kn", 0.0))
    wind_angle_deg = _arr(env.get("wind_angle_deg", 0.0))
    r_wind = blendermann_wind_resistance(v_ms, wind_kn, wind_angle_deg, A_front, A_lateral, Cd_air, rho_air)

    hs = _arr(env.get("Hs", 0.0))
    tp = _arr(env.get("Tp", 0.0))
    wave_angle_deg = _arr(env.get("wave_angle_deg", 0.0))
    wave_method = str(env.get("wave_method", "stawave1")).lower()

    displacement = float(_get(vessel_params, "displacement", L * B * T * Cb))
    if wave_method == "kwon":
        r_wave = kwon_resistance(v_ms, hs, tp, Cb, L, B, T, displacement, wave_angle_deg)
    else:
        r_wave = stawave1_resistance(hs, wave_angle_deg, B, L, rho, g)

    months = _arr(_get(vessel_params, "months_since_cleaning", 0.0))
    delta_cf = fouling_delta_cf(months, res["Cf"])
    r_foul = 0.5 * np.asarray(rho) * v_ms**2 * S * delta_cf

    draft_trim_factor = _draft_trim_factor(vessel_params)
    depth_m = _arr(env.get("depth_m", 0.0))
    shallow_water_factor = _shallow_water_factor(depth_m, T, v_ms)

    r_calm = np.asarray(res["R_total"]) * draft_trim_factor * shallow_water_factor
    r_total = calm_fac * r_calm + wind_fac * np.asarray(r_wind) + wave_fac * np.asarray(r_wave) + foul_fac * np.asarray(r_foul)

    eta_0 = float(_get(vessel_params, "eta_0", 0.72))
    eta_wave_loss = float(_get(vessel_params, "eta_wave_loss", 0.03))
    eta_prop = np.clip(eta_0 * (1.0 - eta_wave_loss * hs), 0.20, 1.0)

    p_shaft_kw = np.where(v_ms > 0.0, (r_total * v_ms) / np.maximum(eta_prop, 1e-6) / 1000.0, 0.0)

    mcr = float(_get(vessel_params, "MCR", 10000.0))
    load = np.clip(p_shaft_kw / np.maximum(mcr, 1e-6), 0.0, 1.0)
    sfoc_at_mcr = float(_get(vessel_params, "sfoc_at_mcr", 180.0))
    sfoc = np.asarray(sfoc_curve(load, sfoc_at_mcr, sfoc_factor=sfoc_fac), dtype=float)

    fuel_main_mt = p_shaft_kw * time_h * sfoc / 1e6

    fuel_aux_mt = np.zeros_like(np.asarray(fuel_main_mt, dtype=float))
    if bool(_get(vessel_params, "include_aux", False)):
        fuel_aux_mt = np.asarray(
            auxiliary_fuel(
                _arr(_get(vessel_params, "aux_power_kw", 400.0)),
                float(_get(vessel_params, "aux_sfoc", 205.0)),
                time_h,
            ),
            dtype=float,
        )

    fuel_boiler_mt = np.zeros_like(np.asarray(fuel_main_mt, dtype=float))
    if bool(_get(vessel_params, "include_boiler", False)):
        fuel_boiler_mt = np.asarray(
            boiler_fuel(
                _arr(_get(vessel_params, "boiler_power_kw", 200.0)),
                float(_get(vessel_params, "boiler_sfoc", 280.0)),
                time_h,
            ),
            dtype=float,
        )

    total_fuel_mt = np.maximum(fuel_main_mt + fuel_aux_mt + fuel_boiler_mt, 0.0)

    output = {
        "speed_through_water_kn": speed_kn,
        "speed_over_ground_kn": speed_over_ground_kn,
        "transit_time_h": time_h,
        "calm_water_resistance_n": r_calm,
        "wind_resistance_n": np.asarray(r_wind),
        "wave_resistance_n": np.asarray(r_wave),
        "fouling_resistance_n": np.asarray(r_foul),
        "total_resistance_n": r_total,
        "propulsion_efficiency": eta_prop,
        "shaft_power_kw": p_shaft_kw,
        "load_fraction": load,
        "sfoc_g_per_kwh": sfoc,
        "main_fuel_mt": fuel_main_mt,
        "aux_fuel_mt": fuel_aux_mt,
        "boiler_fuel_mt": fuel_boiler_mt,
        "total_fuel_mt": total_fuel_mt,
        "shallow_water_factor": shallow_water_factor,
        "draft_trim_factor": np.asarray(draft_trim_factor, dtype=float) + np.zeros_like(np.asarray(total_fuel_mt, dtype=float)),
    }
    if is_scalar:
        return {key: _maybe_scalar(value, True) for key, value in output.items()}
    return output


def fuel_model(
    distance_km: ArrayLikeFloat,
    speed_tw_kn: ArrayLikeFloat,
    env: dict[str, Any],
    vessel_params: dict[str, Any],
    calib: dict[str, float] | None = None,
) -> ArrayLikeFloat:
    """Compute voyage segment fuel consumption.

    Parameters
    ----------
    distance_km : float or numpy.ndarray
        Segment distance (km).
    speed_tw_kn : float or numpy.ndarray
        Speed through water (knots).
    env : dict
        Environmental inputs: ``wind_kn``, ``wind_angle_deg``, ``Hs``, ``Tp``,
        ``current_kn``, ``current_angle_deg``, ``sst_c``, ``depth_m``.
    vessel_params : dict
        Vessel geometry, engine, and operating parameters.
    calib : dict, optional
        Calibration multipliers ``{calm_water, wind, waves, sfoc_factor, fouling}``.

    Returns
    -------
    float or numpy.ndarray
        Fuel consumption in metric tons.

    References
    ----------
    Holtrop-Mennen, Blendermann, ISO 15016 STAWAVE-1, Kwon (2008),
    Schultz (2007), UNESCO (1983), Sharqawy (2010).
    """
    components = fuel_components(distance_km, speed_tw_kn, env, vessel_params, calib)
    return components["total_fuel_mt"]


def calibrate_model(
    observations: Iterable[dict[str, Any]],
    vessel_params: dict[str, Any],
    method: str = "L-BFGS-B",
) -> dict[str, float]:
    """Fit calibration multipliers from voyage observations.

    Parameters
    ----------
    observations : iterable of dict
        Each record should include ``distance_km``, ``speed_tw_kn``, ``env``, and
        ``fuel_mt``.
    vessel_params : dict
        Vessel parameters used by :func:`fuel_model`.
    method : str, default="L-BFGS-B"
        SciPy optimization method.

    Returns
    -------
    dict
        Calibration dictionary with keys ``calm_water``, ``wind``, ``waves``,
        ``sfoc_factor``, ``fouling``.

    References
    ----------
    SciPy ``scipy.optimize.minimize``.
    """
    obs = list(observations)
    if len(obs) == 0:
        return {"calm_water": 1.0, "wind": 1.0, "waves": 1.0, "sfoc_factor": 1.0, "fouling": 1.0}

    def objective(x: np.ndarray) -> float:
        calib = {
            "calm_water": float(x[0]),
            "wind": float(x[1]),
            "waves": float(x[2]),
            "sfoc_factor": float(x[3]),
            "fouling": float(x[4]),
        }
        errs = []
        for r in obs:
            pred = fuel_model(r["distance_km"], r["speed_tw_kn"], r["env"], vessel_params, calib)
            errs.append((float(pred) - float(r["fuel_mt"])) ** 2)
        return float(np.mean(errs))

    x0 = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=float)
    bounds = [(0.3, 2.0), (0.1, 3.0), (0.1, 3.0), (0.5, 1.5), (0.1, 3.0)]
    res = minimize(objective, x0=x0, method=method, bounds=bounds)

    x = res.x if res.success else x0
    return {
        "calm_water": float(x[0]),
        "wind": float(x[1]),
        "waves": float(x[2]),
        "sfoc_factor": float(x[3]),
        "fouling": float(x[4]),
    }


def calibration_report(
    observations: Iterable[dict[str, Any]],
    vessel_params: dict[str, Any],
    calib: dict[str, float] | None = None,
) -> dict[str, float | int]:
    """Summarize fit quality for a set of voyage observations.

    Parameters
    ----------
    observations : iterable of dict
        Each record should include ``distance_km``, ``speed_tw_kn``, ``env``, and
        ``fuel_mt``.
    vessel_params : dict
        Vessel parameters used by :func:`fuel_model`.
    calib : dict, optional
        Calibration multipliers. When omitted, identity factors are used.

    Returns
    -------
    dict
        Summary metrics including RMSE, MAE, MAPE, bias, and sample count.

    References
    ----------
    Standard regression error metrics for model evaluation.
    """
    obs = list(observations)
    if len(obs) == 0:
        return {"count": 0, "rmse": 0.0, "mae": 0.0, "mape_pct": 0.0, "bias": 0.0}

    preds = np.array(
        [
            float(fuel_model(record["distance_km"], record["speed_tw_kn"], record["env"], vessel_params, calib))
            for record in obs
        ],
        dtype=float,
    )
    actuals = np.array([float(record["fuel_mt"]) for record in obs], dtype=float)
    errors = preds - actuals
    denom = np.maximum(np.abs(actuals), 1e-9)
    return {
        "count": int(len(obs)),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "mae": float(np.mean(np.abs(errors))),
        "mape_pct": float(np.mean(np.abs(errors) / denom) * 100.0),
        "bias": float(np.mean(errors)),
    }


def validate_model(vessel_params: dict[str, Any], calib: dict[str, float] | None = None) -> dict[str, bool | float]:
    """Run simple diagnostics for model behavior.

    Parameters
    ----------
    vessel_params : dict
        Vessel parameter dictionary.
    calib : dict, optional
        Calibration multipliers.

    Returns
    -------
    dict
        Diagnostic status dictionary with keys ``monotonicity``,
        ``scaling_ratio``, ``sfoc_variation``, and ``overall``.

    References
    ----------
    Internal model QA checks.
    """
    speeds = np.linspace(6.0, 16.0, 6)
    env = {"wind_kn": 10.0, "wind_angle_deg": 20.0, "Hs": 1.5, "Tp": 8.0, "sst_c": 15.0, "wave_angle_deg": 0.0}
    components = fuel_components(100.0, speeds, env, vessel_params, calib)
    fuels = np.asarray(components["total_fuel_mt"], dtype=float)

    monotonicity = bool(np.all(np.diff(fuels) > 0.0))
    f10 = float(fuel_model(100.0, 10.0, env, vessel_params, calib))
    f14 = float(fuel_model(100.0, 14.0, env, vessel_params, calib))
    scaling_ratio = f14 / max(f10, 1e-9)

    loads = np.linspace(0.1, 1.0, 10)
    sfocs = np.asarray(sfoc_curve(loads, float(_get(vessel_params, "sfoc_at_mcr", 180.0))), dtype=float)
    sfoc_variation = float((sfocs.max() - sfocs.min()) / max(sfocs.mean(), 1e-9))
    adverse_to_calm_ratio = float(
        fuel_model(100.0, 12.0, {**env, "wind_kn": 20.0, "Hs": 3.0}, vessel_params, calib)
        / max(float(fuel_model(100.0, 12.0, {**env, "wind_kn": 0.0, "Hs": 0.0}, vessel_params, calib)), 1e-9)
    )

    overall = bool(monotonicity and scaling_ratio > 1.0 and sfoc_variation > 0.01 and adverse_to_calm_ratio > 1.0)

    report = {
        "monotonicity": monotonicity,
        "scaling_ratio": float(scaling_ratio),
        "sfoc_variation": float(sfoc_variation),
        "adverse_to_calm_ratio": float(adverse_to_calm_ratio),
        "overall": overall,
    }

    print("Model validation report")
    print(f"- monotonicity: {report['monotonicity']}")
    print(f"- scaling_ratio: {report['scaling_ratio']:.3f}")
    print(f"- sfoc_variation: {report['sfoc_variation']:.3f}")
    print(f"- adverse_to_calm_ratio: {report['adverse_to_calm_ratio']:.3f}")
    print(f"- overall: {report['overall']}")
    return report
