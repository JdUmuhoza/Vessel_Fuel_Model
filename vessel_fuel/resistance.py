"""Resistance sub-models: calm-water, wind, and waves."""

from __future__ import annotations

from typing import Union

import numpy as np

ArrayLikeFloat = Union[float, np.ndarray]


def _as_array(x: ArrayLikeFloat) -> tuple[np.ndarray, bool]:
    arr = np.asarray(x, dtype=float)
    return arr, arr.ndim == 0


def _maybe_scalar(x: np.ndarray, is_scalar: bool) -> ArrayLikeFloat:
    if is_scalar:
        return float(np.asarray(x))
    return x


def holtrop_mennen_resistance(
    V_ms: ArrayLikeFloat,
    L: float,
    B: float,
    T: float,
    Cb: float,
    S: float,
    Cp: float,
    Cm: float,
    Cwp: float,
    lcb_frac: float,
    half_entrance_angle: float,
    transom_area: float,
    bulb_area: float,
    bulb_center: float,
    stern_shape_coeff: float,
    appendage_factor: float,
    rho: ArrayLikeFloat,
    nu: ArrayLikeFloat,
    g: float,
) -> dict[str, ArrayLikeFloat]:
    """Compute calm-water resistance using a Holtrop-Mennen style decomposition.

    Parameters
    ----------
    V_ms : float or numpy.ndarray
        Speed through water (m/s).
    L, B, T : float
        Principal dimensions (m).
    Cb, S, Cp, Cm, Cwp : float
        Hull coefficients and wetted surface.
    lcb_frac : float
        Longitudinal center of buoyancy as fraction of L from midship.
    half_entrance_angle : float
        Half entrance angle (deg).
    transom_area, bulb_area : float
        Transom immersed area and bulbous bow frontal area (m²).
    bulb_center : float
        Vertical bulb center location from baseline (m).
    stern_shape_coeff : float
        Stern shape correction coefficient.
    appendage_factor : float
        Fractional appendage resistance multiplier.
    rho : float or numpy.ndarray
        Water density (kg/m³).
    nu : float or numpy.ndarray
        Kinematic viscosity (m²/s).
    g : float
        Gravity acceleration (m/s²).

    Returns
    -------
    dict
        Keys: ``Rf``, ``Rw``, ``Rapp``, ``Rb``, ``Rtr``, ``Ra``, ``R_total``,
        ``k1``, ``Fn``, ``Cf``.

    References
    ----------
    Holtrop, J. and Mennen, G. G. J. (1982, 1984).
    """
    v, is_scalar = _as_array(V_ms)
    rho_arr = np.asarray(rho, dtype=float)
    nu_arr = np.asarray(nu, dtype=float)

    v2 = v**2
    re = np.where(v > 0.0, v * L / np.maximum(nu_arr, 1e-12), 1.0)
    cf_ittc = np.where(v > 0.0, 0.075 / (np.log10(np.maximum(re, 10.0)) - 2.0) ** 2, 0.0)
    cf = cf_ittc + 4.0e-4

    fn = np.where(L > 0.0, v / np.sqrt(g * L), 0.0)

    k1 = np.clip(
        0.93
        + 0.25 * (Cb - 0.6)
        + 0.15 * (Cp - 0.65)
        + 0.10 * stern_shape_coeff
        + 0.20 * abs(lcb_frac)
        + 0.05 * (Cm - 0.98)
        + 0.03 * (Cwp - 0.80),
        0.70,
        1.80,
    )

    rf = 0.5 * rho_arr * v2 * S * cf
    rapp = np.maximum(appendage_factor, 0.0) * 0.1 * rf

    disp_vol = np.maximum(L * B * T * Cb, 1e-9)
    shape = (1.0 + 0.5 * (half_entrance_angle / 20.0)) * (1.0 + 2.0 * (Cb - 0.6) ** 2) * (1.0 + 0.5 * (B / L))
    rw = 0.5 * rho_arr * g * disp_vol * shape * (fn**4 / (1.0 + fn**2))

    fni = np.where(v > 0.0, v / np.sqrt(g * np.maximum(T - bulb_center, 0.1)), 0.0)
    rb = 0.5 * rho_arr * v2 * np.maximum(bulb_area, 0.0) * 0.20 * np.exp(-((fni - 0.4) / 0.25) ** 2)

    rtr = 0.5 * rho_arr * v2 * np.maximum(transom_area, 0.0) * 0.25 * np.clip(fn / 0.3, 0.0, 1.0)
    ra = 0.5 * rho_arr * v2 * S * 3.5e-4

    r_total = rf * (1.0 + k1) + rapp + rw + rb + rtr + ra

    out = {
        "Rf": rf,
        "Rw": rw,
        "Rapp": rapp,
        "Rb": rb,
        "Rtr": rtr,
        "Ra": ra,
        "R_total": r_total,
        "k1": np.asarray(k1, dtype=float) + np.zeros_like(v),
        "Fn": fn,
        "Cf": cf,
    }
    if is_scalar:
        return {k: _maybe_scalar(np.asarray(vv, dtype=float), True) for k, vv in out.items()}
    return out


