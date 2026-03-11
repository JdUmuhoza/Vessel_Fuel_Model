"""Hull fouling model."""

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


def fouling_delta_cf(months_since_cleaning: ArrayLikeFloat, base_cf: ArrayLikeFloat) -> ArrayLikeFloat:
    """Estimate increment in skin friction coefficient due to hull fouling.

    Parameters
    ----------
    months_since_cleaning : float or numpy.ndarray
        Months since last hull cleaning.
    base_cf : float or numpy.ndarray
        Baseline skin-friction coefficient.

    Returns
    -------
    float or numpy.ndarray
        Increment :math:`\Delta C_f` to add to the baseline coefficient.

    References
    ----------
    Schultz, M. P. (2007). Effects of coating roughness and biofouling on
    ship resistance and powering.
    """
    m, is_scalar = _as_array(months_since_cleaning)
    cf = np.asarray(base_cf, dtype=float)

    m = np.maximum(m, 0.0)
    delta = np.where(
        m <= 6.0,
        2.0e-5 * m,
        np.where(m <= 24.0, 1.2e-4 + 1.0e-5 * (m - 6.0), 3.0e-4 + 5.0e-6 * (m - 24.0)),
    )

    scale = np.sqrt(np.clip(cf, 1e-6, None) / 2.5e-3)
    delta_cf = np.minimum(delta * scale, 1.5e-3)
    return _maybe_scalar(np.asarray(delta_cf, dtype=float), is_scalar)
