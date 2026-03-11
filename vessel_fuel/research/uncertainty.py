"""Uncertainty quantification and sensitivity ranking."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .metrics import regression_metrics


def conformal_interval(
    y_cal: Sequence[float],
    y_cal_pred: Sequence[float],
    y_pred: Sequence[float],
    alpha: float = 0.1,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute split-conformal prediction intervals.

    Parameters
    ----------
    y_cal : sequence of float
        Calibration observed targets.
    y_cal_pred : sequence of float
        Calibration predictions.
    y_pred : sequence of float
        Point predictions to wrap with intervals.
    alpha : float, default=0.1
        Miscoverage level. Coverage target is approximately $1-\alpha$.

    Returns
    -------
    tuple of numpy.ndarray
        Lower and upper bounds.
    """
    yc = np.asarray(y_cal, dtype=float)
    ycp = np.asarray(y_cal_pred, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    abs_err = np.abs(yc - ycp)
    q = float(np.quantile(abs_err, np.clip(1.0 - alpha, 0.0, 1.0), method="higher"))
    return yp - q, yp + q


def interval_coverage(y_true: Sequence[float], lo: Sequence[float], hi: Sequence[float]) -> float:
    """Compute empirical interval coverage."""
    y = np.asarray(y_true, dtype=float)
    l = np.asarray(lo, dtype=float)
    h = np.asarray(hi, dtype=float)
    return float(np.mean((y >= l) & (y <= h)))


def permutation_sensitivity(
    model_predict_fn,
    x: np.ndarray,
    y_true: Sequence[float],
    feature_names: Sequence[str],
    n_repeats: int = 10,
    seed: int = 42,
) -> list[tuple[str, float]]:
    """Permutation sensitivity ranking using MAE increase.

    Parameters
    ----------
    model_predict_fn : callable
        Function mapping feature matrix to predictions.
    x : numpy.ndarray
        Feature matrix.
    y_true : sequence of float
        Ground truth targets.
    feature_names : sequence of str
        Names aligned with ``x`` columns.

    Returns
    -------
    list of tuple
        Sorted pairs ``(feature_name, delta_mae)`` descending.
    """
    x0 = np.asarray(x, dtype=float)
    y = np.asarray(y_true, dtype=float)
    rng = np.random.default_rng(seed)

    base_pred = np.asarray(model_predict_fn(x0), dtype=float)
    base_mae = regression_metrics(y, base_pred)["mae"]

    scores: list[tuple[str, float]] = []
    for j, name in enumerate(feature_names):
        deltas = []
        for _ in range(n_repeats):
            xp = x0.copy()
            idx = np.arange(len(xp))
            rng.shuffle(idx)
            xp[:, j] = xp[idx, j]
            pred = np.asarray(model_predict_fn(xp), dtype=float)
            mae = regression_metrics(y, pred)["mae"]
            deltas.append(mae - base_mae)
        scores.append((name, float(np.mean(deltas))))

    return sorted(scores, key=lambda t: t[1], reverse=True)
