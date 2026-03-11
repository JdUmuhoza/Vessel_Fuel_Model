"""Engine and fuel-consumption utilities."""

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


def sfoc_curve(load_fraction: ArrayLikeFloat, sfoc_at_mcr: float, sfoc_factor: float = 1.0) -> ArrayLikeFloat:
    """Compute load-dependent SFOC using a five-zone profile.

    Zones are [0.10–0.25], [0.25–0.50], [0.50–0.75], [0.75–0.90], [0.90–1.00].

    Parameters
    ----------
    load_fraction : float or numpy.ndarray
        Engine load fraction, :math:`P / MCR`.
    sfoc_at_mcr : float
        Specific fuel oil consumption at MCR (g/kWh).
    sfoc_factor : float, default=1.0
        Calibration multiplier.

    Returns
    -------
    float or numpy.ndarray
        SFOC (g/kWh).

    References
    ----------
    Typical medium-speed marine engine load-dependent SFOC behavior.
    """
    lf, is_scalar = _as_array(load_fraction)
    x = np.clip(lf, 0.0, 1.0)

    xp = np.array([0.10, 0.25, 0.50, 0.75, 0.90, 1.00])
    yp = np.array([1.20, 1.08, 1.00, 0.97, 0.99, 1.02])

    mult = np.interp(np.clip(x, xp[0], xp[-1]), xp, yp)
    mult = np.where(x < 0.10, 1.35 - 0.15 * (x / 0.10), mult)
    sfoc = np.maximum(sfoc_at_mcr, 1e-9) * mult * np.maximum(sfoc_factor, 1e-9)
    return _maybe_scalar(np.asarray(sfoc, dtype=float), is_scalar)


def auxiliary_fuel(aux_power_kw: ArrayLikeFloat, aux_sfoc: float, time_h: ArrayLikeFloat) -> ArrayLikeFloat:
    """Compute auxiliary engine fuel consumption.

    Parameters
    ----------
    aux_power_kw : float or numpy.ndarray
        Auxiliary electrical/mechanical power (kW).
    aux_sfoc : float
        Auxiliary engine SFOC (g/kWh).
    time_h : float or numpy.ndarray
        Operating duration (h).

    Returns
    -------
    float or numpy.ndarray
        Auxiliary fuel in metric tons.

    References
    ----------
    Standard fuel mass relation :math:`m = P\,t\,\mathrm{SFOC}`.
    """
    p, is_scalar = _as_array(aux_power_kw)
    t = np.asarray(time_h, dtype=float)
    fuel_mt = np.maximum(p, 0.0) * np.maximum(t, 0.0) * np.maximum(aux_sfoc, 0.0) / 1e6
    return _maybe_scalar(np.asarray(fuel_mt, dtype=float), is_scalar)


def boiler_fuel(boiler_power_kw: ArrayLikeFloat, boiler_sfoc: float, time_h: ArrayLikeFloat) -> ArrayLikeFloat:
    """Compute boiler fuel consumption.

    Parameters
    ----------
    boiler_power_kw : float or numpy.ndarray
        Boiler thermal equivalent power (kW).
    boiler_sfoc : float
        Boiler specific fuel consumption (g/kWh equivalent).
    time_h : float or numpy.ndarray
        Operating duration (h).

    Returns
    -------
    float or numpy.ndarray
        Boiler fuel in metric tons.

    References
    ----------
    Standard fuel mass relation :math:`m = P\,t\,\mathrm{SFOC}`.
    """
    p, is_scalar = _as_array(boiler_power_kw)
    t = np.asarray(time_h, dtype=float)
    fuel_mt = np.maximum(p, 0.0) * np.maximum(t, 0.0) * np.maximum(boiler_sfoc, 0.0) / 1e6
    return _maybe_scalar(np.asarray(fuel_mt, dtype=float), is_scalar)