def blendermann_wind_resistance(
    V_vessel_ms: ArrayLikeFloat,
    wind_kn: ArrayLikeFloat,
    wind_angle_deg: ArrayLikeFloat,
    A_front: float,
    A_lateral: float,
    Cd_air: float,
    rho_air: float,
) -> ArrayLikeFloat:
    """Estimate aerodynamic resistance using apparent wind.

    Parameters
    ----------
    V_vessel_ms : float or numpy.ndarray
        Vessel speed through water (m/s).
    wind_kn : float or numpy.ndarray
        True wind speed (knots).
    wind_angle_deg : float or numpy.ndarray
        True wind direction relative to bow (deg), 0=head wind.
    A_front, A_lateral : float
        Frontal and lateral projected areas (m²).
    Cd_air : float
        Aerodynamic drag coefficient.
    rho_air : float
        Air density (kg/m³).

    Returns
    -------
    float or numpy.ndarray
        Wind resistance in N.

    References
    ----------
    Blendermann, W. (1994).
    """
    v_ship, is_scalar = _as_array(V_vessel_ms)
    w = np.asarray(wind_kn, dtype=float) * 0.51444
    theta = np.deg2rad(np.asarray(wind_angle_deg, dtype=float))

    v_true_x = -w * np.cos(theta)
    v_true_y = -w * np.sin(theta)

    v_app_x = v_true_x - v_ship
    v_app_y = v_true_y
    v_app = np.sqrt(v_app_x**2 + v_app_y**2)

    beta_app = np.arctan2(np.abs(v_app_y), np.maximum(np.abs(v_app_x), 1e-9))
    a_eq = np.maximum(A_front, 0.0) * np.cos(beta_app) ** 2 + np.maximum(A_lateral, 0.0) * np.sin(beta_app) ** 2

    fx = 0.5 * rho_air * np.maximum(Cd_air, 0.0) * a_eq * v_app * v_app_x
    resistance = np.maximum(-fx, 0.0)
    return _maybe_scalar(np.asarray(resistance, dtype=float), is_scalar)


def stawave1_resistance(
    Hs: ArrayLikeFloat,
    wave_angle_deg: ArrayLikeFloat,
    B: float,
    L: float,
    rho: ArrayLikeFloat,
    g: float,
) -> ArrayLikeFloat:
    """Compute added resistance in waves using an ISO 15016 STAWAVE-1 form.

    Parameters
    ----------
    Hs : float or numpy.ndarray
        Significant wave height (m).
    wave_angle_deg : float or numpy.ndarray
        Wave direction relative to bow (deg), 0=head seas.
    B, L : float
        Beam and length (m).
    rho : float or numpy.ndarray
        Water density (kg/m³).
    g : float
        Gravity acceleration (m/s²).

    Returns
    -------
    float or numpy.ndarray
        Added wave resistance in N.

    References
    ----------
    ISO 15016 STAWAVE-1 guideline.
    """
    hs, is_scalar = _as_array(Hs)
    beta = np.deg2rad(np.asarray(wave_angle_deg, dtype=float))
    rho_arr = np.asarray(rho, dtype=float)

    heading = np.cos(beta) ** 2
    rwave = 0.5 * rho_arr * g * (np.maximum(B, 0.0) ** 2 / np.maximum(L, 1e-6)) * np.maximum(hs, 0.0) ** 2 * heading
    return _maybe_scalar(np.asarray(rwave, dtype=float), is_scalar)


def kwon_resistance(
    V_ms: ArrayLikeFloat,
    Hs: ArrayLikeFloat,
    Tp: ArrayLikeFloat,
    Cb: float,
    L: float,
    B: float,
    T: float,
    displacement: float,
    wave_angle_deg: ArrayLikeFloat,
) -> ArrayLikeFloat:
    """Estimate wave-added resistance from Kwon-style speed-loss relation.

    Parameters
    ----------
    V_ms : float or numpy.ndarray
        Vessel speed through water (m/s).
    Hs : float or numpy.ndarray
        Significant wave height (m).
    Tp : float or numpy.ndarray
        Peak wave period (s).
    Cb, L, B, T : float
        Hull parameters.
    displacement : float
        Displacement volume (m³).
    wave_angle_deg : float or numpy.ndarray
        Wave direction relative to bow (deg), 0=head seas.

    Returns
    -------
    float or numpy.ndarray
        Added wave resistance in N.

    References
    ----------
    Kwon, Y. J. (2008). Speed loss due to added resistance in waves.
    """
    v, is_scalar = _as_array(V_ms)
    hs = np.maximum(np.asarray(Hs, dtype=float), 0.0)
    tp = np.maximum(np.asarray(Tp, dtype=float), 0.0)
    beta = np.deg2rad(np.asarray(wave_angle_deg, dtype=float))

    coeff = 0.015 * (Cb / 0.7) * (np.maximum(L, 1e-6) / 100.0) ** 0.3 * (np.maximum(B, 1e-6) / np.maximum(T, 1e-6)) ** 0.2
    heading = 0.5 * (1.0 + np.cos(beta))
    speed_loss = np.clip(coeff * hs**1.2 * (1.0 + 0.05 * tp) * heading, 0.0, 0.6)

    rho = 1025.0
    scale = np.maximum(displacement, 1e-6) / np.maximum(L * B * T * Cb, 1e-6)
    r_wave = 0.5 * rho * v**2 * np.maximum(L * B, 1e-6) * speed_loss * 0.05 * scale
    r_wave = np.where(v <= 0.0, 0.0, r_wave)
    return _maybe_scalar(np.asarray(r_wave, dtype=float), is_scalar)
