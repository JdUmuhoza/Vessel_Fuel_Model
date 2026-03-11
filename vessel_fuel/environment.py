"""Seawater thermophysical properties."""

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


def sw_density(sst_c: ArrayLikeFloat) -> ArrayLikeFloat:
    """Compute seawater density at 35 PSU using UNESCO 1983 polynomial.

    Parameters
    ----------
    sst_c : float or numpy.ndarray
        Sea surface temperature in °C.

    Returns
    -------
    float or numpy.ndarray
        Seawater density in kg/m³.

    References
    ----------
    UNESCO (1983). Algorithms for computation of fundamental properties of
    seawater.
    """
    t, is_scalar = _as_array(sst_c)
    s = 35.0

    rho_w = (
        999.842594
        + 6.793952e-2 * t
        - 9.095290e-3 * t**2
        + 1.001685e-4 * t**3
        - 1.120083e-6 * t**4
        + 6.536332e-9 * t**5
    )
    a = 0.824493 - 4.0899e-3 * t + 7.6438e-5 * t**2 - 8.2467e-7 * t**3 + 5.3875e-9 * t**4
    b = -5.72466e-3 + 1.0227e-4 * t - 1.6546e-6 * t**2
    c = 4.8314e-4

    rho = rho_w + a * s + b * s ** 1.5 + c * s**2
    return _maybe_scalar(rho, is_scalar)


def sw_viscosity(sst_c: ArrayLikeFloat) -> ArrayLikeFloat:
    """Compute seawater kinematic viscosity at 35 PSU using Sharqawy 2010.

    Parameters
    ----------
    sst_c : float or numpy.ndarray
        Sea surface temperature in °C.

    Returns
    -------
    float or numpy.ndarray
        Seawater kinematic viscosity in m²/s.

    References
    ----------
    Sharqawy, M. H., Lienhard V, J. H., and Zubair, S. M. (2010).
    Thermophysical properties of seawater.
    """
    t, is_scalar = _as_array(sst_c)
    s = 35.0

    mu_w = 4.2844e-5 + 1.0 / (0.157 * (t + 64.993) ** 2 - 91.296)
    a = 1.541 + 1.998e-2 * t - 9.52e-5 * t**2
    b = 7.974 - 7.561e-2 * t + 4.724e-4 * t**2
    mu_sw = mu_w * (1.0 + a * (s * 1e-3) + b * (s * 1e-3) ** 2)

    rho_sw = np.asarray(sw_density(t), dtype=float)
    nu = mu_sw / rho_sw
    return _maybe_scalar(nu, is_scalar)
